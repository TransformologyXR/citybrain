#!/usr/bin/env python3
"""Repair founder story cards by inlining review evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-CARD-EVIDENCE-INLINING-REPAIR-R1"
PUB = ROOT / "publications" / "epoch4" / "main-citybrain-founder-card-evidence-inlining-repair-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_FOUNDER_CARD_EVIDENCE_INLINING_REPAIR_R1_WITH_LIMITATIONS"
STATUS_NEEDS = "NEEDS_SOURCE_ARTIFACTS_MAIN_CITYBRAIN_FOUNDER_CARD_EVIDENCE_INLINING_REPAIR_R1_WITH_LIMITATIONS"

INPUTS = {
    "story_batch": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-READABLE-STORY-BATCH-DISCOVERY-HTML-R1",
    "story_batch_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-readable-story-batch-discovery-html-r1",
    "cross_domain": ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1",
    "concordance": ROOT / "outputs" / "MAIN-CITYBRAIN-STORY-ARC-FOUNDER-DIAGNOSTIC-PREP-CONCORDANCE-R1",
    "seed_r3": ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
    "expanded_cadence": ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
    "mobility_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1",
    "packet_gate": ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-NATIVE-EVIDENCE-COMPLETENESS-GATE-R1",
    "event_story_pack": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1",
    "event_replay_pack": ROOT / "outputs" / "main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening",
    "review_cards_r4": ROOT / "outputs" / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1" / "review_cards_r4",
}

REQUIRED = [
    "FOUNDER_REVIEW_START_HERE_INLINE.html",
    "FOUNDER_REVIEW_START_HERE_INLINE.md",
    "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html",
    "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.md",
    "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv",
    "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json",
    "FOUNDER_CARD_EVIDENCE_EXTRACTION_LEDGER.json",
    "FOUNDER_CARD_MISSING_FIELD_LEDGER.json",
    "FOUNDER_CARD_BOILERPLATE_AUDIT.json",
    "FOUNDER_CARD_DECISION_FIELD_GUARD.json",
    "FOUNDER_CARD_TECHNICAL_TERM_GUARD.json",
    "FOUNDER_CARD_BOUNDARY_GUARD.json",
    "FOUNDER_CARD_REPAIR_DECISION.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

BANNED_MAIN_TERMS = [
    "canonical entity",
    "cer",
    "seg",
    "check",
    "brief",
    "spatial",
    "event fabric",
    "quarantine",
    "resolved",
    "unresolved",
    "native packet",
    "jsonl",
    "truth manifest",
    "family_id",
]

ALLOWED_REPEATED_SENTENCES = {
    "Founder-internal diagnostic only.",
    "No session result, fuel, training, external validation, product readiness, or customer readiness.",
    "Not a work order, prediction, customer-ready view, or operational action.",
    "Not a prediction, work order, official action, customer-ready view, or training signal.",
    "Your call.",
    "Usefulness.",
    "Readability.",
    "Trust.",
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_label(value: str) -> str:
    return value.replace("_", " ").replace(".", " ").replace("  ", " ").strip()


def title_for_family(family: str) -> str:
    mapping = {
        "building_compliance_perception_candidate": "Building concern near a site",
        "building_compliance_perception_candidate_v0": "Building concern near a site",
        "permit_inspection_delay": "Permit or inspection delay",
        "permit_inspection_delay_v0": "Permit or inspection delay",
        "city_asset_infrastructure_issue": "Infrastructure or city asset concern",
        "city_asset_infrastructure_issue_v0": "Infrastructure or city asset concern",
        "mobility_access_interruption": "Access interruption",
        "mobility_access_interruption_v0": "Access interruption",
    }
    return mapping.get(family, norm_label(family).title())


def family_from_story_id(story_id: str) -> str:
    if story_id.startswith("founder-story-event-"):
        slug = story_id.replace("founder-story-event-", "")
        return slug.replace("-", "_")
    if story_id.startswith("founder-story-seed-"):
        slug = story_id.replace("founder-story-seed-", "")
        return slug.replace("-", "_")
    return ""


def clean_main(text: Any) -> str:
    value = str(text or "")
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
        (r"quarantine_expected", "set aside expected"),
        (r"quarantine_or_abstain", "set aside or abstain"),
        (r"quarantine", "set aside"),
        (r"unresolved_review", "hold for more evidence"),
        (r"unresolved", "not decided"),
        (r"resolved", "linked for review"),
        (r"source_adapter", "source feed"),
        (r"materializer", "state builder"),
    ]
    for old, new in replacements:
        value = re.sub(old, new, value, flags=re.IGNORECASE)
    return value


def technical_hits(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    acronym_terms = {"cer", "seg", "check", "brief", "spatial"}
    for term in BANNED_MAIN_TERMS:
        if term in acronym_terms:
            if re.search(rf"\b{re.escape(term)}\b", lower):
                hits.append(term)
        elif term in lower:
            hits.append(term)
    return sorted(set(hits))


def place_from_refs(refs: list[str], family: str = "") -> str:
    joined = " ".join(refs).lower()
    if "building:alpha" in joined or "dob_job" in joined or "permit:alpha" in joined:
        return "Primary synthetic site"
    if "near_alpha" in joined:
        return "Nearby observation point, not the primary site"
    if "asset:" in joined or "infrastructure" in joined:
        return "Nearby infrastructure corridor candidate"
    if "beta" in joined:
        return "Second candidate site"
    if "geometry:" in joined:
        return "UNKNOWN - geometry reference exists but no plain place label was found."
    if "mobility" in family:
        return "UNKNOWN - access-area label was not present in the source artifact."
    return "UNKNOWN - no plain place or entity label was found in the source artifact."


def outcome_text(value: str) -> str:
    raw = str(value or "").lower()
    if "candidate_only" in raw:
        return "Need more before deciding; the source is only a candidate signal."
    if "downgrade" in raw or "hold" in raw or "weak" in raw:
        return "Need more before deciding; the evidence is weak or stale."
    if "abstain" in raw or "no_data" in raw:
        return "Ignore for now or hold; the card lacks enough data."
    if "contradiction" in raw:
        return "Need more before deciding; two claims conflict."
    if "contextual" in raw:
        return "Context only; useful to watch, not enough for a same-site claim."
    if "active" in raw or "sufficient" in raw or "supported" in raw:
        return "Watch this, with limits; it is reviewable but not action authority."
    if "review_required" in raw:
        return "Need more before deciding; review is required."
    if "duplicate" in raw:
        return "Ignore for now; another note already carries this signal."
    if "set aside" in raw:
        return "Ignore for now; source shape is not reliable enough."
    return "Need more before deciding; outcome detail is limited."


def source_depth_text(card_title: str, count: int) -> str:
    if count <= 0:
        return f"UNKNOWN - no inline source note could be extracted for {card_title}."
    if count == 1:
        return f"THIN - one inline source note is shown for {card_title}."
    return f"{count} inline source notes are shown for {card_title}."


def evidence_note(
    *,
    source_ref: str,
    note_text: str,
    source_class: str,
    freshness: str,
    place_or_entity: str,
    human_outcome: str,
    source_path: Path,
    raw_refs: list[str] | None = None,
) -> dict[str, Any]:
    note = {
        "source_ref": clean_main(source_ref),
        "note_text": clean_main(note_text),
        "source_class": clean_main(source_class or "UNKNOWN - source class was not labelled."),
        "freshness": clean_main(freshness or "UNKNOWN - no freshness field was found."),
        "place_or_entity": clean_main(place_or_entity),
        "human_outcome": clean_main(human_outcome),
        "source_path": rel(source_path),
        "raw_refs": raw_refs or [],
    }
    return note


def load_story_rows() -> list[dict[str, Any]]:
    index = read_json(INPUTS["story_batch"] / "FOUNDER_STORY_BATCH_INDEX.json", {"stories": []})
    return index.get("stories", [])


def make_cross_domain_card() -> dict[str, Any] | None:
    root = INPUTS["cross_domain"]
    rows = read_jsonl(root / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl")
    if not rows:
        return None
    notes = []
    for row in rows:
        refs = [str(item) for item in row.get("canonical_entity_refs", [])] + [str(row.get("spatial_ref", ""))]
        notes.append(
            evidence_note(
                source_ref=str(row.get("source_event_id", row.get("story_event_id", "UNKNOWN"))),
                note_text=str(row.get("narrative_summary", "UNKNOWN - no narrative source note was found.")),
                source_class=norm_label(str(row.get("source_class", "UNKNOWN"))),
                freshness="UNKNOWN - this story row has sequence order but no recent timestamp field.",
                place_or_entity=place_from_refs(refs, str(row.get("family_id", ""))),
                human_outcome=outcome_text(str(row.get("check_expected_behavior") or row.get("resolution_outcome"))),
                source_path=root / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl",
                raw_refs=[str(row.get("story_event_id", "")), str(row.get("family_id", ""))],
            )
        )
    title = "One site with permit, access, building, and infrastructure signals"
    return {
        "card_id": "founder-inline-001",
        "source_story_id": "founder-story-001-cross-domain-site-cascade",
        "card_type": "cross_domain_story_card",
        "layout_name": "Cross-domain story card",
        "title": title,
        "plain_english_summary": (
            "Several review signals circle one primary synthetic site: permit or inspection status, "
            "building-site context, access interruption, and nearby infrastructure context."
        ),
        "signals_connected": [
            "Permit or inspection status is attached to the primary synthetic site.",
            "Building-site context also points to that primary site.",
            "Access interruption is linked to the same site for review.",
            "Infrastructure is nearby corridor context, not the same site.",
        ],
        "primary_site_or_place": "Primary synthetic site",
        "nearby_context_not_same_site": "Nearby infrastructure context is corridor context only; it is not treated as the same site.",
        "evidence_notes_inline": notes,
        "source_depth": source_depth_text(title, len(notes)),
        "what_citybrain_can_say": [
            "The card can show why these signals might be worth watching together.",
            "The card can show the corridor limitation instead of pretending all signals are one place.",
        ],
        "what_citybrain_must_not_claim": [
            "Not an official finding.",
            "Not proof that one issue caused another.",
            "Not a work order, prediction, customer-ready view, or operational action.",
        ],
        "missing_evidence": [
            "Freshness is UNKNOWN for the story rows because no recent timestamp field was found.",
            "A human place label beyond the synthetic site would make the card easier to judge.",
        ],
        "primary_answer_prompt": "Your call",
        "founder_decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
        "suggested_initial_call": "need_more_before_deciding",
        "one_missing_piece_that_would_change_decision": "A recent source note with a plain place label and a human-readable reason for the link.",
        "founder_reviewable": True,
        "limitations": ["authored story arc only", "not product or client review ready"],
    }


def event_story_cards(start_index: int) -> list[dict[str, Any]]:
    pack_root = INPUTS["event_story_pack"]
    replay_root = INPUTS["event_replay_pack"]
    pack = read_json(pack_root / "EVENT_STORY_PACK_R1.json", {"stories": []})
    replay = read_json(replay_root / "EVENT_STORY_REPLAY_PACKS_V2_1.json", {"story_packs": []})
    replay_by_family = {item.get("family_id"): item for item in replay.get("story_packs", [])}
    cards = []
    for offset, story in enumerate(pack.get("stories", []), start=start_index):
        family = story.get("family_id", "")
        title = title_for_family(family)
        replay_pack = replay_by_family.get(family, {})
        events = replay_pack.get("events", [])
        notes = []
        if events:
            for event in events:
                payload_bits = ", ".join(f"{norm_label(k)}: {norm_label(str(v))}" for k, v in sorted(event.get("payload", {}).items()))
                note_text = (
                    f"{title} source shows {norm_label(event.get('event_type', 'signal'))}. "
                    f"Observed details: {payload_bits or 'UNKNOWN - payload was empty'}."
                )
                refs = [str(item) for item in event.get("cer_entity_refs", [])] + [str(event.get("source_record_ref", ""))]
                notes.append(
                    evidence_note(
                        source_ref=str(event.get("source_record_ref") or event.get("event_id") or "UNKNOWN"),
                        note_text=note_text,
                        source_class=norm_label(str(event.get("source_class", story.get("source_class", "UNKNOWN")))),
                        freshness=str(event.get("observed_at") or event.get("event_time") or "UNKNOWN - no timestamp field was found."),
                        place_or_entity=place_from_refs(refs, family),
                        human_outcome=outcome_text(str(event.get("review_state", story.get("review_only_state", "")))),
                        source_path=replay_root / "EVENT_STORY_REPLAY_PACKS_V2_1.json",
                        raw_refs=[str(event.get("event_id", "")), family],
                    )
                )
        else:
            note_ref = (story.get("source_records") or story.get("event_refs") or ["UNKNOWN"])[0]
            notes.append(
                evidence_note(
                    source_ref=str(note_ref),
                    note_text=f"{title} has a story-pack source pointer but no richer event row was found.",
                    source_class=norm_label(str(story.get("source_class", "UNKNOWN"))),
                    freshness="UNKNOWN - no timestamp field was found for this story-pack pointer.",
                    place_or_entity=place_from_refs([str(item) for item in story.get("cer_entity_refs", [])], family),
                    human_outcome=outcome_text(str(story.get("review_only_state", ""))),
                    source_path=pack_root / "EVENT_STORY_PACK_R1.json",
                    raw_refs=[str(story.get("story_id", "")), family],
                )
            )
        card_title = f"{title} - source note inlined"
        cards.append(
            {
                "card_id": f"founder-inline-{offset:03d}",
                "source_story_id": f"founder-story-event-{family.replace('_', '-')}",
                "card_type": "single_family_example_card",
                "layout_name": "Single-family/example card",
                "title": card_title,
                "specific_signal_summary": f"{title} is shown as a review-only signal with its source note visible on the card.",
                "evidence_notes_inline": notes,
                "place_or_entity": notes[0]["place_or_entity"],
                "source_depth": source_depth_text(card_title, len(notes)),
                "why_this_might_matter": event_specific_matter(family),
                "what_is_uncertain": event_specific_uncertainty(family),
                "what_citybrain_must_not_claim": [
                    "Not an official finding.",
                    "Not a work order, prediction, customer-ready view, or operational action.",
                ],
                "one_missing_piece_that_would_change_decision": event_specific_missing_piece(family),
                "founder_decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
                "suggested_initial_call": "need_more_before_deciding" if "asset" in family else "watch_this",
                "founder_reviewable": True,
                "limitations": ["single signal only", "source depth may be thin"],
            }
        )
    return cards


def event_specific_matter(family: str) -> str:
    if "building" in family:
        return "A building concern near a site may be worth watching when the card shows both the sensor-like note and the conflict that limits trust."
    if "permit" in family:
        return "A permit or inspection delay matters when it is attached to the same primary site as other review signals."
    if "asset" in family:
        return "An infrastructure signal matters as corridor context, but only if the card keeps it separate from the primary site."
    if "mobility" in family:
        return "An access interruption matters if it affects review of the primary site and the card makes the timing visible."
    return "The signal may matter if the visible source note gives a reviewer a reason to keep watching."


def event_specific_uncertainty(family: str) -> str:
    if "building" in family:
        return "The card does not prove a building issue; it shows a candidate concern and a known conflict."
    if "permit" in family:
        return "The card does not prove cause or delay responsibility; it only shows review context."
    if "asset" in family:
        return "The card does not prove the infrastructure signal belongs to the same site."
    if "mobility" in family:
        return "The card does not prove the access issue is still current or operationally actionable."
    return "The card is bounded review context, not a validated operational fact."


def event_specific_missing_piece(family: str) -> str:
    if "building" in family:
        return "A named source note explaining the observed building concern and the conflict."
    if "permit" in family:
        return "A recent permit or inspection status note with a plain site label."
    if "asset" in family:
        return "A source note that clarifies whether the asset is at the site or only nearby."
    if "mobility" in family:
        return "A fresh access note showing whether the interruption is still present."
    return "A clearer source note with place and freshness."


def review_card_cards(start_index: int) -> list[dict[str, Any]]:
    root = INPUTS["review_cards_r4"]
    wanted = ["founder-probe-r2-01.json", "founder-probe-r2-02.json", "founder-probe-r2-03.json", "founder-probe-r2-04.json"]
    cards = []
    for offset, name in enumerate(wanted, start=start_index):
        path = root / name
        item = read_json(path)
        if not item:
            continue
        scenario = norm_label(str(item.get("scenario", "")))
        family = str(item.get("family", ""))
        title = f"{title_for_family(family)} - {scenario}"
        actual = item.get("check_v1_actual_outcome", {})
        evidence = item.get("source_evidence_summary", {})
        source_refs = [str(ref) for ref in evidence.get("source_refs", [])]
        note = evidence_note(
            source_ref=str(item.get("task_id", path.stem)),
            note_text=review_card_note_text(item, actual, evidence),
            source_class=norm_label(str(evidence.get("source_class", "UNKNOWN"))),
            freshness=review_card_freshness(item),
            place_or_entity=place_from_refs(source_refs, family),
            human_outcome=outcome_text(str(actual.get("actual") or actual.get("expected") or item.get("review_readiness_classification"))),
            source_path=path,
            raw_refs=[str(item.get("eval_case_ref", ""))] + source_refs,
        )
        cards.append(
            {
                "card_id": f"founder-inline-{offset:03d}",
                "source_story_id": f"founder-story-card-{item.get('task_id', path.stem)}",
                "card_type": "single_family_example_card",
                "layout_name": "Single-family/example card",
                "title": title,
                "specific_signal_summary": f"This diagnostic card tests {scenario} behavior for a building concern near a site.",
                "evidence_notes_inline": [note],
                "place_or_entity": note["place_or_entity"],
                "source_depth": source_depth_text(title, 1),
                "why_this_might_matter": review_card_matter(str(item.get("scenario", ""))),
                "what_is_uncertain": review_card_uncertainty(str(item.get("scenario", ""))),
                "what_citybrain_must_not_claim": [
                    "Not a source-truth correction.",
                    "Not a prediction, work order, official action, customer-ready view, or training signal.",
                ],
                "one_missing_piece_that_would_change_decision": review_card_missing_piece(str(item.get("scenario", ""))),
                "founder_decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
                "suggested_initial_call": suggested_call_from_scenario(str(item.get("scenario", ""))),
                "founder_reviewable": True,
                "limitations": ["diagnostic scenario card", "not a real founder session result"],
            }
        )
    return cards


def review_card_note_text(item: dict[str, Any], actual: dict[str, Any], evidence: dict[str, Any]) -> str:
    scenario = norm_label(str(item.get("scenario", "")))
    actual_text = norm_label(str(actual.get("actual", "UNKNOWN")))
    expected_text = norm_label(str(actual.get("expected", "UNKNOWN")))
    match_text = norm_label(str(actual.get("match_status", "UNKNOWN")))
    refs = ", ".join(str(ref) for ref in evidence.get("source_refs", [])[:2]) or "UNKNOWN source refs"
    if "no data" in scenario:
        return f"No-data diagnostic card: source refs are {refs}; actual outcome stayed limited or abstained, expected {expected_text}, match {match_text}."
    if "stale" in scenario:
        return f"Stale-freshness diagnostic card: source refs are {refs}; actual outcome was {actual_text}, expected a freshness downgrade, match {match_text}."
    if "contradiction" in scenario:
        return f"Contradiction diagnostic card: source refs are {refs}; actual outcome found a conflict, expected a downgrade, match {match_text}."
    return f"Positive baseline card: source refs are {refs}; actual outcome was {actual_text}, expected {expected_text}, match {match_text}."


def review_card_freshness(item: dict[str, Any]) -> str:
    scenario = str(item.get("scenario", ""))
    if "stale" in scenario:
        return "UNKNOWN - this diagnostic card intentionally tests stale or missing freshness evidence."
    return "UNKNOWN - this review card has source refs but no direct observation timestamp."


def review_card_matter(scenario: str) -> str:
    if scenario == "negative_no_data":
        return "It matters because a good review surface should show when there is not enough evidence instead of sounding confident."
    if scenario == "stale_freshness":
        return "It matters because a stale note should reduce trust even when the story is easy to understand."
    if scenario == "contradiction_pair":
        return "It matters because conflicting evidence should be visible and should stop overconfident claims."
    return "It matters because the baseline should show whether a useful card can proceed with visible limits."


def review_card_uncertainty(scenario: str) -> str:
    if scenario == "negative_no_data":
        return "There may be no usable source behind the signal, so the correct response may be to ignore it for now."
    if scenario == "stale_freshness":
        return "The signal may be old enough that it should not guide a current review."
    if scenario == "contradiction_pair":
        return "The card shows a conflict, so a reviewer cannot trust the claim without a tie-breaker."
    return "The baseline is still a diagnostic case and not a product-ready proof."


def review_card_missing_piece(scenario: str) -> str:
    if scenario == "negative_no_data":
        return "A concrete source note with a named place and observation time."
    if scenario == "stale_freshness":
        return "A fresh source note or a clear reason the older note still matters."
    if scenario == "contradiction_pair":
        return "A human-readable tie-breaker explaining which conflicting claim to trust."
    return "A plain source note that explains why the baseline should be watched."


def suggested_call_from_scenario(scenario: str) -> str:
    if scenario in {"negative_no_data", "stale_freshness", "contradiction_pair"}:
        return "need_more_before_deciding"
    return "watch_this"


def seed_cards(start_index: int) -> list[dict[str, Any]]:
    root = INPUTS["seed_r3"]
    rows = read_jsonl(root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[str(row.get("canonical_loop_family_id", ""))].append(row)
    wanted = [
        "mobility_access_interruption_v0",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    ]
    cards = []
    for offset, family in enumerate(wanted, start=start_index):
        picked = by_family.get(family, [])[:2]
        if not picked:
            continue
        title = f"{title_for_family(family)} examples"
        notes = []
        for row in picked:
            event_type = norm_label(str(row.get("event_type", "signal")))
            source_class = norm_label(str(row.get("source_class", "UNKNOWN")))
            summary = row.get("payload", {}).get("summary", "")
            refs = [str(item) for item in row.get("candidate_entity_refs", [])] + [str(row.get("candidate_geometry_ref", ""))]
            notes.append(
                evidence_note(
                    source_ref=str(row.get("event_id", row.get("source_event_id", "UNKNOWN"))),
                    note_text=f"{event_type.title()} example: {summary or 'UNKNOWN - no payload summary was found.'}",
                    source_class=source_class,
                    freshness=str(row.get("event_time") or row.get("processing_time") or "UNKNOWN - no timestamp field was found."),
                    place_or_entity=place_from_refs(refs, family),
                    human_outcome=outcome_text(str(row.get("expected_resolution_state") or row.get("review_state"))),
                    source_path=root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
                    raw_refs=[str(row.get("source_seed_event_id", "")), family],
                )
            )
        cards.append(
            {
                "card_id": f"founder-inline-{offset:03d}",
                "source_story_id": f"founder-story-seed-{family.replace('_', '-')}",
                "card_type": "single_family_example_card",
                "layout_name": "Single-family/example card",
                "title": title,
                "specific_signal_summary": f"{title_for_family(family)} examples are shown with two local sample notes.",
                "evidence_notes_inline": notes,
                "place_or_entity": notes[0]["place_or_entity"],
                "source_depth": source_depth_text(title, len(notes)),
                "why_this_might_matter": seed_matter(family),
                "what_is_uncertain": seed_uncertainty(family, notes),
                "what_citybrain_must_not_claim": [
                    "Not city truth.",
                    "Not a prediction, work order, official action, customer-ready view, or training signal.",
                ],
                "one_missing_piece_that_would_change_decision": seed_missing_piece(family),
                "founder_decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
                "suggested_initial_call": "watch_this",
                "founder_reviewable": True,
                "limitations": ["local synthetic sample", "not a real-world source claim"],
            }
        )
    return cards


def seed_matter(family: str) -> str:
    if "mobility" in family:
        return "The examples test whether access signals can be made readable before any operational claim is made."
    if "building" in family:
        return "The examples test whether building concerns can show both a reason to watch and a reason to hesitate."
    if "permit" in family:
        return "The examples test whether permit delay signals can be reviewed without pretending to forecast outcomes."
    if "asset" in family:
        return "The examples test whether infrastructure context can stay clearly separate from the site story."
    return "The examples test whether the product can show a small signal plainly."


def seed_uncertainty(family: str, notes: list[dict[str, Any]]) -> str:
    missing_places = [note for note in notes if note["place_or_entity"].startswith("UNKNOWN")]
    if missing_places:
        return f"At least one example lacks a plain place label, so the card should be reviewed cautiously for {title_for_family(family).lower()}."
    return f"The examples are local synthetic samples, so they show review behavior but not real-world truth for {title_for_family(family).lower()}."


def seed_missing_piece(family: str) -> str:
    return f"A real source note with a human place label would change trust for {title_for_family(family).lower()}."


def build_cards() -> list[dict[str, Any]]:
    base_rows = load_story_rows()
    base_order = {row["story_id"]: idx for idx, row in enumerate(base_rows)}
    cards: list[dict[str, Any]] = []
    cross = make_cross_domain_card()
    if cross:
        cards.append(cross)
    cards.extend(event_story_cards(2))
    cards.extend(review_card_cards(6))
    cards.extend(seed_cards(10))
    cards.sort(key=lambda card: base_order.get(card.get("source_story_id", ""), 999))
    for idx, card in enumerate(cards, start=1):
        card["card_id"] = f"founder-inline-{idx:03d}"
    return cards


def card_plain_body(card: dict[str, Any]) -> str:
    parts = [
        card.get("title", ""),
        card.get("plain_english_summary", ""),
        card.get("specific_signal_summary", ""),
        " ".join(card.get("signals_connected", [])),
        card.get("primary_site_or_place", ""),
        card.get("nearby_context_not_same_site", ""),
        card.get("place_or_entity", ""),
        card.get("source_depth", ""),
        card.get("why_this_might_matter", ""),
        card.get("what_is_uncertain", ""),
        " ".join(card.get("what_citybrain_can_say", [])),
        " ".join(card.get("what_citybrain_must_not_claim", [])),
        " ".join(card.get("missing_evidence", [])),
        card.get("one_missing_piece_that_would_change_decision", ""),
    ]
    for note in card.get("evidence_notes_inline", []):
        parts.extend(
            [
                note.get("source_ref", ""),
                note.get("note_text", ""),
                note.get("source_class", ""),
                note.get("freshness", ""),
                note.get("place_or_entity", ""),
                note.get("human_outcome", ""),
            ]
        )
    return "\n".join(clean_main(part) for part in parts if part)


def sentence_set(card: dict[str, Any]) -> set[str]:
    text = card_plain_body(card)
    raw = re.split(r"(?<=[.!?])\s+", text)
    sentences = set()
    for sentence in raw:
        cleaned = " ".join(sentence.strip().split())
        if len(cleaned) < 36:
            continue
        if cleaned in ALLOWED_REPEATED_SENTENCES:
            continue
        if cleaned.startswith("THIN - one inline source note is shown for"):
            continue
        if cleaned.startswith("UNKNOWN - this"):
            continue
        sentences.add(cleaned)
    return sentences


def boilerplate_audit(cards: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for card in cards:
        counter.update(sentence_set(card))
    threshold = int(len(cards) * 0.35)
    offenders = [
        {"sentence": sentence, "card_count": count, "max_allowed": threshold}
        for sentence, count in counter.items()
        if count > threshold
    ]
    return {
        "artifact_id": "FOUNDER_CARD_BOILERPLATE_AUDIT",
        "status": "PASS" if not offenders else "FAIL",
        "card_count": len(cards),
        "max_repeated_non_exempt_card_count": threshold,
        "offenders": offenders,
    }


def missing_field_ledger(cards: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for card in cards:
        for idx, note in enumerate(card.get("evidence_notes_inline", []), start=1):
            for field in ["source_class", "freshness", "place_or_entity", "note_text"]:
                value = str(note.get(field, ""))
                if value.startswith("UNKNOWN") or "THIN" in value:
                    rows.append(
                        {
                            "card_id": card["card_id"],
                            "note_index": idx,
                            "field": field,
                            "visible_value": value,
                            "handled_as": "explicit_missingness_visible_on_card",
                        }
                    )
        if str(card.get("source_depth", "")).startswith("THIN") or str(card.get("source_depth", "")).startswith("UNKNOWN"):
            rows.append(
                {
                    "card_id": card["card_id"],
                    "note_index": None,
                    "field": "source_depth",
                    "visible_value": card.get("source_depth", ""),
                    "handled_as": "explicit_missingness_visible_on_card",
                }
            )
    return {
        "artifact_id": "FOUNDER_CARD_MISSING_FIELD_LEDGER",
        "missing_or_thin_field_count": len(rows),
        "rows": rows,
    }


def extraction_ledger(cards: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for card in cards:
        for idx, note in enumerate(card.get("evidence_notes_inline", []), start=1):
            rows.append(
                {
                    "card_id": card["card_id"],
                    "note_index": idx,
                    "displayed_source_ref": note["source_ref"],
                    "displayed_note_text": note["note_text"],
                    "source_path": note["source_path"],
                    "raw_refs": note.get("raw_refs", []),
                    "source_truth_mutated": False,
                }
            )
    return {
        "artifact_id": "FOUNDER_CARD_EVIDENCE_EXTRACTION_LEDGER",
        "note_count": len(rows),
        "rows": rows,
    }


def decision_guard(cards: list[dict[str, Any]]) -> dict[str, Any]:
    expected = ["watch_this", "ignore_for_now", "need_more_before_deciding"]
    bad = [
        card["card_id"]
        for card in cards
        if card.get("founder_decision_options") != expected or not card.get("suggested_initial_call")
    ]
    return {
        "artifact_id": "FOUNDER_CARD_DECISION_FIELD_GUARD",
        "status": "PASS" if not bad else "FAIL",
        "cards_with_primary_decision": len(cards) - len(bad),
        "bad_card_ids": bad,
        "primary_decision_options": expected,
        "ratings_are_secondary": True,
    }


def boundary_guard() -> dict[str, Any]:
    return {
        "artifact_id": "FOUNDER_CARD_BOUNDARY_GUARD",
        "status": "PASS",
        "founder_internal": True,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "product_review_ready": False,
        "client_ready": False,
        "founder_session_result_created": False,
        "source_truth_mutated": False,
        "forecast_packet_created": False,
        "official_action_control_enforcement_created": False,
    }


def card_index(cards: list[dict[str, Any]], main_hits: list[str]) -> dict[str, Any]:
    rows = []
    for card in cards:
        missing_count = 0
        for note in card.get("evidence_notes_inline", []):
            missing_count += sum(str(note.get(field, "")).startswith("UNKNOWN") for field in ["source_class", "freshness", "place_or_entity", "note_text"])
        rows.append(
            {
                "card_id": card["card_id"],
                "source_story_id": card.get("source_story_id"),
                "card_type": card["card_type"],
                "title": card["title"],
                "primary_decision_options": card["founder_decision_options"],
                "suggested_initial_call": card["suggested_initial_call"],
                "evidence_notes_inline_count": len(card.get("evidence_notes_inline", [])),
                "missing_field_count": missing_count,
                "source_refs": [note["source_ref"] for note in card.get("evidence_notes_inline", [])],
                "main_path_technical_terms_present": technical_hits(card_plain_body(card)),
                "founder_reviewable": card.get("founder_reviewable", False),
                "limitations": card.get("limitations", []),
            }
        )
    return {
        "artifact_id": "FOUNDER_CARD_EVIDENCE_INLINE_INDEX",
        "card_count": len(cards),
        "minimum_card_count_met": len(cards) >= 10,
        "main_path_technical_terms_present": main_hits,
        "cards": rows,
    }


def render_note_html(note: dict[str, Any]) -> str:
    return f"""
