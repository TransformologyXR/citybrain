#!/usr/bin/env python3
"""Materialize founder-grade candidate stories from existing evidence artifacts."""

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
OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-GRADE-STORY-MATERIALIZATION-R1"
PUB = ROOT / "publications" / "epoch4" / "main-citybrain-founder-grade-story-materialization-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_FOUNDER_GRADE_STORY_MATERIALIZATION_R1_WITH_LIMITATIONS"
STATUS_NOT_ENOUGH = "NOT_ENOUGH_FOUNDER_GRADE_STORIES_AFTER_MATERIALIZATION_WITH_LIMITATIONS"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_FOUNDER_GRADE_STORY_MATERIALIZATION_R1"
ALLOWED_STATUSES = {STATUS_PASS, STATUS_NOT_ENOUGH, STATUS_FAIL}

INPUT_ROOTS = {
    "selection_quality_gate": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-STORY-SELECTION-QUALITY-GATE-R1",
    "selection_quality_gate_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-story-selection-quality-gate-r1",
    "operator_view_rendering": ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-OPERATOR-VIEW-CARD-RENDERING-R1",
    "operator_view_rendering_publication": ROOT / "publications" / "epoch4" / "main-citybrain-founder-operator-view-card-rendering-r1",
    "cross_domain_story_arc": ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1",
    "cross_domain_story_arc_publication": ROOT / "publications" / "epoch4" / "main-citybrain-cross-domain-story-arc-eval-expansion-r1",
    "seed_r3_adapter_corpus": ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
    "expanded_cadence": ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
    "mobility_native_repair": ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1",
    "simulation_distribution_checked": ROOT / "outputs" / "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1",
    "deep_data_estate_audit": ROOT / "outputs" / "main_citybrain_epoch4_deep_data_estate_audit_r1",
    "review_quality_global_gap": ROOT / "outputs" / "main_citybrain_epoch4_review_quality_global_gap_sequence_r1",
}

