#!/usr/bin/env python3
"""Repair D14 route taxonomy v0.2 and export a new blind label sample.

This lane does not train a router and does not run Split/Seal R3.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
PREV_ROOT = OUTPUTS / "main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate"
ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v02_r1"
PROMPT_ROOT = REPO / "tmp" / "citybrain_d14_route_taxonomy_repair_v02_r1"

TASK = "MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V02-R1"
STATUS = "PAUSED_D14_ROUTE_TAXONOMY_V02_AWAITING_INDEPENDENT_DOUBLE_LABELS"

INPUTS = {
    "prior_double_label_audit": PREV_ROOT / "CORPUS_V0_DOUBLE_LABEL_AUDIT.json",
    "v01_labeled": PREV_ROOT / "operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl",
    "assembled_unlabeled": PREV_ROOT / "operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl",
    "prior_gap_report": PREV_ROOT / "CORPUS_V0_TEMPLATE_GAP_REPORT.json",
    "independent_labels": PREV_ROOT / "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl",
}

TEMPLATE_ROUTES = {
    "template:ask:entity_360@v1": "Entity profile/fact lookup for a visible/canonical entity.",
    "template:ask:what_supports@v1": "Evidence/support for a selected situation, not a single source-row semantics request.",
    "template:ask:what_is_uncertain@v1": "General uncertainty known to the existing template.",
    "template:ask:cannot_claim@v1": "Supported negative/cannot-claim answer for current item/entity/board state.",
}

GAP_DEFINITIONS = {
    "gap:source_record_360_needed": {
        "artifact": "ASK template",
        "priority": "P0",
        "blocks_router_v0": True,
        "description": "Named source-row questions asking what a source says, proves, supports, or does not say.",
    },
    "gap:evidence_gap_template_needed": {
        "artifact": "ASK template",
        "priority": "P0",
        "blocks_router_v0": True,
        "description": "Missing evidence, absent live source, or source-depth questions for a current item/entity.",
    },
    "gap:patch_queue_filter_by_city": {
        "artifact": "WATCH query",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Filter visible patch-board queue by city.",
    },
    "gap:patch_queue_open_count": {
        "artifact": "WATCH query",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Count open/current review items across the patch board.",
    },
    "gap:patch_queue_update_date_comparison": {
        "artifact": "WATCH query",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Compare queue items by update date such as today versus yesterday.",
    },
    "gap:patch_queue_filtering_and_summary_by_city_date": {
        "artifact": "WATCH query",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Return city-filtered situation summaries for a date window.",
    },
    "gap:patch_queue_aggregate_counts": {
        "artifact": "WATCH query",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Aggregate patch-board queue counts by status, city, date, or category.",
    },
    "gap:external_sharing_guidance": {
        "artifact": "UI help / policy content",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Questions about sharing cockpit content outside the local review context.",
    },
    "gap:local_note_visibility_guidance": {
        "artifact": "UI help / review workspace feature",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Questions about local note storage, visibility, and export scope.",
    },
    "gap:human_review_timestamp_status": {
        "artifact": "review workspace feature",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Questions asking when a human last reviewed or checked an item.",
    },
    "gap:weather_context_for_patch_area": {
        "artifact": "source/data gap",
        "priority": "P2",
        "blocks_router_v0": False,
        "description": "Weather-context questions for the current patch area where no local source is connected.",
    },
    "gap:charging_site_source_depth_scan": {
        "artifact": "CHECK rule",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Scan source depth across other charging sites or comparable charger records.",
    },
    "gap:boundary_status_template_needed": {
        "artifact": "ASK template / UI help",
        "priority": "P0",
        "blocks_router_v0": True,
        "description": "Board capability/boundary-state questions that are answerable but lack a deterministic template.",
    },
    "gap:planning_context_boundary_template_needed": {
        "artifact": "ASK template",
        "priority": "P1",
        "blocks_router_v0": False,
        "description": "Planning-context candidate-only and building-control verification boundary questions.",
    },
}

REFUSAL_CLASSES = {
    "refuse:action_shaped": "The user asks the system to execute or initiate an action.",
    "refuse:prediction_or_finding": "The user asks for a prediction, legal/certified finding, or unsupported determination outside a supported negative answer.",
    "refuse:identity_or_person": "The user asks to identify or infer a person/party.",
    "refuse:out_of_scope_entity": "The user asks about an entity/domain outside the local bundle and not represented as a product gap.",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def preserve_independent_v02_labels() -> dict[str, bytes]:
    preserved: dict[str, bytes] = {}
    for filename in [
        "CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS.jsonl",
        "CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS_REPORT.json",
    ]:
        path = ROOT / filename
        if path.exists():
            preserved[filename] = path.read_bytes()
    return preserved


def restore_preserved_files(preserved: dict[str, bytes]) -> None:
    for filename, data in preserved.items():
        (ROOT / filename).write_bytes(data)


def route_family(label: str | None) -> str:
    if not label:
        return "missing"
    if label.startswith("template:ask:"):
        return label.replace("template:ask:", "").replace("@v1", "")
    if label.startswith("refuse:"):
        return label
    if label.startswith("gap:"):
        return "gap"
    return label


def failure_analysis(audit: dict[str, Any]) -> tuple[dict[str, Any], str]:
    disagreements = audit.get("disagreements", [])
    pair_counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    refusal_vs_answerable: list[str] = []
    aggregate_gap_rows: list[str] = []
    generic_gap_rows: list[str] = []
    for item in disagreements:
        codex = item.get("codex_expected_route_label")
        independent = item.get("independent_expected_route_label")
        pair = f"{route_family(codex)} -> {route_family(independent)}"
        pair_counts[pair] += 1
        row = {
            "row_id": item.get("row_id"),
            "raw_question": item.get("raw_question"),
            "codex_expected_route_label": codex,
            "independent_expected_route_label": independent,
            "codex_expected_refusal_class": item.get("codex_expected_refusal_class"),
            "independent_expected_refusal_class": item.get("independent_expected_refusal_class"),
            "pair": pair,
        }
        rows.append(row)
        if str(codex).startswith("refuse:") and not str(independent).startswith("refuse:"):
            refusal_vs_answerable.append(item.get("row_id"))
        if "unsupported_aggregate_or_comparison" in str(codex) and str(independent).startswith("gap:"):
            aggregate_gap_rows.append(item.get("row_id"))
        if str(codex) == "gap:general operator question needs taxonomy review":
            generic_gap_rows.append(item.get("row_id"))

    context_disagreements = audit.get("context_dependency_disagreements", [])
    report = {
        "schema_version": "citybrain.d14.double_label_failure_analysis_r1",
        "generated_at": now(),
        "prior_status": audit.get("status"),
        "disagreement_count": len(disagreements),
        "disagreement_rate": audit.get("route_or_refusal_disagreement_rate"),
        "context_dependency_disagreement_count": len(context_disagreements),
        "context_dependency_disagreement_rate": audit.get("context_dependency_disagreement_rate"),
        "pair_counts": dict(pair_counts.most_common()),
        "refusal_used_where_supported_negative_or_gap_exists": refusal_vs_answerable,
        "aggregate_or_filter_questions_misclassified_as_refusal": aggregate_gap_rows,
        "generic_gap_rows_requiring_precise_gap_id": generic_gap_rows,
        "evidence_rows": rows,
        "diagnosis": [
            "The corpus rows parsed and survived assembly; the failure is route taxonomy overlap.",
            "Refusal must be reserved for user requests outside the review/query boundary, not negative answers backed by local evidence.",
            "Patch-board aggregation/filter requests are product gaps, not refusals.",
            "Source-row semantics need a separate route or precise gap from entity_360.",
        ],
        "status": "PASS_FAILURE_ANALYSIS_COMPLETE",
    }
    md_lines = [
        "# D14 Double-Label Failure Analysis R1",
        "",
        f"Prior disagreement: `{len(disagreements)} / {audit.get('blind_sample_rows')}` = `{audit.get('route_or_refusal_disagreement_rate')}`.",
        "",
        "## Pair Counts",
    ]
    for pair, count in pair_counts.most_common():
        md_lines.append(f"- `{pair}`: {count}")
    md_lines += ["", "## Evidence Rows"]
    for row in rows:
        md_lines.append(
            f"- `{row['row_id']}` {row['raw_question']} | Codex `{row['codex_expected_route_label']}` vs independent `{row['independent_expected_route_label']}`"
        )
    return report, "\n".join(md_lines)


def taxonomy_contract() -> tuple[dict[str, Any], str]:
    routes = {
        **{route: {"kind": "template", "description": description} for route, description in TEMPLATE_ROUTES.items()},
        **{route: {"kind": "gap", **meta} for route, meta in GAP_DEFINITIONS.items()},
        **{route: {"kind": "refusal", "description": description} for route, description in REFUSAL_CLASSES.items()},
        "ui_help": {"kind": "ui_help", "description": "Static UI/help answer for usage mechanics covered by the cockpit."},
    }
    contract = {
        "schema_version": "citybrain.d14.route_taxonomy_v0_2",
        "generated_at": now(),
        "version_id": "citybrain.d14.route_taxonomy_v0_2",
        "status": "PASS",
        "closed_route_labels": routes,
        "core_rules": [
            "Refusal is not a supported negative answer; use templates or precise gaps when retained local evidence can answer cannot-claim/not-supported/not-in-records.",
            "Action commands are refusals; questions about board capability or whether an action occurred are cannot-claim, ui_help, or precise gaps.",
            "Named source-row semantics route to source_record_360 gap until a deterministic source-row template exists.",
            "Missing evidence/source-depth questions route to evidence_gap gap until a deterministic evidence-gap template exists.",
            "Patch-board list/count/filter/comparison requests are query gaps, not unsupported-aggregate refusals.",
            "Entity_360 is for entity profile/facts, not source-row proof or missing-evidence questions.",
            "requires_selected_item_context is true only when the raw question target is not identifiable without selected item/session context.",
        ],
        "do_not_use": [
            "gap:general operator question needs taxonomy review",
            "refuse:insufficient_source_depth",
            "refuse:unsupported_aggregate_or_comparison for patch-board list/filter/count requests",
            "entity_360 for every question that merely contains a named entity",
        ],
    }
    md = """# Route Taxonomy v0.2 Decision Tree