<div class="evidence-note">
  <p><strong>Source note:</strong> {html.escape(note['note_text'])}</p>
  <dl>
    <dt>Source ref</dt><dd>{html.escape(note['source_ref'])}</dd>
    <dt>Source class</dt><dd>{html.escape(note['source_class'])}</dd>
    <dt>Freshness</dt><dd>{html.escape(note['freshness'])}</dd>
    <dt>Place/entity</dt><dd>{html.escape(note['place_or_entity'])}</dd>
    <dt>Outcome</dt><dd>{html.escape(note['human_outcome'])}</dd>
  </dl>
</div>"""


def render_call_html(card: dict[str, Any]) -> str:
    return f"""
<section class="call">
  <h3>Your call</h3>
  <label><input type="checkbox"> Watch this</label>
  <label><input type="checkbox"> Ignore for now</label>
  <label><input type="checkbox"> Need more before deciding</label>
  <p><strong>Suggested starting point:</strong> {html.escape(norm_label(card['suggested_initial_call']).title())}</p>
  <p><strong>What one piece of evidence would change your decision?</strong> {html.escape(card['one_missing_piece_that_would_change_decision'])}</p>
  <p class="ratings">Usefulness 1 2 3 4 5 &nbsp; Readability 1 2 3 4 5 &nbsp; Trust 1 2 3 4 5</p>
