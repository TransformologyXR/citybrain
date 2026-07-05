#!/usr/bin/env python3
"""Run D14 route taxonomy repair v0.4A subject-answer consolidation.

This supersedes the prepared v0.4 pass. It does not train a router, does not
run Split/Seal R3, and does not claim real operator validation. It relabels the
150-row synthetic corpus with a consolidated subject-answer route family,
exports a blind double-label sample, defines bucket gates, and stops.
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
ASSEMBLY_ROOT = OUTPUTS / "main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate"
V02_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v02_r1"
V03_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v03_r1"
ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1"
PROMPT_ROOT = (
    REPO
    / "tmp"
    / "citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1"
    / "citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1"
)
TOPUP_ROOT = REPO / "inputs" / "d14_synthetic_operator_questions" / "hard_shaped_topup"

TASK = "MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04A-SUBJECT-ANSWER-R1"
STATUS = "PAUSED_D14_ROUTE_TAXONOMY_V04A_AWAITING_INDEPENDENT_DOUBLE_LABELS"
TAXONOMY_VERSION = "route_taxonomy_v04a_subject_answer"
THRESHOLD = 0.15

INPUTS = {
    "assembly_labeled": ASSEMBLY_ROOT / "operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl",
    "assembly_unlabeled": ASSEMBLY_ROOT / "operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl",
    "v02_audit": V02_ROOT / "D14_DOUBLE_LABEL_V02_AUDIT.json",
    "v03_audit": V03_ROOT / "D14_DOUBLE_LABEL_V03_AUDIT.json",
    "v03_ambiguity_json": V03_ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.json",
    "v03_ambiguity_md": V03_ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md",
    "v03_labeled": V03_ROOT / "operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl",
}

EXPECTED_INPUT_FILES = [
    INPUTS["assembly_labeled"],
    INPUTS["assembly_unlabeled"],
    INPUTS["v02_audit"],
    INPUTS["v03_audit"],
    INPUTS["v03_ambiguity_json"],
    INPUTS["v03_ambiguity_md"],
    INPUTS["v03_labeled"],
]

SUBJECT_LABELS = {
    "template:ask:subject_answer@v1:lens=support",
    "template:ask:subject_answer@v1:lens=uncertainty",
    "template:ask:subject_answer@v1:lens=claimability",
    "template:ask:subject_answer@v1:lens=summary",
}

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
    "template:ask:entity_360@v2": {
        "kind": "template",
        "description": "Explicit entity/address/asset/case profile lookup.",
    },
    "ui_help": {
        "kind": "help",
        "description": "Board usage, local workflow help, or capability/boundary question.",
    },
    "refuse:action_shaped": {
        "kind": "refusal",
        "expected_refusal_class": "action_shaped",
        "description": "Imperative/request to initiate external action or official operational outcome.",
    },
    "refuse:prediction_or_finding": {
        "kind": "refusal",
        "expected_refusal_class": "prediction_or_finding",
        "description": "Prediction, legal/certified/official/compliance finding outside supported subject-answer boundary.",
    },
    "refuse:identity_or_person": {
        "kind": "refusal",
        "expected_refusal_class": "identity_or_person",
        "description": "Person/contact/owner/driver/biometric identity request not present in visible records.",
    },
    "refuse:out_of_scope_entity": {
        "kind": "refusal",
        "expected_refusal_class": "out_of_scope_entity",
        "description": "Unrelated entity/place/domain outside the current board.",
    },
    "gap:patch_queue_query_needed": {
        "kind": "gap",
        "description": "Patch queue count/list/filter/compare/summarize/rank query needing a product consumer.",
    },
    "gap:source_record_360_needed": {
        "kind": "gap",
        "description": "Fields/details/contents of a specific source record.",
    },
    "gap:evidence_gap_template_needed": {
        "kind": "gap",
        "description": "Missing evidence request that needs a deterministic product template/backlog consumer.",
    },
    "gap:external_context_source_needed": {
        "kind": "gap",
        "description": "External context or data source not connected to the board.",
    },
}

DEPRECATED_LABELS = sorted(
    {
        "template:ask:what_supports@v1",
        "template:ask:what_is_uncertain@v1",
        "template:ask:cannot_claim@v1",
        "template:ask:entity_360@v1",
        "gap:boundary_status_template_needed",
        "gap:charging_site_source_depth_scan",
        "gap:external_sharing_guidance",
        "gap:human_review_timestamp_status",
        "gap:local_note_visibility_guidance",
        "gap:patch_queue_aggregate_counts",
        "gap:patch_queue_filter_by_city",
        "gap:patch_queue_filtering_and_summary_by_city_date",
        "gap:patch_queue_open_count",
        "gap:patch_queue_update_date_comparison",
        "gap:planning_context_boundary_template_needed",
    }
)

REFUSAL_CLASS_BY_LABEL = {
    label: meta["expected_refusal_class"]
    for label, meta in LABELS.items()
    if meta.get("kind") == "refusal"
}


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
        raise SystemExit("Missing required v0.4A inputs: " + ", ".join(rel(path) for path in missing))


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def preserve_independent_v04a_labels() -> dict[str, bytes]:
    preserved: dict[str, bytes] = {}
    for filename in [
        "CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS.jsonl",
        "CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS_REPORT.json",
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
    replacements = {
        "whats": "what is",
        "chrgr": "charger",
        "rn": "right now",
        "pls": "please",
        "ev": "EV",
        "nyc": "NYC",
        "mvc": "MVC",
        "uprn": "UPRN",
    }
    for src, dst in replacements.items():
        q = re.sub(rf"\b{re.escape(src)}\b", dst, q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if q and q[-1] not in "?!.":  # preserve terse operator fragments while keeping readable labels
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def subject_hint(raw: str, selected_context: str) -> str:
    q = raw.lower()
    context = selected_context.lower()
    if re.search(r"\b(ev\s*87|asset\s*87|charger\s*87|charging-site|rapid charger)\b", q) or context == "ev_asset_87":
        return "ev_asset_87"
    if re.search(r"\b(wood lane|scrubbs|scrubs)\b", q):
        return "wood_lane_review_context"
    if re.search(r"\b(nyc|mvc|4463710|collision)\b", q) or context == "nyc_mvc_candidate_context":
        return "nyc_mvc_candidate_context"
    if re.search(r"\b(london|planning|uprn|d10|opportunity-area)\b", q):
        return "london_planning_context"
    if re.search(r"\b(queue|patch|item\s*#?\d+)\b", q) or context == "general_patch_board":
        return "patch_queue"
    if re.search(r"\b(board|screen|software|operator workflow)\b", q):
        return "operator_board"
    if selected_context:
        return selected_context
    return "selected_subject"


def explicit_context_named(raw: str) -> bool:
    q = raw.lower()
    return bool(
        re.search(
            r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|scrubbs|scrubs|westway|nyc|mvc|4463710|uprn|london|chicago|tims-\d+|record\s*\d+|item\s*#?\d+|queue|patch|board|screen|software|source row|source record|london datastore)\b",
            q,
        )
    )


def requires_context_v04a(row: dict[str, Any]) -> bool:
    raw = str(row.get("raw_question", ""))
    q = raw.lower()
    if explicit_context_named(raw):
        return False
    if re.search(
        r"\b(what about this|what about that|what does it|what is missing here|what is missing on this|run the check|generate the brief for this|mark this reviewed|selected item|this item|this issue|this record|this evidence|here\??|this\??|that\??)\b",
        q,
    ):
        return True
    if re.search(r"\b(this|that|it|here|selected|these|those)\b", q) and not explicit_context_named(raw):
        return True
    return False


def route_v04a(row: dict[str, Any]) -> tuple[str, str | None, str | None]:
    q = str(row.get("raw_question", "")).lower()

    # 1. Imperative/requested external action.
    if re.search(
        r"\b(alert .*team|alert .*department|alert .*operator|alert someone|dispatch|route drivers|route traffic|enforce|approve|create a case|create case|open a ticket|file a case|tell drivers|tell the public|get .*fixed|send .*email|send .*externally|call the charger operator|call .*operator|call .*department|call the police|notify .*team|publish an alert now|email .*externally)\b",
        q,
    ):
        return "refuse:action_shaped", "action_shaped", None
    if re.match(r"^\s*(dispatch|route|enforce|approve|notify|alert|call|send|create|open|file|publish)\b", q):
        return "refuse:action_shaped", "action_shaped", None

    # 2. High-stakes findings/predictions. Claimability questions stay subject-answer.
    if re.search(r"\b(comply with|compliance with|legal violation|violation|liable|fine them|will there|predict|tomorrow|next week|probability|likelihood|future incident|cyber security standards|officially noncompliant)\b", q):
        if re.search(r"\b(can .*claim|can .*treat|what .*claim|what .*prove|what .*establish|whether .*claim)\b", q):
            return "template:ask:subject_answer@v1:lens=claimability", None, "claimability"
        return "refuse:prediction_or_finding", "prediction_or_finding", None

    # 3. Personal identity/contact.
    if re.search(r"\b(who do i call|who should i call|which person|owner name|driver|face|biometric|identify|responsible person|contact details)\b", q):
        return "refuse:identity_or_person", "identity_or_person", None

    # 4. Board usage/capability.
    if re.search(
        r"\b(how do i|where do i|what button|can i click|use this board|export|copy|add note|mark reviewed|open ask|generate brief|run check|checks panel|can this board|can the board|does the board|from this screen|this screen|the screen|this board|the board|does .*create.*case|local review only|what prevents .*live monitoring|treating this replay as live monitoring|can an operator certify|board.*alert|board.*dispatch|board.*route|board.*publish|call .*from this screen|activity saved|notes stored|visibility)\b",
        q,
    ):
        return "ui_help", None, None

    # 5. Patch queue query.
    if re.search(
        r"\b(queue|patch queue|item\s*#?\d+|show all|list all|list the|filter|compare|count|how many|total number of records|which item|highest ranked|ranked item|open items|updated today|updated yesterday|today versus yesterday|city/date|three queue|three ranked|record count|same wood lane evidence gap|separate from item|source records on file|records currently on file)\b",
        q,
    ):
        return "gap:patch_queue_query_needed", None, None

    # 6. Source record contents/details.
    if re.search(
        r"\b(what does .*record.*say|what does .*row.*say|what .*source row.*say|what exactly is in|what fields|field-level|show me record|record .*details|tims-\d+|contents of .*record|fields in .*record|source row actually say)\b",
        q,
    ):
        return "gap:source_record_360_needed", None, None

    # 8. Support/evidence lens.
    if re.search(
        r"\b(what supports|source supports|which source|what source|sources support|records support|evidence supports|citations|what backs|backing evidence|evidence and uncertainty|source brief|source link|source records indicate|source records validate|representative point matched|list the evidence)\b",
        q,
    ):
        if re.search(r"\b(missing|needed|would confirm|could confirm|confirm a blockage|confirm blocked|before saying|before claiming)\b", q):
            return "template:ask:subject_answer@v1:lens=uncertainty", None, "uncertainty"
        return "template:ask:subject_answer@v1:lens=support", None, "support"

    # 9. Uncertainty/missing evidence lens or product gap if the missing consumer is not present.
    if re.search(
        r"\b(missing evidence|evidence missing|what evidence.*missing|what source.*needed|what would confirm|could confirm|before saying|before claiming|why .*candidate-only|candidate-only|verification absent|direct evidence|stronger evidence|source depth|no .*source|needed before|need before|what is missing before|what is uncertain|uncertain|unknowns|what do we not know|limitations|limitation)\b",
        q,
    ):
        if re.search(r"\b(weather source|traffic feed|live service source|external source|new data source|source not connected)\b", q):
            return "gap:evidence_gap_template_needed", None, None
        return "template:ask:subject_answer@v1:lens=uncertainty", None, "uncertainty"

    # 10. Claimability/proof/live/blocked lens.
    if re.search(
        r"\b(can .*claim|can we claim|can .*prove|does this prove|what .*prove|what .*establish|what .*verified|verified by|certify|certified|legal finding|official finding|blocked|live|available|unavailable|availability|down|working right now|working now|avail now|current status|affected|caused|causality|what does this not prove|not proof|not prove|cannot claim|can .*be treated|only proximity|static registry|live status feed|proof .*existed|operational|access impact|changed availability|urgent|urgency finding|review order|source record prove|row establish|constraints are verified)\b",
        q,
    ):
        if re.search(r"\b(legal finding|official finding|certify a legal|certified legal)\b", q) and not re.search(r"\b(can .*claim|can an operator|whether)\b", q):
            return "refuse:prediction_or_finding", "prediction_or_finding", None
        return "template:ask:subject_answer@v1:lens=claimability", None, "claimability"

    # 12. External context.
    if re.search(r"\b(weather|other charging sites|other chargers|nearby not shown|external data|budget report|emergency database|ownership records|traffic live feed)\b", q):
        return "gap:external_context_source_needed", None, None

    # 7. Entity profile lookup.
    if re.search(
        r"\b(profile|look up|rapid or slow|fast charger|normal charger|UPRN|uprn|confidence value|planning-context linkage|opportunity-area context|what do we know about ev|what do we know about asset|what do we know about charger|ev\s*87|asset\s*87|charger\s*87|mvc|4463710|building|parcel)\b",
        q,
    ):
        return "template:ask:entity_360@v2", None, None

    # 11. General subject summary.
    if re.search(r"\b(what is going on|what do we know|summarize|summary|brief me|explain this|what happened)\b", q):
        return "template:ask:subject_answer@v1:lens=summary", None, "summary"

    if re.search(r"\b(school|hospital|crime|unrelated place|outside this board)\b", q):
        return "refuse:out_of_scope_entity", "out_of_scope_entity", None

    return "ui_help", None, None


def clean_row_for_blind(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["question_id"],
        "raw_question": row.get("raw_question"),
        "persona": row.get("persona"),
        "selected_item_context": row.get("selected_item_context"),
        "source_type": row.get("source_type"),
        "source_session_id": row.get("source_session_id"),
        "source_run_file": row.get("source_run_file"),
        "original_question_id": row.get("original_question_id"),
        "topup_batch": row.get("topup_batch"),
    }


def create_contract() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04a_subject_answer",
        "generated_at": now(),
        "status": "ACTIVE_FOR_V04A_DOUBLE_LABEL_GATE",
        "double_label_gate_threshold": THRESHOLD,
        "route_labels": LABELS,
        "closed_labels": sorted(LABELS),
        "subject_answer_family": {
            "route": "template:ask:subject_answer@v1(subject,lens)",
            "closed_lenses": ["support", "uncertainty", "claimability", "summary"],
            "rule": "Lens changes which section renders first; it does not change the underlying answer object.",
            "answer_object_sections": [
                "subject_summary",
                "knowns",
                "source_support",
                "uncertainty_missing_evidence",
                "cannot_claim",
                "citations",
                "coverage_status_notes",
            ],
        },
        "superseded_labels_for_v04a_relabeling": [
            "template:ask:what_supports@v1",
            "template:ask:what_is_uncertain@v1",
            "template:ask:cannot_claim@v1",
        ],
        "deprecated_labels": DEPRECATED_LABELS,
        "first_match_rules": [
            "external_action_request_refuse_action_shaped",
            "prediction_official_legal_certified_finding_refuse_unless_claimability_question",
            "person_identity_refuse_identity_or_person",
            "board_usage_or_capability_ui_help",
            "patch_queue_count_list_filter_compare_gap",
            "source_record_fields_details_contents_gap",
            "support_evidence_subject_answer_support",
            "missing_uncertain_subject_answer_uncertainty_or_evidence_gap",
            "claim_prove_establish_verify_live_blocked_subject_answer_claimability",
            "external_context_source_gap",
            "explicit_entity_profile_entity_360",
            "general_subject_summary_subject_answer_summary",
        ],
        "requires_selected_item_context_rule": {
            "true_only_if": "question cannot be interpreted without current selected item/pronoun context",
            "false_if": "question names Wood Lane, EV asset 87, NYC MVC, a source record, board capability, city, or queue scope",
        },
        "pass_gate_notes": [
            "Aggregate disagreement <= 15 percent.",
            "Refusal-boundary hard errors <= 1 row and preferably 0.",
            "Subject-answer lens-only disagreement is lower severity and informs UI section priority.",
            "No Split/Seal R3 or router preflight until independent labels and gates pass.",
        ],
    }


def write_decision_tree() -> None:
    text = """# Route Taxonomy v0.4A Decision Tree

