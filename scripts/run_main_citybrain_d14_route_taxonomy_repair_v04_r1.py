#!/usr/bin/env python3
"""Run D14 route taxonomy repair v0.4 and stop at double-label handoff.

This pass does not adjudicate v0.3 into a pass. It turns the 21 known hard
v0.3 disagreement rows into deterministic anchors, relabels the full synthetic
corpus under the tighter v0.4 first-match rules, exports a fresh non-anchor
blind sample, and stops before Split/Seal R3 or router preflight.
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
V03_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v03_r1"
ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04_r1"
PROMPT_ROOT = (
    REPO
    / "tmp"
    / "citybrain_d14_route_taxonomy_repair_v04_r1"
    / "citybrain_d14_route_taxonomy_repair_v04_r1"
)

TASK = "MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04-R1"
STATUS = "PAUSED_D14_ROUTE_TAXONOMY_V04_AWAITING_INDEPENDENT_DOUBLE_LABELS"
TAXONOMY_VERSION = "route_taxonomy_v04"
THRESHOLD = 0.15

INPUTS = {
    "v03_audit": V03_ROOT / "D14_DOUBLE_LABEL_V03_AUDIT.json",
    "v03_ambiguity_json": V03_ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.json",
    "v03_ambiguity_md": V03_ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md",
    "v03_labeled": V03_ROOT / "operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl",
    "v03_contract": V03_ROOT / "ROUTE_TAXONOMY_V03_CONTRACT.json",
    "v03_tree": V03_ROOT / "ROUTE_TAXONOMY_V03_DECISION_TREE.md",
    "v04_anchor_draft": PROMPT_ROOT / "ROUTE_TAXONOMY_V04_ANCHOR_SET_DRAFT.json",
    "v04_tree_draft": PROMPT_ROOT / "ROUTE_TAXONOMY_V04_DECISION_TREE_DRAFT.md",
}

EXPECTED_INPUT_FILES = list(INPUTS.values())

LABELS: dict[str, dict[str, str | None]] = {
    "template:ask:entity_360@v2": {
        "kind": "template",
        "description": "Neutral profile/facts/attributes of a named visible or selected entity.",
    },
    "template:ask:what_supports@v1": {
        "kind": "template",
        "description": "Evidence, citations, or source records that support a selected item, brief, or claim.",
    },
    "template:ask:what_is_uncertain@v1": {
        "kind": "template",
        "description": "Broad uncertainty/unknowns when no more specific support, gap, queue, claimability, or help route matches.",
    },
    "template:ask:cannot_claim@v1": {
        "kind": "template",
        "description": "Supported negative answer about claimability, live/blocked/available status, proof, certification, or what evidence does not establish.",
    },
    "ui_help": {
        "kind": "help",
        "description": "Board/screen/software/operator workflow capability, local-boundary, or usage question.",
    },
    "gap:patch_queue_query_needed": {
        "kind": "gap",
        "description": "Patch queue counts, lists, filters, comparisons, rank, item-number relationships, open counts, and city/date summaries.",
    },
    "gap:evidence_gap_template_needed": {
        "kind": "gap",
        "description": "Missing evidence, needed source, verification absence, candidate-only, or what would confirm a claim.",
    },
    "gap:source_record_360_needed": {
        "kind": "gap",
        "description": "Field/content/details profile of a named source record itself.",
    },
    "gap:external_context_source_needed": {
        "kind": "gap",
        "description": "External context not connected to the current board, such as weather or nearby external assets.",
    },
    "refuse:action_shaped": {
        "kind": "refusal",
        "expected_refusal_class": "action_shaped",
        "description": "Request to initiate an external/action-shaped outcome.",
    },
    "refuse:prediction_or_finding": {
        "kind": "refusal",
        "expected_refusal_class": "prediction_or_finding",
        "description": "Prediction, legal/certified/official/compliance finding outside supported claim-boundary answer.",
    },
    "refuse:identity_or_person": {
        "kind": "refusal",
        "expected_refusal_class": "identity_or_person",
        "description": "Person/contact/owner/department identity request not present in visible records.",
    },
    "refuse:out_of_scope_entity": {
        "kind": "refusal",
        "expected_refusal_class": "out_of_scope_entity",
        "description": "Entity/place/domain unrelated to the local board.",
    },
}

DEPRECATED_LABELS = sorted(
    {
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
        "template:ask:entity_360@v1",
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_inputs() -> None:
    missing = [path for path in EXPECTED_INPUT_FILES if not path.exists()]
    if missing:
        raise SystemExit("Missing required v0.4 inputs: " + ", ".join(rel(path) for path in missing))


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def copy_prompt_pack() -> None:
    prompt_out = ROOT / "prompt_pack"
    prompt_out.mkdir(parents=True, exist_ok=True)
    for path in sorted(PROMPT_ROOT.glob("*")):
        if path.is_file():
            shutil.copy2(path, prompt_out / path.name)


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
    if q and q[-1] not in "?!.":  # keep terse operator fragments readable
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def explicit_context_named(raw: str) -> bool:
    q = raw.lower()
    return bool(
        re.search(
            r"\b(ev\s*87|asset\s*87|charger\s*87|charging-site|wood lane|scrubbs|scrubs|westway|nyc|mvc|4463710|uprn|london|chicago|tims-\d+|record\s*\d+|item\s*#?\d+|queue|patch|board|screen|software|operator workflow|source row|source record|london datastore)\b",
            q,
        )
    )


def requires_context_v04(row: dict[str, Any]) -> bool:
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


def route_v04(row: dict[str, Any]) -> tuple[str, str | None]:
    q = str(row.get("raw_question", "")).lower()

    # 0a. Board/screen/software/operator workflow capability or boundary.
    if re.search(
        r"\b(can this board|can the board|does the board|from this screen|from the screen|this screen|this board|the board|the screen|software|operator workflow|mark reviewed|create a case if i mark|does .*create.*case|local review only|live monitoring|treating this replay as live monitoring|what prevents .*live monitoring|can an operator certify|board.*alert|board.*dispatch|board.*route|board.*publish|call .*from this screen|can we call .*from this screen)\b",
        q,
    ):
        return "ui_help", None

    # 0b. External action-shaped outcome.
    if re.search(
        r"\b(alert .*team|alert .*department|alert .*operator|alert someone|dispatch|route drivers|route traffic|enforce|approve|create a case|create case|open a ticket|file a case|tell drivers|tell the public|get .*fixed|send .*email|send .*externally|call the charger operator|call .*operator|call .*department|call the police|notify .*team|publish an alert now|email .*externally)\b",
        q,
    ):
        return "refuse:action_shaped", "action_shaped"
    if re.match(r"^\s*(dispatch|route|enforce|approve|notify|alert|call|send|create|open|file|publish)\b", q):
        return "refuse:action_shaped", "action_shaped"

    # 1. Queue/patch-board query.
    if re.search(
        r"\b(queue|patch queue|item\s*#?\d+|show all|list all|list the|filter|compare|count|how many|total number of records|which item|highest ranked|ranked item|open items|updated today|updated yesterday|today versus yesterday|city/date|three queue|three ranked|record count|same wood lane evidence gap|separate from item)\b",
        q,
    ):
        return "gap:patch_queue_query_needed", None

    # 2. Evidence-source retrieval.
    if re.search(
        r"\b(what supports|source supports|which source|what source|sources support|records support|evidence supports|citations|what backs|backing evidence|evidence and uncertainty|source brief|source link|source records indicate|source records validate|representative point matched|list the evidence)\b",
        q,
    ):
        if re.search(r"\b(missing|needed|would confirm|could confirm|confirm a blockage|confirm blocked|before saying|before claiming)\b", q):
            return "gap:evidence_gap_template_needed", None
        return "template:ask:what_supports@v1", None

    # 3. Missing evidence / source-depth question.
    if re.search(
        r"\b(missing evidence|evidence missing|what evidence.*missing|what source.*needed|what would confirm|could confirm|before saying|before claiming|why .*candidate-only|candidate-only|verification absent|direct evidence|stronger evidence|source depth|no .*source|needed before|need before|what is missing before)\b",
        q,
    ):
        return "gap:evidence_gap_template_needed", None

    # 4. Claimability/live/blocked/proof boundary.
    if re.search(
        r"\b(blocked|live|available|unavailable|availability|down|working right now|working now|avail now|current status|affected|certified|legal finding|official finding|can we claim|can .*claim|does this prove|what does .*prove|what .*establish|what .*verified|verified by|what does this not prove|not proof|not prove|cannot claim|can .*be treated|only proximity|causality|static registry|live status feed|proof .*existed|operational|access impact|changed availability|is .*official|urgent|urgency finding|review order|source record prove|row establish|constraints are verified)\b",
        q,
    ):
        return "template:ask:cannot_claim@v1", None

    # 5. Named source-record profile.
    if re.search(
        r"\b(what does .*record.*say|what does .*row.*say|what .*source row.*say|what exactly is in|what fields|field-level|show me record|record .*details|tims-\d+|contents of .*record|fields in .*record|source row actually say)\b",
        q,
    ):
        return "gap:source_record_360_needed", None

    # 6. Entity profile.
    if re.search(
        r"\b(what do we know|profile|look up|rapid or slow|fast charger|normal charger|UPRN|uprn|confidence value|planning-context linkage|opportunity-area context|ev\s*87|asset\s*87|charger\s*87|mvc|4463710|building|parcel)\b",
        q,
    ):
        return "template:ask:entity_360@v2", None

    # 7. General uncertainty.
    if re.search(r"\b(what is uncertain|uncertain|unknowns|what do we not know|what else.*needed|limitations|limitation)\b", q):
        return "template:ask:what_is_uncertain@v1", None

    # 8. External context.
    if re.search(r"\b(weather|other charging sites|other chargers|nearby not shown|external data|budget report|emergency database)\b", q):
        return "gap:external_context_source_needed", None

    # 9. Refusals not handled by action.
    if re.search(r"\b(comply with|compliance with|legal violation|violation|liable|fine them|will there|predict|tomorrow|next week|probability|likelihood|future incident|cyber security standards)\b", q):
        return "refuse:prediction_or_finding", "prediction_or_finding"
    if re.search(r"\b(who do i call|who should i call|which person|which department|owner name|driver|face|biometric|identify|responsible person|contact details)\b", q):
        return "refuse:identity_or_person", "identity_or_person"
    if re.search(r"\b(school|hospital|crime|unrelated place|outside this board)\b", q):
        return "refuse:out_of_scope_entity", "out_of_scope_entity"

    return "ui_help", None


def create_contract() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04",
        "generated_at": now(),
        "double_label_gate_threshold": THRESHOLD,
        "labels": LABELS,
        "closed_labels": sorted(LABELS),
        "deprecated_labels": DEPRECATED_LABELS,
        "first_match_rules": [
            "board_capability_or_boundary_before_external_action",
            "external_action_shaped_refusal",
            "patch_queue_query_collapse",
            "evidence_source_retrieval",
            "missing_evidence_gap",
            "claimability_live_blocked_proof_boundary",
            "named_source_record_profile_narrow",
            "entity_profile_neutral_facts",
            "general_uncertainty",
            "external_context_source_gap",
            "remaining_refusals",
        ],
        "requires_selected_item_context_rule": {
            "true_only_when": [
                "pronoun_or_ellipsis_without_named_entity_record_city_or_board",
                "selected-item action/help request such as run the check or generate the brief for this",
            ],
            "false_when": [
                "question explicitly names item/entity/record/city/source/board capability",
                "selected context would help but is not required to interpret the question",
            ],
        },
        "v04_policy": [
            "No new labels are introduced.",
            "Known v0.3 hard rows are anchors and excluded from the next double-label denominator.",
            "prove/establish/verify wording routes to cannot_claim unless asking for field contents.",
            "source-record profile is restricted to record contents/fields/details.",
            "capability questions are ui_help; imperative external outcomes are refuse:action_shaped.",
        ],
    }


def validate_anchor_set(
    anchors: dict[str, Any], v03_audit: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    row_by_id = {row["question_id"]: row for row in rows}
    audit_by_id = {item["row_id"]: item for item in v03_audit.get("disagreements", [])}
    anchor_map = {item["row_id"]: item for item in anchors.get("anchors", [])}

    results = []
    for row_id, anchor in sorted(anchor_map.items()):
        corpus_row = row_by_id.get(row_id)
        audit_row = audit_by_id.get(row_id)
        errors = []
        if corpus_row is None:
            errors.append("missing_from_full_150_row_corpus")
        if audit_row is None:
            errors.append("missing_from_v03_disagreement_audit")
        if corpus_row and audit_row and corpus_row.get("raw_question") != audit_row.get("raw_question"):
            errors.append("raw_question_mismatch_between_corpus_and_v03_audit")
        if corpus_row and corpus_row.get("raw_question") != audit_row.get("raw_question"):
            pass
        route = anchor.get("canonical_route")
        refusal_class = anchor.get("expected_refusal_class")
        if route not in LABELS:
            errors.append("canonical_route_not_closed_v04_label")
        expected_refusal = REFUSAL_CLASS_BY_LABEL.get(route)
        if expected_refusal != refusal_class:
            errors.append("refusal_class_does_not_match_route")
        results.append(
            {
                "row_id": row_id,
                "status": "PASS" if not errors else "FAIL",
                "raw_question": None if corpus_row is None else corpus_row.get("raw_question"),
                "canonical_route": route,
                "expected_refusal_class": refusal_class,
                "errors": errors,
            }
        )

    missing_from_anchor = sorted(set(audit_by_id) - set(anchor_map))
    extra_in_anchor = sorted(set(anchor_map) - set(audit_by_id))
    report = {
        "schema_version": "citybrain.d14.route_taxonomy_v04.anchor_set_validation.v1",
        "generated_at": now(),
        "status": "PASS"
        if len(anchor_map) == 21
        and not missing_from_anchor
        and not extra_in_anchor
        and all(item["status"] == "PASS" for item in results)
        else "FAIL",
        "anchor_rows": len(anchor_map),
        "v03_disagreement_rows": len(audit_by_id),
        "missing_from_anchor": missing_from_anchor,
        "extra_in_anchor": extra_in_anchor,
        "results": results,
    }
    return anchor_map, report


def relabel_rows(rows: list[dict[str, Any]], anchor_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    relabeled = []
    for row in rows:
        out = dict(row)
        row_id = out["question_id"]
        if row_id in anchor_map:
            label = anchor_map[row_id]["canonical_route"]
            refusal_class = anchor_map[row_id]["expected_refusal_class"]
            out["adjudicated_anchor_v04"] = True
            out["adjudicated_anchor_reason_v04"] = anchor_map[row_id].get("reason")
        else:
            label, refusal_class = route_v04(out)
            out["adjudicated_anchor_v04"] = False
        out["taxonomy_version"] = TAXONOMY_VERSION
        out["normalized_question"] = normalize_question(str(out.get("raw_question", "")))
        out["requires_selected_item_context"] = requires_context_v04(out)
        out["expected_route_label"] = label
        out["expected_refusal_class"] = refusal_class
        out["notes"] = "v0.4 adjudicated anchor" if out["adjudicated_anchor_v04"] else "v0.4 first-match relabel"
        relabeled.append(out)
    return relabeled


def distribution_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_counts = Counter(row.get("expected_route_label") for row in rows)
    persona_counts = Counter(row.get("persona") for row in rows)
    route_by_persona: dict[str, dict[str, int]] = defaultdict(dict)
    for row in rows:
        persona = str(row.get("persona"))
        route = str(row.get("expected_route_label"))
        route_by_persona[persona][route] = route_by_persona[persona].get(route, 0) + 1

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
    refusal_class_errors = []
    for row in rows:
        label = row.get("expected_route_label")
        expected = REFUSAL_CLASS_BY_LABEL.get(label)
        actual = row.get("expected_refusal_class")
        if expected != actual:
            refusal_class_errors.append({"row_id": row["question_id"], "label": label, "expected": expected, "actual": actual})

    return {
        "schema_version": "citybrain.d14.corpus_v0_label_distribution_v04.v1",
        "generated_at": now(),
        "status": "PASS" if not deprecated_hits and not non_closed_hits and not refusal_class_errors else "FAIL",
        "rows": len(rows),
        "route_counts": dict(sorted(route_counts.items())),
        "persona_counts": dict(sorted(persona_counts.items())),
        "route_by_persona": {k: dict(sorted(v.items())) for k, v in sorted(route_by_persona.items())},
        "adjudicated_anchor_rows": sum(1 for row in rows if row.get("adjudicated_anchor_v04")),
        "deprecated_label_hits": deprecated_hits,
        "non_closed_label_hits": non_closed_hits,
        "refusal_class_errors": refusal_class_errors,
    }


def gap_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gap_rows = [
        {
            "row_id": row["question_id"],
            "persona": row.get("persona"),
            "expected_route_label": row.get("expected_route_label"),
            "raw_question": row.get("raw_question"),
            "adjudicated_anchor_v04": row.get("adjudicated_anchor_v04", False),
        }
        for row in rows
        if str(row.get("expected_route_label", "")).startswith("gap:")
    ]
    return {
        "schema_version": "citybrain.d14.corpus_v0_template_gap_v04.v1",
        "generated_at": now(),
        "status": "PASS",
        "gap_rows": len(gap_rows),
        "gap_route_counts": dict(sorted(Counter(row["expected_route_label"] for row in gap_rows).items())),
        "rows": gap_rows,
    }


def label_change_report(v03_rows: list[dict[str, Any]], v04_rows: list[dict[str, Any]]) -> dict[str, Any]:
    old_by_id = {row["question_id"]: row for row in v03_rows}
    changes = []
    for row in v04_rows:
        old = old_by_id[row["question_id"]]
        route_changed = old.get("expected_route_label") != row.get("expected_route_label")
        context_changed = old.get("requires_selected_item_context") != row.get("requires_selected_item_context")
        refusal_changed = old.get("expected_refusal_class") != row.get("expected_refusal_class")
        if route_changed or context_changed or refusal_changed or row.get("adjudicated_anchor_v04"):
            changes.append(
                {
                    "row_id": row["question_id"],
                    "raw_question": row.get("raw_question"),
                    "v03_route": old.get("expected_route_label"),
                    "v04_route": row.get("expected_route_label"),
                    "v03_refusal_class": old.get("expected_refusal_class"),
                    "v04_refusal_class": row.get("expected_refusal_class"),
                    "v03_requires_selected_item_context": old.get("requires_selected_item_context"),
                    "v04_requires_selected_item_context": row.get("requires_selected_item_context"),
                    "adjudicated_anchor_v04": row.get("adjudicated_anchor_v04"),
                }
            )
    return {
        "schema_version": "citybrain.d14.corpus_v0_v03_to_v04_label_change_report.v1",
        "generated_at": now(),
        "status": "PASS",
        "rows_total": len(v04_rows),
        "changed_rows": len(changes),
        "route_changed_rows": sum(1 for item in changes if item["v03_route"] != item["v04_route"]),
        "context_changed_rows": sum(
            1
            for item in changes
            if item["v03_requires_selected_item_context"] != item["v04_requires_selected_item_context"]
        ),
        "changes": changes,
    }


def relabel_audit(rows: list[dict[str, Any]], dist: dict[str, Any]) -> dict[str, Any]:
    source_type_errors = [
        {"row_id": row["question_id"], "source_type": row.get("source_type")}
        for row in rows
        if row.get("source_type") != "synthetic_v0_clean_ai"
    ]
    return {
        "schema_version": "citybrain.d14.v04_relabel_audit.v1",
        "generated_at": now(),
        "status": "PASS"
        if len(rows) == 150
        and dist["status"] == "PASS"
        and not source_type_errors
        and sum(1 for row in rows if row.get("adjudicated_anchor_v04")) == 21
        else "FAIL",
        "rows": len(rows),
        "source_type_errors": source_type_errors,
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "refusal_class_errors": len(dist["refusal_class_errors"]),
        "adjudicated_anchor_rows": sum(1 for row in rows if row.get("adjudicated_anchor_v04")),
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }


def select_blind_sample(rows: list[dict[str, Any]], anchor_ids: set[str], target: int = 50) -> list[dict[str, Any]]:
    non_anchor = [row for row in rows if row["question_id"] not in anchor_ids]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in non_anchor:
        groups[(str(row.get("expected_route_label")), str(row.get("persona")))].append(row)

    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []

    # First pass: one from every represented route/persona group, sorted for determinism.
    for key in sorted(groups):
        row = sorted(groups[key], key=lambda item: item["question_id"])[0]
        selected_ids.add(row["question_id"])
        selected.append(row)

    # Second pass: fill by route scarcity then row id to keep coverage broad and stable.
    route_counts = Counter(row.get("expected_route_label") for row in selected)
    candidates = [row for row in non_anchor if row["question_id"] not in selected_ids]
    for row in sorted(candidates, key=lambda item: (route_counts[item.get("expected_route_label")], item.get("expected_route_label"), item.get("persona"), item["question_id"])):
        if len(selected) >= target:
            break
        selected.append(row)
        selected_ids.add(row["question_id"])
        route_counts[row.get("expected_route_label")] += 1

    # If group coverage exceeded target, keep it; the prompt allows 40-50 preferred, not hard max.
    sample = []
    for row in sorted(selected, key=lambda item: item["question_id"]):
        sample.append(
            {
                "row_id": row["question_id"],
                "raw_question": row.get("raw_question"),
                "persona": row.get("persona"),
                "selected_item_context": row.get("selected_item_context"),
                "source_type": row.get("source_type"),
                "source_session_id": row.get("source_session_id"),
                "source_run_file": row.get("source_run_file"),
                "original_question_id": row.get("original_question_id"),
            }
        )
    return sample


def sample_decision(sample: list[dict[str, Any]], rows: list[dict[str, Any]], anchor_ids: set[str]) -> dict[str, Any]:
    sample_ids = {row["row_id"] for row in sample}
    anchor_overlap = sorted(sample_ids & anchor_ids)
    sample_row_lookup = {row["question_id"]: row for row in rows}
    route_counts = Counter(sample_row_lookup[row_id]["expected_route_label"] for row_id in sample_ids)
    persona_counts = Counter(sample_row_lookup[row_id]["persona"] for row_id in sample_ids)
    return {
        "schema_version": "citybrain.d14.double_label_v04_sample_r1",
        "generated_at": now(),
        "status": STATUS,
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04_BLIND_SAMPLE.jsonl"),
        "blind_sample_rows": len(sample),
        "non_anchor_rows": len(rows) - len(anchor_ids),
        "minimum_required_rows": 26,
        "preferred_rows": "40-50",
        "sample_pct_of_non_anchor_rows": round(len(sample) / max(len(rows) - len(anchor_ids), 1), 4),
        "anchor_rows_excluded_from_denominator": len(anchor_ids),
        "anchor_overlap_rows": anchor_overlap,
        "codex_labels_included": False,
        "route_counts": dict(sorted(route_counts.items())),
        "persona_counts": dict(sorted(persona_counts.items())),
        "expected_next_file": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04_INDEPENDENT_LABELS.jsonl"),
        "split_seal_r3": "NOT_RUN_BLOCKED_PENDING_INDEPENDENT_V04_LABELS",
        "router_preflight": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }


def write_instructions() -> None:
    text = """# v0.4 Independent Double-Label Instructions

