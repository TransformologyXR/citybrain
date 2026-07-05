#!/usr/bin/env python3
"""Run D14 route taxonomy repair v0.4B boundary-stability pass.

v0.4B keeps the v0.4A subject-answer architecture intact and only tightens
the unstable boundaries found in the v0.4A double-label audit. It stops at the
independent-label gate and does not run Split/Seal R3 or router preflight.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
V04A_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1"
ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04b_boundary_stability_r1"
PROMPT_ROOT = (
    REPO
    / "tmp"
    / "citybrain_d14_route_taxonomy_repair_v04b_boundary_stability_r1"
    / "citybrain_d14_route_taxonomy_repair_v04b_boundary_stability_r1"
)
TOPUP_ROOT = REPO / "inputs" / "d14_synthetic_operator_questions" / "hard_shaped_topup"

TASK = "MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04B-BOUNDARY-STABILITY-R1"
STATUS = "PAUSED_D14_ROUTE_TAXONOMY_V04B_AWAITING_INDEPENDENT_DOUBLE_LABELS"
TAXONOMY_VERSION = "route_taxonomy_v04b_boundary_stability"

INPUTS = {
    "v04a_audit": V04A_ROOT / "D14_DOUBLE_LABEL_V04A_AUDIT.json",
    "v04a_comparison_md": V04A_ROOT / "D14_ROUTE_TAXONOMY_V04A_COMPARISON_REPORT.md",
    "v04a_contract": V04A_ROOT / "ROUTE_TAXONOMY_V04A_CONTRACT.json",
    "v04a_labeled": V04A_ROOT / "operator_question_corpus_synthetic_v0_labeled_v04a_codex_prelim.jsonl",
}

EXPECTED_INPUT_FILES = list(INPUTS.values())

LABELS: dict[str, dict[str, str | None]] = {
    "template:ask:subject_answer@v1:lens=support": {
        "kind": "template",
        "route_family": "ask_subject_answer",
        "lens": "support",
        "description": "Subject answer with evidence/source-support section first.",
    },
    "template:ask:subject_answer@v1:lens=uncertainty": {
        "kind": "template",
        "route_family": "ask_subject_answer",
        "lens": "uncertainty",
        "description": "Subject answer with uncertainty/missing-evidence section first.",
    },
    "template:ask:subject_answer@v1:lens=claimability": {
        "kind": "template",
        "route_family": "ask_subject_answer",
        "lens": "claimability",
        "description": "Subject answer with cannot-claim/proof-boundary section first.",
    },
    "template:ask:subject_answer@v1:lens=summary": {
        "kind": "template",
        "route_family": "ask_subject_answer",
        "lens": "summary",
        "description": "Subject answer with summary/knowns section first.",
    },
    "template:ask:entity_360@v2": {"kind": "template", "description": "Explicit entity/asset/profile lookup."},
    "ui_help": {"kind": "help", "description": "Board capability, workflow, and local boundary help."},
    "gap:patch_queue_query_needed": {"kind": "gap", "description": "Patch-board count/list/filter/compare/query consumer gap."},
    "gap:source_record_360_needed": {"kind": "gap", "description": "Fields/details/contents of one specific source row or record."},
    "gap:external_context_source_needed": {"kind": "gap", "description": "External context/source not connected to the local board."},
    "refuse:action_shaped": {
        "kind": "refusal",
        "expected_refusal_class": "action_shaped",
        "description": "Command/request to perform external action.",
    },
    "refuse:prediction_or_finding": {
        "kind": "refusal",
        "expected_refusal_class": "prediction_or_finding",
        "description": "Requested prediction, official/legal/certified finding, or unsupported world determination.",
    },
    "refuse:identity_or_person": {
        "kind": "refusal",
        "expected_refusal_class": "identity_or_person",
        "description": "Personal identity, owner, driver, contact, or biometric inference.",
    },
}

SUBJECT_LABELS = {label for label, meta in LABELS.items() if meta.get("route_family") == "ask_subject_answer"}
REFUSAL_CLASS_BY_LABEL = {
    label: meta["expected_refusal_class"]
    for label, meta in LABELS.items()
    if meta.get("kind") == "refusal"
}
DEPRECATED_LABELS = sorted(
    {
        "template:ask:what_supports@v1",
        "template:ask:what_is_uncertain@v1",
        "template:ask:cannot_claim@v1",
        "template:ask:entity_360@v1",
        "gap:boundary_status_template_needed",
        "gap:charging_site_source_depth_scan",
        "gap:external_context_source_needed:v04a_old",
        "gap:external_sharing_guidance",
        "gap:evidence_gap_template_needed",
        "gap:human_review_timestamp_status",
        "gap:local_note_visibility_guidance",
        "gap:patch_queue_aggregate_counts",
        "gap:patch_queue_filter_by_city",
        "gap:patch_queue_filtering_and_summary_by_city_date",
        "gap:patch_queue_open_count",
        "gap:patch_queue_update_date_comparison",
        "gap:planning_context_boundary_template_needed",
        "refuse:out_of_scope_entity",
    }
)

CANONICAL_ANCHORS = [
    {
        "row_id": "syn-v0-0020",
        "raw_question": "Can an operator certify a legal finding based on these local notes?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Capability/boundary question about local notes and legal finding; not a command to certify.",
    },
    {
        "row_id": "syn-v0-0029",
        "raw_question": "Does the asset 87 record include connector counts or power ratings?",
        "canonical_route_label": "gap:source_record_360_needed",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Asks for fields/details of a source row.",
    },
    {
        "row_id": "syn-v0-0035",
        "raw_question": "charger status??",
        "canonical_route_label": "template:ask:subject_answer@v1:lens=claimability",
        "canonical_refusal_class": None,
        "requires_selected_item_context": True,
        "canonical_reason": "Messy selected-EV status question; supported negative answer about no live availability.",
    },
    {
        "row_id": "syn-v0-0037",
        "raw_question": "List the evidence and uncertainty in the EV asset 87 source brief.",
        "canonical_route_label": "template:ask:subject_answer@v1:lens=support",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Asks for evidence/uncertainty in a named brief, not patch-board query.",
    },
    {
        "row_id": "syn-v0-0041",
        "raw_question": "What specific TfL TIMS records are currently linked to the Wood Lane item?",
        "canonical_route_label": "template:ask:subject_answer@v1:lens=support",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Asks which supporting records are linked to a selected city item.",
    },
    {
        "row_id": "syn-v0-0050",
        "raw_question": "Can this board alert someone if there is a problem?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Board capability question; not an instruction to alert.",
    },
    {
        "row_id": "syn-v0-0060",
        "raw_question": "Does any part of this patch certify a legal or official finding?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Board/patch boundary question; not a request to certify.",
    },
    {
        "row_id": "syn-v0-0062",
        "raw_question": "Can I tell others this is urgent?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Sharing/urgency-boundary guidance; not an external command.",
    },
    {
        "row_id": "syn-v0-0070",
        "raw_question": "Is there weather data available for this patch area?",
        "canonical_route_label": "gap:external_context_source_needed",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Asks for weather/external context not in the local cockpit.",
    },
    {
        "row_id": "syn-v0-0071",
        "raw_question": "is it rapid charging?",
        "canonical_route_label": "template:ask:entity_360@v2",
        "canonical_refusal_class": None,
        "requires_selected_item_context": True,
        "canonical_reason": "Selected EV entity attribute/profile question.",
    },
    {
        "row_id": "syn-v0-0076",
        "raw_question": "Is the ranking an urgency finding or just review order?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Board semantics and ranking boundary.",
    },
    {
        "row_id": "syn-v0-0128",
        "raw_question": "Why is there no live availability source in this bundle at all?",
        "canonical_route_label": "gap:external_context_source_needed",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Asks why external/live source coverage is absent.",
    },
    {
        "row_id": "syn-v0-0142",
        "raw_question": "Can we call the police department directly from this screen?",
        "canonical_route_label": "ui_help",
        "canonical_refusal_class": None,
        "requires_selected_item_context": False,
        "canonical_reason": "Board capability question; not an instruction to call.",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_inputs() -> None:
    missing = [path for path in EXPECTED_INPUT_FILES if not path.exists()]
    if missing:
        raise SystemExit("Missing required v0.4B inputs: " + ", ".join(rel(path) for path in missing))


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def preserve_independent_v04b_labels() -> dict[str, bytes]:
    preserved: dict[str, bytes] = {}
    for filename in [
        "CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS.jsonl",
        "CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS_REPORT.json",
    ]:
        path = ROOT / filename
        if path.exists():
            preserved[filename] = path.read_bytes()
    return preserved


def restore_preserved_files(preserved: dict[str, bytes]) -> None:
    for filename, data in preserved.items():
        (ROOT / filename).write_bytes(data)


def copy_prompt_pack() -> None:
    out = ROOT / "prompt_pack"
    out.mkdir(parents=True, exist_ok=True)
    if PROMPT_ROOT.exists():
        for path in sorted(PROMPT_ROOT.glob("*")):
            if path.is_file():
                shutil.copy2(path, out / path.name)


def normalize_question(raw: str) -> str:
    q = raw.strip()
    replacements = {"whats": "what is", "chrgr": "charger", "rn": "right now", "pls": "please", "ev": "EV", "nyc": "NYC", "mvc": "MVC", "uprn": "UPRN"}
    for src, dst in replacements.items():
        q = re.sub(rf"\b{re.escape(src)}\b", dst, q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if q and q[-1] not in "?!.":  # keep terse operator fragments readable
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def anchor_map() -> dict[str, dict[str, Any]]:
    return {item["row_id"]: item for item in CANONICAL_ANCHORS}


def is_anchor(row: dict[str, Any]) -> bool:
    anchor = anchor_map().get(row["question_id"])
    return bool(anchor and anchor["raw_question"] == row.get("raw_question"))


def subject_hint(raw: str, selected_context: str) -> str:
    q = raw.lower()
    context = selected_context.lower()
    if re.search(r"\b(ev\s*87|asset\s*87|charger\s*87|charging-site|rapid charger)\b", q) or context == "ev_asset_87":
        return "ev_asset_87"
    if re.search(r"\b(wood lane|scrubbs|scrubs|tfl|tims)\b", q):
        return "wood_lane_review_context"
    if re.search(r"\b(nyc|mvc|4463710|collision)\b", q) or context == "nyc_mvc_candidate_context":
        return "nyc_mvc_candidate_context"
    if re.search(r"\b(london|planning|uprn|d10|opportunity-area)\b", q):
        return "london_planning_context"
    if re.search(r"\b(queue|patch|item\s*#?\d+)\b", q) or context == "general_patch_board":
        return "patch_queue"
    if selected_context:
        return selected_context
    return "selected_subject"


def explicit_context_named(raw: str) -> bool:
    q = raw.lower()
    return bool(
        re.search(
            r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|scrubbs|scrubs|westway|nyc|mvc|4463710|uprn|london|chicago|tims-\d+|record\s*\d+|item\s*#?\d+|queue|patch|board|screen|software|source row|source record|london datastore|ranking|notes|export|police|weather|open items|all items)\b",
            q,
        )
    )


def requires_context_v04b(row: dict[str, Any]) -> bool:
    raw = str(row.get("raw_question", ""))
    q = raw.lower()
    if row.get("question_id") in anchor_map():
        return bool(anchor_map()[row["question_id"]]["requires_selected_item_context"])
    if re.fullmatch(r"\s*(charger status\?\?|is it rapid charging\??|is it working right now\??|what about this\??|what about that\??|run the check\??|what is missing here\??)\s*", q):
        return True
    if explicit_context_named(raw):
        return False
    if re.search(r"\b(this|that|it|here|selected|these|those)\b", q):
        return True
    return False


def route_v04b(row: dict[str, Any]) -> tuple[str, str | None, str | None]:
    row_id = row["question_id"]
    raw = str(row.get("raw_question", ""))
    q = raw.lower()
    anchor = anchor_map().get(row_id)
    if anchor and anchor["raw_question"] == raw:
        label = anchor["canonical_route_label"]
        return label, anchor["canonical_refusal_class"], LABELS.get(label, {}).get("lens")

    # Rule 1: identity/person questions.
    if re.search(r"\b(who is|who owns|who do i call|who should i call|which person|owner name|driver|face|biometric|identify|responsible person|contact details|personal identity)\b", q):
        return "refuse:identity_or_person", "identity_or_person", None

    # Rule 2: imperative external action. Capability questions are not action.
    capability = bool(re.search(r"\b(can this board|can the board|can we .*from this screen|directly from this screen|does the board|does this patch|can an operator|is the ranking|how do i|where do i|what button|whether .*screen|whether .*board)\b", q))
    if not capability:
        if re.search(r"\b(alert .*team|alert .*department|alert someone|dispatch|route traffic|route drivers|enforce|approve|create a case|create case|open a ticket|file a case|tell drivers now|tell the public|send .*email|send .*operator|call the police|call .*operator|call .*department|notify .*team|publish an alert now)\b", q):
            return "refuse:action_shaped", "action_shaped", None
        if re.match(r"^\s*(dispatch|route|enforce|approve|notify|alert|call|send|create|open|file|publish)\b", q):
            return "refuse:action_shaped", "action_shaped", None

    # Rule 3: board capability, workflow, and boundary help.
    if re.search(
        r"\b(can this board|can the board|can we .*from this screen|directly from this screen|does the board|does this patch|can an operator|local notes|certify a legal finding based on .*notes|screen can|screen.*call|board.*alert|board.*dispatch|ranking .*urgency|urgency finding|review order|how do i|where do i|what button|export|copy|add note|mark reviewed|open ask|generate brief|run check|checks panel|create.*case|local review only|activity saved|notes stored|visibility|can i tell others this is urgent)\b",
        q,
    ):
        return "ui_help", None, None

    # Rule 4: requested official/legal finding about the world.
    if re.search(r"\b(is this legally|legally non-compliant|will this cause|predict|tomorrow|next week|certify that|make an official finding|officially find|liable|fine them|compliance with|cyber security standards)\b", q):
        return "refuse:prediction_or_finding", "prediction_or_finding", None

    # Rule 5: patch-board query gap.
    if re.search(
        r"\b(show all|list all|list the three queue|list the queue|filter|compare|count|how many|which city has more|which item|highest ranked|ranked item|open items|updated today|updated yesterday|today versus yesterday|city/date|record count|same wood lane evidence gap|separate from item|records currently on file)\b",
        q,
    ):
        return "gap:patch_queue_query_needed", None, None

    # Rule 6: source-row profile gap.
    if re.search(
        r"\b(connector counts|power ratings|what fields|field-level|show me .*row|show me .*record|record .*details|tims-\d+.*fields|what exactly is in|contents of .*record|raw values|source row actually say|what does .*row.*say|what does .*record.*say)\b",
        q,
    ):
        return "gap:source_record_360_needed", None, None

    # Rule 7: external context/source gap.
    if re.search(r"\b(weather data|weather|live availability source|live service-status|external contacts|real-time data|where do we get the live|why is there no live availability source|external source|source is absent)\b", q):
        return "gap:external_context_source_needed", None, None

    # Rule 8: entity profile.
    if re.search(r"\b(is it rapid charging|rapid charging|what is ev asset|what is asset 87|what do we know about uprn|what is .*uprn|profile|look up|fast charger|normal charger|connector type|asset attribute|entity profile)\b", q):
        return "template:ask:entity_360@v2", None, None

    # Rule 9: subject answer lenses.
    if re.search(r"\b(what supports|source supports|which source|what source|sources support|records support|evidence supports|citations|what backs|backing evidence|evidence and uncertainty|source brief|source link|source records indicate|source records validate|specific .*records.*linked|list the evidence)\b", q):
        return "template:ask:subject_answer@v1:lens=support", None, "support"
    if re.search(r"\b(missing evidence|evidence missing|what evidence.*missing|what source.*needed|what would confirm|could confirm|before saying|before claiming|why .*candidate-only|candidate-only|verification absent|direct evidence|stronger evidence|source depth|no .*source|needed before|need before|what is missing before|what is uncertain|uncertain|unknowns|what do we not know|limitations|limitation|unclear|stale)\b", q):
        return "template:ask:subject_answer@v1:lens=uncertainty", None, "uncertainty"
    if re.search(r"\b(charger status|is .*working right now|can .*claim|can we claim|can .*prove|does this prove|what .*prove|what .*establish|what .*verified|verified by|certify|certified|legal finding|official finding|blocked|live|available|unavailable|availability|down|working now|avail now|current status|affected|caused|causality|what does this not prove|not proof|not prove|cannot claim|can .*be treated|only proximity|static registry|live status feed|proof .*existed|operational|access impact|changed availability|urgent|source record prove|row establish|constraints are verified)\b", q):
        return "template:ask:subject_answer@v1:lens=claimability", None, "claimability"
    if re.search(r"\b(what is going on|what do we know|summarize|summary|brief me|explain this|what happened)\b", q):
        return "template:ask:subject_answer@v1:lens=summary", None, "summary"
    if re.search(r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|selected item|this item)\b", q):
        return "template:ask:subject_answer@v1:lens=summary", None, "summary"

    return "ui_help", None, None


def clean_row_for_blind(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["question_id"],
        "raw_question": row.get("raw_question"),
        "persona": row.get("persona"),
        "selected_item_context": row.get("selected_item_context"),
        "source_type": row.get("source_type"),
        "source_session_id": row.get("source_session_id"),
        "original_question_id": row.get("original_question_id"),
    }


def create_contract() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04b_boundary_stability",
        "generated_at": now(),
        "status": "ACTIVE_FOR_V04B_DOUBLE_LABEL_GATE",
        "preserves_subject_answer_architecture": True,
        "closed_labels": sorted(LABELS),
        "route_labels": LABELS,
        "deprecated_labels": DEPRECATED_LABELS,
        "first_match_rules": [
            "identity_person_questions_refuse_identity_or_person",
            "imperative_external_action_refuse_action_shaped",
            "board_capability_workflow_boundary_help_ui_help",
            "requested_official_legal_world_finding_refuse_prediction_or_finding",
            "patch_board_query_gap",
            "source_row_profile_gap",
            "external_context_source_gap",
            "entity_profile_entity_360",
            "subject_answer_lenses",
        ],
        "core_boundary_rules": [
            "Capability question is not an action request.",
            "Field/details of one source row is source_record_360 gap.",
            "What the record supports/proves is subject_answer lens.",
            "Supported negative answers are not refusals.",
            "Board semantics/ranking/certification capability questions are ui_help.",
        ],
    }


def write_decision_tree() -> None:
    text = """# Route Taxonomy v0.4B Decision Tree