v0.4A introduces `template:ask:subject_answer@v1(subject,lens)`.

Allowed lenses:

- `support`
- `uncertainty`
- `claimability`
- `summary`

The lens changes which section renders first. It does not change the underlying answer object.
Every subject answer can include summary, knowns, source support, uncertainty/missing evidence,
cannot-claim, citations, and coverage/status notes.

## First-Match Rules

1. External action request: if the user asks the system or operator to alert, dispatch, route,
   enforce, approve, create/send an official case, contact someone, publish, or fix something,
   use `refuse:action_shaped`.
2. Prediction/finding: if the user asks for a prediction, legal/certified/official finding,
   compliance determination, causality conclusion, or certainty the data does not provide, use
   `refuse:prediction_or_finding`, unless they ask what the board can claim. Claimability
   questions use subject-answer claimability.
3. Person/identity: if the user asks for a person, owner, driver, contact, or biometric identity,
   use `refuse:identity_or_person`.
4. Board usage/capability: how to export, mark reviewed, add notes, whether notes/clicks create
   a case, whether the board can alert/dispatch, or where activity is saved uses `ui_help`.
5. Patch queue query: counts, lists, filters, comparisons, ranked items, open items, city/date
   summaries, and item relationships use `gap:patch_queue_query_needed`.