Use only:

- `ROUTE_TAXONOMY_V04_CONTRACT.json`
- `ROUTE_TAXONOMY_V04_DECISION_TREE.md`
- this blind sample file

Do not consult `operator_question_corpus_synthetic_v0_labeled_v04_codex_prelim.jsonl`.
Do not use Codex preliminary labels.

For every row in `CORPUS_V0_DOUBLE_LABEL_V04_BLIND_SAMPLE.jsonl`, return JSONL named:

`CORPUS_V0_DOUBLE_LABEL_V04_INDEPENDENT_LABELS.jsonl`

Each row must contain:

- `row_id`
- `normalized_question`
- `requires_selected_item_context`
- `expected_route_label`
- `expected_refusal_class`

Use closed v0.4 labels only. Non-refusal rows must set `expected_refusal_class` to `null`.
The 21 v0.3 hard rows are adjudicated anchors and intentionally excluded from this blind sample.
"""
    write_text(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04_INSTRUCTIONS.md", text)


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
        "schema_version": "citybrain.d14.route_taxonomy_v04.json_parse_audit.v1",
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
        if not path.is_file() or path.suffix.lower() in {".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                hits.append({"path": rel(path), "pattern": pattern})
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v04.secret_audit.v1",
        "generated_at": now(),
        "status": "PASS" if not hits else "FAIL",
        "hits": hits,
    }


def write_changelog() -> None:
    text = """# Route Taxonomy v0.4 Changelog

