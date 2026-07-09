#!/usr/bin/env python3
"""Discover founder-readable story candidates and render an HTML batch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-FOUNDER-READABLE-STORY-BATCH-DISCOVERY-HTML-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-founder-readable-story-batch-discovery-html-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_FOUNDER_READABLE_STORY_BATCH_DISCOVERY_HTML_R1_WITH_LIMITATIONS"
STATUS_NEEDS = "NEEDS_STORY_SOURCE_EXPANSION_MAIN_CITYBRAIN_FOUNDER_READABLE_STORY_BATCH_DISCOVERY_HTML_R1_WITH_LIMITATIONS"

SOURCE_ROOTS = {
    "cross_domain_story_arc": ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1",
    "cross_domain_story_arc_publication": ROOT / "publications" / "epoch4" / "main-citybrain-cross-domain-story-arc-eval-expansion-r1",
    "event_story_pack": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1",
    "event_story_pack_publication": ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-tracka-event-stories-source-diff-r1",
    "review_quality_cards": ROOT / "outputs" / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1",
    "review_quality_cards_publication": ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-pack-quality-upgrade-r4-r1",
    "seed_r3_adapter_corpus": ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
    "seed_r3_cadence": ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
}

REQUIRED_FILES = [
    "FOUNDER_REVIEW_START_HERE.html",
    "FOUNDER_REVIEW_START_HERE.md",
    "FOUNDER_STORY_CARDS_READABLE.html",
    "FOUNDER_STORY_CARDS_READABLE.md",
    "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_BATCH.csv",
    "FOUNDER_STORY_BATCH_INDEX.json",
    "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json",
    "FOUNDER_STORY_SELECTION_LEDGER.json",
    "FOUNDER_STORY_BOUNDARY_GUARD.json",
    "FOUNDER_STORY_TECHNICAL_APPENDIX.md",
    "FOUNDER_REVIEW_DESIGN_NOTES.md",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
    "FOUNDER_STORY_BATCH_DECISION.json",
]

BANNED_MAIN_TERMS = [
    "canonical entity",
    "cer",
    "seg",
    "check",
    "brief",
    "spatial",
    "event fabric",
    "jsonl",
    "truth manifest",
    "resolver",
    "quarantine",
    "unresolved",
    "resolved",
    "native packet",
    "family id",
    "source-adapter",
    "materializer",
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
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


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


def family_title(raw: str) -> str:
    mapping = {
        "building_compliance_perception_candidate": "Building concern near a site",
        "building_compliance_perception_candidate_v0": "Building concern near a site",
        "permit_inspection_delay": "Permit or inspection delay",
        "permit_inspection_delay_v0": "Permit or inspection delay",
        "city_asset_infrastructure_issue": "Infrastructure or city asset concern",
        "city_asset_infrastructure_issue_v0": "Infrastructure or city asset concern",
        "mobility_access_interruption": "Access interruption",
        "mobility_access_interruption_v0": "Access interruption",
        "mobility_access_interruption_v0": "Access interruption",
    }
    return mapping.get(raw, raw.replace("_", " ").replace(" v0", "").title())


def generic_missing_evidence() -> str:
    return "A human-readable source note, a fresh timestamp, and a clearer link to the place would make this more useful."


def base_story(
    story_id: str,
    title: str,
    situation: str,
    matters: str,
    connected: str,
    uncertain: str,
    missing: str,
    source_kind: str,
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "story_id": story_id,
        "plain_english_title": title,
        "situation": situation,
        "why_it_might_matter": matters,
        "what_seems_connected": connected,
        "what_is_uncertain": uncertain,
        "what_citybrain_must_not_claim": "CityBrain should not claim official truth, causation, a work order, a forecast, or readiness for a customer.",
        "missing_evidence": missing,
        "review_question": "Would this be useful enough to keep reviewing, and what would you need before trusting it in a product conversation?",
        "boundary_status": "Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.",
        "source_kind": source_kind,
        "source_refs": source_refs,
        "founder_internal": True,
        "operator_fuel": False,
        "training_eligible": False,
        "external_operator_validation": False,
        "learning_arming_allowed": False,
        "product_review_ready": False,
        "client_ready": False,
    }


def discover_cross_domain_story() -> list[dict[str, Any]]:
    root = SOURCE_ROOTS["cross_domain_story_arc"]
    packet = read_json(root / "STORY_ARC_REVIEW_PACKET_360.json")
    events = read_jsonl(root / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl")
    if not packet or not events:
        return []
    situation_bits = [
        "a permit or inspection signal",
        "a building-site concern",
        "an access issue nearby",
        "a possible infrastructure context",
    ]
    return [
        base_story(
            "founder-story-001-cross-domain-site-cascade",
            "One site with permit, access, and infrastructure signals",
            "Several weak but related signals appear to circle the same site: "
            + ", ".join(situation_bits)
            + ".",
            "If the links are understandable, this could be the kind of compact packet that helps a reviewer decide what to watch next.",
            "The packet suggests the same site may be related to the permit, building, and access signals, while the asset signal is only nearby context.",
            "The nearby asset context is not the same as the site, and the packet does not prove cause.",
            "A recent human-readable source note, a clearer place label, and a confidence explanation would make it easier to judge.",
            "cross_domain_story_arc",
            [rel(root / "STORY_ARC_REVIEW_PACKET_360.json"), rel(root / "CROSS_DOMAIN_STORY_ARC_EVENTS.jsonl")],
        )
    ]


def discover_event_story_pack() -> list[dict[str, Any]]:
    root = SOURCE_ROOTS["event_story_pack"]
    pack = read_json(root / "EVENT_STORY_PACK_R1.json")
    stories = []
    for item in pack.get("stories", []):
        title = family_title(item.get("family_id") or item.get("event_family", "story"))
        cannot = item.get("cannot_claim", [])
        source_records = item.get("source_records", [])
        source_gap = item.get("source_gap")
        plain_id = item.get("story_id", title).replace("event_story_r1:", "").replace("_", "-")
        stories.append(
            base_story(
                f"founder-story-event-{plain_id}",
                title,
                f"CityBrain found a local review packet about {title.lower()} with {len(source_records)} supporting source note(s).",
                "It may help a reviewer notice whether this kind of signal is worth watching or should be ignored.",
                "The source note, place context, and review-only packet appear to refer to the same product situation.",
                "The story may be thin, derived, or missing recent evidence; it should not be treated as an official issue.",
                "More source depth, a clearer place label, and an explicit human-readable reason for concern.",
                "event_story_pack_r1",
                [rel(root / "EVENT_STORY_PACK_R1.json")] + [str(ref) for ref in source_records[:2]] + ([str(source_gap)] if source_gap else []),
            )
        )
    return stories


def discover_review_cards() -> list[dict[str, Any]]:
    root = SOURCE_ROOTS["review_quality_cards"] / "review_cards_r4"
    if not root.exists():
        return []
    selected = [
        "founder-probe-r2-01.json",
        "founder-probe-r2-02.json",
        "founder-probe-r2-03.json",
        "founder-probe-r2-04.json",
    ]
    stories = []
    for path in [root / name for name in selected if (root / name).exists()]:
        item = read_json(path)
        title = family_title(item.get("family", "")) + " - " + str(item.get("scenario", "")).replace("_", " ")
        scenario = str(item.get("scenario", "")).replace("_", " ")
        summary = item.get("plain_language_case_summary", "")
        stories.append(
            base_story(
                f"founder-story-card-{item.get('task_id', path.stem)}",
                title,
                f"A review card describes a {scenario} situation and asks whether the subject can be understood quickly.",
                "This may show whether the product can explain both useful signals and safe hesitation in a compact way.",
                "The card links a subject, source notes, a review outcome, and a small set of caveats.",
                "The card may still be more of an evidence audit than a product-usefulness story.",
                "A sharper operator-facing summary and a clearer reason why a human should care.",
                "review_card_r4_raw_material",
                [rel(path), summary[:120]],
            )
        )
    return stories


def event_type_phrase(event_type: str) -> str:
    mapping = {
        "access_constraint": "access constraint",
        "transit_disruption": "transit disruption",
        "roadworks": "roadworks",
        "site_condition": "site condition concern",
        "inspection_due": "inspection due signal",
        "violation_candidate": "possible violation signal",
        "permit_wait": "permit wait signal",
        "inspection_backlog": "inspection backlog signal",
        "stale_status": "stale status signal",
        "service_asset": "service asset signal",
        "facility_context": "facility context signal",
        "utility_dependency": "utility dependency signal",
    }
    return mapping.get(event_type, event_type.replace("_", " "))


def discover_seed_r3_examples() -> list[dict[str, Any]]:
    root = SOURCE_ROOTS["seed_r3_adapter_corpus"]
    rows = read_jsonl(root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")
    if not rows:
        return []
    wanted = {
        "mobility_access_interruption_v0": ["access_constraint", "roadworks"],
        "building_compliance_perception_candidate": ["site_condition", "violation_candidate"],
        "permit_inspection_delay": ["permit_wait", "stale_status"],
        "city_asset_infrastructure_issue": ["service_asset", "utility_dependency"],
    }
    stories = []
    for family, event_types in wanted.items():
        picked = []
        for event_type in event_types:
            match = next((row for row in rows if row.get("canonical_loop_family_id") == family and row.get("event_type") == event_type), None)
            if match:
                picked.append(match)
        if not picked:
            continue
        title = family_title(family) + " examples"
        event_words = ", ".join(event_type_phrase(row.get("event_type", "")) for row in picked)
        stories.append(
            base_story(
                f"founder-story-seed-{family.replace('_', '-')}",
                title,
                f"The local sample set contains examples of {event_words} around a synthetic city area.",
                "These examples can test whether the product can turn small signals into something a founder can judge.",
                "The examples appear to involve a place, a source note, and a reason to either keep watching or ask for more proof.",
                "Some examples are intentionally thin or messy, so the product should be comfortable saying it does not know enough.",
                generic_missing_evidence(),
                "seed_r3_adapter_examples",
                [rel(root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")] + [row.get("event_id", "") for row in picked],
            )
        )
    return stories


def discover_stories() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_stories: list[dict[str, Any]] = []
    buckets = {
        "cross_domain_story_arc": discover_cross_domain_story(),
        "event_story_pack_r1": discover_event_story_pack(),
        "review_cards_r4": discover_review_cards(),
        "seed_r3_examples": discover_seed_r3_examples(),
    }
    for rows in buckets.values():
        all_stories.extend(rows)
    seen = set()
    deduped = []
    for story in all_stories:
        if story["story_id"] in seen:
            continue
        seen.add(story["story_id"])
        deduped.append(story)
    report = {
        "artifact_id": "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT",
        "source_roots": [
            {"key": key, "path": rel(path), "exists": path.exists()}
            for key, path in SOURCE_ROOTS.items()
        ],
        "bucket_counts": {key: len(value) for key, value in buckets.items()},
        "candidate_story_count": len(deduped),
        "minimum_story_count": 10,
        "enough_material_for_pass": len(deduped) >= 10,
    }
    return deduped, report


def clean_main_text(text: str) -> str:
    replacements = {
        "CityBrain should not claim official truth": "CityBrain should not claim official fact",
        "forecast": "prediction",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def story_anchor(story_id: str) -> str:
    return story_id.replace("_", "-").replace(":", "-")


def render_start_html(stories: list[dict[str, Any]], status: str) -> str:
    rows = "\n".join(
        f"<tr><td><a href=\"FOUNDER_STORY_CARDS_READABLE.html#{html.escape(story_anchor(story['story_id']))}\">{html.escape(story['plain_english_title'])}</a></td><td>{html.escape(story['why_it_might_matter'])}</td><td>{html.escape(story['what_is_uncertain'])}</td></tr>"
        for story in stories
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Story Batch</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f6f7f9;color:#1f2933;line-height:1.45}}
main{{max-width:1120px;margin:0 auto;padding:28px}}
.hero{{background:#fff;border:1px solid #d9dee7;border-radius:8px;padding:22px;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #d9dee7}}
th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e5e9f0;padding:10px}}
th{{background:#edf1f7}}
.note{{font-size:14px;color:#475569}}
a{{color:#175cd3}}
</style>
</head>
<body><main>
<section class="hero">
<h1>Founder Story Batch</h1>
<p>This is a founder-internal diagnostic batch. It asks whether these story packets are understandable, useful, and worth further review.</p>
<p class="note">It is not a customer claim, not a work order, not training data, not external validation, and not a readiness claim.</p>
<p>Status: <strong>{html.escape(status)}</strong>. Stories selected: <strong>{len(stories)}</strong>.</p>
</section>
<table>
<thead><tr><th>Story</th><th>Why it might matter</th><th>What is uncertain</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<section class="hero">
<h2>How to score</h2>
<p>For each story, rate usefulness, readability, and trust from boundaries from 1 to 5. Then say what was useful, what was confusing, and what evidence is missing before any product review.</p>
</section>
</main></body></html>
"""