6. Source record profile: fields, details, or contents of a specific source record use
   `gap:source_record_360_needed`.
7. Support lens: sources, evidence, citations, or records that support a subject use
   `template:ask:subject_answer@v1:lens=support`.
8. Uncertainty lens: missing evidence, unknowns, uncertainty, or what would be needed to confirm a
   claim uses `template:ask:subject_answer@v1:lens=uncertainty`, unless it asks for a missing
   external data source/product consumer, then use `gap:evidence_gap_template_needed`.
9. Claimability lens: can claim/prove/establish/verify/certify/live/blocked/available/affected/
   caused uses `template:ask:subject_answer@v1:lens=claimability` when the board can answer with
   limits. Refuse only if it asks for an official/legal finding.
10. External context: weather, ownership, traffic, live service sources, or external data not
    connected to the board uses `gap:external_context_source_needed`.
11. Entity profile: explicit entity/address/asset/case profile lookups use
    `template:ask:entity_360@v2`.
12. General summary: what is going on, what do we know, summarize, or brief me uses
    `template:ask:subject_answer@v1:lens=summary`.

## Selected Context

Set `requires_selected_item_context = true` only when the question cannot be interpreted without
the current selected item, such as "what about this?", "run the check", or "what is missing here?"

Set it to false when the question explicitly names the item, record, city, source, board capability,
or queue scope.
"""
    write_text(ROOT / "ROUTE_TAXONOMY_V04A_DECISION_TREE.md", text)


def hard_bucket(raw: str) -> str:
    q = raw.lower()
    if re.search(r"\b(alert|dispatch|route|call|create case|board|screen|operator|local notes|reviewed)\b", q):
        return "board_capability_vs_external_action"
    if re.search(r"\b(queue|item\s*#?\d+|count|list|filter|ranked|records on file|patch)\b", q):
        return "patch_queue_query"
    if re.search(r"\b(source row|source record|record|evidence|supports|citation|prove|establish)\b", q):
        return "source_support_vs_source_record_vs_claimability"
    if re.search(r"\b(ev\s*87|asset\s*87|charger|blocked|live|available|unavailable|down|working)\b", q):
        return "ev_live_blocked_claimability"
    if re.search(r"\b(planning|uprn|profile|confidence|representative point|entity)\b", q):
        return "entity_profile_vs_planning_source_boundary"
    if re.search(r"\b(this|that|it|here)\b", q):
        return "noisy_followup_pronoun"
    return "general_subject_answer"


def v03_root_cause(v03_audit: dict[str, Any], ambiguity: dict[str, Any]) -> str:
    pair_counts = ambiguity.get("pair_counts", {})
    categories = ambiguity.get("categories", {})
    lines = [
        "# D14 v0.3 Ambiguity Root Cause R2",
        "",
        f"v0.3 route/refusal disagreement: `{v03_audit.get('route_or_refusal_disagreement_count')} / {v03_audit.get('blind_sample_rows')}` = `{v03_audit.get('route_or_refusal_disagreement_rate')}`.",
        "",
        "## Conclusion",
        "",
        "The remaining disagreement is concentrated, not random. Many hard questions are asking for sections of the same subject answer rather than genuinely different product destinations.",
        "",
        "The clearest recurring issue is that `what_supports`, `what_is_uncertain`, and `cannot_claim` compete even though a good answer naturally contains all three sections: support, uncertainty, and claimability.",
        "",
        "## Pair Counts",
    ]
    for pair, count in pair_counts.items():
        lines.append(f"- `{pair}`: {count}")
    lines += ["", "## Categories"]
    for name, rows in categories.items():
        lines.append(f"- `{name}`: {len(rows)} rows")
    lines += [
        "",
        "## v0.4A Repair",
        "",
        "- Consolidate support/uncertainty/claimability into `template:ask:subject_answer@v1(subject,lens)`.",
        "- Keep `gap:source_record_360_needed` only for fields/details/contents of a specific source row.",
        "- Keep board capability vs imperative external action as a separate governance boundary.",
        "- Treat subject-answer lens disagreement as lower severity than crossing into refusal/action/gap boundaries.",
        "",
        "This step does not adjudicate v0.3 into a pass.",
    ]
    return "\n".join(lines)


def architecture_decision() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.subject_answer_architecture_decision_r1",
        "generated_at": now(),
        "status": "ADOPTED_FOR_V04A_DOUBLE_LABEL_GATE",
        "decision": "Introduce template:ask:subject_answer@v1(subject,lens).",
        "route_family": "ask_subject_answer",
        "allowed_lenses": ["support", "uncertainty", "claimability", "summary"],
        "lens_rule": "The lens changes which section renders first. It does not change the underlying answer object.",
        "answer_object_sections": [
            "subject_summary",
            "knowns",
            "source_support",
            "uncertainty_missing_evidence",
            "cannot_claim",
            "citations",
            "coverage_status_notes",
        ],
        "superseded_v04a_targets": [
            "template:ask:what_supports@v1",
            "template:ask:what_is_uncertain@v1",
            "template:ask:cannot_claim@v1",
        ],
        "preserved_separate_routes": [
            "template:ask:entity_360@v2",
            "ui_help",
            "refuse:action_shaped",
            "refuse:prediction_or_finding",
            "refuse:identity_or_person",
            "refuse:out_of_scope_entity",
            "gap:patch_queue_query_needed",
            "gap:source_record_360_needed",
            "gap:evidence_gap_template_needed",
            "gap:external_context_source_needed",
        ],
        "claims": {
            "real_operator_validation_claimed": False,
            "router_training_opened": False,
            "split_seal_r3_run": False,
            "new_source_facts_created": False,
        },
    }


def write_architecture_summary() -> None:
    text = """# Subject Answer Architecture Decision R1