REQUIRED = [
    "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json",
    "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json",
    "FOUNDER_STORY_CANDIDATE_CLASSIFICATION_LEDGER.json",
    "FOUNDER_STORY_MATERIALIZATION_LEDGER.json",
    "FOUNDER_GRADE_STORY_BATCH_INDEX.json",
    "FOUNDER_OPERATOR_STORY_CARDS.html",
    "FOUNDER_OPERATOR_STORY_CARDS.md",
    "FOUNDER_REVIEW_START_HERE.html",
    "FOUNDER_REVIEW_START_HERE.md",
    "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv",
    "FOUNDER_DIAGNOSTIC_APPENDIX_WEAK_DIAGNOSTIC_CARDS.html",
    "FOUNDER_DIAGNOSTIC_APPENDIX_WEAK_DIAGNOSTIC_CARDS.md",
    "FOUNDER_STORY_AUDIENCE_BACKLOG.md",
    "FOUNDER_STORY_BOUNDARY_GUARD.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

CLASSIFICATIONS = [
    "founder_reviewable_watch_candidate",
    "founder_reviewable_ignore_candidate",
    "founder_reviewable_need_more_candidate",
    "diagnostic_boundary_case",
    "negative_abstain_case",
    "not_reviewable_due_to_missing_place",
    "not_reviewable_due_to_missing_freshness",
    "not_reviewable_due_to_thin_source_depth",
    "not_reviewable_due_to_no_human_readable_consequence",
    "not_reviewable_due_to_no_next_step",
    "not_reviewable_due_to_no_audience_fit",
]

PASS_BAR = {
    "minimum_founder_grade_stories": 10,
    "minimum_watch_candidates": 5,
    "minimum_cross_domain_stories": 2,
    "minimum_ignore_candidates": 2,
    "maximum_need_more_stories": 3,
}

BANNED_MAIN_TERMS = [
    "cer",
    "seg",
    "check",
    "brief",
    "spatial",
    "event fabric",
    "canonical entity",
    "quarantine",
    "resolved",
    "unresolved",
    "family_id",
    "jsonl",
    "truth manifest",
    "native packet",
]

FAMILY_LABELS = {
    "mobility_access_interruption_v0": "access interruption",
    "mobility_access_interruption": "access interruption",
    "building_compliance_perception_candidate": "building concern",
    "permit_inspection_delay": "permit or inspection delay",
    "city_asset_infrastructure_issue": "infrastructure concern",
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
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: Any) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").replace(".", " ").strip()


def family_label(family: str) -> str:
    return FAMILY_LABELS.get(family, normalize(family))


def main_clean(text: Any) -> str:
    value = str(text or "")
    replacements = [
        (r"\bCER\b", "same-site matching"),
        (r"\bSEG\b", "area link"),
        (r"\bCHECK\b", "evidence review"),
        (r"\bBRIEF\b", "review summary"),
        (r"\bSPATIAL\b", "map view"),
        (r"Event Fabric", "event history"),
        (r"canonical entity", "same-site record"),
        (r"truth manifest", "source map"),
        (r"native packet", "direct evidence packet"),
        (r"family_id", "story group"),
        (r"JSONL", "source rows"),
        (r"quarantine", "set aside"),
        (r"unresolved", "not decided"),
        (r"resolved", "linked for review"),
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


def event_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup = {}
    for row in rows:
        for key in ["event_id", "source_event_id"]:
            if row.get(key):
                lookup[str(row[key])] = row
    return lookup


def source_class_text(row: dict[str, Any]) -> str:
    source_class = str(row.get("source_class", "UNKNOWN")).lower()
    truth_layer = str(row.get("truth_layer", "")).lower()
    if "gold" in source_class or "gold" in truth_layer:
        return "local gold sample, non-authoritative"
    if "dirty" in source_class or "dirty" in truth_layer:
        return "local dirty-source sample, non-authoritative"
    if "challenge" in source_class or "challenge" in truth_layer:
        return "local challenge sample, non-authoritative"
    if "scenario" in source_class or "scenario" in truth_layer:
        return "local scenario sample, non-authoritative"
    return "local review sample, non-authoritative"


def place_label(row: dict[str, Any], *, cross_domain: bool = False) -> str:
    geometry = str(row.get("candidate_geometry_ref") or row.get("spatial_ref") or "")
    family = str(row.get("canonical_loop_family_id") or row.get("family_id") or "")
    refs = " ".join(str(ref) for ref in row.get("candidate_entity_refs", []) + row.get("canonical_entity_refs", []))
    if cross_domain:
        return "Synthetic Dubai AOI, Alpha site and nearby corridor"
    if "building:alpha" in refs or "permit:" in refs or "building_compliance" in geometry or "permit_inspection" in geometry:
        return "Synthetic Dubai AOI, Alpha site"
    if "mobility_access" in geometry or "mobility" in family:
        return "Synthetic Dubai AOI, access corridor near Alpha site"
    if "asset_infrastructure" in geometry or "asset" in family or "infrastructure" in family:
        return "Synthetic Dubai AOI, nearby infrastructure corridor"
    return "Derived local place label from geometry reference"


def area_label(row: dict[str, Any]) -> str:
    geometry = str(row.get("candidate_geometry_ref") or row.get("spatial_ref") or "")
    if "synthetic-dubai-aoi" in geometry:
        return "Synthetic Dubai AOI"
    return "Derived local review area"


def map_ref(row: dict[str, Any]) -> str:
    return str(row.get("candidate_geometry_ref") or row.get("spatial_ref") or "derived-map-ref-not-present")


def outcome_text(row: dict[str, Any]) -> str:
    state = str(row.get("expected_resolution_state") or row.get("resolution_outcome") or row.get("check_expected_behavior") or "").lower()
    reason = normalize(row.get("resolution_reason_class"))
    if "quarantine" in state or "invalid" in reason:
        return "Ignore for now; the source shape is not reliable enough for review time."
    if "unresolved" in state or "weak" in reason or "missing" in reason:
        return "Need more before deciding; the source is visible but still weak."
    if "candidate" in state:
        return "Need more before deciding; it is still candidate-only."
    return "Watch this with limits; the note is usable for review but not action authority."


def supports_text(row: dict[str, Any]) -> str:
    family = str(row.get("canonical_loop_family_id") or row.get("family_id") or "")
    label = family_label(family)
    return f"Supports reviewing {label} around {place_label(row)}."


def evidence_note(row: dict[str, Any], *, source_path: Path, cross_domain_note: str | None = None) -> dict[str, Any]:
    event_type = normalize(row.get("event_type") or row.get("source_event_type") or "source signal")
    summary = cross_domain_note or row.get("narrative_summary") or row.get("payload", {}).get("summary") or f"{event_type} source note"
    return {
        "note_text": main_clean(f"{event_type}: {summary}"),
        "source_class": source_class_text(row),
        "freshness": str(row.get("event_time") or row.get("processing_time") or row.get("observed_at") or "UNKNOWN - no timestamp found"),
        "place": place_label(row),
        "map_or_geometry_ref": map_ref(row),
        "supports": main_clean(supports_text(row)),
        "does_not_prove": "It does not prove official fact, causation, action authority, prediction, or customer readiness.",
        "source_ref": str(row.get("event_id") or row.get("source_event_id") or row.get("story_event_id") or "unknown-source-ref"),
        "source_path": rel(source_path),
    }


def story_common(
    *,
    story_id: str,
    title: str,
    classification: str,
    operator_verdict: str,
    card_type: str,
    evidence_rows: list[dict[str, Any]],
    source_path: Path,
    so_what: str,
    next_step: str,
    confidence_label: str,
    confidence_reason: str,
    uncertainty: list[str] | None = None,
    cross_domain_notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    notes = []
    for row in evidence_rows:
        notes.append(
            evidence_note(
                row,
                source_path=source_path,
                cross_domain_note=(cross_domain_notes or {}).get(str(row.get("event_id") or row.get("source_event_id"))),
            )
        )
    first = evidence_rows[0]
    return {
        "story_id": story_id,
        "title": main_clean(title),
        "classification": classification,
        "card_type": card_type,
        "operator_verdict": operator_verdict,
        "what_where": main_clean(f"{title} around {place_label(first, cross_domain=card_type == 'cross_domain_story')}."),
        "so_what": main_clean(so_what),
        "suggested_next_step": main_clean(next_step),
        "confidence_label": confidence_label,
        "confidence_reason": main_clean(confidence_reason),
        "place_anchor": {
            "human_label": place_label(first, cross_domain=card_type == "cross_domain_story"),
            "district_or_area": area_label(first),
            "map_or_geometry_ref": map_ref(first),
            "derived_non_authoritative": True,
        },
        "evidence_notes": notes,
        "uncertainty": uncertainty
        or [
            "This is still a founder-internal diagnostic story, not a product or client-ready claim.",
            "Place labels are derived from existing geometry and entity references, not asserted as official truth.",
        ],
        "cannot_claim": [
            "official fact",
            "causation",
            "work order",
            "prediction",
            "customer readiness",
            "official action",
        ],
        "decision_options": ["watch_this", "ignore_for_now", "need_more_before_deciding"],
        "secondary_ratings": ["usefulness_1_to_5", "readability_1_to_5", "trust_1_to_5"],
        "audience_fit": "operator",
        "source_truth_mutated": False,
    }


def load_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seed_rows = read_jsonl(INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")
    cross_rows = read_jsonl(INPUT_ROOTS["cross_domain_story_arc"] / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl")
    old_cards = read_json(INPUT_ROOTS["operator_view_rendering"] / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json", {"cards": []}).get("cards", [])
    return seed_rows, cross_rows, old_cards


def materialize_cross_domain(seed_rows: list[dict[str, Any]], cross_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = event_index(seed_rows)
    source_path = INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl"
    stories = []

    enriched = []
    notes = {}
    for row in cross_rows:
        source_id = str(row.get("source_event_id", ""))
        seed = dict(by_id.get(source_id, {}))
        if seed:
            enriched.append(seed)
            notes[str(seed.get("event_id"))] = str(row.get("narrative_summary", ""))
    if len(enriched) >= 4:
        stories.append(
            story_common(
                story_id="founder-grade-cross-alpha-permit-access-compliance",
                title="Alpha site permit, access, and building review bundle",
                classification="founder_reviewable_watch_candidate",
                operator_verdict="watch_this",
                card_type="cross_domain_story",
                evidence_rows=enriched[:6],
                source_path=source_path,
                cross_domain_notes=notes,
                so_what="If these signals stay related, an operator-style reviewer can watch one site where permit status, access, and building context appear together without claiming cause.",
                next_step="Compare the permit status, access note, and building note in the next review pass before any customer-facing use.",
                confidence_label="medium",
                confidence_reason="multiple timestamped source notes point to the same review area, while corridor context remains non-authoritative.",
            )
        )

    families = {
        "mobility_access_interruption_v0",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    }
    alpha_rows = [
        row
        for row in seed_rows
        if row.get("expected_resolution_state") == "resolved"
        and row.get("canonical_loop_family_id") in families
        and any("building:alpha" in str(ref) or "permit:" in str(ref) for ref in row.get("candidate_entity_refs", []))
    ]
    if len(alpha_rows) >= 4:
        stories.append(
            story_common(
                story_id="founder-grade-cross-alpha-repeat-window",
                title="Alpha site repeated review window",
                classification="founder_reviewable_watch_candidate",
                operator_verdict="watch_this",
                card_type="cross_domain_story",
                evidence_rows=alpha_rows[:5],
                source_path=source_path,
                so_what="If repeated access, permit, and building signals keep landing on the same review area, the site is worth watching as a compact operator triage story.",
                next_step="Keep this grouped story in the watch queue and request one fresh source pull that confirms the current state of the site.",
                confidence_label="medium",
                confidence_reason="the group has several timestamped notes and derived place labels backed by geometry references, but it remains non-authoritative.",
            )
        )
    return stories


def rows_by_family_state(seed_rows: list[dict[str, Any]], family: str, state: str) -> list[dict[str, Any]]:
    return [
        row
        for row in seed_rows
        if row.get("canonical_loop_family_id") == family and row.get("expected_resolution_state") == state
    ]


def materialize_family_stories(seed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_path = INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl"
    specs = [
        (
            "mobility_access_interruption_v0",
            "resolved",
            "founder-grade-mobility-alpha-access-window",
            "Access corridor review window near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "If access constraints persist near the same review area, the operator can watch for repeated disruption without treating it as live control.",
            "Request one fresh access source note and compare it with the current permit/building review area.",
        ),
        (
            "building_compliance_perception_candidate",
            "resolved",
            "founder-grade-building-alpha-site-window",
            "Building concern review window near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "If building-context notes repeat near Alpha, the reviewer can watch the site while keeping the concern non-authoritative.",
            "Compare the building note against the latest permit or site context before advancing the story.",
        ),
        (
            "permit_inspection_delay",
            "resolved",
            "founder-grade-permit-alpha-timeline-window",
            "Permit and inspection timeline near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "If permit and inspection signals stay attached to Alpha, the reviewer can track uncertainty that may affect site review sequencing.",
            "Verify the latest permit or inspection status before any founder diagnostic response is collected.",
        ),
        (
            "city_asset_infrastructure_issue",
            "resolved",
            "founder-grade-asset-corridor-context-window",
            "Infrastructure corridor context near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "If nearby infrastructure notes repeat in the corridor, they may explain context an operator should keep separate from the Alpha site.",
            "Ask whether the asset note is at the site or nearby corridor context, then keep it separate in review.",
        ),
        (
            "mobility_access_interruption_v0",
            "resolved",
            "founder-grade-mobility-second-window",
            "Second access signal window near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "A second access window gives the reviewer a repeat pattern to watch instead of a one-off caveat.",
            "Compare the later access window with the earlier one and ask whether the interruption is still current.",
        ),
        (
            "permit_inspection_delay",
            "resolved",
            "founder-grade-permit-second-window",
            "Second permit review window near Alpha",
            "founder_reviewable_watch_candidate",
            "watch_this",
            "A second permit window gives enough structure to watch the review timeline without inventing a forecast.",
            "Request one current permit-source pull and compare it with the older review window.",
        ),
    ]
    stories = []
    for family, state, story_id, title, classification, verdict, so_what, next_step in specs:
        rows = rows_by_family_state(seed_rows, family, state)
        offset = 0 if "second" not in story_id else 4
        picked = rows[offset : offset + 2]
        if len(picked) < 2:
            continue
        stories.append(
            story_common(
                story_id=story_id,
                title=title,
                classification=classification,
                operator_verdict=verdict,
                card_type="single_family_example",
                evidence_rows=picked,
                source_path=source_path,
                so_what=so_what,
                next_step=next_step,
                confidence_label="medium",
                confidence_reason="two timestamped evidence notes and a derived place anchor are available, but the story is still non-authoritative.",
            )
        )
    return stories


def materialize_ignore_stories(seed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_path = INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl"
    stories = []
    specs = [
        (
            "city_asset_infrastructure_issue",
            "founder-grade-ignore-asset-invalid-shape",
            "Ignore infrastructure signal with unreliable source shape",
            "If the source shape is unreliable, the useful operator action is to not spend main review attention yet.",
            "Dismiss this signal from the main watch set unless a cleaner asset source note arrives.",
        ),
        (
            "mobility_access_interruption_v0",
            "founder-grade-ignore-access-missing-link",
            "Ignore access signal until place link is cleaner",
            "If the access note cannot be cleanly tied to the review area, ignoring it for now prevents a noisy watch queue.",
            "Dismiss for now unless a fresh access source confirms the place link.",
        ),
    ]
    for family, story_id, title, so_what, next_step in specs:
        rows = rows_by_family_state(seed_rows, family, "quarantine_expected")
        if len(rows) < 2:
            continue
        picked = rows[:2]
        stories.append(
            story_common(
                story_id=story_id,
                title=title,
                classification="founder_reviewable_ignore_candidate",
                operator_verdict="ignore_for_now",
                card_type="single_family_example",
                evidence_rows=picked,
                source_path=source_path,
                so_what=so_what,
                next_step=next_step,
                confidence_label="medium",
                confidence_reason="two timestamped notes show why the safe review choice is to ignore for now rather than escalate.",
                uncertainty=[
                    "The signal may become useful later if a cleaner source note arrives.",
                    "This is an honest abstain/ignore story, not a product failure.",
                ],
            )
        )
    return stories


def materialize_need_more(seed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_path = INPUT_ROOTS["seed_r3_adapter_corpus"] / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl"
    rows = rows_by_family_state(seed_rows, "building_compliance_perception_candidate", "unresolved_review")
    if len(rows) < 2:
        return []
    return [
        story_common(
            story_id="founder-grade-need-more-building-weak-match",
            title="Building concern that needs one stronger source",
            classification="founder_reviewable_need_more_candidate",
            operator_verdict="need_more_before_deciding",
            card_type="single_family_example",
            evidence_rows=rows[:2],
            source_path=source_path,
            so_what="If the weak match improves, this could become a useful building concern story; until then it should not crowd out stronger watch candidates.",
            next_step="Request one clearer building-source note before deciding whether to watch this story.",
            confidence_label="medium",
            confidence_reason="two timestamped notes are visible, but the matching reason remains weak.",
            uncertainty=[
                "This belongs in the main set only if the batch has enough stronger watch and ignore stories.",
            ],
        )
    ]


def materialize_candidates() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    seed_rows, cross_rows, old_cards = load_sources()
    stories = []
    stories.extend(materialize_cross_domain(seed_rows, cross_rows))
    stories.extend(materialize_family_stories(seed_rows))
    stories.extend(materialize_ignore_stories(seed_rows))
    stories.extend(materialize_need_more(seed_rows))
    diagnostic = []
    for card in old_cards:
        diagnostic.append(
            {
                "source_card_id": card.get("card_id"),
                "title": card.get("verdict_line", "previous weak card"),
                "reason_moved_to_appendix": "Previous rendered card was useful diagnostic material but did not pass founder-grade story selection.",
                "operator_verdict": card.get("operator_verdict_suggestion"),
                "confidence": card.get("confidence_plain_english"),
            }
        )
    discovery = {
        "artifact_id": "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT",
        "input_roots": [{"key": key, "path": rel(path), "exists": path.exists()} for key, path in INPUT_ROOTS.items()],
        "seed_r3_event_count": len(seed_rows),
        "cross_domain_event_count": len(cross_rows),
        "previous_operator_card_count": len(old_cards),
        "materialization_note": "Candidate stories are built only from existing source rows and previous card outputs; derived labels are non-authoritative and backed by geometry/source references.",
    }
    return stories, diagnostic, discovery


def story_quality_ok(story: dict[str, Any]) -> bool:
    if story["classification"] not in {
        "founder_reviewable_watch_candidate",
        "founder_reviewable_ignore_candidate",
        "founder_reviewable_need_more_candidate",
    }:
        return False
    if story["audience_fit"] != "operator":
        return False
    if len(story["evidence_notes"]) < 2:
        return False
    if not story["so_what"] or not story["suggested_next_step"]:
        return False
    if story["confidence_label"] not in {"low", "medium", "high"} or not story["confidence_reason"]:
        return False
    if story["operator_verdict"] not in {"watch_this", "ignore_for_now", "need_more_before_deciding"}:
        return False
    for note in story["evidence_notes"]:
        if str(note.get("freshness", "")).startswith("UNKNOWN"):
            return False
        if str(note.get("place", "")).startswith("UNKNOWN"):
            return False
    return True


def select_main(stories: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = [story for story in stories if story_quality_ok(story)]
    selected = []
    need_more = 0
    order = {
        "founder_reviewable_watch_candidate": 0,
        "founder_reviewable_ignore_candidate": 1,
        "founder_reviewable_need_more_candidate": 2,
    }
    eligible.sort(key=lambda story: (order.get(story["classification"], 9), story["story_id"]))
    for story in eligible:
        if story["operator_verdict"] == "need_more_before_deciding":
            if need_more >= PASS_BAR["maximum_need_more_stories"]:
                continue
            need_more += 1
        selected.append(story)
    selected_ids = {story["story_id"] for story in selected}
    appendix = [story for story in stories if story["story_id"] not in selected_ids]
    return selected, appendix


def metrics(main: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(story["classification"] for story in main)
    verdicts = Counter(story["operator_verdict"] for story in main)
    cross = sum(story["card_type"] == "cross_domain_story" for story in main)
    pass_bar_met = (
        len(main) >= PASS_BAR["minimum_founder_grade_stories"]
        and counts["founder_reviewable_watch_candidate"] >= PASS_BAR["minimum_watch_candidates"]
        and cross >= PASS_BAR["minimum_cross_domain_stories"]
        and counts["founder_reviewable_ignore_candidate"] >= PASS_BAR["minimum_ignore_candidates"]
        and verdicts["need_more_before_deciding"] <= PASS_BAR["maximum_need_more_stories"]
    )
    blockers = []
    if len(main) < PASS_BAR["minimum_founder_grade_stories"]:
        blockers.append(f"only {len(main)} founder-grade stories; need {PASS_BAR['minimum_founder_grade_stories']}")
    if counts["founder_reviewable_watch_candidate"] < PASS_BAR["minimum_watch_candidates"]:
        blockers.append(f"only {counts['founder_reviewable_watch_candidate']} watch candidates; need {PASS_BAR['minimum_watch_candidates']}")
    if cross < PASS_BAR["minimum_cross_domain_stories"]:
        blockers.append(f"only {cross} cross-domain stories; need {PASS_BAR['minimum_cross_domain_stories']}")
    if counts["founder_reviewable_ignore_candidate"] < PASS_BAR["minimum_ignore_candidates"]:
        blockers.append(f"only {counts['founder_reviewable_ignore_candidate']} ignore candidates; need {PASS_BAR['minimum_ignore_candidates']}")
    if verdicts["need_more_before_deciding"] > PASS_BAR["maximum_need_more_stories"]:
        blockers.append(f"{verdicts['need_more_before_deciding']} need-more stories; max {PASS_BAR['maximum_need_more_stories']}")
    return {
        "main_story_count": len(main),
        "watch_candidate_count": counts["founder_reviewable_watch_candidate"],
        "ignore_candidate_count": counts["founder_reviewable_ignore_candidate"],
        "need_more_candidate_count": counts["founder_reviewable_need_more_candidate"],
        "cross_domain_story_count": cross,
        "verdict_counts": dict(verdicts),
        "classification_counts": dict(counts),
        "pass_bar": PASS_BAR,
        "pass_bar_met": pass_bar_met,
        "blockers": blockers,
    }


def boundary_guard() -> dict[str, Any]:
    return {
        "artifact_id": "FOUNDER_STORY_BOUNDARY_GUARD",
        "status": "PASS",
        "founder_session_result_created": False,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "learning_arming_allowed": False,
        "source_truth_mutated": False,
        "live_ingestion_claim": False,
        "forecast_packet_created": False,
        "official_workflow_case_action_control_enforcement_created": False,
        "product_review_ready": False,
        "client_ready": False,
    }


def main_path_text(out: Path) -> str:
    files = [
        out / "FOUNDER_OPERATOR_STORY_CARDS.html",
        out / "FOUNDER_OPERATOR_STORY_CARDS.md",
        out / "FOUNDER_REVIEW_START_HERE.html",
        out / "FOUNDER_REVIEW_START_HERE.md",
        out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in files if path.exists())


def render_start_html(main: list[dict[str, Any]], status: str) -> str:
    rows = []
    for story in main:
        rows.append(
            f"<tr><td><a href=\"FOUNDER_OPERATOR_STORY_CARDS.html#{html.escape(story['story_id'])}\">{html.escape(story['title'])}</a></td>"
            f"<td>{html.escape(story['operator_verdict'])}</td><td>{html.escape(story['confidence_label'] + ' - ' + story['confidence_reason'])}</td>"
            f"<td>{html.escape(story['place_anchor']['human_label'])}</td></tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder-Grade Story Materialization</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#1f2937;line-height:1.45}}
main{{max-width:1160px;margin:0 auto;padding:28px}}
.hero{{background:#fff;border:1px solid #d9e1ec;border-radius:8px;padding:22px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d9e1ec}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e5ebf2;padding:10px}}
th{{background:#edf2f7}} a{{color:#175cd3;text-decoration:none}}
</style>
</head>
<body><main>
<section class="hero">
<h1>Founder-Grade Story Materialization</h1>
<p>Status: <strong>{html.escape(status)}</strong>. Main stories: <strong>{len(main)}</strong>.</p>
<p>This is a candidate-only founder-internal operator review batch. It uses existing artifacts and non-authoritative derived labels where supported.</p>
<p>Do not treat this as product readiness, client readiness, training data, fuel, or official action.</p>
</section>
<table>
<thead><tr><th>Story</th><th>Verdict</th><th>Confidence</th><th>Place</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</main></body></html>
"""


def render_start_md(main: list[dict[str, Any]], status: str) -> str:
    lines = [
        "# Founder-Grade Story Materialization",
        "",
        f"Status: `{status}`",
        f"Main stories: `{len(main)}`",
        "",
        "Candidate-only founder-internal operator review batch.",
        "",
    ]
    for story in main:
        lines.append(f"- {story['title']} - {story['operator_verdict']} - {story['confidence_label']}: {story['confidence_reason']}")
    return "\n".join(lines)


def render_story_html(story: dict[str, Any]) -> str:
    notes = []
    for note in story["evidence_notes"]:
        notes.append(
            f"""<div class="note">
<p><strong>Source note:</strong> {html.escape(note['note_text'])}</p>
<dl>
<dt>Source class</dt><dd>{html.escape(note['source_class'])}</dd>
<dt>Freshness</dt><dd>{html.escape(note['freshness'])}</dd>
<dt>Place</dt><dd>{html.escape(note['place'])}</dd>
<dt>Map/geometry</dt><dd>{html.escape(note['map_or_geometry_ref'])}</dd>
<dt>Supports</dt><dd>{html.escape(note['supports'])}</dd>
<dt>Does not prove</dt><dd>{html.escape(note['does_not_prove'])}</dd>
</dl>
</div>"""
        )
    cannot = "".join(f"<li>{html.escape(item)}</li>" for item in story["cannot_claim"])
    uncertainty = "".join(f"<li>{html.escape(item)}</li>" for item in story["uncertainty"])
    return f"""<article class="card" id="{html.escape(story['story_id'])}">
<h2>Verdict: {html.escape(story['operator_verdict'].replace('_', ' ').title())} - {html.escape(story['title'])}</h2>
<section class="decision"><strong>Your decision:</strong>
<label><input type="checkbox"> Watch this</label>
<label><input type="checkbox"> Ignore for now</label>
<label><input type="checkbox"> Need more before deciding</label>
</section>
<h3>What/where</h3><p>{html.escape(story['what_where'])}</p>
<h3>So what</h3><p>{html.escape(story['so_what'])}</p>
<h3>Suggested next review step</h3><p>{html.escape(story['suggested_next_step'])}</p>
<h3>Confidence</h3><p>{html.escape(story['confidence_label'] + ' - ' + story['confidence_reason'])}</p>
<h3>Evidence snapshot</h3>{''.join(notes)}
<h3>What CityBrain is unsure about</h3><ul>{uncertainty}</ul>
<h3>What CityBrain will not claim</h3><ul>{cannot}</ul>
<h3>Your decision</h3>
<p>Choose: watch_this / ignore_for_now / need_more_before_deciding.</p>
<p class="ratings">Usefulness 1 2 3 4 5 &nbsp; Readability 1 2 3 4 5 &nbsp; Trust 1 2 3 4 5</p>
<p class="boundary">Founder-internal diagnostic only. No fuel, training, external validation, product readiness, customer readiness, or official action.</p>
</article>"""


def render_cards_html(main: list[dict[str, Any]]) -> str:
    cards = "\n".join(render_story_html(story) for story in main)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Operator Story Cards</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#1f2937;line-height:1.45}}
main{{max-width:980px;margin:0 auto;padding:28px}}
.card{{background:#fff;border:1px solid #d9e1ec;border-radius:8px;padding:22px;margin:0 0 18px}}
.decision{{background:#eef6ff;border:1px solid #bfdbfe;border-radius:6px;padding:10px;margin:10px 0}}
.note{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin:10px 0}}
dl{{display:grid;grid-template-columns:150px 1fr;gap:6px 12px;margin:0}} dt{{font-weight:bold;color:#475569}} dd{{margin:0}}
label{{display:inline-block;margin:4px 14px 4px 0}} .ratings,.boundary{{font-size:14px;color:#526173}}
</style>
</head>
<body><main>
<h1>Founder Operator Story Cards</h1>
{cards}
</main></body></html>
"""


def render_cards_md(main: list[dict[str, Any]]) -> str:
    lines = ["# Founder Operator Story Cards", ""]
    for story in main:
        lines.extend(
            [
                f"## Verdict: {story['operator_verdict'].replace('_', ' ').title()} - {story['title']}",
                "",
                "Your decision: watch_this / ignore_for_now / need_more_before_deciding",
                "",
                f"What/where: {story['what_where']}",
                f"So what: {story['so_what']}",
                f"Suggested next review step: {story['suggested_next_step']}",
                f"Confidence: {story['confidence_label']} - {story['confidence_reason']}",
                "",
                "Evidence snapshot:",
            ]
        )
        for note in story["evidence_notes"]:
            lines.extend(
                [
                    f"- Source note: {note['note_text']}",
                    f"  - Source class: {note['source_class']}",
                    f"  - Freshness: {note['freshness']}",
                    f"  - Place: {note['place']}",
                    f"  - Map/geometry: {note['map_or_geometry_ref']}",
                    f"  - Supports: {note['supports']}",
                    f"  - Does not prove: {note['does_not_prove']}",
                ]
            )
        lines.extend(
            [
                "",
                "What CityBrain is unsure about:",
                *[f"- {item}" for item in story["uncertainty"]],
                "",
                "What CityBrain will not claim:",
                *[f"- {item}" for item in story["cannot_claim"]],
                "",
                "Usefulness: 1 2 3 4 5",
                "Readability: 1 2 3 4 5",
                "Trust: 1 2 3 4 5",
                "",
            ]
        )
    return "\n".join(lines)


def render_appendix_html(appendix: list[dict[str, Any]], weak_old: list[dict[str, Any]]) -> str:
    rows = []
    for story in appendix:
        rows.append(f"<tr><td>{html.escape(story['story_id'])}</td><td>{html.escape(story['classification'])}</td><td>{html.escape(story['title'])}</td></tr>")
    for card in weak_old:
        rows.append(f"<tr><td>{html.escape(str(card.get('source_card_id')))}</td><td>previous weak diagnostic card</td><td>{html.escape(str(card.get('title')))}</td></tr>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Weak Diagnostic Appendix</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f5f7fb;color:#1f2937}}table{{border-collapse:collapse;width:100%;background:#fff}}td,th{{border:1px solid #e2e8f0;padding:8px;text-align:left;vertical-align:top}}th{{background:#edf2f7}}</style></head>
<body><h1>Weak Diagnostic Appendix</h1><p>These cards are useful for diagnostics but not used to pad the founder-grade main set.</p>
<table><thead><tr><th>ID</th><th>Reason/class</th><th>Title</th></tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""


def render_appendix_md(appendix: list[dict[str, Any]], weak_old: list[dict[str, Any]]) -> str:
    lines = ["# Weak Diagnostic Appendix", "", "These cards are useful for diagnostics but not used to pad the founder-grade main set.", ""]
    for story in appendix:
        lines.append(f"- {story['story_id']}: {story['classification']} - {story['title']}")
    for card in weak_old:
        lines.append(f"- {card.get('source_card_id')}: previous weak diagnostic card - {card.get('title')}")
    return "\n".join(lines)


def render_csv(main: list[dict[str, Any]]) -> str:
    fields = [
        "story_id",
        "title",
        "classification",
        "operator_verdict",
        "usefulness_1_to_5",
        "readability_1_to_5",
        "trust_1_to_5",
        "what_would_make_this_confident",
        "audience_fit_operator_manager_public_or_none",
        "free_text_notes",
        "founder_internal",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "product_review_ready",
        "client_ready",
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for story in main:
        writer.writerow(
            {
                "story_id": story["story_id"],
                "title": story["title"],
                "classification": story["classification"],
                "operator_verdict": story["operator_verdict"],
                "usefulness_1_to_5": "",
                "readability_1_to_5": "",
                "trust_1_to_5": "",
                "what_would_make_this_confident": "",
                "audience_fit_operator_manager_public_or_none": "",
                "free_text_notes": "",
                "founder_internal": "true",
                "operator_fuel": "false",
                "training_eligible": "false",
                "external_operator_validation": "false",
                "product_review_ready": "false",
                "client_ready": "false",
            }
        )
    return output.getvalue()


def audience_backlog() -> str:
    return """# Founder Story Audience Backlog

Built now: operator-view founder diagnostic stories.

Manager rollup remains backlog: counts, clusters, trend, oldest issue age, risk if ignored, and confidence distribution.

Public-human view remains backlog: plain meaning, location anchor, what might be happening, what is not confirmed, why it matters to a person, and zero internal system vocabulary.
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
    stories, weak_old_cards, discovery = materialize_candidates()
    main, appendix = select_main(stories)
    m = metrics(main)
    status = STATUS_PASS if m["pass_bar_met"] else STATUS_NOT_ENOUGH
    decision = {
        "artifact_id": "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION",
        "task_id": "MAIN-CITYBRAIN-FOUNDER-GRADE-STORY-MATERIALIZATION-R1",
        "status": status,
        "main_story_count": m["main_story_count"],
        "watch_candidate_count": m["watch_candidate_count"],
        "ignore_candidate_count": m["ignore_candidate_count"],
        "need_more_candidate_count": m["need_more_candidate_count"],
        "cross_domain_story_count": m["cross_domain_story_count"],
        "founder_review_allowed": status == STATUS_PASS,
        "product_review_ready": False,
        "client_ready": False,
        "operator_fuel": False,
        "training_eligible": False,
        "source_truth_mutated": False,
        "metrics": m,
        "next_recommendation": "RUN_FOUNDER_OPERATOR_REVIEW_FROM_MATERIALIZED_STORIES_WITH_LIMITATIONS"
        if status == STATUS_PASS
        else "SOURCE_OR_STORY_DEPTH_EXPANSION_REQUIRED_BEFORE_FOUNDER_REVIEW",
    }
    classification = {
        "artifact_id": "FOUNDER_STORY_CANDIDATE_CLASSIFICATION_LEDGER",
        "candidate_count": len(stories),
        "rows": [
            {
                "story_id": story["story_id"],
                "classification": story["classification"],
                "operator_verdict": story["operator_verdict"],
                "card_type": story["card_type"],
                "evidence_note_count": len(story["evidence_notes"]),
                "selected_for_main": story in main,
            }
            for story in stories
        ],
    }
    materialization = {
        "artifact_id": "FOUNDER_STORY_MATERIALIZATION_LEDGER",
        "materialized_candidate_count": len(stories),
        "main_count": len(main),
        "appendix_candidate_count": len(appendix) + len(weak_old_cards),
        "derived_labels_policy": "Derived place labels are candidate-only, non-authoritative, and backed by existing geometry/source references.",
        "rows": [
            {
                "story_id": story["story_id"],
                "source_refs": [note["source_ref"] for note in story["evidence_notes"]],
                "source_paths": sorted({note["source_path"] for note in story["evidence_notes"]}),
                "derived_place_label": story["place_anchor"]["human_label"],
                "source_truth_mutated": False,
            }
            for story in stories
        ],
    }
    batch = {
        "artifact_id": "FOUNDER_GRADE_STORY_BATCH_INDEX",
        "status": status,
        "main_story_count": len(main),
        "stories": main,
        "appendix_story_count": len(appendix) + len(weak_old_cards),
    }
    write_json(out / "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json", decision)
    write_json(out / "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json", discovery)
    write_json(out / "FOUNDER_STORY_CANDIDATE_CLASSIFICATION_LEDGER.json", classification)
    write_json(out / "FOUNDER_STORY_MATERIALIZATION_LEDGER.json", materialization)
    write_json(out / "FOUNDER_GRADE_STORY_BATCH_INDEX.json", batch)
    write_text(out / "FOUNDER_OPERATOR_STORY_CARDS.html", render_cards_html(main))
    write_text(out / "FOUNDER_OPERATOR_STORY_CARDS.md", render_cards_md(main))
    write_text(out / "FOUNDER_REVIEW_START_HERE.html", render_start_html(main, status))
    write_text(out / "FOUNDER_REVIEW_START_HERE.md", render_start_md(main, status))
    write_text(out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv", render_csv(main))
    write_text(out / "FOUNDER_DIAGNOSTIC_APPENDIX_WEAK_DIAGNOSTIC_CARDS.html", render_appendix_html(appendix, weak_old_cards))
    write_text(out / "FOUNDER_DIAGNOSTIC_APPENDIX_WEAK_DIAGNOSTIC_CARDS.md", render_appendix_md(appendix, weak_old_cards))
    write_text(out / "FOUNDER_STORY_AUDIENCE_BACKLOG.md", audience_backlog())
    write_json(out / "FOUNDER_STORY_BOUNDARY_GUARD.json", boundary_guard())
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Founder-Grade Story Materialization R1

Status: `{status}`

- Main stories: `{m['main_story_count']}`
- Watch candidates: `{m['watch_candidate_count']}`
- Ignore candidates: `{m['ignore_candidate_count']}`
- Need-more candidates: `{m['need_more_candidate_count']}`
- Cross-domain stories: `{m['cross_domain_story_count']}`

Blockers:
{chr(10).join('- ' + item for item in m['blockers']) if m['blockers'] else '- none'}

Boundaries: candidate-only materialization over existing artifacts; no founder session result, operator fuel, training rows, source-truth mutation, live ingestion claim, ForecastPacket, official action/control/enforcement, or product/client-ready claim.
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
    decision = read_json(out / "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json")
    batch = read_json(out / "FOUNDER_GRADE_STORY_BATCH_INDEX.json")
    classification = read_json(out / "FOUNDER_STORY_CANDIDATE_CLASSIFICATION_LEDGER.json")
    boundary = read_json(out / "FOUNDER_STORY_BOUNDARY_GUARD.json")
    text = main_path_text(out)

    if decision["status"] not in ALLOWED_STATUSES:
        errors.append(f"invalid decision status: {decision['status']}")
    if decision["status"] == STATUS_PASS:
        if not decision["metrics"]["pass_bar_met"]:
            errors.append("PASS without pass bar")
        if decision["main_story_count"] < PASS_BAR["minimum_founder_grade_stories"]:
            errors.append("PASS with too few main stories")
        if decision["watch_candidate_count"] < PASS_BAR["minimum_watch_candidates"]:
            errors.append("PASS with too few watch candidates")
        if decision["cross_domain_story_count"] < PASS_BAR["minimum_cross_domain_stories"]:
            errors.append("PASS with too few cross-domain stories")
        if decision["ignore_candidate_count"] < PASS_BAR["minimum_ignore_candidates"]:
            errors.append("PASS with too few ignore candidates")
        if decision["need_more_candidate_count"] > PASS_BAR["maximum_need_more_stories"]:
            errors.append("PASS with too many need-more stories")
    if decision["status"] == STATUS_NOT_ENOUGH and decision["metrics"]["pass_bar_met"]:
        errors.append("not-enough status despite pass bar")
    if len(batch.get("stories", [])) != decision["main_story_count"]:
        errors.append("batch story count mismatch")
    for row in classification.get("rows", []):
        if row["classification"] not in CLASSIFICATIONS:
            errors.append(f"unknown classification: {row['classification']}")
    for story in batch.get("stories", []):
        for key in ["operator_verdict", "what_where", "so_what", "suggested_next_step", "confidence_label", "confidence_reason", "evidence_notes", "cannot_claim"]:
            if not story.get(key):
                errors.append(f"main story missing {key}: {story.get('story_id')}")
        if len(story.get("evidence_notes", [])) < 2:
            errors.append(f"main story has thin evidence: {story.get('story_id')}")
        if story.get("audience_fit") != "operator":
            errors.append(f"main story has bad audience fit: {story.get('story_id')}")
    hits = technical_hits(text)
    if hits:
        errors.append(f"banned technical terms in main founder path: {hits}")
    for key, value in {
        "founder_session_result_created": False,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "learning_arming_allowed": False,
        "source_truth_mutated": False,
        "live_ingestion_claim": False,
        "forecast_packet_created": False,
        "official_workflow_case_action_control_enforcement_created": False,
        "product_review_ready": False,
        "client_ready": False,
    }.items():
        if boundary.get(key) is not value:
            errors.append(f"boundary guard mismatch for {key}")
    if not (PUB / "FOUNDER_REVIEW_START_HERE.html").exists():
        errors.append("publication start page missing")
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