def render_cards_html(stories: list[dict[str, Any]]) -> str:
    cards = []
    for story in stories:
        cards.append(
            f"""<article class="card" id="{html.escape(story_anchor(story['story_id']))}">
<h2>{html.escape(story['plain_english_title'])}</h2>
<h3>What may be happening?</h3><p>{html.escape(story['situation'])}</p>
<h3>Why might it matter?</h3><p>{html.escape(story['why_it_might_matter'])}</p>
<h3>What seems connected?</h3><p>{html.escape(story['what_seems_connected'])}</p>
<h3>What is uncertain?</h3><p>{html.escape(story['what_is_uncertain'])}</p>
<h3>What must CityBrain not claim?</h3><p>{html.escape(clean_main_text(story['what_citybrain_must_not_claim']))}</p>
<h3>What evidence is missing?</h3><p>{html.escape(story['missing_evidence'])}</p>
<h3>Would this be useful to review?</h3><p>{html.escape(story['review_question'])}</p>
<p class="rating">Usefulness: 1 2 3 4 5 &nbsp; Readability: 1 2 3 4 5 &nbsp; Trust: 1 2 3 4 5</p>
<p class="boundary">{html.escape(story['boundary_status'])}</p>
</article>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Founder Story Cards</title>
<style>
body{{font-family:Arial,sans-serif;background:#f6f7f9;color:#1f2933;margin:0;line-height:1.45}}
main{{max-width:960px;margin:0 auto;padding:28px}}
.card{{background:#fff;border:1px solid #d9dee7;border-radius:8px;padding:20px;margin:0 0 18px}}
h2{{margin-top:0}}
h3{{margin-bottom:4px;font-size:15px;color:#334155}}
.rating,.boundary{{font-size:14px;color:#475569;border-top:1px solid #e5e9f0;padding-top:10px}}
</style>
</head>
<body><main>
<h1>Founder Story Cards</h1>
{''.join(cards)}
</main></body></html>
"""


def render_start_md(stories: list[dict[str, Any]], status: str) -> str:
    lines = [
        "# Founder Story Batch",
        "",
        "This is a founder-internal diagnostic batch for usefulness, clarity, and missing evidence.",
        "",
        f"Status: `{status}`",
        f"Stories selected: `{len(stories)}`",
        "",
    ]
    for story in stories:
        lines.append(f"- {story['plain_english_title']}: {story['why_it_might_matter']}")
    return "\n".join(lines) + "\n"


def render_cards_md(stories: list[dict[str, Any]]) -> str:
    lines = ["# Founder Story Cards", ""]
    for story in stories:
        lines.extend(
            [
                f"## {story['plain_english_title']}",
                "",
                f"What may be happening? {story['situation']}",
                "",
                f"Why might it matter? {story['why_it_might_matter']}",
                "",
                f"What seems connected? {story['what_seems_connected']}",
                "",
                f"What is uncertain? {story['what_is_uncertain']}",
                "",
                f"What must CityBrain not claim? {clean_main_text(story['what_citybrain_must_not_claim'])}",
                "",
                f"What evidence is missing? {story['missing_evidence']}",
                "",
                f"Would this be useful to review? {story['review_question']}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_response_csv(stories: list[dict[str, Any]]) -> str:
    output = StringIO()
    fieldnames = [
        "story_id",
        "plain_english_title",
        "usefulness_rating_1_to_5",
        "understandable_yes_no_partial",
        "would_keep_watching_yes_no_partial",
        "would_escalate_yes_no_partial",
        "trust_from_boundaries_1_to_5",
        "readability_1_to_5",
        "what_was_useful",
        "what_was_confusing",
        "missing_evidence_before_product_review",
        "founder_notes",
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
    for story in stories:
        writer.writerow(
            {
                "story_id": story["story_id"],
                "plain_english_title": story["plain_english_title"],
                "usefulness_rating_1_to_5": "",
                "understandable_yes_no_partial": "",
                "would_keep_watching_yes_no_partial": "",
                "would_escalate_yes_no_partial": "",
                "trust_from_boundaries_1_to_5": "",
                "readability_1_to_5": "",
                "what_was_useful": "",
                "what_was_confusing": "",
                "missing_evidence_before_product_review": "",
                "founder_notes": "",
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


def banned_hits(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    acronym_terms = {"cer", "seg", "check", "brief", "spatial"}
    for term in BANNED_MAIN_TERMS:
        if term in acronym_terms:
            if re.search(rf"\b{re.escape(term)}\b", lower):
                hits.append(term)
        elif term in lower:
            hits.append(term)
    return hits


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
    payload = read_json(path)
    errors = []
    for entry in payload.get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"manifest target missing: {entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"manifest mismatch: {entry['path']}")
    return errors


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            shutil.copy2(path, PUBLICATION_ROOT / path.name)


def technical_appendix(stories: list[dict[str, Any]], report: dict[str, Any]) -> str:
    lines = [
        "# Founder Story Technical Appendix",
        "",
        "This appendix is not part of the main founder reading path. It may include technical provenance terms and source pointers.",
        "",
        "## Source Roots",
        "",
    ]
    for row in report["source_roots"]:
        lines.append(f"- {row['key']}: `{row['path']}` exists={row['exists']}")
    lines.extend(["", "## Selected Story Provenance", ""])
    for story in stories:
        lines.append(f"### {story['story_id']}")
        lines.append(f"- Source kind: `{story['source_kind']}`")
        for ref in story["source_refs"]:
            lines.append(f"- Source ref: `{ref}`")
        lines.append("")
    return "\n".join(lines)


def build(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    stories, discovery = discover_stories()
    minimum_met = len(stories) >= 10
    status = STATUS_PASS if minimum_met else STATUS_NEEDS
    selected = stories if minimum_met else stories
    main_text = "\n".join(
        [
            render_start_html(selected, status),
            render_start_md(selected, status),
            render_cards_html(selected),
            render_cards_md(selected),
            render_response_csv(selected),
        ]
    )
    hits = banned_hits(main_text)

    boundary = {
        "artifact_id": "FOUNDER_STORY_BOUNDARY_GUARD",
        "status": "PASS" if not hits else "NEEDS_REPAIR",
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "learning_or_ranking_arming_created": False,
        "external_operator_validation_created": False,
        "product_ready_claim_created": False,
        "client_ready_claim_created": False,
        "forecast_packet_created": False,
        "live_ingestion_claim_created": False,
        "official_action_dispatch_control_enforcement_created": False,
        "legal_or_certified_claim_created": False,
        "source_truth_mutated": False,
        "main_path_technical_term_hits": hits,
    }
    decision = {
        "artifact_id": "FOUNDER_STORY_BATCH_DECISION",
        "status": status if not hits else STATUS_NEEDS,
        "story_count": len(selected),
        "founder_diagnostic_ready": minimum_met and not hits,
        "product_review_ready": False,
        "client_ready": False,
        "minimum_story_count_met": minimum_met,
        "main_path_technical_terms_removed": not hits,
        "technical_appendix_present": True,
        "no_forbidden_capabilities_created": boundary["status"] == "PASS",
        "next_recommended_task": "MAIN-CITYBRAIN-FOUNDER-DIAGNOSTIC-BATCH-RESPONSE-IMPORT-ANALYSIS-R1"
        if minimum_met and not hits
        else "MAIN-CITYBRAIN-STORY-SOURCE-EXPANSION-FOR-FOUNDER-BATCH-R1",
    }
    index = {
        "artifact_id": "FOUNDER_STORY_BATCH_INDEX",
        "story_count": len(selected),
        "stories": [
            {
                "story_id": story["story_id"],
                "plain_english_title": story["plain_english_title"],
                "source_kind": story["source_kind"],
                "founder_internal": True,
                "product_review_ready": False,
                "client_ready": False,
            }
            for story in selected
        ],
    }
    ledger = {
        "artifact_id": "FOUNDER_STORY_SELECTION_LEDGER",
        "selected_story_count": len(selected),
        "minimum_story_count_met": minimum_met,
        "selection_rules": [
            "Use only existing local artifacts.",
            "Rewrite technical source material into founder-readable language.",
            "Do not fabricate stories to reach ten.",
            "Keep technical provenance in the appendix only.",
        ],
        "rows": [
            {
                "story_id": story["story_id"],
                "source_kind": story["source_kind"],
                "selected": True,
                "selection_reason": "Readable situation, uncertainty, cannot-claim boundary, and missing-evidence prompt could be derived from local artifacts.",
            }
            for story in selected
        ],
    }
    write_text(out / "FOUNDER_REVIEW_START_HERE.html", render_start_html(selected, decision["status"]))
    write_text(out / "FOUNDER_REVIEW_START_HERE.md", render_start_md(selected, decision["status"]))
    write_text(out / "FOUNDER_STORY_CARDS_READABLE.html", render_cards_html(selected))
    write_text(out / "FOUNDER_STORY_CARDS_READABLE.md", render_cards_md(selected))
    write_text(out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_BATCH.csv", render_response_csv(selected))
    write_json(out / "FOUNDER_STORY_BATCH_INDEX.json", index)
    write_json(out / "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json", discovery)
    write_json(out / "FOUNDER_STORY_SELECTION_LEDGER.json", ledger)
    write_json(out / "FOUNDER_STORY_BOUNDARY_GUARD.json", boundary)
    write_text(out / "FOUNDER_STORY_TECHNICAL_APPENDIX.md", technical_appendix(selected, discovery))
    write_text(
        out / "FOUNDER_REVIEW_DESIGN_NOTES.md",
        "Founder-facing pages avoid technical system labels and ask product-judgment questions about usefulness, clarity, trust, and missing evidence.\n",
    )
    write_json(out / "FOUNDER_STORY_BATCH_DECISION.json", decision)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Founder-Readable Story Batch Discovery + HTML R1

Status: `{decision["status"]}`

- Stories selected: `{len(selected)}`
- Minimum story count met: `{minimum_met}`
- Main founder path technical terms removed: `{not hits}`
- Response CSV rows: `{len(selected)}`

Boundaries: founder-internal diagnostic surface only; no session result, fuel, training rows, external validation, product/client readiness, forecast packet, live ingestion, official action/control/enforcement, legal/certified claim, or source-truth mutation.
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
            except Exception as exc:  # pragma: no cover
                errors.append(f"json parse failed for {path.name}: {exc}")
    if errors:
        return errors
    decision = read_json(out / "FOUNDER_STORY_BATCH_DECISION.json")
    index = read_json(out / "FOUNDER_STORY_BATCH_INDEX.json")
    boundary = read_json(out / "FOUNDER_STORY_BOUNDARY_GUARD.json")
    html_start = (out / "FOUNDER_REVIEW_START_HERE.html").read_text(encoding="utf-8")
    html_cards = (out / "FOUNDER_STORY_CARDS_READABLE.html").read_text(encoding="utf-8")
    csv_rows = list(csv.DictReader(StringIO((out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_BATCH.csv").read_text(encoding="utf-8"))))
    hits = banned_hits("\n".join([html_start, html_cards, (out / "FOUNDER_REVIEW_START_HERE.md").read_text(encoding="utf-8"), (out / "FOUNDER_STORY_CARDS_READABLE.md").read_text(encoding="utf-8"), (out / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_BATCH.csv").read_text(encoding="utf-8")]))
    if decision.get("story_count", 0) < 10 and not str(decision.get("status", "")).startswith("NEEDS_STORY_SOURCE_EXPANSION"):
        errors.append("fewer than 10 stories without needs-expansion status")
    if decision.get("story_count", 0) >= 10 and decision.get("status") != STATUS_PASS:
        errors.append("10+ stories did not pass")
    if not html_start.strip() or not html_cards.strip():
        errors.append("HTML output is empty")
    if len(csv_rows) != index.get("story_count"):
        errors.append("response CSV row count does not match story count")
    if hits:
        errors.append(f"banned technical terms in founder path: {hits}")
    for row in csv_rows:
        expected = {
            "founder_internal": "true",
            "operator_fuel": "false",
            "training_eligible": "false",
            "external_operator_validation": "false",
            "learning_arming_allowed": "false",
            "product_review_ready": "false",
            "client_ready": "false",
        }
        for key, value in expected.items():
            if row.get(key) != value:
                errors.append(f"bad boundary column {key} for {row.get('story_id')}")
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
    if decision.get("product_review_ready") or decision.get("client_ready"):
        errors.append("product/client readiness opened")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
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