Decision: introduce `template:ask:subject_answer@v1(subject,lens)`.

Allowed lenses: `support`, `uncertainty`, `claimability`, `summary`.

The lens only changes section ordering and framing. The underlying answer object stays the same
and can include knowns, source support, uncertainty/missing evidence, cannot-claim, citations,
and coverage/status notes.

This supersedes direct v0.4A relabeling to `what_supports`, `what_is_uncertain`, and
`cannot_claim`. Those remain historical templates, not active v0.4A route labels.
"""
    write_text(ROOT / "SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.md", text)


def write_topup_protocol() -> tuple[bool, int]:
    topup_files = []
    if TOPUP_ROOT.exists():
        topup_files = [path for path in sorted(TOPUP_ROOT.rglob("*.jsonl")) if path.is_file()]
    included = bool(topup_files)
    topup_rows = 0
    for path in topup_files:
        try:
            topup_rows += len(read_jsonl(path))
        except Exception:
            pass

    protocol = """# Hard-Shaped Top-Up Corpus Protocol

Purpose: avoid denominator gaming. The next double-label sample must include fresh unseen rows
shaped like the ambiguity buckets that caused v0.3 to fail, not only easier remainder rows.

Use fresh clean sessions, not this project thread and not Codex.

Clean-session prompt constraints:

- Use the frozen default human-visible operator cockpit text as the stimulus where possible.
- Do not show taxonomy labels, implementation details, templates, routes, or this contract.
- Generate 60 rows across at least 2 clean runs and 2 model families if feasible.
- Keep all labels null.
- Preserve `source_type = synthetic_v0_clean_ai_hard_topup` or set `topup_batch = hard_v04a`.

Target distribution:

- 15 source-support vs source-record phrasings
- 15 EV live/blocked/availability/claimability phrasings
- 10 board capability vs external action phrasings
- 10 patch queue count/list/filter/compare phrasings
- 5 entity profile vs planning/source boundary phrasings
- 5 noisy follow-up/pronoun rows across the above

Current local top-up status: `{status}`.
""".format(status="FOUND_LOCAL_TOPUP_FILES" if included else "NO_LOCAL_TOPUP_FILES_FOUND")
    prompt = """# Clean-Session Prompt For Hard-Shaped D14 Top-Up Rows

You are generating synthetic operator questions from the frozen operator cockpit visible text.
Do not use or infer route labels. Do not mention templates, taxonomy, implementation details, or
this instruction set.

Generate JSONL rows only. Leave all label fields null. Use realistic operator wording, including
some terse, messy, and follow-up style questions.

Required fields:

- raw_question
- persona
- selected_item_context
- source_type = synthetic_v0_clean_ai_hard_topup
- topup_batch = hard_v04a
- normalized_question = null
- requires_selected_item_context = null
- expected_route_label = null
- expected_refusal_class = null