v0.4B preserves the v0.4A subject-answer architecture. Do not route back to
`what_supports`, `what_is_uncertain`, or `cannot_claim`.

## First-Match Rules

1. Identity/person questions: identifying a person, owner, driver, biometric identity, or contact
   details uses `refuse:identity_or_person`.
2. Imperative external action: commands to alert, dispatch, route, enforce, approve, create/send a
   case, contact someone, publish, fix, or call someone use `refuse:action_shaped`.
   Mentions of an action word are not enough. Capability questions go to Rule 3.
3. Board capability/workflow/boundary help: questions asking whether the board, cockpit, screen, or
   operator workflow can do something use `ui_help`. This includes whether the screen can call or
   alert, whether notes/export create a case, whether ranking means urgency, and whether local notes
   certify anything.
4. Requested official/legal finding about the world: if the user asks the system to determine,
   certify, predict, or legally find something about the world or situation, use
   `refuse:prediction_or_finding`. Capability questions about whether the board can certify remain
   `ui_help`.
5. Patch-board query gap: lists, counts, filters, comparisons, rankings, open items, city/date
   summaries, and queue item relationships use `gap:patch_queue_query_needed`.
6. Source-row profile gap: fields, columns, connector counts, power ratings, raw values, and details
   of one source row use `gap:source_record_360_needed`.
   What a record supports/proves/establishes is not this gap; use subject-answer support or
   claimability.
