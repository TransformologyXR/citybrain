#!/usr/bin/env python3
"""Render evidence-inline founder cards as operator-view diagnostic cards."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import importlib.util
import json
import re
import shutil
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-OPERATOR-VIEW-CARD-RENDERING-R1"
PUB = ROOT / "publications" / "epoch4" / "main-citybrain-founder-operator-view-card-rendering-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_FOUNDER_OPERATOR_VIEW_CARD_RENDERING_R1_WITH_LIMITATIONS"
STATUS_NEEDS = "NEEDS_STORY_SOURCE_EXPANSION_MAIN_CITYBRAIN_FOUNDER_OPERATOR_VIEW_CARD_RENDERING_R1_WITH_LIMITATIONS"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_FOUNDER_OPERATOR_VIEW_CARD_RENDERING_R1"

REQUIRED = [
    "FOUNDER_OPERATOR_REVIEW_START_HERE.html",
    "FOUNDER_OPERATOR_REVIEW_START_HERE.md",
    "FOUNDER_OPERATOR_STORY_CARDS_INLINE.html",
    "FOUNDER_OPERATOR_STORY_CARDS_INLINE.md",
    "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json",
    "FOUNDER_OPERATOR_RESPONSE_TEMPLATE.csv",
    "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE.json",
    "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE.json",
    "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT.json",
    "FOUNDER_OPERATOR_RENDERING_GUARD.json",
    "FOUNDER_OPERATOR_AUDIENCE_FIT_REPORT.json",
    "MANAGER_ROLLUP_VIEW_BACKLOG.md",
    "PUBLIC_HUMAN_VIEW_BACKLOG.md",
    "MULTI_AUDIENCE_RENDERING_NOTES.md",
    "SOURCE_DISCOVERY_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

INPUT_ROOTS = {
    "cross_domain": ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1",
    "cross_domain_publication": ROOT / "publications" / "epoch4" / "main-citybrain-cross-domain-story-arc-eval-expansion-r1",
    "concordance": ROOT / "outputs" / "MAIN-CITYBRAIN-STORY-ARC-FOUNDER-DIAGNOSTIC-PREP-CONCORDANCE-R1",
    "concordance_publication": ROOT / "publications" / "epoch4" / "main-citybrain-story-arc-founder-diagnostic-prep-concordance-r1",
    "founder_story_batch": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-READABLE-STORY-BATCH-DISCOVERY-HTML-R1",
    "founder_story_batch_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-readable-story-batch-discovery-html-r1",
    "evidence_inline_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-CARD-EVIDENCE-INLINING-REPAIR-R1",
    "evidence_inline_repair_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-card-evidence-inlining-repair-r1",
    "seed_r3": ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
    "expanded_cadence": ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
    "mobility_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1",
}

FORBIDDEN_PLACEHOLDERS = [
    "supporting source note(s)",
    "source notes available",
    "place context",
    "same site may be related",
    "clearer place label would help",
    "review-only packet appears",
]

TECHNICAL_TERMS = [
    "canonical entity",
    "cer",
    "seg",
    "check",
    "brief",
    "spatial",
    "event fabric",
    "family_id",
    "quarantine",
    "resolved",
    "unresolved",
    "jsonl",
    "truth manifest",
    "native packet",
]

FORBIDDEN_ACTION_INSTRUCTIONS = [
    "dispatch",
    "issue work order",
    "enforce",
    "approve official",
    "reject official",
    "route as official case",
    "alert live operator",
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_evidence_module():
    script = ROOT / "scripts" / "run_main_citybrain_founder_card_evidence_inlining_repair_r1.py"
    spec = importlib.util.spec_from_file_location("evidence_inline_repair", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load evidence-inline repair script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").replace("  ", " ").strip()


def clean_for_main(value: Any) -> str:
    text = str(value or "")
    replacements = [
        (r"\bCER\b", "same-site matching"),
        (r"\bSEG\b", "area link"),
        (r"\bCHECK\b", "evidence review"),
        (r"\bBRIEF/SPATIAL\b", "review summary and map view"),
        (r"\bBRIEF\b", "review summary"),
        (r"\bSPATIAL\b", "map view"),
        (r"Event Fabric", "event history"),
        (r"canonical entity", "same-site record"),
        (r"native packet", "direct evidence packet"),
        (r"truth manifest", "source map"),
        (r"JSONL", "source rows"),
        (r"family_id", "story group"),
        (r"quarantine", "set aside"),
        (r"unresolved", "not decided"),
        (r"resolved", "linked for review"),
    ]
    for old, new in replacements:
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    return text


def technical_hits(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    acronym_terms = {"cer", "seg", "check", "brief", "spatial"}
    for term in TECHNICAL_TERMS:
        if term in acronym_terms:
            if re.search(rf"\b{re.escape(term)}\b", lower):
                hits.append(term)
        elif term in lower:
            hits.append(term)
    return sorted(set(hits))


def source_discovery() -> dict[str, Any]:
    return {
        "artifact_id": "SOURCE_DISCOVERY_REPORT",
        "input_roots": [{"key": key, "path": rel(path), "exists": path.exists()} for key, path in INPUT_ROOTS.items()],
        "preferred_input": rel(INPUT_ROOTS["evidence_inline_repair"]),
        "notes": [
            "Operator cards are rendered from the evidence-inlining repair layer when available.",
            "The render layer does not mutate source truth or create review results.",
        ],
    }


def card_type(source_card: dict[str, Any]) -> str:
    if source_card.get("card_type") == "cross_domain_story_card":
        return "cross_domain_story"
    return "single_family_example"


def first_place(source_card: dict[str, Any]) -> str:
    direct = source_card.get("primary_site_or_place") or source_card.get("place_or_entity")
    if direct:
        return clean_for_main(direct)
    for note in source_card.get("evidence_notes_inline", []):
        place = clean_for_main(note.get("place_or_entity", ""))
        if place:
            return place
    return "UNKNOWN - no place label found."


def district_or_area(source_card: dict[str, Any]) -> str:
    body = json.dumps(source_card).lower()
    if "synthetic-dubai-aoi" in body or "synthetic dubai" in body:
        return "Synthetic Dubai AOI"
    if "primary synthetic site" in body:
        return "Synthetic Dubai AOI"
    return "UNKNOWN - district or area was not present in the source card."


def map_ref(source_card: dict[str, Any]) -> str:
    body = json.dumps(source_card)
    match = re.search(r"geometry:[A-Za-z0-9:_\-]+", body)
    if match:
        return match.group(0)
    return "UNKNOWN - no map or geometry reference was available on the rendered source card."


def confidence(source_card: dict[str, Any]) -> tuple[str, str]:
    notes = source_card.get("evidence_notes_inline", [])
    unknowns = 0
    for note in notes:
        unknowns += sum(str(note.get(field, "")).startswith("UNKNOWN") for field in ["source_class", "freshness", "place_or_entity"])
    if source_card.get("card_type") == "cross_domain_story_card" and len(notes) >= 4:
        return "medium", "multiple signals are visible, but some freshness and nearby-context limits remain."
    if len(notes) >= 2 and unknowns <= 2:
        return "medium", "more than one note is visible and the basic source fields are mostly labelled."
    return "low", "source depth is thin or key fields such as freshness or place are missing."


def suggested_next_step(source_card: dict[str, Any]) -> str:
    title = source_card.get("title", "").lower()
    missing = clean_for_main(source_card.get("one_missing_piece_that_would_change_decision", ""))
    if "permit" in title:
        return "Verify against the permit or inspection source and request a fresher status note."
    if "access" in title or "mobility" in title:
        return "Request a fresh access note and keep it in the watch queue until another source appears."
    if "infrastructure" in title or "asset" in title:
        return "Ask whether the infrastructure signal is at the site or only nearby corridor context."
    if "contradiction" in title:
        return "Ask for a human-readable tie-breaker before spending more review time."
    if "no data" in title:
        return "Dismiss for now unless a concrete source note arrives."
    if "stale" in title:
        return "Request a fresh source pull before treating it as current."
    if missing:
        return missing.rstrip(".") + "."
    return "Keep in the watch queue until another source appears."


def verdict(source_card: dict[str, Any], level: str, reason: str) -> tuple[str, str]:
    suggestion = source_card.get("suggested_initial_call") or "need_more_before_deciding"
    title = source_card.get("title", "this card")
    if suggestion == "watch_this":
        line = f"Verdict: Watch this - {title} has visible evidence, but no cause or action is proven."
    elif suggestion == "ignore_for_now":
        line = f"Verdict: Ignore for now - {title} is too thin for review attention right now."
    else:
        line = f"Verdict: Need more before deciding - {title} has limits that should be checked first."
    if level == "low" and suggestion == "watch_this":
        line = f"Verdict: Need more before deciding - {title} has visible evidence but confidence is low."
        suggestion = "need_more_before_deciding"
    return suggestion, line


def what_where_line(source_card: dict[str, Any], place: str) -> str:
    if source_card.get("card_type") == "cross_domain_story_card":
        return f"What/where: multiple review signals around {place}; nearby infrastructure is context only."
    return f"What/where: {source_card.get('title')} around {place}."


def so_what_line(source_card: dict[str, Any]) -> str:
    if source_card.get("card_type") == "cross_domain_story_card":
        return "So what: if these signals are related, a reviewer may want to watch the site while keeping cause unproven."
    matter = clean_for_main(source_card.get("why_this_might_matter", ""))
    if matter:
        return "So what: " + matter[0].lower() + matter[1:]
    return "So what: this may be worth triage only if the visible evidence is enough to justify review time."


def uncertainty(source_card: dict[str, Any]) -> list[str]:
    rows = []
    for key in ["what_is_uncertain", "source_depth"]:
        if source_card.get(key):
            rows.append(clean_for_main(source_card[key]))
    rows.extend(clean_for_main(item) for item in source_card.get("missing_evidence", []))
    if not rows:
        rows.append("UNKNOWN - the source card did not include a separate uncertainty statement.")
    return rows


def cannot_claim(source_card: dict[str, Any]) -> list[str]:
    rows = [clean_for_main(item) for item in source_card.get("what_citybrain_must_not_claim", [])]
    needed = ["official fact", "causation", "work order", "prediction", "customer readiness"]
    existing = " ".join(rows).lower()
    for item in needed:
        if item not in existing:
            rows.append(f"Not {item}.")
    return rows


def evidence_snapshot(source_card: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = []
    for note in source_card.get("evidence_notes_inline", []):
        source_text = clean_for_main(note.get("note_text", "UNKNOWN - no source note text found."))
        place = clean_for_main(note.get("place_or_entity", "UNKNOWN - no place label found."))
        snapshots.append(
            {
                "source_note_text": source_text,
                "source_class": clean_for_main(note.get("source_class", "UNKNOWN - source class absent.")),
                "timestamp_or_freshness": clean_for_main(note.get("freshness", "UNKNOWN - no usable timestamp found.")),
                "outcome_in_plain_language": clean_for_main(note.get("human_outcome", "Need more before deciding.")),
                "entity_or_place_label": place,
                "what_this_supports": evidence_supports(source_text, place),
                "what_this_does_not_prove": "It does not prove official fact, cause, action authority, prediction, or customer readiness.",
            }
        )
    if not snapshots:
        snapshots.append(
            {
                "source_note_text": "UNKNOWN - no evidence note was found.",
                "source_class": "UNKNOWN - source class absent.",
                "timestamp_or_freshness": "UNKNOWN - no usable timestamp found.",
                "outcome_in_plain_language": "Need more before deciding; no source note is visible.",
                "entity_or_place_label": "UNKNOWN - no place label found.",
                "what_this_supports": "Nothing beyond the need to repair evidence before review.",
                "what_this_does_not_prove": "It does not prove official fact, cause, action authority, prediction, or customer readiness.",
            }
        )
    return snapshots


def evidence_supports(source_text: str, place: str) -> str:
    lower = source_text.lower()
    if "permit" in lower or "inspection" in lower:
        return f"Supports reviewing permit or inspection uncertainty around {place}."
    if "access" in lower or "roadworks" in lower or "transit" in lower:
        return f"Supports watching access or mobility constraints around {place}."
    if "infrastructure" in lower or "asset" in lower:
        return f"Supports corridor-context review around {place}."
    if "contradiction" in lower or "conflict" in lower:
        return f"Supports holding review until the conflict around {place} is explained."
    if "no-data" in lower or "no data" in lower:
        return f"Supports ignoring for now unless better evidence appears for {place}."
    return f"Supports limited review around {place}."


def render_operator_card(source_card: dict[str, Any]) -> dict[str, Any]:
    level, why = confidence(source_card)
    suggestion, verdict_line = verdict(source_card, level, why)
    place_label = first_place(source_card)
    return {
        "card_id": source_card["card_id"].replace("founder-inline", "operator-view"),
        "source_card_id": source_card["card_id"],
        "audience": "operator_view",
        "card_type": card_type(source_card),
        "operator_verdict_suggestion": suggestion,
        "verdict_line": verdict_line,
        "what_where_line": what_where_line(source_card, place_label),
        "so_what_line": so_what_line(source_card),
        "suggested_review_next_step": suggested_next_step(source_card),
        "confidence_plain_english": f"{level} - {why}",
        "place_anchor": {
            "human_label": place_label,
            "district_or_area": district_or_area(source_card),
            "map_or_geometry_ref": map_ref(source_card),
            "missing_reason": "" if not place_label.startswith("UNKNOWN") else place_label,
        },
        "evidence_snapshot": evidence_snapshot(source_card),
        "uncertainty": uncertainty(source_card),
        "cannot_claim": cannot_claim(source_card),
        "decision_question": "Would you watch this, ignore it, or need more before deciding?",
        "decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
        "secondary_ratings": ["usefulness_1_to_5", "readability_1_to_5", "trust_1_to_5"],
        "audience_fit_question": "Which audience is this card actually for? operator / manager / public-human / none-cleanly",
        "boundary": {
            "founder_internal_diagnostic_only": True,
            "operator_fuel": False,
            "training_eligible": False,
            "external_operator_validation": False,
            "product_review_ready": False,
            "client_ready": False,
        },
    }


def build_cards() -> list[dict[str, Any]]:
    evidence_module = load_evidence_module()
    source_cards = evidence_module.build_cards()
    return [render_operator_card(card) for card in source_cards]


def card_body_text(card: dict[str, Any]) -> str:
    return json.dumps(card, ensure_ascii=False)


def main_path_text(out: Path) -> str:
    files = [
        "FOUNDER_OPERATOR_REVIEW_START_HERE.html",
        "FOUNDER_OPERATOR_REVIEW_START_HERE.md",
        "FOUNDER_OPERATOR_STORY_CARDS_INLINE.html",
        "FOUNDER_OPERATOR_STORY_CARDS_INLINE.md",
        "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json",
        "FOUNDER_OPERATOR_RESPONSE_TEMPLATE.csv",
    ]
    return "\n".join((out / name).read_text(encoding="utf-8") for name in files if (out / name).exists())


def coverage(cards: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for card in cards:
        snapshots = card["evidence_snapshot"]
        anchor = card["place_anchor"]
        rows.append(
            {
                "card_id": card["card_id"],
                "has_source_note_text": all(bool(item["source_note_text"]) for item in snapshots),
                "has_source_class": all(bool(item["source_class"]) for item in snapshots),
                "has_freshness_or_timestamp": all(bool(item["timestamp_or_freshness"]) for item in snapshots),
                "has_place_anchor": bool(anchor["human_label"]),
                "has_confidence_plain_english": bool(card["confidence_plain_english"]),
                "has_suggested_review_next_step": bool(card["suggested_review_next_step"]),
                "has_so_what_line": bool(card["so_what_line"]),
                "has_cannot_claim_block": bool(card["cannot_claim"]),
                "has_primary_decision": card["decision_options"] == ["watch_this", "ignore_for_now", "need_more_before_deciding"],
            }
        )
    return {
        "artifact_id": "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE",
        "status": "PASS" if all(all(v for k, v in row.items() if k != "card_id") for row in rows) else "FAIL",
        "card_count": len(cards),
        "rows": rows,
    }


def place_coverage(cards: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for card in cards:
        anchor = card["place_anchor"]
        rows.append(
            {
                "card_id": card["card_id"],
                "human_label": anchor["human_label"],
                "district_or_area": anchor["district_or_area"],
                "map_or_geometry_ref": anchor["map_or_geometry_ref"],
                "missing_reason": anchor["missing_reason"],
                "has_human_label_or_explicit_unknown": bool(anchor["human_label"]),
            }
        )
    return {
        "artifact_id": "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE",
        "status": "PASS" if all(row["has_human_label_or_explicit_unknown"] for row in rows) else "FAIL",
        "rows": rows,
    }


def confidence_report(cards: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    counts = {"low": 0, "medium": 0, "high": 0}
    for card in cards:
        level = card["confidence_plain_english"].split(" - ", 1)[0]
        counts[level] = counts.get(level, 0) + 1
        rows.append({"card_id": card["card_id"], "confidence_plain_english": card["confidence_plain_english"]})
    return {
        "artifact_id": "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT",
        "status": "PASS" if all(row["confidence_plain_english"] for row in rows) else "FAIL",
        "counts": counts,
        "rows": rows,
    }


def rendering_guard(cards: list[dict[str, Any]], status: str, main_hits: list[str], placeholders: list[str]) -> dict[str, Any]:
    action_hits = [term for term in FORBIDDEN_ACTION_INSTRUCTIONS if term in main_path_text(OUT).lower()]
    return {
        "artifact_id": "FOUNDER_OPERATOR_RENDERING_GUARD",
        "status": "PASS" if status == STATUS_PASS and not main_hits and not placeholders and not action_hits else "FAIL",
        "decision_status": status,
        "card_count": len(cards),
        "founder_internal_diagnostic_only": True,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "external_operator_validation_created": False,
        "product_review_ready_claim": False,
        "client_ready_claim": False,
        "official_action_created": False,
        "dispatch_control_enforcement_claim": False,
        "forecast_packet_created": False,
        "source_truth_mutated": False,
        "main_path_uses_operator_view_only": True,
        "manager_view_built": False,
        "public_human_view_built": False,
        "technical_term_hits": main_hits,
        "placeholder_phrase_hits": placeholders,
        "forbidden_action_instruction_hits": action_hits,
    }


def audience_fit_report(cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_id": "FOUNDER_OPERATOR_AUDIENCE_FIT_REPORT",
        "status": "PASS",
        "built_audience": "operator_view",
        "operator_view_card_count": len(cards),
        "manager_rollup_view_built": False,
        "public_human_view_built": False,
        "why_operator_view_now": "The immediate review question is whether a card should be watched, ignored, or held for more evidence.",
        "manager_view_backlog_reason": "Managers need counts, clusters, oldest issue age, risk if ignored, trend over time, and confidence distribution.",
        "public_human_view_backlog_reason": "Public readers need plain meaning, location anchor, what is not confirmed, resident relevance, and zero internal vocabulary.",
    }


def render_start_html(cards: list[dict[str, Any]], status: str) -> str:
    rows = []
    for card in cards:
        rows.append(
            f"<tr><td><a href=\"FOUNDER_OPERATOR_STORY_CARDS_INLINE.html#{html.escape(card['card_id'])}\">{html.escape(card['verdict_line'])}</a></td>"
            f"<td>{html.escape(card['what_where_line'])}</td><td>{html.escape(card['operator_verdict_suggestion'])}</td>"
            f"<td>{html.escape(card['confidence_plain_english'])}</td></tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Operator Review Start Here</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f3f6fa;color:#1f2937;line-height:1.45}}
main{{max-width:1180px;margin:0 auto;padding:28px}}
.hero{{background:#fff;border:1px solid #d8e0ea;border-radius:8px;padding:22px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d8e0ea}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e5ebf2;padding:10px}}
th{{background:#edf2f7}} a{{color:#175cd3;text-decoration:none}}
</style>
</head>
<body><main>
<section class="hero">
<h1>Founder Operator-View Review</h1>
<p>This is founder-internal diagnostic review for operator-style triage only. Decide: watch this, ignore for now, or need more before deciding.</p>
<p>Ratings are secondary. The cards are not product readiness, client readiness, external validation, fuel, or training rows.</p>
<p>Status: <strong>{html.escape(status)}</strong>. Cards: <strong>{len(cards)}</strong>.</p>
</section>
<table>
<thead><tr><th>Verdict first</th><th>What and where</th><th>Suggested decision</th><th>Confidence</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</main></body></html>
"""