Generate 60 total rows distributed across source-support/source-row/claimability, EV live or
blocked claimability, board capability versus external action, patch queue query, entity profile
versus source/planning boundary, and noisy pronoun follow-ups.
"""
    write_text(ROOT / "HARD_SHAPED_TOPUP_CORPUS_PROTOCOL.md", protocol)
    write_text(ROOT / "HARD_SHAPED_TOPUP_CLEAN_SESSION_PROMPT.md", prompt)
    return included, topup_rows


def relabel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relabeled = []
    for row in rows:
        out = dict(row)
        raw = str(out.get("raw_question", ""))
        label, refusal_class, lens = route_v04a(out)
        out["taxonomy_version"] = TAXONOMY_VERSION
        out["normalized_question"] = normalize_question(raw)
        out["requires_selected_item_context"] = requires_context_v04a(out)
        out["expected_route_label"] = label
        out["expected_refusal_class"] = refusal_class
        out["hard_bucket_v04a"] = hard_bucket(raw)
        out["subject_hint"] = subject_hint(raw, str(out.get("selected_item_context", ""))) if label in SUBJECT_LABELS else None
        out["lens"] = lens
        out["route_family"] = "ask_subject_answer" if label in SUBJECT_LABELS else None
        out["v04a_label_note"] = "subject-answer lens" if label in SUBJECT_LABELS else "v0.4A first-match route"
        relabeled.append(out)
    return relabeled


def distribution_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_counts = Counter(row.get("expected_route_label") for row in rows)
    lens_counts = Counter(row.get("lens") for row in rows if row.get("lens"))
    bucket_counts = Counter(row.get("hard_bucket_v04a") for row in rows)
    deprecated_hits = [
        {"row_id": row["question_id"], "label": row.get("expected_route_label")}
        for row in rows
        if row.get("expected_route_label") in DEPRECATED_LABELS
    ]
    non_closed_hits = [
        {"row_id": row["question_id"], "label": row.get("expected_route_label")}
        for row in rows
        if row.get("expected_route_label") not in LABELS
    ]
    refusal_errors = []
    for row in rows:
        label = row.get("expected_route_label")
        expected = REFUSAL_CLASS_BY_LABEL.get(label)
        actual = row.get("expected_refusal_class")
        if expected != actual:
            refusal_errors.append({"row_id": row["question_id"], "label": label, "expected": expected, "actual": actual})
    return {
        "schema_version": "citybrain.d14.corpus_v0_label_distribution_v04a.v1",
        "generated_at": now(),
        "status": "PASS" if not deprecated_hits and not non_closed_hits and not refusal_errors else "FAIL",
        "rows": len(rows),
        "route_counts": dict(sorted(route_counts.items())),
        "lens_counts": dict(sorted(lens_counts.items())),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "source_type_counts": dict(sorted(Counter(row.get("source_type") for row in rows).items())),
        "deprecated_label_hits": deprecated_hits,
        "non_closed_label_hits": non_closed_hits,
        "refusal_class_errors": refusal_errors,
    }


def gap_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gap_rows = [
        {
            "row_id": row["question_id"],
            "persona": row.get("persona"),
            "expected_route_label": row.get("expected_route_label"),
            "hard_bucket_v04a": row.get("hard_bucket_v04a"),
            "raw_question": row.get("raw_question"),
        }
        for row in rows
        if str(row.get("expected_route_label", "")).startswith("gap:")
    ]
    return {
        "schema_version": "citybrain.d14.corpus_v0_template_gap_v04a.v1",
        "generated_at": now(),
        "status": "PASS",
        "gap_rows": len(gap_rows),
        "gap_route_counts": dict(sorted(Counter(row["expected_route_label"] for row in gap_rows).items())),
        "rows": gap_rows,
    }


def deprecated_label_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = [
        {"row_id": row["question_id"], "label": row.get("expected_route_label")}
        for row in rows
        if row.get("expected_route_label") in DEPRECATED_LABELS
    ]
    legacy_notes = [
        {"row_id": row["question_id"], "v03_route_label": row.get("expected_route_label")}
        for row in rows
        if row.get("taxonomy_version") == "route_taxonomy_v03" and row.get("expected_route_label") in DEPRECATED_LABELS
    ]
    return {
        "schema_version": "citybrain.d14.v04a_deprecated_label_audit.v1",
        "generated_at": now(),
        "status": "PASS" if not hits else "FAIL",
        "deprecated_labels": DEPRECATED_LABELS,
        "hits": hits,
        "historical_legacy_notes": legacy_notes,
    }


def relabel_audit(rows: list[dict[str, Any]], dist: dict[str, Any]) -> dict[str, Any]:
    source_errors = [
        {"row_id": row["question_id"], "source_type": row.get("source_type")}
        for row in rows
        if row.get("source_type") != "synthetic_v0_clean_ai"
    ]
    return {
        "schema_version": "citybrain.d14.v04a_relabel_audit.v1",
        "generated_at": now(),
        "status": "PASS" if len(rows) == 150 and dist["status"] == "PASS" and not source_errors else "FAIL",
        "rows": len(rows),
        "source_type_errors": source_errors,
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "refusal_class_errors": len(dist["refusal_class_errors"]),
        "subject_answer_rows": sum(1 for row in rows if row.get("expected_route_label") in SUBJECT_LABELS),
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }


def select_blind_sample(rows: list[dict[str, Any]], hard_ids: set[str], target: int = 50) -> list[dict[str, Any]]:
    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []
    by_id = {row["question_id"]: row for row in rows}

    # Include all v0.3 hard disagreement rows. Labels stay hidden in blind export.
    for row_id in sorted(hard_ids):
        if row_id in by_id:
            selected.append(by_id[row_id])
            selected_ids.add(row_id)

    # Cover represented hard buckets and routes, then fill deterministically.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["question_id"] not in selected_ids:
            groups[(str(row.get("hard_bucket_v04a")), str(row.get("expected_route_label")))].append(row)
    for key in sorted(groups):
        if len(selected) >= target:
            break
        row = sorted(groups[key], key=lambda item: item["question_id"])[0]
        selected.append(row)
        selected_ids.add(row["question_id"])

    route_counts = Counter(row.get("expected_route_label") for row in selected)
    bucket_counts = Counter(row.get("hard_bucket_v04a") for row in selected)
    candidates = [row for row in rows if row["question_id"] not in selected_ids]
    for row in sorted(
        candidates,
        key=lambda item: (
            bucket_counts[item.get("hard_bucket_v04a")],
            route_counts[item.get("expected_route_label")],
            item.get("hard_bucket_v04a"),
            item.get("expected_route_label"),
            item.get("persona"),
            item["question_id"],
        ),
    ):
        if len(selected) >= target:
            break
        selected.append(row)
        selected_ids.add(row["question_id"])
        route_counts[row.get("expected_route_label")] += 1
        bucket_counts[row.get("hard_bucket_v04a")] += 1

    return [clean_row_for_blind(row) for row in sorted(selected, key=lambda item: item["question_id"])]


def sample_manifest(sample: list[dict[str, Any]], rows: list[dict[str, Any]], hard_ids: set[str], topup_included: bool) -> dict[str, Any]:
    by_id = {row["question_id"]: row for row in rows}
    sample_ids = {row["row_id"] for row in sample}
    route_counts = Counter(by_id[row_id]["expected_route_label"] for row_id in sample_ids)
    lens_counts = Counter(by_id[row_id]["lens"] for row_id in sample_ids if by_id[row_id].get("lens"))
    bucket_counts = Counter(by_id[row_id]["hard_bucket_v04a"] for row_id in sample_ids)
    codex_fields = {
        "expected_route_label",
        "expected_refusal_class",
        "normalized_question",
        "requires_selected_item_context",
        "subject_hint",
        "lens",
        "route_family",
    }
    leaked_fields = sorted({field for row in sample for field in row if field in codex_fields})
    return {
        "schema_version": "citybrain.d14.double_label_v04a_sample_manifest.v1",
        "generated_at": now(),
        "status": STATUS,
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl"),
        "blind_sample_rows": len(sample),
        "minimum_required_rows": 50,
        "sample_pct_of_original_150": round(len(sample) / 150, 4),
        "v03_hard_rows_required": len(hard_ids),
        "v03_hard_rows_included": len(sample_ids & hard_ids),
        "fresh_hard_topup_rows_included": sum(1 for row in sample if row.get("topup_batch") == "hard_v04a"),
        "hard_topup_available": topup_included,
        "codex_label_fields_in_blind_sample": leaked_fields,
        "route_counts_hidden_expected": dict(sorted(route_counts.items())),
        "lens_counts_hidden_expected": dict(sorted(lens_counts.items())),
        "bucket_counts_hidden_expected": dict(sorted(bucket_counts.items())),
        "sample_audit_categories_supported": [
            "aggregate_disagreement_rate",
            "refusal_boundary_disagreement_rate",
            "subject_answer_lens_disagreement_rate",
            "gap_vs_template_disagreement_rate",
            "anchor_row_disagreement_rate",
            "fresh_hard_row_disagreement_rate_if_topup_exists",
        ],
        "expected_next_file": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS.jsonl"),
        "split_seal_r3": "NOT_RUN_BLOCKED_PENDING_INDEPENDENT_V04A_LABELS",
        "router_preflight": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }


def write_double_label_instructions() -> None:
    text = """# v0.4A Independent Double-Label Instructions