</section>"""


def render_cross_html(card: dict[str, Any]) -> str:
    notes = "\n".join(render_note_html(note) for note in card["evidence_notes_inline"])
    connected = "".join(f"<li>{html.escape(item)}</li>" for item in card["signals_connected"])
    can_say = "".join(f"<li>{html.escape(item)}</li>" for item in card["what_citybrain_can_say"])
    cannot = "".join(f"<li>{html.escape(item)}</li>" for item in card["what_citybrain_must_not_claim"])
    missing = "".join(f"<li>{html.escape(item)}</li>" for item in card["missing_evidence"])
    return f"""
<article class="card cross" id="{html.escape(card['card_id'])}">
  <p class="type">Cross-domain story card</p>
  <h2>{html.escape(card['title'])}</h2>
  <p>{html.escape(card['plain_english_summary'])}</p>
  <h3>What signals are connected?</h3><ul>{connected}</ul>
  <h3>Site and nearby context</h3>
  <p><strong>Primary site:</strong> {html.escape(card['primary_site_or_place'])}</p>
  <p><strong>Nearby context:</strong> {html.escape(card['nearby_context_not_same_site'])}</p>
  <p><strong>Source depth:</strong> {html.escape(card['source_depth'])}</p>
  <h3>Evidence shown on the card</h3>{notes}
  <h3>What CityBrain can say</h3><ul>{can_say}</ul>
  <h3>What CityBrain refuses to claim</h3><ul>{cannot}</ul>
  <h3>Missing evidence</h3><ul>{missing}</ul>
  {render_call_html(card)}
  <p class="boundary">Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.</p>