def render_start_md(cards: list[dict[str, Any]], status: str) -> str:
    lines = [
        "# Founder Operator-View Review",
        "",
        "This is founder-internal diagnostic review for operator-style triage only.",
        "",
        f"Status: `{status}`",
        f"Cards: `{len(cards)}`",
        "",
    ]
    for card in cards:
        lines.append(f"- {card['verdict_line']} ({card['confidence_plain_english']})")
    return "\n".join(lines)


def render_snapshot_html(snapshot: dict[str, Any]) -> str:
    return f"""
<div class="evidence">
<p><strong>Source note:</strong> {html.escape(snapshot['source_note_text'])}</p>
<dl>
<dt>Source class</dt><dd>{html.escape(snapshot['source_class'])}</dd>
<dt>Freshness</dt><dd>{html.escape(snapshot['timestamp_or_freshness'])}</dd>
<dt>Place/entity</dt><dd>{html.escape(snapshot['entity_or_place_label'])}</dd>
<dt>Outcome</dt><dd>{html.escape(snapshot['outcome_in_plain_language'])}</dd>
<dt>Supports</dt><dd>{html.escape(snapshot['what_this_supports'])}</dd>
<dt>Does not prove</dt><dd>{html.escape(snapshot['what_this_does_not_prove'])}</dd>
</dl>
</div>"""