Use only this file plus:

- `ROUTE_TAXONOMY_V04A_CONTRACT.json`
- `ROUTE_TAXONOMY_V04A_DECISION_TREE.md`
- `CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl`

Do not consult Codex preliminary labels.

For each blind sample row, return JSONL named:

`CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS.jsonl`

Required fields:

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
- `gap:evidence_gap_template_needed`
- `gap:external_context_source_needed`
- `refuse:action_shaped`
- `refuse:prediction_or_finding`
- `refuse:identity_or_person`
- `refuse:out_of_scope_entity`

Subject-answer rule:

`support`, `uncertainty`, `claimability`, and `summary` are lenses over one answer object.
If two rows differ only by subject-answer lens, that is lower severity than crossing into refusal,
gap, or UI-help. Still choose the lens that best matches the user's wording.

Use refusals only for true action, prediction/finding, identity, or out-of-scope requests.
Supported negative answers about what can or cannot be claimed are subject-answer claimability,
not refusals.
"""
    write_text(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_INSTRUCTIONS.md", text)


def refusal_boundary_gates(topup_included: bool) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.refusal_boundary_bucket_gates_r1",
        "generated_at": now(),
        "status": "DEFINED_PENDING_INDEPENDENT_LABELS",
        "aggregate_route_refusal_disagreement_max": THRESHOLD,
        "refusal_boundary_hard_error_max_rows": 1,
        "refusal_boundary_preferred_rows": 0,
        "subject_answer_lens_disagreement": {
            "blocking": False,
            "interpretation": "If both labels are subject_answer and differ only by lens, count separately for UI section-priority tuning.",
        },
        "gap_vs_template_disagreement": {
            "pause_threshold": 0.10,
            "reason": "This changes product backlog vs implemented capability.",
        },
        "action_shaped_rows": {
            "imperative_external_action": "refuse:action_shaped",
            "interrogative_board_capability": "ui_help",
        },
        "deprecated_label_usage": "BLOCKING",
        "clean_stimulus_leak": "QUARANTINE_AND_REVIEW",
        "fresh_hard_topup_gate": "PENDING_TOPUP_NOT_INCLUDED" if not topup_included else "READY_FOR_FRESH_HARD_ROW_AUDIT",
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


def compare_v04a_labels(rows: list[dict[str, Any]], sample: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    independent_path = ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS.jsonl"
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

        if codex_label != independent_label:
            item = {
                "row_id": row_id,
                "raw_question": codex.get("raw_question"),
                "persona": codex.get("persona"),
                "selected_item_context": codex.get("selected_item_context"),
                "hard_bucket_v04a": codex.get("hard_bucket_v04a"),
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
            exact_disagreements.append(item)
            pair_counts[pair] += 1
            family_pair_counts[family_pair] += 1
            if codex_family == "subject_answer" and independent_family == "subject_answer":
                subject_lens_disagreements.append(item)
            else:
                family_disagreements.append(item)
            if {codex_family, independent_family} & {"gap"} and {codex_family, independent_family} & {"subject_answer", "entity_360"}:
                gap_vs_template_disagreements.append(item)
            if (codex_family == "refusal") != (independent_family == "refusal"):
                refusal_boundary_hard_errors.append(item)

        if codex.get("requires_selected_item_context") != independent.get("requires_selected_item_context"):
            context_disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_requires_selected_item_context": codex.get("requires_selected_item_context"),
                    "independent_requires_selected_item_context": independent.get("requires_selected_item_context"),
                }
            )

    denominator = len(sample_ids)
    exact_rate = round(len(exact_disagreements) / denominator, 4) if denominator else 1.0
    family_rate = round(len(family_disagreements) / denominator, 4) if denominator else 1.0
    lens_rate = round(len(subject_lens_disagreements) / denominator, 4) if denominator else 0.0
    refusal_rate = round(len(refusal_boundary_hard_errors) / denominator, 4) if denominator else 1.0
    gap_template_rate = round(len(gap_vs_template_disagreements) / denominator, 4) if denominator else 1.0
    context_rate = round(len(context_disagreements) / denominator, 4) if denominator else 0.0

    gate_status = (
        "PASS_D14_ROUTE_TAXONOMY_V04A_DOUBLE_LABEL_GATES"
        if exact_rate <= THRESHOLD
        and len(refusal_boundary_hard_errors) <= 1
        and not closed_label_errors
        and not deprecated_label_errors
        and not schema_errors
        else "FAIL_D14_ROUTE_TAXONOMY_V04A_DOUBLE_LABEL_GATES"
    )

    audit = {
        "schema_version": "citybrain.d14.double_label_v04a_audit.v1",
        "generated_at": now(),
        "status": gate_status,
        "threshold": THRESHOLD,
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
        "pair_counts": dict(sorted(pair_counts.items())),
        "family_pair_counts": dict(sorted(family_pair_counts.items())),
        "exact_disagreements": exact_disagreements,
        "family_disagreements_excluding_lens_only": family_disagreements,
        "subject_answer_lens_only_disagreements": subject_lens_disagreements,
        "refusal_boundary_hard_errors": refusal_boundary_hard_errors,
        "gap_vs_template_disagreements": gap_vs_template_disagreements,
        "context_dependency_disagreements": context_disagreements,
        "real_operator_validation_claimed": False,
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
    }

    gates = {
        "schema_version": "citybrain.d14.refusal_boundary_bucket_gate_results_r1",
        "generated_at": now(),
        "status": gate_status,
        "aggregate_exact_route_disagreement": {
            "count": len(exact_disagreements),
            "rate": exact_rate,
            "threshold": THRESHOLD,
            "status": "PASS" if exact_rate <= THRESHOLD else "FAIL",
        },
        "aggregate_family_disagreement_excluding_lens_only": {
            "count": len(family_disagreements),
            "rate": family_rate,
            "threshold": THRESHOLD,
            "status": "PASS" if family_rate <= THRESHOLD else "FAIL",
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
        "deprecated_label_usage": {
            "count": len(deprecated_label_errors),
            "status": "PASS" if not deprecated_label_errors else "FAIL",
        },
        "closed_label_usage": {
            "errors": len(closed_label_errors),
            "status": "PASS" if not closed_label_errors else "FAIL",
        },
        "row_id_alignment": {
            "row_ids_match_blind_sample_order": independent_ids == sample_ids,
            "missing_row_ids": missing_ids,
            "extra_row_ids": extra_ids,
            "status": "PASS" if independent_ids == sample_ids and not missing_ids and not extra_ids else "FAIL",
        },
        "final_gate": "BLOCKED_REPAIR_REQUIRED" if gate_status.startswith("FAIL") else "PASS_PENDING_SPLIT_SEAL_POLICY",
    }

    md_lines = [
        "# D14 v0.4A Double-Label Comparison",
        "",
        f"Status: `{gate_status}`",
        "",
        f"- Exact route disagreement: `{len(exact_disagreements)} / {denominator}` = `{exact_rate}`",
        f"- Family disagreement excluding subject-answer lens-only: `{len(family_disagreements)} / {denominator}` = `{family_rate}`",
        f"- Subject-answer lens-only disagreement: `{len(subject_lens_disagreements)} / {denominator}` = `{lens_rate}`",
        f"- Refusal-boundary hard errors: `{len(refusal_boundary_hard_errors)}`",
        f"- Gap-vs-template disagreement: `{len(gap_vs_template_disagreements)} / {denominator}` = `{gap_template_rate}`",
        "",
        "## Refusal-Boundary Hard Errors",
    ]
    if refusal_boundary_hard_errors:
        for item in refusal_boundary_hard_errors:
            md_lines.append(
                f"- `{item['row_id']}`: `{item['codex_expected_route_label']}` -> `{item['independent_expected_route_label']}` — {item['raw_question']}"
            )
    else:
        md_lines.append("- None")
    md_lines += ["", "## Non-Lens Family Disagreements"]
    for item in family_disagreements:
        md_lines.append(
            f"- `{item['row_id']}`: `{item['codex_expected_route_label']}` -> `{item['independent_expected_route_label']}` — {item['raw_question']}"
        )
    report_md = "\n".join(md_lines)
    return audit, gates, report_md


def select_probe(rows: list[dict[str, Any]], target: int = 20) -> list[dict[str, Any]]:
    bucket_targets = [
        ("source_support_vs_source_record_vs_claimability", 4),
        ("ev_live_blocked_claimability", 4),
        ("board_capability_vs_external_action", 4),
        ("patch_queue_query", 4),
        ("entity_profile_vs_planning_source_boundary", 2),
        ("general_subject_answer", 2),
    ]
    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []
    for bucket, count in bucket_targets:
        candidates = [row for row in rows if row.get("hard_bucket_v04a") == bucket and row["question_id"] not in selected_ids]
        for row in sorted(candidates, key=lambda item: item["question_id"])[:count]:
            selected.append(row)
            selected_ids.add(row["question_id"])
    for row in sorted(rows, key=lambda item: (item.get("hard_bucket_v04a"), item.get("expected_route_label"), item["question_id"])):
        if len(selected) >= target:
            break
        if row["question_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["question_id"])
    return selected[:target]


def write_cold_labeler_probe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    probe_rows = select_probe(rows, target=20)
    blind_rows = [clean_row_for_blind(row) for row in probe_rows]
    write_jsonl(ROOT / "COLD_LABELER_PROBE_PACKET_R1.jsonl", blind_rows)
    write_text(
        ROOT / "COLD_LABELER_PROBE_INSTRUCTIONS.md",
        """# Cold-Labeler Probe Instructions