1. If the user asks the system to execute or initiate an action, use `refuse:action_shaped`.
2. If the user asks for person/party identification, use `refuse:identity_or_person`.
3. If the question is a prediction or legal/certified finding outside a supported negative answer, use `refuse:prediction_or_finding`.
4. If the question asks what a named source row says, proves, supports, or lacks, use `gap:source_record_360_needed`.
5. If the question asks whether evidence is missing, whether a live source exists, or why a claim is unsupported, use `gap:evidence_gap_template_needed`.
6. If the question asks whether a current item/entity/board can claim something, use `template:ask:cannot_claim@v1`.
7. If the question asks source support for a selected situation, use `template:ask:what_supports@v1`.
8. If the question asks current known uncertainties in ordinary terms and is covered by the existing uncertainty template, use `template:ask:what_is_uncertain@v1`.
9. If the question asks entity facts/profile/attributes, use `template:ask:entity_360@v1`.
10. If the question asks how to use the UI, use `ui_help` when static help covers it; otherwise use a precise UI/help gap.
11. If the question asks patch-board list/filter/count/date comparison, use a precise patch queue gap.

Do not use generic gaps. Do not train or seal from this taxonomy until v0.2 double-label disagreement is <= 15%.
"""
    return contract, md


def normalize_question(raw: str) -> str:
    q = raw.strip()
    replacements = {
        "whats": "what is",
        "chrgr": "charger",
        "scrubs ln": "Scrubbs Lane",
        "ev": "EV",
        "nyc": "NYC",
        "mvc": "MVC",
        "uprn": "UPRN",
    }
    for src, dst in replacements.items():
        q = re.sub(rf"\b{re.escape(src)}\b", dst, q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if q and q[-1] not in "?!.":
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def requires_context_v02(raw: str, selected_context: str) -> bool:
    q = raw.lower()
    named = re.search(
        r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|scrubbs|scrubs|westway|nyc|mvc|4463710|uprn|london datastore|chicago|london|howard avenue)\b",
        q,
    )
    if named:
        return False
    if selected_context == "general_patch_board":
        return False
    if re.search(r"\b(this|that|it|here|there|selected|these|those|all this|the item|the brief|the log|the board)\b", q):
        return True
    if len(q.split()) <= 4 and selected_context != "general_patch_board":
        return True
    return False


def classify_v02(row: dict[str, Any]) -> tuple[str, str | None]:
    q = str(row.get("raw_question", "")).lower()
    context = str(row.get("selected_item_context", "")).lower()

    # Commands that ask the system to initiate external action.
    if re.search(r"\b(dispatch|enforce|approve|take action|assign|notify|alert .*team|call .*team|call .*operator|send .*team|publish alert now|create case now|open a ticket|file a case|fine them)\b", q):
        return "refuse:action_shaped", "action_shaped"
    if re.search(r"^(dispatch|route|enforce|approve|publish|alert|call|notify|create|open|file|send)\b", q) and not re.search(r"\b(can|could|did|does|how|what|where|why|is|are)\b", q[:25]):
        return "refuse:action_shaped", "action_shaped"
    if re.search(r"\b(person|driver|face|biometric|owner name|who is responsible|identify)\b", q) and not re.search(r"\bwho can see|reviewed by a person|checked by a person\b", q):
        return "refuse:identity_or_person", "identity_or_person"
    if re.search(r"\b(will there|predict|tomorrow|next week|probability|likelihood of|future incident)\b", q):
        return "refuse:prediction_or_finding", "prediction_or_finding"

    # Product gaps before broad templates.
    if re.search(r"\b(source row|source record|london datastore|tims|what .*source.*say|what .*source.*prove|does .*source.*say|does .*record.*say|what .*record.*prove|record actually say|source brief)\b", q):
        return "gap:source_record_360_needed", None
    if re.search(r"\b(live service-status|live service status|live source|evidence is missing|what evidence.*missing|missing data|missing source|source depth|stronger evidence|direct evidence|why .*unsupported|without .*data|no .*source|available now|blocked\\?|definitely available|currently available|is .*blocked|is .*available|was unavailable)\b", q):
        if re.search(r"\b(can we claim|can .*be treated|claim|cannot claim|what cannot|not prove|not supported|unsupported|only proximity)\b", q):
            return "template:ask:cannot_claim@v1", None
        return "gap:evidence_gap_template_needed", None

    if re.search(r"\b(show|list|filter).*\blondon\b|\ball london\b", q):
        if re.search(r"\btoday|yesterday|updated|date\b", q):
            return "gap:patch_queue_filtering_and_summary_by_city_date", None
        return "gap:patch_queue_filter_by_city", None
    if re.search(r"\bhow many|count|open across|aggregate|total\b", q) and re.search(r"\b(review items|patch|queue|items|open)\b", q):
        return "gap:patch_queue_open_count", None
    if re.search(r"\btoday versus yesterday|updated today|updated yesterday|date comparison|last checked\b", q):
        if re.search(r"\bperson|human\b", q):
            return "gap:human_review_timestamp_status", None
        return "gap:patch_queue_update_date_comparison", None
    if re.search(r"\bweather\b", q):
        return "gap:weather_context_for_patch_area", None
    if re.search(r"\bother charging sites|other charger|all chargers|charging site.*scan\b", q):
        return "gap:charging_site_source_depth_scan", None
    if re.search(r"\bshare externally|safe to share|external sharing|send this to my email|export my review notes|who else can see|where .*notes stored|notes stored|visibility\b", q):
        if re.search(r"\bhow do i export|copy|download\b", q):
            return "ui_help", None
        return "gap:external_sharing_guidance" if "share" in q or "email" in q else "gap:local_note_visibility_guidance", None
    if re.search(r"\bwhen .*checked by a person|last reviewed by a person|human last reviewed\b", q):
        return "gap:human_review_timestamp_status", None
    if re.search(r"\bbuilding-control verification|candidate-only|candidate only|planning context boundary\b", q):
        return "gap:planning_context_boundary_template_needed", None
    if re.search(r"\bcan this board|can this publish|did .*publish|alerts published|official happen|anything official|official from this board|created from this board|what happens if.*mark reviewed|what to do next|is .*official|urgent|urgency finding|review order|live monitoring|production|public api\b", q):
        return "template:ask:cannot_claim@v1", None

    if re.search(r"\b(how do i|where do i|what button|can i click|use this board|export|copy|add note|mark reviewed|open ask|generate brief|run check|checks panel|why does .*panel)\b", q):
        return "ui_help", None
    if re.search(r"\b(can we claim|what can.*claim|what cannot|cannot claim|not prove|prove|only proximity|causality|legal determination|certified|availability changed|affected building truth|access impact)\b", q):
        return "template:ask:cannot_claim@v1", None
    if re.search(r"\b(what supports|support|evidence for|why .*ranked|why .*review|knowns|on file|what backs|source records support)\b", q):
        return "template:ask:what_supports@v1", None
    if re.search(r"\b(what is uncertain|uncertain|unknowns|what do we not know|what else.*needed|gap)\b", q):
        return "template:ask:what_is_uncertain@v1", None
    if re.search(r"\b(what do we know|profile|look up|rapid or slow|fast charger|normal charger|uprn|ev\s*87|asset\s*87|charger\s*87|mvc|4463710)\b", q) or context in {"ev_asset_87", "nyc_mvc_candidate_context"}:
        return "template:ask:entity_360@v1", None
    if re.search(r"\b(budget|school|hospital|crime|police)\b", q):
        return "refuse:out_of_scope_entity", "out_of_scope_entity"
    return "gap:boundary_status_template_needed", None


def relabel_v02(assembled: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in assembled:
        label, refusal = classify_v02(row)
        new_row = dict(row)
        new_row["normalized_question"] = normalize_question(str(row.get("raw_question", "")))
        new_row["requires_selected_item_context"] = requires_context_v02(str(row.get("raw_question", "")), str(row.get("selected_item_context", "")))
        new_row["expected_route_label"] = label
        new_row["expected_refusal_class"] = refusal
        new_row["taxonomy_version"] = "citybrain.d14.route_taxonomy_v0_2"
        rows.append(new_row)
    return rows


def distribution_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_counts = Counter(row["expected_route_label"] for row in rows)
    refusal_counts = Counter(row["expected_refusal_class"] for row in rows if row.get("expected_refusal_class"))
    crosstab: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        crosstab[row["persona"]][row["expected_route_label"]] += 1
    return {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.label_distribution_v02.v1",
        "generated_at": now(),
        "row_count": len(rows),
        "route_counts": dict(route_counts.most_common()),
        "refusal_class_counts": dict(refusal_counts.most_common()),
        "persona_route_crosstab": {persona: dict(sorted(routes.items())) for persona, routes in sorted(crosstab.items())},
        "requires_selected_item_context_count": sum(1 for row in rows if row["requires_selected_item_context"]),
        "requires_selected_item_context_rate": round(sum(1 for row in rows if row["requires_selected_item_context"]) / max(len(rows), 1), 4),
        "generic_gap_count": sum(1 for row in rows if row["expected_route_label"] == "gap:general operator question needs taxonomy review"),
        "status": "PASS",
    }


def gap_reports(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    counts = Counter(row["expected_route_label"] for row in rows if str(row["expected_route_label"]).startswith("gap:"))
    for row in rows:
        label = row["expected_route_label"]
        if str(label).startswith("gap:") and len(examples[label]) < 8:
            examples[label].append(
                {
                    "row_id": row["question_id"],
                    "persona": row["persona"],
                    "raw_question": row["raw_question"],
                }
            )
    gap_report = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.template_gap_v02_report.v1",
        "generated_at": now(),
        "gap_count": sum(counts.values()),
        "gaps_ranked": [
            {"gap_id": gap, "count": count, "examples": examples[gap], **GAP_DEFINITIONS.get(gap, {})}
            for gap, count in counts.most_common()
        ],
        "status": "PASS",
    }
    registry = {
        "schema_version": "citybrain.d14.template_gap_registry_v02.v1",
        "generated_at": now(),
        "status": "PASS",
        "no_generic_gap_labels": "gap:general operator question needs taxonomy review" not in counts,
        "gaps": [
            {"gap_id": gap, "count": count, "examples": examples[gap], **GAP_DEFINITIONS.get(gap, {})}
            for gap, count in counts.most_common()
        ],
    }
    md = ["# Template Gap Registry v0.2", ""]
    for item in registry["gaps"]:
        md.append(f"- `{item['gap_id']}`: {item['count']} rows, priority `{item.get('priority')}`, consumer `{item.get('artifact')}`")
    return gap_report, "\n".join(md), registry


def label_change_report(v01_rows: list[dict[str, Any]], v02_rows: list[dict[str, Any]]) -> dict[str, Any]:
    old = {row["question_id"]: row for row in v01_rows}
    changes: list[dict[str, Any]] = []
    for row in v02_rows:
        prior = old.get(row["question_id"], {})
        if prior.get("expected_route_label") != row.get("expected_route_label") or prior.get("expected_refusal_class") != row.get("expected_refusal_class"):
            changes.append(
                {
                    "row_id": row["question_id"],
                    "raw_question": row["raw_question"],
                    "v01_route": prior.get("expected_route_label"),
                    "v02_route": row.get("expected_route_label"),
                    "v01_refusal_class": prior.get("expected_refusal_class"),
                    "v02_refusal_class": row.get("expected_refusal_class"),
                }
            )
    return {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.label_change_from_v01.v1",
        "generated_at": now(),
        "row_count": len(v02_rows),
        "changed_rows": len(changes),
        "unchanged_rows": len(v02_rows) - len(changes),
        "changes": changes,
        "status": "PASS",
    }


def blind_sample_v02(rows: list[dict[str, Any]], prior_disagreement_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {row["question_id"]: row for row in rows}
    selected_ids: list[str] = []
    for row_id in prior_disagreement_ids:
        if row_id in by_id and row_id not in selected_ids:
            selected_ids.append(row_id)
    target = max(math.ceil(len(rows) * 0.20), 1)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["persona"], row["expected_route_label"])].append(row)
    for group_rows in groups.values():
        group_rows.sort(key=lambda row: row["question_id"])
    index = 0
    while len(selected_ids) < target or index < 2:
        made_progress = False
        for key in sorted(groups):
            group_rows = groups[key]
            if index >= len(group_rows):
                continue
            row_id = group_rows[index]["question_id"]
            if row_id not in selected_ids:
                selected_ids.append(row_id)
                made_progress = True
        if not made_progress:
            break
        index += 1
        if len(selected_ids) >= max(target, len(prior_disagreement_ids)) and index >= 2:
            break
    sample_rows = [by_id[row_id] for row_id in selected_ids]
    sample_rows.sort(key=lambda row: row["question_id"])
    return [
        {
            "row_id": row["question_id"],
            "persona": row["persona"],
            "selected_item_context": row["selected_item_context"],
            "raw_question": row["raw_question"],
        }
        for row in sample_rows
    ]


def compare_v02_labels(v02_rows: list[dict[str, Any]], blind_sample: list[dict[str, Any]]) -> dict[str, Any] | None:
    independent_path = ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS.jsonl"
    if not independent_path.exists():
        return None
    independent_rows = read_jsonl(independent_path)
    codex_by_id = {row["question_id"]: row for row in v02_rows}
    blind_ids = [row["row_id"] for row in blind_sample]
    independent_ids = [str(row.get("row_id", "")) for row in independent_rows]
    required_fields = {
        "row_id",
        "normalized_question",
        "requires_selected_item_context",
        "expected_route_label",
        "expected_refusal_class",
    }
    schema_errors = [
        {"row_index": index, "row_id": row.get("row_id"), "fields": sorted(row)}
        for index, row in enumerate(independent_rows, 1)
        if set(row) != required_fields
    ]
    disagreements: list[dict[str, Any]] = []
    context_disagreements: list[dict[str, Any]] = []
    for row in independent_rows:
        row_id = str(row.get("row_id", ""))
        codex = codex_by_id.get(row_id)
        if not codex:
            continue
        if codex.get("expected_route_label") != row.get("expected_route_label") or codex.get("expected_refusal_class") != row.get("expected_refusal_class"):
            disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_expected_route_label": codex.get("expected_route_label"),
                    "independent_expected_route_label": row.get("expected_route_label"),
                    "codex_expected_refusal_class": codex.get("expected_refusal_class"),
                    "independent_expected_refusal_class": row.get("expected_refusal_class"),
                    "adjudication_status": "NOT_ADJUDICATED_TAXONOMY_STILL_AMBIGUOUS",
                }
            )
        if bool(codex.get("requires_selected_item_context")) != bool(row.get("requires_selected_item_context")):
            context_disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_requires_selected_item_context": codex.get("requires_selected_item_context"),
                    "independent_requires_selected_item_context": row.get("requires_selected_item_context"),
                }
            )
    denominator = len(blind_ids) if blind_ids else 1
    disagreement_rate = len(disagreements) / denominator
    missing_ids = sorted(set(blind_ids) - set(independent_ids))
    extra_ids = sorted(set(independent_ids) - set(blind_ids))
    row_order_ok = blind_ids == independent_ids
    status = (
        "PASS_D14_ROUTE_TAXONOMY_V02_DOUBLE_LABEL_STABLE_READY_FOR_SPLIT_SEAL"
        if disagreement_rate <= 0.15 and not schema_errors and not missing_ids and not extra_ids and row_order_ok
        else "PAUSED_D14_ROUTE_TAXONOMY_V02_STILL_AMBIGUOUS"
    )
    audit = {
        "schema_version": "citybrain.d14.double_label_v02_audit.v1",
        "generated_at": now(),
        "status": status,
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl"),
        "independent_labels": rel(independent_path),
        "independent_labels_sha256": sha256_file(independent_path),
        "blind_sample_rows": len(blind_ids),
        "independent_rows": len(independent_rows),
        "row_ids_match_blind_sample_order": row_order_ok,
        "missing_row_ids": missing_ids,
        "extra_row_ids": extra_ids,
        "schema_errors": schema_errors,
        "route_or_refusal_disagreement_count": len(disagreements),
        "route_or_refusal_disagreement_rate": round(disagreement_rate, 4),
        "context_dependency_disagreement_count": len(context_disagreements),
        "context_dependency_disagreement_rate": round(len(context_disagreements) / denominator, 4),
        "threshold": 0.15,
        "disagreements": disagreements,
        "context_dependency_disagreements": context_disagreements,
        "split_and_seal_r3_status": "READY" if disagreement_rate <= 0.15 else "BLOCKED_TAXONOMY_STILL_AMBIGUOUS",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }
    write_json(ROOT / "D14_DOUBLE_LABEL_V02_AUDIT.json", audit)
    return audit


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def local_index(status: str) -> None:
    lines = [
        "# D14 Route Taxonomy Repair v0.2 R1",
        "",
        f"Status: `{status}`",
        "",
        "Open first:",
        "- `ROUTE_TAXONOMY_V02_DECISION_TREE.md`",
        "- `D14_DOUBLE_LABEL_FAILURE_ANALYSIS_R1.md`",
        "- `TEMPLATE_GAP_REGISTRY_V02.md`",
        "- `CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl`",
        "- `D14_DOUBLE_LABEL_V02_GATE_DECISION.json`",
        "",
        "Split/Seal R3 and router training are still blocked pending independent v0.2 labels.",
    ]
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(ROOT / "D14_ROUTE_TAXONOMY_REPAIR_README.md", "\n".join(lines))
    write_text(ROOT / "README.md", "\n".join(lines))


def main() -> None:
    preserved = preserve_independent_v02_labels()
    clean_root()
    restore_preserved_files(preserved)
    (ROOT / "prompt_pack").mkdir(parents=True, exist_ok=True)
    for path in sorted(PROMPT_ROOT.glob("*.md")):
        shutil.copy2(path, ROOT / "prompt_pack" / path.name)

    audit = read_json(INPUTS["prior_double_label_audit"], {})
    v01_rows = read_jsonl(INPUTS["v01_labeled"])
    assembled = read_jsonl(INPUTS["assembled_unlabeled"])

    analysis_json, analysis_md = failure_analysis(audit)
    write_json(ROOT / "D14_DOUBLE_LABEL_FAILURE_ANALYSIS_R1.json", analysis_json)
    write_text(ROOT / "D14_DOUBLE_LABEL_FAILURE_ANALYSIS_R1.md", analysis_md)

    contract, decision_tree_md = taxonomy_contract()
    write_json(ROOT / "ROUTE_TAXONOMY_V02_CONTRACT.json", contract)
    write_text(ROOT / "ROUTE_TAXONOMY_V02_DECISION_TREE.md", decision_tree_md)

    relabeled = relabel_v02(assembled)
    distribution = distribution_report(relabeled)
    gap_report, gap_md, gap_registry = gap_reports(relabeled)
    change_report = label_change_report(v01_rows, relabeled)
    write_jsonl(ROOT / "operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl", relabeled)
    write_json(ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_V02_REPORT.json", distribution)
    write_json(ROOT / "CORPUS_V0_TEMPLATE_GAP_V02_REPORT.json", gap_report)
    write_json(ROOT / "CORPUS_V0_LABEL_CHANGE_FROM_V01_REPORT.json", change_report)
    write_json(ROOT / "TEMPLATE_GAP_REGISTRY_V02.json", gap_registry)
    write_text(ROOT / "TEMPLATE_GAP_REGISTRY_V02.md", gap_md)

    prior_ids = [row["row_id"] for row in analysis_json["evidence_rows"]]
    blind = blind_sample_v02(relabeled, prior_ids)
    v02_audit = compare_v02_labels(relabeled, blind)
    write_jsonl(ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl", blind)
    write_text(
        ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_INSTRUCTIONS.md",
        """# v0.2 Independent Double-Label Instructions