7. External context/source gap: weather, live service-status feeds, real-time data, missing external
   source coverage, or where to get unavailable outside context uses
   `gap:external_context_source_needed`.
8. Entity profile: basic facts about a selected or named entity/asset/place use
   `template:ask:entity_360@v2`.
9. Subject answer: all remaining supported questions about a selected subject/item/packet/brief use
   `template:ask:subject_answer@v1` with one lens:
   - support: evidence, source support, backing records, linked records.
   - uncertainty: missing, unclear, unknown, stale, or absent local records.
   - claimability: can/cannot claim, prove, establish, verify, certify, blocked/live/available status.
   - summary: what is going on, explain this item, overview.

## Context Flag

Set `requires_selected_item_context = true` only if the raw question cannot be interpreted without
selected item or prior context.

True examples include:
- "what about this?"
- "is it rapid charging?"
- "charger status??"
- "is it working right now?"

False examples include questions that name Wood Lane, NYC MVC, EV asset 87, TIMS-219173, the patch
board, ranking, notes, export, police, legal finding, weather, or all/open items.
"""
    write_text(ROOT / "ROUTE_TAXONOMY_V04B_DECISION_TREE.md", text)


def write_anchor_files(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_id = {row["question_id"]: row for row in rows}
    results = []
    for item in CANONICAL_ANCHORS:
        row = row_by_id.get(item["row_id"])
        errors = []
        if row is None:
            errors.append("missing_from_v04a_corpus")
        elif row.get("raw_question") != item["raw_question"]:
            errors.append("raw_question_mismatch")
        if item["canonical_route_label"] not in LABELS:
            errors.append("canonical_route_not_closed")
        if REFUSAL_CLASS_BY_LABEL.get(item["canonical_route_label"]) != item["canonical_refusal_class"]:
            errors.append("canonical_refusal_class_mismatch")
        results.append({**item, "validation_status": "PASS" if not errors else "FAIL", "errors": errors})
    status = "PASS" if all(item["validation_status"] == "PASS" for item in results) else "FAIL"
    report = {
        "schema_version": "citybrain.d14.v04b.canonical_boundary_anchors.v1",
        "generated_at": now(),
        "status": status,
        "anchor_count": len(results),
        "anchors": results,
    }
    write_json(ROOT / "D14_V04B_CANONICAL_BOUNDARY_ANCHORS.json", report)
    md = ["# D14 v0.4B Canonical Boundary Anchors", "", f"Status: `{status}`", ""]
    for item in results:
        md.append(f"- `{item['row_id']}` -> `{item['canonical_route_label']}`: {item['canonical_reason']}")
    write_text(ROOT / "D14_V04B_CANONICAL_BOUNDARY_ANCHORS.md", "\n".join(md))
    return report


def hard_bucket(raw: str) -> str:
    q = raw.lower()
    if re.search(r"\b(board|screen|operator|alert|dispatch|call|certify|ranking|urgency|notes)\b", q):
        return "ui_action_boundary"
    if re.search(r"\b(source row|source record|record|connector counts|power ratings|fields|tims)\b", q):
        return "source_record_boundary"
    if re.search(r"\b(weather|live availability source|external|real-time)\b", q):
        return "external_context_boundary"
    if re.search(r"\b(rapid charging|profile|entity|attribute)\b", q):
        return "entity_profile_boundary"
    if re.search(r"\b(queue|list|count|filter|compare|open items|rank)\b", q):
        return "patch_query_boundary"
    return "subject_answer_boundary"


def relabel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relabeled = []
    for row in rows:
        out = dict(row)
        label, refusal_class, lens = route_v04b(out)
        out["taxonomy_version"] = TAXONOMY_VERSION
        out["normalized_question"] = normalize_question(str(out.get("raw_question", "")))
        out["requires_selected_item_context"] = requires_context_v04b(out)
        out["expected_route_label"] = label
        out["expected_refusal_class"] = refusal_class
        out["subject_hint"] = subject_hint(str(out.get("raw_question", "")), str(out.get("selected_item_context", ""))) if label in SUBJECT_LABELS else None
        out["lens"] = lens
        out["route_family"] = "ask_subject_answer" if label in SUBJECT_LABELS else None
        out["hard_bucket_v04b"] = hard_bucket(str(out.get("raw_question", "")))
        out["canonical_boundary_anchor_v04b"] = is_anchor(out)
        relabeled.append(out)
    return relabeled


def distribution_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_counts = Counter(row.get("expected_route_label") for row in rows)
    deprecated_hits = [{"row_id": row["question_id"], "label": row.get("expected_route_label")} for row in rows if row.get("expected_route_label") in DEPRECATED_LABELS]
    non_closed_hits = [{"row_id": row["question_id"], "label": row.get("expected_route_label")} for row in rows if row.get("expected_route_label") not in LABELS]
    refusal_errors = []
    for row in rows:
        label = row.get("expected_route_label")
        expected = REFUSAL_CLASS_BY_LABEL.get(label)
        if row.get("expected_refusal_class") != expected:
            refusal_errors.append({"row_id": row["question_id"], "label": label, "expected": expected, "actual": row.get("expected_refusal_class")})
    return {
        "schema_version": "citybrain.d14.corpus_v0_label_distribution_v04b.v1",
        "generated_at": now(),
        "status": "PASS" if not deprecated_hits and not non_closed_hits and not refusal_errors else "FAIL",
        "rows": len(rows),
        "route_counts": dict(sorted(route_counts.items())),
        "lens_counts": dict(sorted(Counter(row.get("lens") for row in rows if row.get("lens")).items())),
        "bucket_counts": dict(sorted(Counter(row.get("hard_bucket_v04b") for row in rows).items())),
        "canonical_boundary_anchor_rows": sum(1 for row in rows if row.get("canonical_boundary_anchor_v04b")),
        "deprecated_label_hits": deprecated_hits,
        "non_closed_label_hits": non_closed_hits,
        "refusal_class_errors": refusal_errors,
    }


def gap_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gap_rows = [
        {
            "row_id": row["question_id"],
            "expected_route_label": row.get("expected_route_label"),
            "hard_bucket_v04b": row.get("hard_bucket_v04b"),
            "raw_question": row.get("raw_question"),
        }
        for row in rows
        if str(row.get("expected_route_label", "")).startswith("gap:")
    ]
    return {
        "schema_version": "citybrain.d14.corpus_v0_template_gap_v04b.v1",
        "generated_at": now(),
        "status": "PASS",
        "gap_rows": len(gap_rows),
        "gap_route_counts": dict(sorted(Counter(row["expected_route_label"] for row in gap_rows).items())),
        "rows": gap_rows,
    }


def relabel_report(rows: list[dict[str, Any]], old_rows: list[dict[str, Any]], dist: dict[str, Any]) -> dict[str, Any]:
    old_by_id = {row["question_id"]: row for row in old_rows}
    changes = []
    for row in rows:
        old = old_by_id[row["question_id"]]
        if (
            row.get("expected_route_label") != old.get("expected_route_label")
            or row.get("expected_refusal_class") != old.get("expected_refusal_class")
            or row.get("requires_selected_item_context") != old.get("requires_selected_item_context")
            or row.get("canonical_boundary_anchor_v04b")
        ):
            changes.append(
                {
                    "row_id": row["question_id"],
                    "raw_question": row.get("raw_question"),
                    "v04a_route": old.get("expected_route_label"),
                    "v04b_route": row.get("expected_route_label"),
                    "v04a_requires_selected_item_context": old.get("requires_selected_item_context"),
                    "v04b_requires_selected_item_context": row.get("requires_selected_item_context"),
                    "canonical_boundary_anchor_v04b": row.get("canonical_boundary_anchor_v04b"),
                }
            )
    return {
        "schema_version": "citybrain.d14.v04b_relabel_report.v1",
        "generated_at": now(),
        "status": "PASS" if len(rows) == 150 and dist["status"] == "PASS" and sum(1 for row in rows if row.get("canonical_boundary_anchor_v04b")) == 13 else "FAIL",
        "rows": len(rows),
        "changed_rows": len(changes),
        "route_changed_rows": sum(1 for item in changes if item["v04a_route"] != item["v04b_route"]),
        "canonical_boundary_anchor_rows": sum(1 for row in rows if row.get("canonical_boundary_anchor_v04b")),
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "refusal_class_errors": len(dist["refusal_class_errors"]),
        "changes": changes,
    }


def boundary_failure_analysis(v04a_audit: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for item in v04a_audit.get("family_disagreements_excluding_lens_only", []):
        anchor = anchor_map().get(item["row_id"])
        rows.append(
            {
                "row_id": item["row_id"],
                "raw_question": item["raw_question"],
                "selected_item_context": item.get("selected_item_context"),
                "codex_label": item.get("codex_expected_route_label"),
                "independent_label": item.get("independent_expected_route_label"),
                "disagreement_bucket": hard_bucket(str(item.get("raw_question", ""))),
                "recommended_v04b_canonical_label": None if anchor is None else anchor["canonical_route_label"],
                "recommended_v04b_requires_selected_item_context": None if anchor is None else anchor["requires_selected_item_context"],
                "reason": None if anchor is None else anchor["canonical_reason"],
            }
        )
    context_rows = []
    for item in v04a_audit.get("context_dependency_disagreements", []):
        fake = {"question_id": item["row_id"], "raw_question": item["raw_question"]}
        context_rows.append({**item, "recommended_v04b_requires_selected_item_context": requires_context_v04b(fake)})
    return {
        "schema_version": "citybrain.d14.v04a_boundary_failure_analysis_r1",
        "generated_at": now(),
        "status": "PASS_ANALYSIS_COMPLETE",
        "exact_route_disagreement_count": v04a_audit.get("exact_route_disagreement_count"),
        "exact_route_disagreement_rate": v04a_audit.get("exact_route_disagreement_rate"),
        "family_disagreement_excluding_lens_only_count": v04a_audit.get("family_disagreement_excluding_lens_only_count"),
        "family_disagreement_excluding_lens_only_rate": v04a_audit.get("family_disagreement_excluding_lens_only_rate"),
        "refusal_boundary_hard_error_count": v04a_audit.get("refusal_boundary_hard_error_count"),
        "refusal_boundary_hard_error_rate": v04a_audit.get("refusal_boundary_hard_error_rate"),
        "non_lens_disagreement_rows": rows,
        "context_dependency_disagreements": context_rows,
    }


def select_blind_sample(rows: list[dict[str, Any]], target: int = 55) -> list[dict[str, Any]]:
    selected_ids: set[str] = set()
    selected = []
    # All 13 boundary anchors first.
    for row_id in sorted(anchor_map()):
        row = next((item for item in rows if item["question_id"] == row_id), None)
        if row:
            selected.append(row)
            selected_ids.add(row_id)

    # At least 10 additional hard-bucket rows, then stratified route/persona fill.
    hard_candidates = [
        row
        for row in rows
        if row["question_id"] not in selected_ids
        and row.get("hard_bucket_v04b")
        in {
            "ui_action_boundary",
            "source_record_boundary",
            "external_context_boundary",
            "entity_profile_boundary",
            "patch_query_boundary",
        }
    ]
    for row in sorted(hard_candidates, key=lambda item: (item["hard_bucket_v04b"], item.get("expected_route_label"), item["question_id"]))[:20]:
        if row["question_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["question_id"])

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["question_id"] not in selected_ids:
            groups[(str(row.get("expected_route_label")), str(row.get("persona")))].append(row)
    for key in sorted(groups):
        if len(selected) >= target:
            break
        row = sorted(groups[key], key=lambda item: item["question_id"])[0]
        selected.append(row)
        selected_ids.add(row["question_id"])

    route_counts = Counter(row.get("expected_route_label") for row in selected)
    candidates = [row for row in rows if row["question_id"] not in selected_ids]
    for row in sorted(candidates, key=lambda item: (route_counts[item.get("expected_route_label")], item.get("expected_route_label"), item.get("persona"), item["question_id"])):
        if len(selected) >= target:
            break
        selected.append(row)
        selected_ids.add(row["question_id"])
        route_counts[row.get("expected_route_label")] += 1

    return [clean_row_for_blind(row) for row in sorted(selected, key=lambda item: item["question_id"])]


def sample_manifest(sample: list[dict[str, Any]], rows: list[dict[str, Any]], topup_available: bool) -> dict[str, Any]:
    by_id = {row["question_id"]: row for row in rows}
    sample_ids = {row["row_id"] for row in sample}
    return {
        "schema_version": "citybrain.d14.double_label_v04b_sample_manifest.v1",
        "generated_at": now(),
        "status": STATUS,
        "blind_sample_rows": len(sample),
        "sample_range_target": "50-60",
        "canonical_boundary_anchor_rows_included": len(sample_ids & set(anchor_map())),
        "additional_hard_bucket_rows": sum(1 for row_id in sample_ids if by_id[row_id].get("hard_bucket_v04b") != "subject_answer_boundary" and row_id not in anchor_map()),
        "fresh_hard_shaped_topup_rows_available": topup_available,
        "fresh_hard_shaped_topup_rows_included": sum(1 for row in sample if row.get("source_type") == "synthetic_v0_clean_ai_hard_topup"),
        "limitation": None if topup_available else "NO_FRESH_HARD_SHAPED_TOPUP_ROWS_AVAILABLE",
        "codex_labels_included": False,
        "route_counts_hidden_expected": dict(sorted(Counter(by_id[row_id]["expected_route_label"] for row_id in sample_ids).items())),
        "bucket_counts_hidden_expected": dict(sorted(Counter(by_id[row_id]["hard_bucket_v04b"] for row_id in sample_ids).items())),
        "expected_next_file": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS.jsonl"),
    }


def route_family(label: str | None) -> str:
    label = label or ""
    if label.startswith("template:ask:subject_answer@v1:"):
        return "subject_answer"
    if label.startswith("refuse:"):
        return "refusal"
    if label.startswith("gap:"):
        return "gap"
    if label == "ui_help":
        return "ui_help"
    if label == "template:ask:entity_360@v2":
        return "entity_360"
    return label or "missing"


def label_lens(label: str | None) -> str | None:
    if not label or not label.startswith("template:ask:subject_answer@v1:lens="):
        return None
    return label.rsplit("=", 1)[-1]


def compare_v04b_labels(rows: list[dict[str, Any]], sample: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    independent_path = ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS.jsonl"
    if not independent_path.exists():
        return None, None, None

    independent_rows = read_jsonl(independent_path)
    independent_by_id = {row.get("row_id"): row for row in independent_rows}
    prelim_by_id = {row["question_id"]: row for row in rows}
    sample_ids = [row["row_id"] for row in sample]
    independent_ids = [row.get("row_id") for row in independent_rows]
    independent_sha = sha256_file(independent_path)

    missing_ids = [row_id for row_id in sample_ids if row_id not in independent_by_id]
    extra_ids = [row_id for row_id in independent_ids if row_id not in set(sample_ids)]
    closed_label_errors = [
        {"row_id": row.get("row_id"), "label": row.get("expected_route_label")}
        for row in independent_rows
        if row.get("expected_route_label") not in LABELS
    ]
    deprecated_label_errors = [
        {"row_id": row.get("row_id"), "label": row.get("expected_route_label")}
        for row in independent_rows
        if row.get("expected_route_label") in DEPRECATED_LABELS
    ]
    schema_errors = []
    for row in independent_rows:
        for field in ["row_id", "normalized_question", "requires_selected_item_context", "expected_route_label", "expected_refusal_class"]:
            if field not in row:
                schema_errors.append({"row_id": row.get("row_id"), "missing_field": field})
        label = row.get("expected_route_label")
        expected_refusal = REFUSAL_CLASS_BY_LABEL.get(label)
        if row.get("expected_refusal_class") != expected_refusal:
            schema_errors.append(
                {
                    "row_id": row.get("row_id"),
                    "field": "expected_refusal_class",
                    "expected": expected_refusal,
                    "actual": row.get("expected_refusal_class"),
                }
            )

    exact_disagreements = []
    family_disagreements = []
    subject_lens_disagreements = []
    refusal_boundary_hard_errors = []
    gap_vs_template_disagreements = []
    context_disagreements = []
    anchor_disagreements = []
    pair_counts: Counter[str] = Counter()
    family_pair_counts: Counter[str] = Counter()

    for row_id in sample_ids:
        if row_id not in independent_by_id or row_id not in prelim_by_id:
            continue
        codex = prelim_by_id[row_id]
        independent = independent_by_id[row_id]
        codex_label = codex.get("expected_route_label")
        independent_label = independent.get("expected_route_label")
        codex_family = route_family(codex_label)
        independent_family = route_family(independent_label)
        pair = f"{codex_label} -> {independent_label}"
        family_pair = f"{codex_family} -> {independent_family}"
        item_base = {
            "row_id": row_id,
            "raw_question": codex.get("raw_question"),
            "persona": codex.get("persona"),
            "selected_item_context": codex.get("selected_item_context"),
            "hard_bucket_v04b": codex.get("hard_bucket_v04b"),
            "canonical_boundary_anchor_v04b": codex.get("canonical_boundary_anchor_v04b", False),
            "codex_expected_route_label": codex_label,
            "independent_expected_route_label": independent_label,
            "codex_expected_refusal_class": codex.get("expected_refusal_class"),
            "independent_expected_refusal_class": independent.get("expected_refusal_class"),
            "codex_family": codex_family,
            "independent_family": independent_family,
            "codex_lens": label_lens(codex_label),
            "independent_lens": label_lens(independent_label),
            "pair": pair,
            "family_pair": family_pair,
        }

        if codex_label != independent_label:
            exact_disagreements.append(item_base)
            pair_counts[pair] += 1
            family_pair_counts[family_pair] += 1
            if codex_family == "subject_answer" and independent_family == "subject_answer":
                subject_lens_disagreements.append(item_base)
            else:
                family_disagreements.append(item_base)
            if {codex_family, independent_family} & {"gap"} and {codex_family, independent_family} & {"subject_answer", "entity_360"}:
                gap_vs_template_disagreements.append(item_base)
            if (codex_family == "refusal") != (independent_family == "refusal"):
                refusal_boundary_hard_errors.append(item_base)
            if codex.get("canonical_boundary_anchor_v04b"):
                anchor_disagreements.append(item_base)

        if codex.get("requires_selected_item_context") != independent.get("requires_selected_item_context"):
            context_disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_requires_selected_item_context": codex.get("requires_selected_item_context"),
                    "independent_requires_selected_item_context": independent.get("requires_selected_item_context"),
                    "canonical_boundary_anchor_v04b": codex.get("canonical_boundary_anchor_v04b", False),
                }
            )

    denominator = len(sample_ids)
    exact_rate = round(len(exact_disagreements) / denominator, 4) if denominator else 1.0
    family_rate = round(len(family_disagreements) / denominator, 4) if denominator else 1.0
    lens_rate = round(len(subject_lens_disagreements) / denominator, 4) if denominator else 0.0
    refusal_rate = round(len(refusal_boundary_hard_errors) / denominator, 4) if denominator else 1.0
    gap_template_rate = round(len(gap_vs_template_disagreements) / denominator, 4) if denominator else 1.0
    context_rate = round(len(context_disagreements) / denominator, 4) if denominator else 0.0
    anchor_rate = round(len(anchor_disagreements) / max(sum(1 for row in rows if row.get("canonical_boundary_anchor_v04b")), 1), 4)

    gate_status = (
        "PASS_D14_ROUTE_TAXONOMY_V04B_DOUBLE_LABEL_GATES"
        if exact_rate <= 0.15
        and len(refusal_boundary_hard_errors) <= 1
        and not closed_label_errors
        and not deprecated_label_errors
        and not schema_errors
        else "FAIL_D14_ROUTE_TAXONOMY_V04B_DOUBLE_LABEL_GATES"
    )

    audit = {
        "schema_version": "citybrain.d14.double_label_v04b_audit.v1",
        "generated_at": now(),
        "status": gate_status,
        "threshold": 0.15,
        "blind_sample_rows": denominator,
        "independent_rows": len(independent_rows),
        "row_ids_match_blind_sample_order": independent_ids == sample_ids,
        "missing_row_ids": missing_ids,
        "extra_row_ids": extra_ids,
        "independent_labels_sha256": independent_sha,
        "closed_label_errors": closed_label_errors,
        "deprecated_label_errors": deprecated_label_errors,
        "schema_errors": schema_errors,
        "exact_route_disagreement_count": len(exact_disagreements),
        "exact_route_disagreement_rate": exact_rate,
        "family_disagreement_excluding_lens_only_count": len(family_disagreements),
        "family_disagreement_excluding_lens_only_rate": family_rate,
        "subject_answer_lens_only_disagreement_count": len(subject_lens_disagreements),
        "subject_answer_lens_only_disagreement_rate": lens_rate,
        "refusal_boundary_hard_error_count": len(refusal_boundary_hard_errors),
        "refusal_boundary_hard_error_rate": refusal_rate,
        "gap_vs_template_disagreement_count": len(gap_vs_template_disagreements),
        "gap_vs_template_disagreement_rate": gap_template_rate,
        "context_dependency_disagreement_count": len(context_disagreements),
        "context_dependency_disagreement_rate": context_rate,
        "canonical_anchor_disagreement_count": len(anchor_disagreements),
        "canonical_anchor_disagreement_rate": anchor_rate,
        "pair_counts": dict(sorted(pair_counts.items())),
        "family_pair_counts": dict(sorted(family_pair_counts.items())),
        "exact_disagreements": exact_disagreements,
        "family_disagreements_excluding_lens_only": family_disagreements,
        "subject_answer_lens_only_disagreements": subject_lens_disagreements,
        "refusal_boundary_hard_errors": refusal_boundary_hard_errors,
        "gap_vs_template_disagreements": gap_vs_template_disagreements,
        "canonical_anchor_disagreements": anchor_disagreements,
        "context_dependency_disagreements": context_disagreements,
        "real_operator_validation_claimed": False,
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
    }

    gates = {
        "schema_version": "citybrain.d14.v04b_double_label_gate_results.v1",
        "generated_at": now(),
        "status": gate_status,
        "aggregate_exact_route_disagreement": {
            "count": len(exact_disagreements),
            "rate": exact_rate,
            "threshold": 0.15,
            "status": "PASS" if exact_rate <= 0.15 else "FAIL",
        },
        "aggregate_family_disagreement_excluding_lens_only": {
            "count": len(family_disagreements),
            "rate": family_rate,
            "threshold": 0.15,
            "status": "PASS" if family_rate <= 0.15 else "FAIL",
        },
        "refusal_boundary_hard_errors": {
            "count": len(refusal_boundary_hard_errors),
            "max_rows": 1,
            "preferred_rows": 0,
            "status": "PASS" if len(refusal_boundary_hard_errors) <= 1 else "FAIL",
        },
        "subject_answer_lens_only_disagreement": {
            "count": len(subject_lens_disagreements),
            "rate": lens_rate,
            "blocking": False,
            "status": "INFO",
        },
        "gap_vs_template_disagreement": {
            "count": len(gap_vs_template_disagreements),
            "rate": gap_template_rate,
            "threshold": 0.10,
            "status": "PASS" if gap_template_rate <= 0.10 else "FAIL",
        },
        "canonical_anchor_disagreement": {
            "count": len(anchor_disagreements),
            "status": "PASS" if not anchor_disagreements else "FAIL",
        },
        "deprecated_label_usage": {"count": len(deprecated_label_errors), "status": "PASS" if not deprecated_label_errors else "FAIL"},
        "closed_label_usage": {"errors": len(closed_label_errors), "status": "PASS" if not closed_label_errors else "FAIL"},
        "row_id_alignment": {
            "row_ids_match_blind_sample_order": independent_ids == sample_ids,
            "missing_row_ids": missing_ids,
            "extra_row_ids": extra_ids,
            "status": "PASS" if independent_ids == sample_ids and not missing_ids and not extra_ids else "FAIL",
        },
        "final_gate": "BLOCKED_REPAIR_REQUIRED" if gate_status.startswith("FAIL") else "PASS_PENDING_SPLIT_SEAL_POLICY",
    }

    md_lines = [
        "# D14 v0.4B Double-Label Comparison",
        "",
        f"Status: `{gate_status}`",
        "",
        f"- Exact route disagreement: `{len(exact_disagreements)} / {denominator}` = `{exact_rate}`",
        f"- Family disagreement excluding subject-answer lens-only: `{len(family_disagreements)} / {denominator}` = `{family_rate}`",
        f"- Subject-answer lens-only disagreement: `{len(subject_lens_disagreements)} / {denominator}` = `{lens_rate}`",
        f"- Refusal-boundary hard errors: `{len(refusal_boundary_hard_errors)}`",
        f"- Gap-vs-template disagreement: `{len(gap_vs_template_disagreements)} / {denominator}` = `{gap_template_rate}`",
        f"- Canonical anchor disagreement: `{len(anchor_disagreements)}`",
        "",
        "## Refusal-Boundary Hard Errors",
    ]
    if refusal_boundary_hard_errors:
        for item in refusal_boundary_hard_errors:
            md_lines.append(f"- `{item['row_id']}`: `{item['codex_expected_route_label']}` -> `{item['independent_expected_route_label']}` — {item['raw_question']}")
    else:
        md_lines.append("- None")
    md_lines += ["", "## Non-Lens Family Disagreements"]
    for item in family_disagreements:
        md_lines.append(f"- `{item['row_id']}`: `{item['codex_expected_route_label']}` -> `{item['independent_expected_route_label']}` — {item['raw_question']}")
    report_md = "\n".join(md_lines)
    return audit, gates, report_md


def write_instructions() -> None:
    text = """# v0.4B Independent Double-Label Instructions