Use only the v0.4A taxonomy contract and decision tree. Do not consult Codex preliminary labels.

Return labels for each row with the same schema as the v0.4A independent double-label file.
This probe tests whether a fresh labeler can apply the taxonomy without prior discussion.
""",
    )
    expected = [
        {
            "row_id": row["question_id"],
            "expected_route_label": row["expected_route_label"],
            "expected_refusal_class": row["expected_refusal_class"],
        }
        for row in probe_rows
    ]
    expected_blob = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in expected).encode("utf-8")
    sealed = {
        "schema_version": "citybrain.d14.cold_labeler_probe_expected_labels_sealed_hash.v1",
        "generated_at": now(),
        "status": "SEALED_EXPECTED_LABELS_HASH_ONLY",
        "probe_rows": len(probe_rows),
        "hash_algorithm": "SHA256",
        "expected_labels_jsonl_sha256": sha256_bytes(expected_blob),
        "expected_labels_not_written": True,
        "probe_packet": rel(ROOT / "COLD_LABELER_PROBE_PACKET_R1.jsonl"),
    }
    write_json(ROOT / "COLD_LABELER_PROBE_EXPECTED_LABELS_SEALED_HASH.json", sealed)
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
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04a.json_parse_audit.v1",
        "generated_at": now(),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "files": rows,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        r"api[_-]?key\s*[:=]",
        r"secret[_-]?key\s*[:=]",
        r"access[_-]?token\s*[:=]",
        r"bearer\s+[a-z0-9._-]{16,}",
        r"password\s*[:=]",
    ]
    hits = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() == ".zip":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                hits.append({"path": rel(path), "pattern": pattern})
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04a.secret_audit.v1",
        "generated_at": now(),
        "status": "PASS" if not hits else "FAIL",
        "hits": hits,
    }


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def package_outputs() -> None:
    package_path = ROOT / "D14_ROUTE_TAXONOMY_V04A_PACKAGE.zip"
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, rel(path))


def write_local_index() -> None:
    text = """# D14 Route Taxonomy Repair v0.4A Subject Answer R1