Status: `PAUSED_D14_ROUTE_TAXONOMY_V04_AWAITING_INDEPENDENT_DOUBLE_LABELS`

v0.4 does not add more labels. It tightens the route decision tree and removes
known recurring ambiguity from the next denominator by treating the 21 v0.3
hard rows as adjudicated anchors.

Key changes:

- 21 v0.3 disagreement rows are canonical v0.4 anchors.
- `prove` / `establish` / `verify` wording routes to `template:ask:cannot_claim@v1`.
- `gap:source_record_360_needed` is limited to source-row fields/details/contents.
- Board/screen/software capability questions route to `ui_help`.
- Imperative external action requests still route to `refuse:action_shaped`.
- Patch board counts/lists/filters/comparisons collapse to `gap:patch_queue_query_needed`.
- `requires_selected_item_context` is true only when the question cannot be interpreted without the selected item.

Split/Seal R3 and router preflight remain blocked pending independent v0.4 labels.
"""
    write_text(ROOT / "ROUTE_TAXONOMY_V04_CHANGELOG.md", text)


def write_local_index() -> None:
    text = """# D14 Route Taxonomy Repair v0.4 R1

Status: `PAUSED_D14_ROUTE_TAXONOMY_V04_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Open first:

- `D14_ROUTE_TAXONOMY_V04_CLOSEOUT_DECISION.json`
- `ROUTE_TAXONOMY_V04_CONTRACT.json`
- `ROUTE_TAXONOMY_V04_DECISION_TREE.md`
- `ROUTE_TAXONOMY_V04_ANCHOR_SET.json`
- `operator_question_corpus_synthetic_v0_labeled_v04_codex_prelim.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04_INSTRUCTIONS.md`

Do not run Split/Seal R3 until independent v0.4 labels are returned and the
double-label disagreement rate is at or below 15%.
"""
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", text)
    write_text(ROOT / "README.md", text)


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def package_outputs() -> None:
    package_path = ROOT / "D14_ROUTE_TAXONOMY_V04_VALIDATION_PACKAGE.zip"
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, rel(path))


def main() -> None:
    validate_inputs()
    clean_root()
    copy_prompt_pack()

    v03_audit = read_json(INPUTS["v03_audit"])
    v03_rows = read_jsonl(INPUTS["v03_labeled"])
    anchors_draft = read_json(INPUTS["v04_anchor_draft"])

    shutil.copy2(INPUTS["v04_tree_draft"], ROOT / "ROUTE_TAXONOMY_V04_DECISION_TREE.md")
    write_json(ROOT / "ROUTE_TAXONOMY_V04_CONTRACT.json", create_contract())
    write_changelog()

    anchor_map, anchor_report = validate_anchor_set(anchors_draft, v03_audit, v03_rows)
    write_json(ROOT / "ROUTE_TAXONOMY_V04_ANCHOR_SET.json", anchors_draft)
    write_json(ROOT / "V04_ANCHOR_SET_VALIDATION_REPORT.json", anchor_report)

    if anchor_report["status"] != "PASS":
        raise SystemExit("Anchor validation failed; see V04_ANCHOR_SET_VALIDATION_REPORT.json")

    v04_rows = relabel_rows(v03_rows, anchor_map)
    write_jsonl(ROOT / "operator_question_corpus_synthetic_v0_labeled_v04_codex_prelim.jsonl", v04_rows)

    dist = distribution_report(v04_rows)
    gaps = gap_report(v04_rows)
    changes = label_change_report(v03_rows, v04_rows)
    relabel_check = relabel_audit(v04_rows, dist)
    write_json(ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_V04_REPORT.json", dist)
    write_json(ROOT / "CORPUS_V0_TEMPLATE_GAP_V04_REPORT.json", gaps)
    write_json(ROOT / "CORPUS_V0_V03_TO_V04_LABEL_CHANGE_REPORT.json", changes)
    write_json(ROOT / "V04_RELABEL_AUDIT.json", relabel_check)

    if relabel_check["status"] != "PASS":
        raise SystemExit("Relabel audit failed; see V04_RELABEL_AUDIT.json")

    anchor_ids = set(anchor_map)
    sample = select_blind_sample(v04_rows, anchor_ids, target=50)
    write_jsonl(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04_BLIND_SAMPLE.jsonl", sample)
    write_instructions()
    gate = sample_decision(sample, v04_rows, anchor_ids)
    write_json(ROOT / "D14_DOUBLE_LABEL_V04_SAMPLE_DECISION.json", gate)

    parse_audit = json_parse_audit()
    secret = secret_audit()
    write_json(ROOT / "JSON_PARSE_AUDIT.json", parse_audit)
    write_json(ROOT / "SECRET_AUDIT.json", secret)

    decision = {
        "task": TASK,
        "status": STATUS,
        "generated_at": now(),
        "input_root": rel(V03_ROOT),
        "output_root": rel(ROOT),
        "v03_remains_failed": True,
        "v03_disagreement_count": v03_audit.get("route_or_refusal_disagreement_count"),
        "v03_disagreement_rate": v03_audit.get("route_or_refusal_disagreement_rate"),
        "v04_contract_exists": True,
        "v04_anchor_set_created": True,
        "v04_anchor_set_validated": anchor_report["status"] == "PASS",
        "full_corpus_relabeled_under_v04": len(v04_rows),
        "adjudicated_anchor_rows": len(anchor_ids),
        "non_anchor_rows": len(v04_rows) - len(anchor_ids),
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "blind_sample_rows": len(sample),
        "blind_sample_anchor_overlap": len(gate["anchor_overlap_rows"]),
        "blind_sample_codex_labels_included": False,
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "json_parse_audit": parse_audit["status"],
        "secret_audit": secret["status"],
        "next_required_file": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V04_INDEPENDENT_LABELS.jsonl"),
    }
    write_json(ROOT / "D14_ROUTE_TAXONOMY_V04_CLOSEOUT_DECISION.json", decision)
    write_local_index()
    package_outputs()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