Use `ROUTE_TAXONOMY_V02_DECISION_TREE.md` and `ROUTE_TAXONOMY_V02_CONTRACT.json`.
Do not consult `operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl`.

Return JSONL with:
- `row_id`
- `normalized_question`
- `requires_selected_item_context`
- `expected_route_label`
- `expected_refusal_class`

Valid labels are the closed labels in `ROUTE_TAXONOMY_V02_CONTRACT.json`.
Use precise `gap:*` labels; do not use `gap:general operator question needs taxonomy review`.
""",
    )
    gate = {
        "schema_version": "citybrain.d14.double_label_v02_gate_r1",
        "generated_at": now(),
        "status": STATUS if v02_audit is None else v02_audit["status"],
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl"),
        "blind_sample_rows": len(blind),
        "blind_sample_pct": round(len(blind) / max(len(relabeled), 1), 4),
        "prior_disagreement_rows_included": len([row for row in blind if row["row_id"] in prior_ids]),
        "prior_disagreement_rows_required": len(prior_ids),
        "codex_labels_included": False,
        "double_label_disagreement_count": None if v02_audit is None else v02_audit["route_or_refusal_disagreement_count"],
        "double_label_disagreement_rate": None if v02_audit is None else v02_audit["route_or_refusal_disagreement_rate"],
        "split_seal_r3": "NOT_RUN_BLOCKED_PENDING_INDEPENDENT_V02_LABELS"
        if v02_audit is None
        else "NOT_RUN_BLOCKED_TAXONOMY_STILL_AMBIGUOUS"
        if v02_audit["status"] == "PAUSED_D14_ROUTE_TAXONOMY_V02_STILL_AMBIGUOUS"
        else "READY_FOR_SEPARATE_SPLIT_SEAL_R3",
        "router_training": "NOT_OPENED",
    }
    write_json(ROOT / "D14_DOUBLE_LABEL_V02_GATE_DECISION.json", gate)

    closeout_status = STATUS if v02_audit is None else v02_audit["status"]
    closeout = {
        "task": TASK,
        "status": closeout_status,
        "generated_at": now(),
        "input_root": rel(PREV_ROOT),
        "output_root": rel(ROOT),
        "failure_analysis": analysis_json["status"],
        "taxonomy_contract": contract["status"],
        "gap_registry": gap_registry["status"],
        "relabeled_rows": len(relabeled),
        "generic_gap_count": distribution["generic_gap_count"],
        "blind_sample_rows": len(blind),
        "prior_disagreement_rows_included": gate["prior_disagreement_rows_included"],
        "double_label_disagreement_count": None if v02_audit is None else v02_audit["route_or_refusal_disagreement_count"],
        "double_label_disagreement_rate": None if v02_audit is None else v02_audit["route_or_refusal_disagreement_rate"],
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "next_required_input": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS.jsonl")
        if v02_audit is None
        else "taxonomy v0.3 tightening required before router training or Split/Seal R3"
        if closeout_status == "PAUSED_D14_ROUTE_TAXONOMY_V02_STILL_AMBIGUOUS"
        else "run Split/Seal R3 in separate step",
    }
    write_json(ROOT / "D14_ROUTE_TAXONOMY_REPAIR_CLOSEOUT_DECISION.json", closeout)
    local_index(STATUS)
    write_hash_manifest()
    print(json.dumps(closeout, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