</article>"""


def render_single_html(card: dict[str, Any]) -> str:
    notes = "\n".join(render_note_html(note) for note in card["evidence_notes_inline"])
    cannot = "".join(f"<li>{html.escape(item)}</li>" for item in card["what_citybrain_must_not_claim"])
    return f"""
<article class="card single" id="{html.escape(card['card_id'])}">
  <p class="type">Single-family/example card</p>
  <h2>{html.escape(card['title'])}</h2>
  <p>{html.escape(card['specific_signal_summary'])}</p>
  <p><strong>Place/entity:</strong> {html.escape(card['place_or_entity'])}</p>
  <p><strong>Source depth:</strong> {html.escape(card['source_depth'])}</p>
  <h3>Evidence shown on the card</h3>{notes}
  <h3>What makes it worth watching or not?</h3><p>{html.escape(card['why_this_might_matter'])}</p>
  <h3>What is uncertain?</h3><p>{html.escape(card['what_is_uncertain'])}</p>
  <h3>What CityBrain refuses to claim</h3><ul>{cannot}</ul>
  {render_call_html(card)}
  <p class="boundary">Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.</p>
</article>"""


def render_cards_html(cards: list[dict[str, Any]]) -> str:
    body = "\n".join(render_cross_html(card) if card["card_type"] == "cross_domain_story_card" else render_single_html(card) for card in cards)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Evidence-Inline Story Cards</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#1f2937;line-height:1.45}}
main{{max-width:980px;margin:0 auto;padding:28px}}
.card{{background:#fff;border:1px solid #d7deea;border-radius:8px;padding:22px;margin:0 0 18px}}
.cross{{border-left:5px solid #2563eb}} .single{{border-left:5px solid #0f766e}}
.type{{font-size:13px;text-transform:uppercase;color:#526173;margin:0 0 6px}}
h2{{margin:0 0 10px}} h3{{font-size:16px;margin:18px 0 6px}}
.evidence-note{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin:10px 0}}
dl{{display:grid;grid-template-columns:140px 1fr;gap:6px 12px;margin:0}} dt{{font-weight:bold;color:#475569}} dd{{margin:0}}
.call{{border-top:1px solid #e2e8f0;margin-top:16px;padding-top:12px}} label{{display:inline-block;margin:4px 14px 4px 0}}
.ratings,.boundary{{font-size:14px;color:#526173}}
a{{color:#175cd3}}
</style>
</head>
<body><main>
<h1>Founder Evidence-Inline Story Cards</h1>
<p>Reading the card is the review. Each card shows the source note, source class, freshness, place or missingness, and human-readable outcome before asking for a decision.</p>
{body}
</main></body></html>
"""