Use only this file, `ROUTE_TAXONOMY_V04B_CONTRACT.json`, and
`ROUTE_TAXONOMY_V04B_DECISION_TREE.md`.

Do not consult Codex preliminary labels or prior independent labels.

Return one JSONL row per blind sample row:

- `row_id`
- `normalized_question`
- `requires_selected_item_context`
- `expected_route_label`
- `expected_refusal_class`

Closed labels:

- `template:ask:subject_answer@v1:lens=support`
- `template:ask:subject_answer@v1:lens=uncertainty`
- `template:ask:subject_answer@v1:lens=claimability`
- `template:ask:subject_answer@v1:lens=summary`
- `template:ask:entity_360@v2`
- `ui_help`
- `gap:patch_queue_query_needed`
- `gap:source_record_360_needed`
- `gap:external_context_source_needed`
- `refuse:action_shaped`
- `refuse:prediction_or_finding`
- `refuse:identity_or_person`

Boundary principles:

- Capability question is not an action request.
- "Can the cockpit notify someone?" is `ui_help`.
- "Notify someone now." is `refuse:action_shaped`.
- Questions about fields/details of one source row are `gap:source_record_360_needed`.
- Questions about what a record supports or proves are subject-answer support or claimability.
- Questions about unavailable weather/live feeds/external context are `gap:external_context_source_needed`.
- Supported negative answers are not refusals.

