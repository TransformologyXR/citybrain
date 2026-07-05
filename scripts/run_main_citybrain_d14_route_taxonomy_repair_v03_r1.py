#!/usr/bin/env python3
"""Run D14 route taxonomy repair v0.3 and export blind double-label sample.

This lane deliberately stops before independent label comparison, Split/Seal R3,
router preflight, or any real-operator validation claim.
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
V02_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v02_r1"
ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v03_r1"
PROMPT_ROOT = REPO / "tmp" / "citybrain_d14_route_taxonomy_repair_v03_r1"

TASK = "MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V03-R1"
STATUS = "PAUSED_D14_ROUTE_TAXONOMY_V03_AWAITING_INDEPENDENT_DOUBLE_LABELS"
TAXONOMY_VERSION = "route_taxonomy_v03"

INPUTS = {
    "v02_audit": V02_ROOT / "D14_DOUBLE_LABEL_V02_AUDIT.json",
    "v02_blind_sample": V02_ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl",
    "v02_independent_labels": V02_ROOT / "CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS.jsonl",
    "v02_labeled": V02_ROOT / "operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl",
    "v03_contract_draft": PROMPT_ROOT / "ROUTE_TAXONOMY_V03_CONTRACT_DRAFT.json",
    "v03_tree_draft": PROMPT_ROOT / "ROUTE_TAXONOMY_V03_DECISION_TREE_DRAFT.md",
}

EXPECTED_INPUT_FILES = [
    INPUTS["v02_audit"],
    INPUTS["v02_blind_sample"],
    INPUTS["v02_independent_labels"],
    INPUTS["v02_labeled"],
    INPUTS["v03_contract_draft"],
    INPUTS["v03_tree_draft"],
]

DEPRECATED_V02_LABELS = {
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

REFUSAL_CLASS_BY_LABEL = {
    "refuse:action_shaped": "action_shaped",
    "refuse:prediction_or_finding": "prediction_or_finding",
    "refuse:identity_or_person": "identity_or_person",
    "refuse:out_of_scope_entity": "out_of_scope_entity",
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


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def preserve_independent_v03_labels() -> dict[str, bytes]:
    preserved: dict[str, bytes] = {}
    for filename in [
        "CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl",
        "CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS_REPORT.json",
    ]:
        path = ROOT / filename
        if path.exists():
            preserved[filename] = path.read_bytes()
    return preserved


def restore_preserved_files(preserved: dict[str, bytes]) -> None:
    for filename, data in preserved.items():
        (ROOT / filename).write_bytes(data)


def validate_inputs() -> None:
    missing = [path for path in EXPECTED_INPUT_FILES if not path.exists()]
    if missing:
        raise SystemExit("Missing required v0.3 inputs: " + ", ".join(rel(path) for path in missing))


def normalize_question(raw: str) -> str:
    q = raw.strip()
    replacements = {
        "whats": "what is",
        "chrgr": "charger",
        "scrubs ln": "Scrubbs Lane",
        "rn": "right now",
        "ev": "EV",
        "nyc": "NYC",
        "mvc": "MVC",
        "uprn": "UPRN",
        "pls": "please",
    }
    for src, dst in replacements.items():
        q = re.sub(rf"\b{re.escape(src)}\b", dst, q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if q and q[-1] not in "?!.":
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def requires_context_v03(raw: str, selected_context: str) -> bool:
    q = raw.lower()
    if re.search(
        r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|scrubbs|scrubs|westway|nyc|mvc|4463710|uprn|london datastore|tims|record 87|chicago|london|howard avenue)\b",
        q,
    ):
        return False
    if re.search(r"\b(this|that|it|here|there|selected|these|those|all this|the item|the brief|the log|the board|the charger)\b", q):
        return True
    if len(q.split()) <= 4 and selected_context != "general_patch_board":
        return True
    return False


def route_v03(row: dict[str, Any]) -> tuple[str, str | None]:
    q = str(row.get("raw_question", "")).lower()
    context = str(row.get("selected_item_context", "")).lower()

    # 1. Imperative external actions before help/capability.
    if re.search(
        r"\b(alert .*team|alert .*department|alert .*operator|alert someone|dispatch|route|enforce|approve|create a case|create case|open a ticket|file a case|tell drivers|tell the public|get .*fixed|send .*email|send .*externally|call .*operator|call .*department|call the police|notify .*team|publish an alert now)\b",
        q,
    ):
        return "refuse:action_shaped", "action_shaped"
    if re.match(r"^\s*(dispatch|route|enforce|approve|notify|alert|call|send|create|open|file|publish)\b", q):
        return "refuse:action_shaped", "action_shaped"

    # 2. Identity/contact requests.
    if re.search(r"\b(who do i call|who should i call|which person|which department|owner name|driver|face|biometric|identify|responsible person)\b", q):
        return "refuse:identity_or_person", "identity_or_person"

    # 3. Predictions/findings outside claim-boundary phrasing.
    if re.search(r"\b(will there|predict|tomorrow|next week|probability|likelihood of|future incident|fine them|liable)\b", q):
        return "refuse:prediction_or_finding", "prediction_or_finding"

    # 4. Board capability/local help. Capability questions are help, not cannot_claim.
    if re.search(
        r"\b(how do i|where do i|what button|can i click|use this board|export|copy|add note|mark reviewed|open ask|generate brief|run check|checks panel|why does .*panel|does .*create.*case|did .*create.*case|whether .*create.*case|can this board|can the board|does the board|is this local review only|local review only|does this route|does this dispatch|does this alert|alerts published|published today|safe to share externally|who else can see|notes stored|visibility)\b",
        q,
    ):
        return "ui_help", None
    if re.search(r"\b(please run the check|pls run the check)\b", q):
        return "ui_help", None

    # 5. Queue list/count/filter/compare collapsed.
    if re.search(
        r"\b(show|list|filter|compare|count|how many|which item|highest ranked|all london|all items|all situation|three queue|three ranked|record count|open items|updated today|updated yesterday|today versus yesterday|queue items|records are connected across|source records on file|locations and stated limitations)\b",
        q,
    ):
        return "gap:patch_queue_query_needed", None

    # 6. External context source gaps.
    if re.search(r"\b(weather|other charging sites|other charger|all chargers|external data|budget report|emergency database)\b", q):
        return "gap:external_context_source_needed", None

    # 7. Source-record profile only when the named record itself is the object.
    if re.search(r"\b(what does .*record.*say|what fields|field-level|show me record|record 87 details|tims-\d+|static registry entry|source row .*say|source row .*not say|what .*source row)\b", q):
        return "gap:source_record_360_needed", None

    # 8. Claimability/live/blocked/available/certified/official negative answer.
    if re.search(
        r"\b(blocked|live|available|unavailable|availability|affected|certified|legal finding|official finding|can we claim|does this prove|what does this not prove|not prove|cannot claim|can .*be treated|only proximity|causality|live monitoring|static registry|access impact|changed availability|is .*official|urgent|urgency finding|review order)\b",
        q,
    ):
        return "template:ask:cannot_claim@v1", None

    # 9. Missing evidence / source-depth / verification.
    if re.search(
        r"\b(missing evidence|evidence missing|what evidence.*missing|what source.*needed|what would confirm|why .*candidate-only|candidate-only|verification absent|building-control verification|direct evidence|stronger evidence|source depth|no .*source)\b",
        q,
    ):
        return "gap:evidence_gap_template_needed", None

    # 10. Source support/citations/source records backing the item or claim.
    if re.search(r"\b(what supports|source supports|records support|evidence supports|citations|what backs|records on file|evidence and uncertainty|source link|source records validate|representative point matched)\b", q):
        return "template:ask:what_supports@v1", None

    # 11. General uncertainty.
    if re.search(r"\b(what is uncertain|uncertain|unknowns|what do we not know|what else.*needed|gap)\b", q):
        return "template:ask:what_is_uncertain@v1", None

    # 12. Entity facts/profile/attributes, v2.
    if re.search(r"\b(what do we know|profile|look up|rapid or slow|fast charger|normal charger|uprn|confidence value|planning-context linkage|opportunity-area context|ev\s*87|asset\s*87|charger\s*87|mvc|4463710)\b", q) or context in {"ev_asset_87", "nyc_mvc_candidate_context"}:
        return "template:ask:entity_360@v2", None

    if re.search(r"\b(school|hospital|crime|unrelated place)\b", q):
        return "refuse:out_of_scope_entity", "out_of_scope_entity"

    return "ui_help", None


def root_cause_report(v02_audit: dict[str, Any]) -> tuple[dict[str, Any], str]:
    disagreements = v02_audit.get("disagreements", [])
    pair_counts: Counter[str] = Counter()
    examples_by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in disagreements:
        pair = f"{item.get('codex_expected_route_label')} -> {item.get('independent_expected_route_label')}"
        pair_counts[pair] += 1
        if len(examples_by_pair[pair]) < 5:
            examples_by_pair[pair].append(
                {
                    "row_id": item.get("row_id", ""),
                    "raw_question": item.get("raw_question", ""),
                    "codex": item.get("codex_expected_route_label", ""),
                    "independent": item.get("independent_expected_route_label", ""),
                }
            )
    categories = {
        "board_capability_vs_cannot_claim": [],
        "source_support_vs_source_record_profile": [],
        "live_blocked_claimability_vs_evidence_gap": [],
        "queue_query_fine_grain_gaps": [],
        "imperative_action_vs_help_gap": [],
        "entity_facts_vs_planning_source_boundary": [],
    }
    for item in disagreements:
        q = str(item.get("raw_question", "")).lower()
        row_id = item.get("row_id")
        if re.search(r"\b(board|alert|case|local review|live monitoring|official)\b", q):
            categories["board_capability_vs_cannot_claim"].append(row_id)
        if re.search(r"\b(source|record|evidence|supports)\b", q):
            categories["source_support_vs_source_record_profile"].append(row_id)
        if re.search(r"\b(ev|charger|blocked|available|live|unavailable)\b", q):
            categories["live_blocked_claimability_vs_evidence_gap"].append(row_id)
        if re.search(r"\b(list|count|compare|highest|all|queue|updated|ranked)\b", q):
            categories["queue_query_fine_grain_gaps"].append(row_id)
        if re.search(r"\b(alert|call|email|send|publish|create|run the check)\b", q):
            categories["imperative_action_vs_help_gap"].append(row_id)
        if re.search(r"\b(entity|planning|context|representative point|source row|record 87|confidence)\b", q):
            categories["entity_facts_vs_planning_source_boundary"].append(row_id)
    report = {
        "schema_version": "citybrain.d14.v02_ambiguity_root_cause_r1",
        "generated_at": now(),
        "v02_status": v02_audit.get("status"),
        "total_rows_compared": v02_audit.get("blind_sample_rows"),
        "total_disagreements": v02_audit.get("route_or_refusal_disagreement_count"),
        "disagreement_rate": v02_audit.get("route_or_refusal_disagreement_rate"),
        "pair_counts": dict(pair_counts.most_common()),
        "examples_by_pair": examples_by_pair,
        "root_cause_categories": {key: sorted(set(value)) for key, value in categories.items()},
        "recommendation": "v0.3 collapses labels and changes decision priority; v0.2 remains failed and is not adjudicated into a pass.",
        "status": "PASS",
    }
    md = [
        "# D14 v0.2 Ambiguity Root Cause",
        "",
        f"v0.2 disagreement: `{report['total_disagreements']} / {report['total_rows_compared']}` = `{report['disagreement_rate']}`.",
        "",
        "## Root Cause",
        "",
        "The label space still mixed conceptual answer type with routeable product destination. v0.3 reduces label granularity.",
        "",
        "## Pair Counts",
    ]
    for pair, count in pair_counts.most_common():
        md.append(f"- `{pair}`: {count}")
    return report, "\n".join(md)


def relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relabeled: list[dict[str, Any]] = []
    for row in rows:
        route, refusal = route_v03(row)
        new_row = dict(row)
        new_row["normalized_question"] = normalize_question(str(row.get("raw_question", "")))
        new_row["requires_selected_item_context"] = requires_context_v03(
            str(row.get("raw_question", "")),
            str(row.get("selected_item_context", "")),
        )
        new_row["expected_route_label"] = route
        new_row["expected_refusal_class"] = refusal
        new_row["taxonomy_version"] = TAXONOMY_VERSION
        relabeled.append(new_row)
    return relabeled


def distribution_report(rows: list[dict[str, Any]], closed_labels: set[str]) -> dict[str, Any]:
    route_counts = Counter(row["expected_route_label"] for row in rows)
    refusal_counts = Counter(row["expected_refusal_class"] for row in rows if row.get("expected_refusal_class"))
    deprecated_hits = [row["question_id"] for row in rows if row["expected_route_label"] in DEPRECATED_V02_LABELS]
    non_closed_hits = [row["question_id"] for row in rows if row["expected_route_label"] not in closed_labels]
    refusal_errors = [
        row["question_id"]
        for row in rows
        if (row["expected_route_label"].startswith("refuse:") and row.get("expected_refusal_class") != REFUSAL_CLASS_BY_LABEL.get(row["expected_route_label"]))
        or (not row["expected_route_label"].startswith("refuse:") and row.get("expected_refusal_class") is not None)
    ]
    crosstab: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        crosstab[row["persona"]][row["expected_route_label"]] += 1
    return {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.label_distribution_v03.v1",
        "generated_at": now(),
        "row_count": len(rows),
        "route_counts": dict(route_counts.most_common()),
        "refusal_class_counts": dict(refusal_counts.most_common()),
        "persona_route_crosstab": {persona: dict(sorted(counts.items())) for persona, counts in sorted(crosstab.items())},
        "requires_selected_item_context_count": sum(1 for row in rows if row["requires_selected_item_context"]),
        "requires_selected_item_context_rate": round(sum(1 for row in rows if row["requires_selected_item_context"]) / max(len(rows), 1), 4),
        "deprecated_label_hits": deprecated_hits,
        "non_closed_label_hits": non_closed_hits,
        "refusal_class_errors": refusal_errors,
        "status": "PASS" if not deprecated_hits and not non_closed_hits and not refusal_errors else "FAIL",
    }


def gap_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["expected_route_label"] for row in rows if str(row["expected_route_label"]).startswith("gap:"))
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        label = row["expected_route_label"]
        if label.startswith("gap:") and len(examples[label]) < 10:
            examples[label].append(
                {
                    "row_id": row["question_id"],
                    "persona": row["persona"],
                    "raw_question": row["raw_question"],
                }
            )
    return {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.template_gap_v03_report.v1",
        "generated_at": now(),
        "gap_count": sum(counts.values()),
        "gaps_ranked": [
            {"gap_id": gap, "count": count, "examples": examples[gap]} for gap, count in counts.most_common()
        ],
        "status": "PASS",
    }


def label_change_report(v02_rows: list[dict[str, Any]], v03_rows: list[dict[str, Any]]) -> dict[str, Any]:
    old = {row["question_id"]: row for row in v02_rows}
    changes = []
    for row in v03_rows:
        prior = old.get(row["question_id"], {})
        if prior.get("expected_route_label") != row.get("expected_route_label") or prior.get("expected_refusal_class") != row.get("expected_refusal_class"):
            changes.append(
                {
                    "row_id": row["question_id"],
                    "raw_question": row["raw_question"],
                    "v02_route": prior.get("expected_route_label"),
                    "v03_route": row.get("expected_route_label"),
                    "v02_refusal_class": prior.get("expected_refusal_class"),
                    "v03_refusal_class": row.get("expected_refusal_class"),
                }
            )
    return {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.v02_to_v03_label_change.v1",
        "generated_at": now(),
        "row_count": len(v03_rows),
        "changed_rows": len(changes),
        "unchanged_rows": len(v03_rows) - len(changes),
        "changes": changes,
        "status": "PASS",
    }


def select_blind_sample(rows: list[dict[str, Any]], prior_disagreement_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {row["question_id"]: row for row in rows}
    selected: list[str] = []
    for row_id in prior_disagreement_ids:
        if row_id in by_id and row_id not in selected:
            selected.append(row_id)
    target = max(60, int(len(rows) * 0.4 + 0.999))
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["expected_route_label"], row["persona"], row["source_session_id"])].append(row)
    for group in groups.values():
        group.sort(key=lambda row: row["question_id"])
    index = 0
    while len(selected) < target:
        progressed = False
        for key in sorted(groups):
            group = groups[key]
            if index >= len(group):
                continue
            row_id = group[index]["question_id"]
            if row_id not in selected:
                selected.append(row_id)
                progressed = True
                if len(selected) >= target:
                    break
        if not progressed:
            break
        index += 1
    sample = [by_id[row_id] for row_id in selected]
    sample.sort(key=lambda row: row["question_id"])
    return [
        {
            "row_id": row["question_id"],
            "raw_question": row["raw_question"],
            "persona": row["persona"],
            "selected_item_context": row["selected_item_context"],
            "source_type": row["source_type"],
            "source_session_id": row["source_session_id"],
        }
        for row in sample
    ]


def compare_v03_labels(v03_rows: list[dict[str, Any]], blind_sample: list[dict[str, Any]]) -> dict[str, Any] | None:
    independent_path = ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl"
    if not independent_path.exists():
        return None
    independent_rows = read_jsonl(independent_path)
    codex_by_id = {row["question_id"]: row for row in v03_rows}
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
    pair_counts: Counter[str] = Counter()
    for row in independent_rows:
        row_id = str(row.get("row_id", ""))
        codex = codex_by_id.get(row_id)
        if not codex:
            continue
        codex_route = codex.get("expected_route_label")
        independent_route = row.get("expected_route_label")
        codex_refusal = codex.get("expected_refusal_class")
        independent_refusal = row.get("expected_refusal_class")
        if codex_route != independent_route or codex_refusal != independent_refusal:
            pair = f"{codex_route} -> {independent_route}"
            pair_counts[pair] += 1
            disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_expected_route_label": codex_route,
                    "independent_expected_route_label": independent_route,
                    "codex_expected_refusal_class": codex_refusal,
                    "independent_expected_refusal_class": independent_refusal,
                    "pair": pair,
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
        "PASS_D14_ROUTE_TAXONOMY_V03_DOUBLE_LABEL_STABLE_READY_FOR_SPLIT_SEAL"
        if disagreement_rate <= 0.15 and not schema_errors and not missing_ids and not extra_ids and row_order_ok
        else "PAUSED_D14_ROUTE_TAXONOMY_V03_STILL_AMBIGUOUS"
    )
    audit = {
        "schema_version": "citybrain.d14.double_label_v03_audit.v1",
        "generated_at": now(),
        "status": status,
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl"),
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
        "pair_counts": dict(pair_counts.most_common()),
        "disagreements": disagreements,
        "context_dependency_disagreements": context_disagreements,
        "split_and_seal_r3_status": "READY" if disagreement_rate <= 0.15 else "BLOCKED_TAXONOMY_STILL_AMBIGUOUS",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
    }
    write_json(ROOT / "D14_DOUBLE_LABEL_V03_AUDIT.json", audit)
    write_remaining_ambiguity_report(audit)
    return audit


def write_remaining_ambiguity_report(audit: dict[str, Any]) -> None:
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in audit.get("disagreements", []):
        q = str(item.get("raw_question", "")).lower()
        pair = item.get("pair")
        if re.search(r"\b(source row|source record|record|evidence|supports|static registry)\b", q):
            category = "source_support_vs_source_record_or_claim"
        elif re.search(r"\b(blocked|live|available|unavailable|charger|ev 87|asset 87)\b", q):
            category = "ev_live_blocked_claimability"
        elif re.search(r"\b(board|alert|case|local notes|review|run the check|publish)\b", q):
            category = "board_capability_vs_action_or_help"
        elif re.search(r"\b(list|compare|queue|items|ranked|records on file)\b", q):
            category = "patch_queue_query_vs_support_or_help"
        elif re.search(r"\b(planning|context|confidence|representative point)\b", q):
            category = "entity_profile_vs_planning_source_boundary"
        else:
            category = "misc_remaining_boundary"
        categories[category].append(
            {
                "row_id": item.get("row_id"),
                "raw_question": item.get("raw_question"),
                "pair": pair,
            }
        )
    report = {
        "schema_version": "citybrain.d14.route_taxonomy_v03.remaining_ambiguity_report.v1",
        "generated_at": now(),
        "status": "PASS_REMAINING_AMBIGUITY_INSPECTED",
        "route_or_refusal_disagreement_count": audit.get("route_or_refusal_disagreement_count"),
        "route_or_refusal_disagreement_rate": audit.get("route_or_refusal_disagreement_rate"),
        "pair_counts": audit.get("pair_counts", {}),
        "categories": {key: value for key, value in sorted(categories.items())},
        "recommendation": "Pause again. Tighten v0.4 around source-row/static-registry, board capability vs action/help, queue queries, and EV live/blocked claimability before Split/Seal R3.",
    }
    md = [
        "# D14 v0.3 Remaining Ambiguity Inspection",
        "",
        f"Disagreement: `{audit.get('route_or_refusal_disagreement_count')} / {audit.get('blind_sample_rows')}` = `{audit.get('route_or_refusal_disagreement_rate')}`.",
        "",
        "## Pair Counts",
    ]
    for pair, count in audit.get("pair_counts", {}).items():
        md.append(f"- `{pair}`: {count}")
    md += ["", "## Categories"]
    for category, rows in sorted(categories.items()):
        md.append(f"- `{category}`: {len(rows)} rows")
    write_json(ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.json", report)
    write_text(ROOT / "D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md", "\n".join(md))


def copy_prompt_pack_and_contracts() -> None:
    (ROOT / "prompt_pack").mkdir(parents=True, exist_ok=True)
    for path in sorted(PROMPT_ROOT.glob("*")):
        if path.is_file():
            shutil.copy2(path, ROOT / "prompt_pack" / path.name)
    shutil.copy2(INPUTS["v03_contract_draft"], ROOT / "ROUTE_TAXONOMY_V03_CONTRACT.json")
    shutil.copy2(INPUTS["v03_tree_draft"], ROOT / "ROUTE_TAXONOMY_V03_DECISION_TREE.md")


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
        "schema_version": "citybrain.d14.route_taxonomy_v03.json_parse_audit.v1",
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
                # "source_type" and "expected_refusal_class" are not secrets; these patterns are intentionally narrow.
                hits.append({"path": rel(path), "pattern": pattern})
    return {
        "schema_version": "citybrain.d14.route_taxonomy_v03.secret_audit.v1",
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
    package_path = ROOT / "D14_ROUTE_TAXONOMY_V03_VALIDATION_PACKAGE.zip"
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, rel(path))


def local_index(status: str) -> None:
    lines = [
        "# D14 Route Taxonomy Repair v0.3 R1",
        "",
        f"Status: `{status}`",
        "",
        "Open first:",
        "- `ROUTE_TAXONOMY_V03_DECISION_TREE.md`",
        "- `ROUTE_TAXONOMY_V03_CONTRACT.json`",
        "- `operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl`",
        "- `CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl`",
        "- `CORPUS_V0_DOUBLE_LABEL_V03_INSTRUCTIONS.md`",
        "",
        "Split/Seal R3 and router preflight remain blocked pending independent v0.3 labels.",
    ]
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(ROOT / "README.md", "\n".join(lines))


def main() -> None:
    validate_inputs()
    preserved = preserve_independent_v03_labels()
    clean_root()
    restore_preserved_files(preserved)
    copy_prompt_pack_and_contracts()

    v02_audit = read_json(INPUTS["v02_audit"])
    v02_rows = read_jsonl(INPUTS["v02_labeled"])
    contract = read_json(ROOT / "ROUTE_TAXONOMY_V03_CONTRACT.json")
    closed_labels = set(contract["labels"])
    prior_disagreement_ids = [item["row_id"] for item in v02_audit.get("disagreements", [])]

    root_cause_json, root_cause_md = root_cause_report(v02_audit)
    write_json(ROOT / "D14_V02_AMBIGUITY_ROOT_CAUSE_REPORT.json", root_cause_json)
    write_text(ROOT / "D14_V02_AMBIGUITY_ROOT_CAUSE_REPORT.md", root_cause_md)

    v03_rows = relabel(v02_rows)
    write_jsonl(ROOT / "operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl", v03_rows)
    dist = distribution_report(v03_rows, closed_labels)
    gaps = gap_report(v03_rows)
    changes = label_change_report(v02_rows, v03_rows)
    write_json(ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_V03_REPORT.json", dist)
    write_json(ROOT / "CORPUS_V0_TEMPLATE_GAP_V03_REPORT.json", gaps)
    write_json(ROOT / "CORPUS_V0_V02_TO_V03_LABEL_CHANGE_REPORT.json", changes)

    sample = select_blind_sample(v03_rows, prior_disagreement_ids)
    write_jsonl(ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl", sample)
    v03_audit = compare_v03_labels(v03_rows, sample)
    write_text(
        ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_INSTRUCTIONS.md",
        """# v0.3 Independent Double-Label Instructions