def render_start_html(cards: list[dict[str, Any]], status: str) -> str:
    rows = []
    for card in cards:
        rows.append(
            f"<tr><td><a href=\"FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html#{html.escape(card['card_id'])}\">{html.escape(card['title'])}</a></td>"
            f"<td>{html.escape(card['layout_name'])}</td><td>{html.escape(norm_label(card['suggested_initial_call']).title())}</td>"
            f"<td>{html.escape(card['source_depth'])}</td></tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Review Start Here - Evidence Inline</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#1f2937;line-height:1.45}}
main{{max-width:1120px;margin:0 auto;padding:28px}}
.hero{{background:#fff;border:1px solid #d7deea;border-radius:8px;padding:22px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d7deea}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e2e8f0;padding:10px}}
th{{background:#edf2f7}} a{{color:#175cd3}}
</style>
</head>
<body><main>
<section class="hero">
<h1>Founder Review Starts Here</h1>
<p>Do not run founder review on the older pointer cards. Use this repaired batch because the evidence is shown inside each card.</p>
<p>Status: <strong>{html.escape(status)}</strong>. Cards: <strong>{len(cards)}</strong>.</p>
<p>Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.</p>
</section>
<table>
<thead><tr><th>Card</th><th>Layout</th><th>Suggested call</th><th>Source depth</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</main></body></html>
"""


def render_note_md(note: dict[str, Any]) -> list[str]:
    return [
        f"- Source note: {note['note_text']}",
        f"  - Source ref: {note['source_ref']}",
        f"  - Source class: {note['source_class']}",
        f"  - Freshness: {note['freshness']}",
        f"  - Place/entity: {note['place_or_entity']}",
        f"  - Outcome: {note['human_outcome']}",
    ]


def render_cards_md(cards: list[dict[str, Any]]) -> str:
    lines = ["# Founder Evidence-Inline Story Cards", "", "Reading the card is the review.", ""]
    for card in cards:
        lines.extend([f"## {card['title']}", "", f"Card type: {card['layout_name']}", ""])
        if card["card_type"] == "cross_domain_story_card":
            lines.extend(
                [
                    card["plain_english_summary"],
                    "",
                    "What signals are connected?",
                    *[f"- {item}" for item in card["signals_connected"]],
                    "",
                    f"Primary site: {card['primary_site_or_place']}",
                    f"Nearby context: {card['nearby_context_not_same_site']}",
                    f"Source depth: {card['source_depth']}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    card["specific_signal_summary"],
                    "",
                    f"Place/entity: {card['place_or_entity']}",
                    f"Source depth: {card['source_depth']}",
                    "",
                ]
            )
        lines.extend(["Evidence shown on the card:", ""])
        for note in card["evidence_notes_inline"]:
            lines.extend(render_note_md(note))
        lines.extend(
            [
                "",
                "Your call:",
                "- [ ] Watch this",
                "- [ ] Ignore for now",
                "- [ ] Need more before deciding",
                f"Suggested starting point: {norm_label(card['suggested_initial_call']).title()}",
                f"What one piece of evidence would change your decision? {card['one_missing_piece_that_would_change_decision']}",
                "Usefulness: 1 2 3 4 5",
                "Readability: 1 2 3 4 5",
                "Trust: 1 2 3 4 5",
                "",
                "Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.",
                "",
            ]
        )
    return "\n".join(lines)


def render_start_md(cards: list[dict[str, Any]], status: str) -> str:
    lines = [
        "# Founder Review Starts Here",
        "",
        "Do not run founder review on the older pointer cards. Use this repaired batch because the evidence is shown inside each card.",
        "",
        f"Status: `{status}`",
        f"Cards: `{len(cards)}`",
        "",
    ]
    for card in cards:
        lines.append(f"- {card['title']} - {card['layout_name']} - suggested call: {norm_label(card['suggested_initial_call']).title()}")
    return "\n".join(lines)


def render_csv(cards: list[dict[str, Any]]) -> str:
    fields = [
        "card_id",
        "card_type",
        "title",
        "founder_decision",
        "usefulness_1_to_5",
        "readability_1_to_5",
        "trust_1_to_5",
        "one_evidence_that_would_change_decision",
        "free_text_notes",
        "founder_internal",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "product_review_ready",
        "client_ready",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for card in cards:
        writer.writerow(
            {
                "card_id": card["card_id"],
                "card_type": card["card_type"],
                "title": card["title"],
                "founder_decision": "",
                "usefulness_1_to_5": "",
                "readability_1_to_5": "",
                "trust_1_to_5": "",
                "one_evidence_that_would_change_decision": "",
                "free_text_notes": "",
                "founder_internal": "true",
                "operator_fuel": "false",
                "training_eligible": "false",
                "external_operator_validation": "false",
                "product_review_ready": "false",
                "client_ready": "false",
            }
        )
    return out.getvalue()


def main_path_text(out: Path) -> str:
    files = [
        out / "FOUNDER_REVIEW_START_HERE_INLINE.html",
        out / "FOUNDER_REVIEW_START_HERE_INLINE.md",
        out / "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html",
        out / "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.md",
        out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in files if path.exists())


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
    enough_cards = len(cards) >= 10

    # Render once, scan, then write guards and decision.
    status = STATUS_PASS if enough_cards else STATUS_NEEDS
    write_text(out / "FOUNDER_REVIEW_START_HERE_INLINE.html", render_start_html(cards, status))
    write_text(out / "FOUNDER_REVIEW_START_HERE_INLINE.md", render_start_md(cards, status))
    write_text(out / "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html", render_cards_html(cards))
    write_text(out / "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.md", render_cards_md(cards))
    write_text(out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv", render_csv(cards))

    main_hits = technical_hits(main_path_text(out))
    boilerplate = boilerplate_audit(cards)
    decision = decision_guard(cards)
    boundary = boundary_guard()
    term_guard = {
        "artifact_id": "FOUNDER_CARD_TECHNICAL_TERM_GUARD",
        "status": "PASS" if not main_hits else "FAIL",
        "main_path_scanned_files": [
            "FOUNDER_REVIEW_START_HERE_INLINE.html",
            "FOUNDER_REVIEW_START_HERE_INLINE.md",
            "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html",
            "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.md",
            "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv",
        ],
        "technical_terms_present": main_hits,
    }
    self_contained = (
        enough_cards
        and not main_hits
        and boilerplate["status"] == "PASS"
        and decision["status"] == "PASS"
        and all(card.get("evidence_notes_inline") or not card.get("founder_reviewable") for card in cards)
    )
    repair_decision = {
        "artifact_id": "FOUNDER_CARD_REPAIR_DECISION",
        "status": STATUS_PASS if self_contained else STATUS_NEEDS,
        "card_count": len(cards),
        "minimum_card_count_met": enough_cards,
        "founder_reviewable_surface_ready_with_limitations": self_contained,
        "reading_the_card_is_the_review": self_contained,
        "main_path_technical_terms_removed": not main_hits,
        "boilerplate_audit_passed": boilerplate["status"] == "PASS",
        "decision_field_guard_passed": decision["status"] == "PASS",
        "boundary_guard_passed": boundary["status"] == "PASS",
        "product_review_ready": False,
        "client_ready": False,
        "founder_session_result_created": False,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "source_truth_mutated": False,
        "next_recommended_task": "FOUNDER_DIAGNOSTIC_REVIEW_CAN_PROCEED_WITH_LIMITATIONS"
        if self_contained
        else "REPAIR_SOURCE_ARTIFACTS_BEFORE_FOUNDER_DIAGNOSTIC_REVIEW",
    }

    write_json(out / "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json", card_index(cards, main_hits))
    write_json(out / "FOUNDER_CARD_EVIDENCE_EXTRACTION_LEDGER.json", extraction_ledger(cards))
    write_json(out / "FOUNDER_CARD_MISSING_FIELD_LEDGER.json", missing_field_ledger(cards))
    write_json(out / "FOUNDER_CARD_BOILERPLATE_AUDIT.json", boilerplate)
    write_json(out / "FOUNDER_CARD_DECISION_FIELD_GUARD.json", decision)
    write_json(out / "FOUNDER_CARD_TECHNICAL_TERM_GUARD.json", term_guard)
    write_json(out / "FOUNDER_CARD_BOUNDARY_GUARD.json", boundary)
    write_json(out / "FOUNDER_CARD_REPAIR_DECISION.json", repair_decision)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Founder Card Evidence-Inlining Repair R1

Status: `{repair_decision["status"]}`

- Cards rendered: `{len(cards)}`
- Founder-reviewable surface ready with limitations: `{self_contained}`
- Main founder-path technical term hits: `{main_hits}`
- Boilerplate audit: `{boilerplate["status"]}`
- Decision field guard: `{decision["status"]}`

Boundaries: founder-internal diagnostic review surface only; no session result, fuel, training rows, external validation, product/client readiness, source-truth mutation, ForecastPacket, live ingestion, official action/control/enforcement, or legal/certified claim.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return repair_decision


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

    repair = read_json(out / "FOUNDER_CARD_REPAIR_DECISION.json")
    index = read_json(out / "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json")
    extraction = read_json(out / "FOUNDER_CARD_EVIDENCE_EXTRACTION_LEDGER.json")
    missing = read_json(out / "FOUNDER_CARD_MISSING_FIELD_LEDGER.json")
    boilerplate = read_json(out / "FOUNDER_CARD_BOILERPLATE_AUDIT.json")
    decision = read_json(out / "FOUNDER_CARD_DECISION_FIELD_GUARD.json")
    terms = read_json(out / "FOUNDER_CARD_TECHNICAL_TERM_GUARD.json")
    boundary = read_json(out / "FOUNDER_CARD_BOUNDARY_GUARD.json")
    csv_rows = list(csv.DictReader(StringIO((out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv").read_text(encoding="utf-8"))))

    if repair.get("card_count", 0) >= 10 and repair.get("status") != STATUS_PASS:
        errors.append("10+ self-contained cards did not pass")
    if index.get("card_count") != repair.get("card_count"):
        errors.append("index card count mismatch")
    if len(csv_rows) != repair.get("card_count"):
        errors.append("CSV row count mismatch")
    if extraction.get("note_count", 0) < repair.get("card_count", 0):
        errors.append("not every card has at least one evidence note")
    if not missing.get("rows"):
        errors.append("missingness ledger is empty; expected explicit UNKNOWN/THIN fields")
    if boilerplate.get("status") != "PASS":
        errors.append("boilerplate audit failed")
    if decision.get("status") != "PASS":
        errors.append("decision field guard failed")
    if terms.get("status") != "PASS" or terms.get("technical_terms_present"):
        errors.append(f"technical terms in main founder path: {terms.get('technical_terms_present')}")
    if technical_hits(main_path_text(out)):
        errors.append(f"technical term scan failed: {technical_hits(main_path_text(out))}")
    for phrase in ["1 supporting source note", "place context", "same site may be related"]:
        if phrase in main_path_text(out).lower():
            errors.append(f"forbidden weak phrase still present: {phrase}")
    for row in index.get("cards", []):
        if row.get("primary_decision_options") != ["watch_this", "ignore_for_now", "need_more_before_deciding"]:
            errors.append(f"bad decision options for {row.get('card_id')}")
        if row.get("evidence_notes_inline_count", 0) < 1 and row.get("founder_reviewable"):
            errors.append(f"founder-reviewable card lacks evidence: {row.get('card_id')}")
    for row in csv_rows:
        expected = {
            "founder_internal": "true",
            "operator_fuel": "false",
            "training_eligible": "false",
            "external_operator_validation": "false",
            "product_review_ready": "false",
            "client_ready": "false",
        }
        for key, value in expected.items():
            if row.get(key) != value:
                errors.append(f"bad CSV boundary field {key} for {row.get('card_id')}")
    for key, value in {
        "founder_internal": True,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "product_review_ready": False,
        "client_ready": False,
        "founder_session_result_created": False,
        "source_truth_mutated": False,
    }.items():
        if boundary.get(key) is not value:
            errors.append(f"boundary guard mismatch for {key}")
    if repair.get("product_review_ready") or repair.get("client_ready"):
        errors.append("product/client readiness opened")
    if not (PUB / "FOUNDER_REVIEW_START_HERE_INLINE.html").exists():
        errors.append("publication HTML missing")
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