Context flag:

- `true` only if the question cannot be interpreted without selected item/prior context.
- `false` if it names the asset, board, patch, record, weather, ranking, police, export, legal finding, or item scope.
"""
    write_text(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_INSTRUCTIONS.md", text)


def write_probe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = []
    for row_id in sorted(anchor_map())[:10]:
        row = next((item for item in rows if item["question_id"] == row_id), None)
        if row:
            selected.append(row)
    for row in rows:
        if len(selected) >= 20:
            break
        if row["question_id"] not in {item["question_id"] for item in selected}:
            selected.append(row)
    write_jsonl(ROOT / "COLD_LABELER_PROBE_V04B_PACKET.jsonl", [clean_row_for_blind(row) for row in selected[:20]])
    write_text(ROOT / "COLD_LABELER_PROBE_V04B_INSTRUCTIONS.md", "Use the v0.4B decision tree and return the same label schema as the main blind sample. Do not consult Codex labels.")
    expected = [
        {"row_id": row["question_id"], "expected_route_label": row["expected_route_label"], "expected_refusal_class": row["expected_refusal_class"]}
        for row in selected[:20]
    ]
    digest = sha256_bytes("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in expected).encode("utf-8"))
    sealed = {
        "schema_version": "citybrain.d14.cold_labeler_probe_v04b_hash.v1",
        "generated_at": now(),
        "status": "SEALED_EXPECTED_LABELS_HASH_ONLY",
        "probe_rows": len(selected[:20]),
        "expected_labels_jsonl_sha256": digest,
        "expected_labels_not_written": True,
    }
    write_json(ROOT / "COLD_LABELER_PROBE_V04B_EXPECTED_LABELS_SEALED_HASH.json", sealed)
    return sealed


def json_parse_audit() -> dict[str, Any]:
    rows = []
    for path in sorted(ROOT.rglob("*.json")) + sorted(ROOT.rglob("*.jsonl")):
        errors = []
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(str(exc))
        else:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except Exception as exc:
                    errors.append(f"{line_number}: {exc}")
        rows.append({"path": rel(path), "status": "PASS" if not errors else "FAIL", "errors": errors[:10]})
    return {"schema_version": "citybrain.d14.v04b.json_parse_audit.v1", "generated_at": now(), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "files": rows}


def secret_audit() -> dict[str, Any]:
    patterns = [r"api[_-]?key\s*[:=]", r"secret[_-]?key\s*[:=]", r"access[_-]?token\s*[:=]", r"bearer\s+[a-z0-9._-]{16,}", r"password\s*[:=]"]
    hits = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() == ".zip":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                hits.append({"path": rel(path), "pattern": pattern})
    return {"schema_version": "citybrain.d14.v04b.secret_audit.v1", "generated_at": now(), "status": "PASS" if not hits else "FAIL", "hits": hits}


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def package_outputs() -> None:
    package_path = ROOT / "D14_ROUTE_TAXONOMY_V04B_PACKAGE.zip"
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, rel(path))


def write_local_index() -> None:
    text = """# D14 Route Taxonomy Repair v0.4B Boundary Stability R1