Use only `ROUTE_TAXONOMY_V03_CONTRACT.json` and `ROUTE_TAXONOMY_V03_DECISION_TREE.md`.
Do not consult `operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl`.

For every row in `CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl`, return JSONL named
`CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl` with:

- `row_id`
- `normalized_question`
- `requires_selected_item_context`
- `expected_route_label`
- `expected_refusal_class`

Use deprecated v0.2 labels never. Non-refusal rows must use `expected_refusal_class: null`.
""",
    )

    gate = {
        "schema_version": "citybrain.d14.double_label_v03_sample_r1",
        "generated_at": now(),
        "status": STATUS if v03_audit is None else v03_audit["status"],
        "blind_sample": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl"),
        "blind_sample_rows": len(sample),
        "blind_sample_pct": round(len(sample) / max(len(v03_rows), 1), 4),
        "minimum_required_rows": 60,
        "prior_v02_disagreement_rows_required": len(prior_disagreement_ids),
        "prior_v02_disagreement_rows_included": len([row for row in sample if row["row_id"] in prior_disagreement_ids]),
        "codex_labels_included": False,
        "double_label_disagreement_count": None if v03_audit is None else v03_audit["route_or_refusal_disagreement_count"],
        "double_label_disagreement_rate": None if v03_audit is None else v03_audit["route_or_refusal_disagreement_rate"],
        "split_seal_r3": "NOT_RUN_BLOCKED_PENDING_INDEPENDENT_V03_LABELS"
        if v03_audit is None
        else "NOT_RUN_BLOCKED_TAXONOMY_STILL_AMBIGUOUS"
        if v03_audit["status"] == "PAUSED_D14_ROUTE_TAXONOMY_V03_STILL_AMBIGUOUS"
        else "READY_FOR_SPLIT_SEAL_R3",
        "router_preflight": "NOT_OPENED",
    }
    write_json(ROOT / "D14_DOUBLE_LABEL_V03_SAMPLE_DECISION.json", gate)

    parse_audit = json_parse_audit()
    secret = secret_audit()
    write_json(ROOT / "JSON_PARSE_AUDIT.json", parse_audit)
    write_json(ROOT / "SECRET_AUDIT.json", secret)

    closeout_status = STATUS if v03_audit is None else v03_audit["status"]
    decision = {
        "task": TASK,
        "status": closeout_status,
        "generated_at": now(),
        "input_root": rel(V02_ROOT),
        "output_root": rel(ROOT),
        "v02_remains_failed": True,
        "v02_disagreement_rate": v02_audit.get("route_or_refusal_disagreement_rate"),
        "v03_contract_exists": True,
        "full_corpus_relabeled_under_v03": len(v03_rows),
        "deprecated_label_hits": len(dist["deprecated_label_hits"]),
        "non_closed_label_hits": len(dist["non_closed_label_hits"]),
        "blind_sample_rows": len(sample),
        "prior_v02_disagreement_rows_included": gate["prior_v02_disagreement_rows_included"],
        "double_label_disagreement_count": None if v03_audit is None else v03_audit["route_or_refusal_disagreement_count"],
        "double_label_disagreement_rate": None if v03_audit is None else v03_audit["route_or_refusal_disagreement_rate"],
        "split_seal_r3": "NOT_RUN",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "json_parse_audit": parse_audit["status"],
        "secret_audit": secret["status"],
        "next_required_file": rel(ROOT / "CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl")
        if v03_audit is None
        else "taxonomy v0.4 tightening required before router training or Split/Seal R3"
        if closeout_status == "PAUSED_D14_ROUTE_TAXONOMY_V03_STILL_AMBIGUOUS"
        else "run Split/Seal R3 in separate step",
    }
    write_json(ROOT / "D14_ROUTE_TAXONOMY_V03_CLOSEOUT_DECISION.json", decision)
    local_index(STATUS)
    package_outputs()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