def render_card_html(card: dict[str, Any]) -> str:
    snapshots = "\n".join(render_snapshot_html(item) for item in card["evidence_snapshot"])
    uncertainty = "".join(f"<li>{html.escape(item)}</li>" for item in card["uncertainty"])
    cannot = "".join(f"<li>{html.escape(item)}</li>" for item in card["cannot_claim"])
    layout_class = "cross" if card["card_type"] == "cross_domain_story" else "single"
    layout_title = "Cross-domain story" if card["card_type"] == "cross_domain_story" else "Single-family example"
    return f"""
<article class="card {layout_class}" id="{html.escape(card['card_id'])}">
<p class="type">{layout_title} - operator view</p>
<h2>{html.escape(card['verdict_line'])}</h2>
<section class="top-decision">
<strong>Your decision:</strong>
<label><input type="checkbox"> Watch this</label>
<label><input type="checkbox"> Ignore for now</label>
<label><input type="checkbox"> Need more before deciding</label>
</section>
<h3>What and where</h3><p>{html.escape(card['what_where_line'])}</p>
<h3>Why this could matter</h3><p>{html.escape(card['so_what_line'])}</p>
<h3>Suggested review next step</h3><p>{html.escape(card['suggested_review_next_step'])}</p>
<h3>Confidence</h3><p>{html.escape(card['confidence_plain_english'])}</p>
<h3>Place anchor</h3>
<p>{html.escape(card['place_anchor']['human_label'])}; area: {html.escape(card['place_anchor']['district_or_area'])}; map ref: {html.escape(card['place_anchor']['map_or_geometry_ref'])}</p>
<h3>Evidence snapshot</h3>{snapshots}
<h3>What CityBrain is unsure about</h3><ul>{uncertainty}</ul>
<h3>What CityBrain will not claim</h3><ul>{cannot}</ul>
<h3>Your decision</h3>
<p>{html.escape(card['decision_question'])}</p>
<label><input type="checkbox"> Watch this</label>
<label><input type="checkbox"> Ignore for now</label>
<label><input type="checkbox"> Need more before deciding</label>
<p class="ratings">Usefulness 1 2 3 4 5 &nbsp; Readability 1 2 3 4 5 &nbsp; Trust 1 2 3 4 5</p>
<p class="audience">{html.escape(card['audience_fit_question'])}</p>
<p class="boundary">Founder-internal diagnostic only. No fuel, training, external validation, product readiness, or customer readiness.</p>
</article>"""