Status: `PAUSED_D14_ROUTE_TAXONOMY_V04B_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Send for independent labeling:

- `CORPUS_V0_DOUBLE_LABEL_V04B_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04B_INSTRUCTIONS.md`

No Split/Seal R3, router preflight, router training, or real-operator validation claim has been made.
"""
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", text)
    write_text(ROOT / "README.md", text)


def main() -> None:
    validate_inputs()
    preserved = preserve_independent_v04b_labels()
    clean_root()
    restore_preserved_files(preserved)
    copy_prompt_pack()

    v04a_audit = read_json(INPUTS["v04a_audit"])
    v04a_rows = read_jsonl(INPUTS["v04a_labeled"])
    write_json(ROOT / "D14_V04A_BOUNDARY_FAILURE_ANALYSIS_R1.json", boundary_failure_analysis(v04a_audit))
    write_json(ROOT / "ROUTE_TAXONOMY_V04B_CONTRACT.json", create_contract())
    write_decision_tree()
    anchors = write_anchor_files(v04a_rows)
    if anchors["status"] != "PASS":
        raise SystemExit("v0.4B canonical anchor validation failed")

    v04b_rows = relabel_rows(v04a_rows)
    write_jsonl(ROOT / "operator_question_corpus_synthetic_v0_labeled_v04b.jsonl", v04b_rows)
    dist = distribution_report(v04b_rows)
    gaps = gap_report(v04b_rows)
    relabel = relabel_report(v04b_rows, v04a_rows, dist)
    write_json(ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_V04B_REPORT.json", dist)
    write_json(ROOT / "CORPUS_V0_TEMPLATE_GAP_V04B_REPORT.json", gaps)
    write_json(ROOT / "D14_V04B_RELABEL_REPORT.json", relabel)
    if relabel["status"] != "PASS":
        raise SystemExit("v0.4B relabel failed")

    topup_available = TOPUP_ROOT.exists() and any(TOPUP_ROOT.rglob("*.jsonl"))
    sample = select_blind_sample(v04b_rows, target=55)
    write_jsonl(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_BLIND_SAMPLE.jsonl", sample)
    write_instructions()
    manifest = sample_manifest(sample, v04b_rows, bool(topup_available))
    write_json(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_SAMPLE_MANIFEST.json", manifest)
    probe = write_probe(v04b_rows)

    comparison_audit, gate_results, comparison_md = compare_v04b_labels(v04b_rows, sample)
    if comparison_audit is not None and gate_results is not None and comparison_md is not None:
        write_json(ROOT / "D14_DOUBLE_LABEL_V04B_AUDIT.json", comparison_audit)
        write_json(ROOT / "D14_ROUTE_TAXONOMY_V04B_GATE_RESULTS.json", gate_results)
        write_text(ROOT / "D14_ROUTE_TAXONOMY_V04B_COMPARISON_REPORT.md", comparison_md)

    parse_audit = json_parse_audit()
    secret = secret_audit()
    write_json(ROOT / "JSON_PARSE_AUDIT.json", parse_audit)
    write_json(ROOT / "SECRET_AUDIT.json", secret)

    if comparison_audit is None:
        decision_status = STATUS
        next_required = rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS.jsonl")
    elif comparison_audit["status"].startswith("PASS"):
        decision_status = "PASS_D14_ROUTE_TAXONOMY_V04B_DOUBLE_LABEL_GATES_READY_FOR_SPLIT_SEAL_R3_WITH_LIMITATIONS"
        next_required = "run Split/Seal R3 only after policy review of remaining limitations"
    else:
        decision_status = "PAUSED_D14_ROUTE_TAXONOMY_V04B_DOUBLE_LABEL_GATES_FAILED_REPAIR_REQUIRED"
        next_required = "inspect v0.4B disagreement rows; consider router-stage split if semantic repair keeps failing"

    decision = {
        "task": TASK,
        "status": decision_status,
        "generated_at": now(),
        "input_root": rel(V04A_ROOT),
        "output_root": rel(ROOT),
        "subject_answer_architecture_preserved": True,
        "v04a_exact_disagreement_count": v04a_audit.get("exact_route_disagreement_count"),
        "v04a_family_disagreement_excluding_lens_only_count": v04a_audit.get("family_disagreement_excluding_lens_only_count"),
        "v04a_refusal_boundary_hard_error_count": v04a_audit.get("refusal_boundary_hard_error_count"),
        "canonical_boundary_anchor_rows": anchors["anchor_count"],
        "full_corpus_relabeled_under_v04b": len(v04b_rows),
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "blind_sample_rows": len(sample),
        "canonical_boundary_anchor_rows_in_blind_sample": manifest["canonical_boundary_anchor_rows_included"],
        "fresh_hard_shaped_topup_rows_available": bool(topup_available),
        "fresh_hard_shaped_topup_rows_included": manifest["fresh_hard_shaped_topup_rows_included"],
        "cold_labeler_probe_packet_created": True,
        "cold_labeler_expected_labels_hash": probe["expected_labels_jsonl_sha256"],
        "independent_double_label_file_present": comparison_audit is not None,
        "independent_labels_sha256": None if comparison_audit is None else comparison_audit["independent_labels_sha256"],
        "exact_route_disagreement_count": None if comparison_audit is None else comparison_audit["exact_route_disagreement_count"],
        "exact_route_disagreement_rate": None if comparison_audit is None else comparison_audit["exact_route_disagreement_rate"],
        "family_disagreement_excluding_lens_only_count": None
        if comparison_audit is None
        else comparison_audit["family_disagreement_excluding_lens_only_count"],
        "family_disagreement_excluding_lens_only_rate": None
        if comparison_audit is None
        else comparison_audit["family_disagreement_excluding_lens_only_rate"],
        "subject_answer_lens_only_disagreement_count": None
        if comparison_audit is None
        else comparison_audit["subject_answer_lens_only_disagreement_count"],
        "subject_answer_lens_only_disagreement_rate": None
        if comparison_audit is None
        else comparison_audit["subject_answer_lens_only_disagreement_rate"],
        "refusal_boundary_hard_error_count": None
        if comparison_audit is None
        else comparison_audit["refusal_boundary_hard_error_count"],
        "refusal_boundary_hard_error_rate": None
        if comparison_audit is None
        else comparison_audit["refusal_boundary_hard_error_rate"],
        "gap_vs_template_disagreement_count": None
        if comparison_audit is None
        else comparison_audit["gap_vs_template_disagreement_count"],
        "gap_vs_template_disagreement_rate": None
        if comparison_audit is None
        else comparison_audit["gap_vs_template_disagreement_rate"],
        "canonical_anchor_disagreement_count": None
        if comparison_audit is None
        else comparison_audit["canonical_anchor_disagreement_count"],
        "double_label_gate_status": None if comparison_audit is None else comparison_audit["status"],
        "split_seal_r3": "NOT_RUN",
        "router_preflight": "NOT_OPENED",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "json_parse_audit": parse_audit["status"],
        "secret_audit": secret["status"],
        "next_required_file": next_required,
    }
    write_json(ROOT / "D14_ROUTE_TAXONOMY_V04B_CLOSEOUT_DECISION.json", decision)
    write_local_index()
    package_outputs()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