Status: `PAUSED_D14_ROUTE_TAXONOMY_V04A_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Open first:

- `D14_ROUTE_TAXONOMY_V04A_CLOSEOUT_DECISION.json`
- `SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.json`
- `ROUTE_TAXONOMY_V04A_CONTRACT.json`
- `ROUTE_TAXONOMY_V04A_DECISION_TREE.md`
- `CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04A_INSTRUCTIONS.md`
- `REFUSAL_BOUNDARY_BUCKET_GATES_R1.json`
- `COLD_LABELER_PROBE_PACKET_R1.jsonl`

No Split/Seal R3, router preflight, or real-operator validation claim has been made.
"""
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", text)
    write_text(ROOT / "README.md", text)


def main() -> None:
    validate_inputs()
    preserved = preserve_independent_v04a_labels()
    clean_root()
    restore_preserved_files(preserved)
    copy_prompt_pack()

    v03_audit = read_json(INPUTS["v03_audit"])
    v03_ambiguity = read_json(INPUTS["v03_ambiguity_json"])
    v03_rows = read_jsonl(INPUTS["v03_labeled"])
    hard_ids = {item["row_id"] for item in v03_audit.get("disagreements", [])}

    write_text(ROOT / "D14_V03_AMBIGUITY_ROOT_CAUSE_R2.md", v03_root_cause(v03_audit, v03_ambiguity))
    write_json(ROOT / "SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.json", architecture_decision())
    write_architecture_summary()
    write_json(ROOT / "ROUTE_TAXONOMY_V04A_CONTRACT.json", create_contract())
    write_decision_tree()
    topup_included, topup_rows = write_topup_protocol()

    v04a_rows = relabel_rows(v03_rows)
    write_jsonl(ROOT / "operator_question_corpus_synthetic_v0_labeled_v04a_codex_prelim.jsonl", v04a_rows)
    dist = distribution_report(v04a_rows)
    gaps = gap_report(v04a_rows)
    deprecated = deprecated_label_audit(v04a_rows)
    relabel_check = relabel_audit(v04a_rows, dist)
    write_json(ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_V04A_REPORT.json", dist)
    write_json(ROOT / "CORPUS_V0_TEMPLATE_GAP_V04A_REPORT.json", gaps)
    write_json(ROOT / "CORPUS_V0_V04A_DEPRECATED_LABEL_AUDIT.json", deprecated)
    write_json(ROOT / "V04A_RELABEL_AUDIT.json", relabel_check)
    if relabel_check["status"] != "PASS":
        raise SystemExit("v0.4A relabel audit failed; see V04A_RELABEL_AUDIT.json")

    sample = select_blind_sample(v04a_rows, hard_ids, target=50)
    write_jsonl(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl", sample)
    write_double_label_instructions()
    manifest = sample_manifest(sample, v04a_rows, hard_ids, topup_included)
    write_json(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_SAMPLE_MANIFEST.json", manifest)
    write_json(ROOT / "REFUSAL_BOUNDARY_BUCKET_GATES_R1.json", refusal_boundary_gates(topup_included))
    probe_hash = write_cold_labeler_probe(v04a_rows)

    comparison_audit, gate_results, comparison_md = compare_v04a_labels(v04a_rows, sample)
    if comparison_audit is not None and gate_results is not None and comparison_md is not None:
        write_json(ROOT / "D14_DOUBLE_LABEL_V04A_AUDIT.json", comparison_audit)
        write_json(ROOT / "REFUSAL_BOUNDARY_BUCKET_GATE_RESULTS_R1.json", gate_results)
        write_text(ROOT / "D14_ROUTE_TAXONOMY_V04A_COMPARISON_REPORT.md", comparison_md)

    parse_audit = json_parse_audit()
    secret = secret_audit()
    write_json(ROOT / "JSON_PARSE_AUDIT.json", parse_audit)
    write_json(ROOT / "SECRET_AUDIT.json", secret)

    if comparison_audit is None:
        decision_status = STATUS
        next_required = rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04A_INDEPENDENT_LABELS.jsonl")
    elif comparison_audit["status"].startswith("PASS"):
        decision_status = "PASS_D14_ROUTE_TAXONOMY_V04A_DOUBLE_LABEL_GATES_WITH_LIMITATIONS"
        next_required = "cold-labeler/top-up policy review before Split/Seal R3"
    else:
        decision_status = "PAUSED_D14_ROUTE_TAXONOMY_V04A_DOUBLE_LABEL_GATES_FAILED_REPAIR_REQUIRED"
        next_required = "inspect v0.4A disagreement rows and repair taxonomy/labeling before Split/Seal R3"

    decision = {
        "task": TASK,
        "status": decision_status,
        "generated_at": now(),
        "input_roots": [rel(ASSEMBLY_ROOT), rel(V02_ROOT), rel(V03_ROOT)],
        "output_root": rel(ROOT),
        "supersedes_prepared_v04": True,
        "v03_remains_failed": True,
        "v03_disagreement_count": v03_audit.get("route_or_refusal_disagreement_count"),
        "v03_disagreement_rate": v03_audit.get("route_or_refusal_disagreement_rate"),
        "subject_answer_consolidation_decision_created": True,
        "v04a_contract_created": True,
        "full_corpus_relabeled_under_v04a": len(v04a_rows),
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "hard_shaped_topup_protocol_created": True,
        "hard_shaped_topup_rows_included": topup_rows if topup_included else 0,
        "hard_shaped_topup_gate_claimed": False,
        "blind_sample_rows": len(sample),
        "prior_v03_hard_rows_included": manifest["v03_hard_rows_included"],
        "fresh_hard_shaped_rows_included": manifest["fresh_hard_topup_rows_included"],
        "cold_labeler_probe_packet_created": True,
        "cold_labeler_expected_labels_hash_created": True,
        "cold_labeler_probe_status": "PACKET_CREATED_AWAITING_FRESH_LABELER",
        "refusal_boundary_bucket_gates_defined": True,
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
        "double_label_gate_status": None if comparison_audit is None else comparison_audit["status"],
        "split_seal_r3": "NOT_RUN",
        "router_preflight": "NOT_OPENED",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "json_parse_audit": parse_audit["status"],
        "secret_audit": secret["status"],
        "next_required_file": next_required,
        "cold_labeler_probe_packet": rel(ROOT / "COLD_LABELER_PROBE_PACKET_R1.jsonl"),
        "cold_labeler_expected_labels_hash": probe_hash["expected_labels_jsonl_sha256"],
    }
    write_json(ROOT / "D14_ROUTE_TAXONOMY_V04A_CLOSEOUT_DECISION.json", decision)
    write_local_index()
    package_outputs()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