def render_cards_html(cards: list[dict[str, Any]]) -> str:
    body = "\n".join(render_card_html(card) for card in cards)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Operator Story Cards</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f3f6fa;color:#1f2937;line-height:1.45}}
main{{max-width:980px;margin:0 auto;padding:28px}}
.card{{background:#fff;border:1px solid #d8e0ea;border-radius:8px;padding:22px;margin:0 0 18px}}
.cross{{border-left:5px solid #2563eb}} .single{{border-left:5px solid #0f766e}}
.type{{font-size:13px;text-transform:uppercase;color:#526173;margin:0 0 6px}}
h2{{margin:0 0 12px}} h3{{font-size:16px;margin:18px 0 6px}}
.top-decision{{background:#eef6ff;border:1px solid #bfdbfe;border-radius:6px;padding:10px;margin:10px 0}}
label{{display:inline-block;margin:4px 14px 4px 0}}
.evidence{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin:10px 0}}
dl{{display:grid;grid-template-columns:150px 1fr;gap:6px 12px;margin:0}} dt{{font-weight:bold;color:#475569}} dd{{margin:0}}
.ratings,.audience,.boundary{{font-size:14px;color:#526173}}
</style>
</head>
<body><main>
<h1>Founder Operator-View Cards</h1>
{body}
</main></body></html>
"""


def render_cards_md(cards: list[dict[str, Any]]) -> str:
    lines = ["# Founder Operator-View Cards", ""]
    for card in cards:
        lines.extend(
            [
                f"## {card['verdict_line']}",
                "",
                f"Card type: {card['card_type']}",
                "",
                "Your decision:",
                "- [ ] Watch this",
                "- [ ] Ignore for now",
                "- [ ] Need more before deciding",
                "",
                f"What and where: {card['what_where_line']}",
                f"Why this could matter: {card['so_what_line']}",
                f"Suggested review next step: {card['suggested_review_next_step']}",
                f"Confidence: {card['confidence_plain_english']}",
                f"Place anchor: {card['place_anchor']['human_label']}; area: {card['place_anchor']['district_or_area']}; map ref: {card['place_anchor']['map_or_geometry_ref']}",
                "",
                "Evidence snapshot:",
            ]
        )
        for item in card["evidence_snapshot"]:
            lines.extend(
                [
                    f"- Source note: {item['source_note_text']}",
                    f"  - Source class: {item['source_class']}",
                    f"  - Freshness: {item['timestamp_or_freshness']}",
                    f"  - Place/entity: {item['entity_or_place_label']}",
                    f"  - Outcome: {item['outcome_in_plain_language']}",
                    f"  - Supports: {item['what_this_supports']}",
                    f"  - Does not prove: {item['what_this_does_not_prove']}",
                ]
            )
        lines.extend(
            [
                "",
                "What CityBrain is unsure about:",
                *[f"- {item}" for item in card["uncertainty"]],
                "",
                "What CityBrain will not claim:",
                *[f"- {item}" for item in card["cannot_claim"]],
                "",
                "Usefulness: 1 2 3 4 5",
                "Readability: 1 2 3 4 5",
                "Trust: 1 2 3 4 5",
                "",
                "Founder-internal diagnostic only. No fuel, training, external validation, product readiness, or customer readiness.",
                "",
            ]
        )
    return "\n".join(lines)


def render_csv(cards: list[dict[str, Any]]) -> str:
    fields = [
        "card_id",
        "card_type",
        "audience",
        "operator_decision",
        "usefulness_1_to_5",
        "readability_1_to_5",
        "trust_1_to_5",
        "what_would_make_this_confident",
        "is_this_card_for_operator_manager_public_or_none",
        "free_text_notes",
        "founder_internal_diagnostic_only",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "product_review_ready",
        "client_ready",
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for card in cards:
        writer.writerow(
            {
                "card_id": card["card_id"],
                "card_type": card["card_type"],
                "audience": card["audience"],
                "operator_decision": "",
                "usefulness_1_to_5": "",
                "readability_1_to_5": "",
                "trust_1_to_5": "",
                "what_would_make_this_confident": "",
                "is_this_card_for_operator_manager_public_or_none": "",
                "free_text_notes": "",
                "founder_internal_diagnostic_only": "true",
                "operator_fuel": "false",
                "training_eligible": "false",
                "external_operator_validation": "false",
                "product_review_ready": "false",
                "client_ready": "false",
            }
        )
    return output.getvalue()


def manager_backlog() -> str:
    return """# Manager Rollup View Backlog

Not built in this package.

City managers need counts, clusters, patterns, oldest unresolved issue, district/site grouping, risk if ignored, trend over time, and confidence distribution. They do not need one packet at a time as the primary surface.
"""


def public_backlog() -> str:
    return """# Public/Human View Backlog

Not built in this package.

Public or human readers need plain meaning, location anchor, what might be happening, what is not confirmed, why it matters to a resident/person, and zero internal system vocabulary.
"""


def multi_audience_notes() -> str:
    return """# Multi-Audience Rendering Notes

This package builds only `operator_view`.

- Operator view: triage decision, evidence snapshot, next review step, confidence, and boundary.
- Manager rollup view: backlog only; should use counts, clusters, age, trends, risk if ignored, and confidence distribution.
- Public/human view: backlog only; should use plain meaning, a map/location anchor, resident relevance, and no internal vocabulary.
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
    cards = build_cards()
    base_status = STATUS_PASS if len(cards) >= 10 else STATUS_NEEDS

    write_text(out / "FOUNDER_OPERATOR_REVIEW_START_HERE.html", render_start_html(cards, base_status))
    write_text(out / "FOUNDER_OPERATOR_REVIEW_START_HERE.md", render_start_md(cards, base_status))
    write_text(out / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.html", render_cards_html(cards))
    write_text(out / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.md", render_cards_md(cards))
    write_json(out / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json", {"artifact_id": "FOUNDER_OPERATOR_STORY_CARDS_INLINE", "status": base_status, "cards": cards})
    write_text(out / "FOUNDER_OPERATOR_RESPONSE_TEMPLATE.csv", render_csv(cards))
    write_json(out / "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE.json", coverage(cards))
    write_json(out / "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE.json", place_coverage(cards))
    write_json(out / "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT.json", confidence_report(cards))
    write_json(out / "FOUNDER_OPERATOR_AUDIENCE_FIT_REPORT.json", audience_fit_report(cards))
    write_text(out / "MANAGER_ROLLUP_VIEW_BACKLOG.md", manager_backlog())
    write_text(out / "PUBLIC_HUMAN_VIEW_BACKLOG.md", public_backlog())
    write_text(out / "MULTI_AUDIENCE_RENDERING_NOTES.md", multi_audience_notes())
    write_json(out / "SOURCE_DISCOVERY_REPORT.json", source_discovery())

    text = main_path_text(out)
    placeholders = [phrase for phrase in FORBIDDEN_PLACEHOLDERS if phrase in text.lower()]
    tech_hits = technical_hits(text)
    cov = read_json(out / "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE.json")
    place = read_json(out / "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE.json")
    conf = read_json(out / "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT.json")
    status = base_status
    if base_status == STATUS_PASS and (placeholders or tech_hits or cov.get("status") != "PASS" or place.get("status") != "PASS" or conf.get("status") != "PASS"):
        status = STATUS_FAIL
    guard = rendering_guard(cards, status, tech_hits, placeholders)
    write_json(out / "FOUNDER_OPERATOR_RENDERING_GUARD.json", guard)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Founder Operator-View Card Rendering R1

Status: `{status}`

- Operator-view cards: `{len(cards)}`
- Main-path technical term hits: `{tech_hits}`
- Placeholder phrase hits: `{placeholders}`
- Evidence coverage: `{cov.get("status")}`
- Place anchor coverage: `{place.get("status")}`
- Confidence language: `{conf.get("status")}`

Boundaries: founder-internal diagnostic operator-view surface only; no founder session result, fuel, training rows, external validation, product/client readiness, source-truth mutation, ForecastPacket, official action/control/enforcement, manager view build, or public/human view build.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return {"status": status, "card_count": len(cards)}


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

    cards_payload = read_json(out / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json")
    cards = cards_payload.get("cards", [])
    guard = read_json(out / "FOUNDER_OPERATOR_RENDERING_GUARD.json")
    cov = read_json(out / "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE.json")
    place = read_json(out / "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE.json")
    conf = read_json(out / "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT.json")
    audience = read_json(out / "FOUNDER_OPERATOR_AUDIENCE_FIT_REPORT.json")
    csv_rows = list(csv.DictReader(StringIO((out / "FOUNDER_OPERATOR_RESPONSE_TEMPLATE.csv").read_text(encoding="utf-8"))))
    text = main_path_text(out)

    if len(cards) >= 10 and cards_payload.get("status") != STATUS_PASS:
        errors.append("10+ cards did not receive PASS status")
    if len(cards) < 10 and cards_payload.get("status") != STATUS_NEEDS:
        errors.append("fewer than 10 cards without honest needs status")
    if not any(card.get("card_type") == "cross_domain_story" for card in cards):
        errors.append("missing cross-domain story layout")
    if not any(card.get("card_type") == "single_family_example" for card in cards):
        errors.append("missing single-family example layout")
    for card in cards:
        if card.get("audience") != "operator_view":
            errors.append(f"bad audience for {card.get('card_id')}")
        if card.get("decision_options") != ["watch_this", "ignore_for_now", "need_more_before_deciding"]:
            errors.append(f"bad decision options for {card.get('card_id')}")
        if not card.get("suggested_review_next_step"):
            errors.append(f"missing next step for {card.get('card_id')}")
        if not card.get("confidence_plain_english") or " - " not in card.get("confidence_plain_english", ""):
            errors.append(f"missing confidence language for {card.get('card_id')}")
        if not card.get("so_what_line"):
            errors.append(f"missing so-what line for {card.get('card_id')}")
        if not card.get("place_anchor", {}).get("human_label"):
            errors.append(f"missing place anchor for {card.get('card_id')}")
        if not card.get("evidence_snapshot"):
            errors.append(f"missing evidence snapshot for {card.get('card_id')}")
    if text.find("Your decision") > text.find("Usefulness 1 2 3 4 5") and "Your decision" in text:
        errors.append("ratings appear before primary decision")
    placeholder_hits = [phrase for phrase in FORBIDDEN_PLACEHOLDERS if phrase in text.lower()]
    if placeholder_hits:
        errors.append(f"forbidden placeholder phrases present: {placeholder_hits}")
    tech_hits = technical_hits(text)
    if tech_hits:
        errors.append(f"technical terms in main path: {tech_hits}")
    action_hits = [term for term in FORBIDDEN_ACTION_INSTRUCTIONS if term in text.lower()]
    if action_hits:
        errors.append(f"forbidden action instructions present: {action_hits}")
    if cov.get("status") != "PASS" or place.get("status") != "PASS" or conf.get("status") != "PASS":
        errors.append("coverage/place/confidence report did not pass")
    if guard.get("status") != "PASS":
        errors.append("rendering guard did not pass")
    for key, value in {
        "founder_internal_diagnostic_only": True,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "external_operator_validation_created": False,
        "product_review_ready_claim": False,
        "client_ready_claim": False,
        "official_action_created": False,
        "dispatch_control_enforcement_claim": False,
        "forecast_packet_created": False,
        "source_truth_mutated": False,
        "main_path_uses_operator_view_only": True,
        "manager_view_built": False,
        "public_human_view_built": False,
    }.items():
        if guard.get(key) is not value:
            errors.append(f"guard mismatch for {key}")
    if audience.get("built_audience") != "operator_view" or audience.get("manager_rollup_view_built") or audience.get("public_human_view_built"):
        errors.append("audience fit report built the wrong audience")
    required_csv = [
        "card_id",
        "card_type",
        "audience",
        "operator_decision",
        "usefulness_1_to_5",
        "readability_1_to_5",
        "trust_1_to_5",
        "what_would_make_this_confident",
        "is_this_card_for_operator_manager_public_or_none",
        "free_text_notes",
        "founder_internal_diagnostic_only",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "product_review_ready",
        "client_ready",
    ]
    if not csv_rows:
        errors.append("response CSV has no rows")
    elif list(csv_rows[0].keys()) != required_csv:
        errors.append("response CSV columns mismatch")
    for row in csv_rows:
        for key, value in {
            "founder_internal_diagnostic_only": "true",
            "operator_fuel": "false",
            "training_eligible": "false",
            "external_operator_validation": "false",
            "product_review_ready": "false",
            "client_ready": "false",
        }.items():
            if row.get(key) != value:
                errors.append(f"CSV boundary mismatch {key} for {row.get('card_id')}")
    if not all(word in (out / "MANAGER_ROLLUP_VIEW_BACKLOG.md").read_text(encoding="utf-8").lower() for word in ["counts", "clusters", "oldest", "risk", "trend", "confidence distribution"]):
        errors.append("manager backlog missing required concepts")
    if not all(word in (out / "PUBLIC_HUMAN_VIEW_BACKLOG.md").read_text(encoding="utf-8").lower() for word in ["plain meaning", "location anchor", "what is not confirmed", "resident", "zero internal system vocabulary"]):
        errors.append("public backlog missing required concepts")
    if not (PUB / "FOUNDER_OPERATOR_REVIEW_START_HERE.html").exists():
        errors.append("published start HTML missing")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        result = build(args.out)
        print(result["status"])
    errors = validate(args.out)
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
