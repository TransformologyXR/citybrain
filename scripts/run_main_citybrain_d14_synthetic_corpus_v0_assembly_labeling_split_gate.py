#!/usr/bin/env python3
"""Assemble and prelim-label Synthetic Corpus v0, stopping at double-label gate.

This runner intentionally does not contain the clean-session generation prompt.
It consumes already-created workspace text files as raw generation outputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import string
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO / "outputs" / "main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate"
RAW_ROOT = REPO / "corpus_raw"
RAW_ORIGINAL_ROOT = RAW_ROOT / "original"
CONTRACT = Path(r"C:\Users\hazem\Downloads\SYNTHETIC_CORPUS_V0_ASSEMBLY_AND_LABELING_CONTRACT.md")

SOURCE_FILES = [
    ("workspace_text_1", REPO / "text 1.txt"),
    ("workspace_text_2", REPO / "text2.txt"),
    ("workspace_text_3", REPO / "text 3.txt"),
    ("workspace_text_4", REPO / "text 4.txt"),
    ("workspace_text_5", REPO / "text 5.txt"),
    ("workspace_text_6", REPO / "text 6.txt"),
]

REQUIRED_RAW_FIELDS = {
    "question_id",
    "source_type",
    "source_session_id",
    "persona",
    "selected_item_context",
    "raw_question",
    "normalized_question",
    "expected_route_label",
    "expected_refusal_class",
    "notes",
}

ALLOWED_PERSONAS = {
    "rushed_duty_operator",
    "formal_planner_analyst",
    "skeptical_risk_reviewer",
    "non_technical_manager",
}

REFUSAL_CLASSES = {
    "out_of_scope_entity",
    "unsupported_aggregate_or_comparison",
    "action_shaped",
    "prediction_or_finding",
    "identity_or_person",
    "insufficient_source_depth",
}

TEMPLATE_REFS = {
    "entity": "template:ask:entity_360@v1",
    "supports": "template:ask:what_supports@v1",
    "uncertain": "template:ask:what_is_uncertain@v1",
    "cannot": "template:ask:cannot_claim@v1",
}

LEAK_PATTERNS = [
    "ask:",
    "@v1",
    "@v2",
    "watch-candidate",
    "entity_360",
    "packages/fixtures",
    "outputs/",
    "mode_run",
    "PASS_",
    "D9_PRODUCT_MODE_RUNTIME_BUNDLE",
    "D9_OPERATOR_COCKPIT_RUNTIME_EXTENSION",
]

PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


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
    return sha256_bytes(path.read_bytes())


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def normalize_for_dedup(question: str) -> str:
    return re.sub(r"\s+", " ", question.lower().translate(PUNCT_TABLE)).strip()


def token_set(question: str) -> set[str]:
    return {tok for tok in normalize_for_dedup(question).split() if tok}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def messiness_score(row: dict[str, Any]) -> tuple[int, int, int, int]:
    q = str(row.get("raw_question", ""))
    notes = str(row.get("notes", "")).lower()
    typo_words = sum(1 for w in q.split() if re.search(r"\d|chrgr|whats|wot|u\b|pls|plz|w/", w.lower()))
    lowercase_start = 1 if q and q[0].islower() else 0
    note_messy = 1 if any(term in notes for term in ["messy", "typo", "short", "fragment", "impatient"]) else 0
    short = 1 if len(q.split()) <= 5 else 0
    return (note_messy + typo_words + lowercase_start + short, -len(q.split()), -len(q), -int(row.get("_source_order", 0)))


def choose_messier(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(rows, key=messiness_score, reverse=True)[0]


def infer_model_family(row: dict[str, Any], source_run_id: str) -> str:
    session = str(row.get("source_session_id") or source_run_id)
    return f"unprovided_model_family_inferred_from_{session}"


def derive_raw_jsonl() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clean_dir(RAW_ORIGINAL_ROOT)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    run_file_records: list[dict[str, Any]] = []
    wrapper_records: list[dict[str, Any]] = []
    for run_id, source in SOURCE_FILES:
        if not source.exists():
            run_file_records.append({"run_id": run_id, "source": rel(source), "exists": False})
            continue
        original_target = RAW_ORIGINAL_ROOT / f"{run_id}_original.txt"
        shutil.copy2(source, original_target)
        lines = source.read_text(encoding="utf-8").splitlines()
        json_lines: list[str] = []
        wrapper_lines: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("{"):
                json_lines.append(line)
            else:
                wrapper_lines.append({"line": line_number, "text": stripped[:160]})
        jsonl_target = RAW_ROOT / f"{run_id}.jsonl"
        jsonl_target.write_text("\n".join(json_lines) + ("\n" if json_lines else ""), encoding="utf-8")
        record = {
            "run_id": run_id,
            "source": rel(source),
            "exists": True,
            "original_copy": rel(original_target),
            "jsonl_copy": rel(jsonl_target),
            "original_sha256": sha256_file(source),
            "jsonl_sha256": sha256_file(jsonl_target),
            "original_line_count": len(lines),
            "json_object_line_count": len(json_lines),
            "wrapper_line_count": len(wrapper_lines),
            "wrapper_normalization_applied": bool(wrapper_lines),
        }
        run_file_records.append(record)
        if wrapper_lines:
            wrapper_records.append({"run_id": run_id, "wrapper_lines": wrapper_lines})
    return run_file_records, wrapper_records


def parse_and_validate(run_file_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    valid_rows: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for file_record in run_file_records:
        if not file_record.get("exists"):
            reports.append({"run_id": file_record["run_id"], "status": "MISSING_SOURCE_FILE", **file_record})
            continue
        jsonl_path = REPO / file_record["jsonl_copy"]
        parse_errors: list[dict[str, Any]] = []
        schema_errors: list[dict[str, Any]] = []
        null_wall_errors: list[dict[str, Any]] = []
        leak_errors: list[dict[str, Any]] = []
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except Exception as exc:
                parse_errors.append({"line": line_number, "error": str(exc), "raw": line[:160]})
                continue
            if not isinstance(value, dict):
                parse_errors.append({"line": line_number, "error": "json value is not an object"})
                continue
            row_errors: list[str] = []
            missing = sorted(REQUIRED_RAW_FIELDS - set(value))
            extra = sorted(set(value) - REQUIRED_RAW_FIELDS)
            if missing:
                row_errors.append(f"missing fields: {', '.join(missing)}")
            if value.get("source_type") != "synthetic_v0_clean_ai":
                row_errors.append("source_type must be synthetic_v0_clean_ai")
            if value.get("persona") not in ALLOWED_PERSONAS:
                row_errors.append("persona enum not recognized")
            if not re.match(r"^syn-v0-s\d{3}-\d{4}$", str(value.get("question_id", ""))):
                row_errors.append("question_id pattern not recognized")
            if value.get("normalized_question") is not None or value.get("expected_route_label") is not None or value.get("expected_refusal_class") is not None:
                null_wall_errors.append({"line": line_number, "question_id": value.get("question_id")})
                row_errors.append("null-wall field was pre-filled")
            blob = json.dumps(value, ensure_ascii=False)
            leaks = [token for token in LEAK_PATTERNS if token in blob]
            if leaks:
                leak_errors.append({"line": line_number, "question_id": value.get("question_id"), "tokens": leaks})
                row_errors.append("leak tokens found")
            if row_errors:
                schema_errors.append({"line": line_number, "question_id": value.get("question_id"), "errors": row_errors, "extra_fields": extra})
                quarantined.append(
                    {
                        "quarantine_reason": row_errors,
                        "source_run_file": file_record["run_id"],
                        "source_line": line_number,
                        "row": value,
                    }
                )
                continue
            value["_source_run_file"] = file_record["run_id"]
            value["_source_line"] = line_number
            value["_source_order"] = len(valid_rows)
            value["_original_question_id"] = value["question_id"]
            value["_model_family"] = infer_model_family(value, file_record["run_id"])
            value["_model_version"] = "unprovided_in_workspace_text"
            rows.append(value)
            valid_rows.append(value)
        persona_counts = Counter(row.get("persona") for row in rows)
        context_counts = Counter(row.get("selected_item_context") for row in rows)
        sessions = sorted({str(row.get("source_session_id")) for row in rows})
        families = sorted({str(row.get("_model_family")) for row in rows})
        row_count = len(rows) + len(schema_errors) + len(parse_errors)
        report_status = "PASS" if not parse_errors and not schema_errors and not null_wall_errors and not leak_errors else "PASS_WITH_QUARANTINE"
        if parse_errors:
            report_status = "FAIL_PARSE"
        if row_count and len(null_wall_errors) / max(row_count, 1) > 0.05:
            report_status = "FAIL_NULL_WALL_LEAKAGE"
        reports.append(
            {
                "run_id": file_record["run_id"],
                "status": report_status,
                "jsonl_copy": file_record["jsonl_copy"],
                "original_copy": file_record["original_copy"],
                "input_rows": row_count,
                "valid_rows": len(rows),
                "quarantined_rows": len(schema_errors),
                "parse_error_count": len(parse_errors),
                "schema_error_count": len(schema_errors),
                "null_wall_prefilled_count": len(null_wall_errors),
                "leak_count": len(leak_errors),
                "wrapper_normalization_applied": file_record["wrapper_normalization_applied"],
                "wrapper_line_count": file_record["wrapper_line_count"],
                "source_session_ids": sessions,
                "model_family_status": "INFERRED_FROM_SOURCE_SESSION_ID_METADATA_MISSING",
                "model_families": families,
                "stimulus_sha256_status": "UNPROVIDED_NOT_VERIFIED",
                "stimulus_token_audit_status": "UNPROVIDED_NOT_VERIFIED",
                "quota_observation": {
                    "persona_counts": dict(sorted(persona_counts.items())),
                    "selected_item_context_counts": dict(sorted(context_counts.items())),
                },
                "parse_errors": parse_errors[:20],
                "schema_errors": schema_errors[:20],
                "null_wall_errors": null_wall_errors[:20],
                "leak_errors": leak_errors[:20],
            }
        )
    aggregate = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.run_validation.v1",
        "generated_at": now(),
        "contract": str(CONTRACT),
        "source_files": run_file_records,
        "runs": reports,
        "run_count": len(reports),
        "raw_valid_rows": len(valid_rows),
        "quarantined_rows": len(quarantined),
        "status": "PASS" if all(r["status"] == "PASS" for r in reports) else "PASS_WITH_LIMITATIONS_OR_QUARANTINE",
        "limitations": [
            "Workspace text files did not include independent run logs; model_family and stimulus metadata are recorded as unprovided/inferred.",
            "One pasted file had markdown wrapper lines; JSON object rows were copied unchanged into corpus_raw JSONL.",
        ],
    }
    return valid_rows, quarantined, aggregate


def dedup_and_select(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        exact_groups[normalize_for_dedup(str(row["raw_question"]))].append(row)
    exact_survivors: list[dict[str, Any]] = []
    exact_log: list[dict[str, Any]] = []
    for norm, group in exact_groups.items():
        if len(group) == 1:
            exact_survivors.append(group[0])
            continue
        kept = choose_messier(group)
        exact_survivors.append(kept)
        exact_log.append(
            {
                "normalized_question_key": norm,
                "kept_original_question_id": kept["_original_question_id"],
                "collapsed_original_question_ids": [row["_original_question_id"] for row in group if row is not kept],
            }
        )

    near_survivors: list[dict[str, Any]] = []
    near_log: list[dict[str, Any]] = []
    for row in sorted(exact_survivors, key=lambda r: (r["_source_run_file"], r["_source_line"], r["_original_question_id"])):
        row_tokens = token_set(str(row["raw_question"]))
        collapsed = False
        for index, kept in enumerate(near_survivors):
            kept_tokens = token_set(str(kept["raw_question"]))
            if len(row_tokens | kept_tokens) >= 3 and jaccard(row_tokens, kept_tokens) >= 0.8:
                chosen = choose_messier([kept, row])
                discarded = row if chosen is kept else kept
                if chosen is row:
                    near_survivors[index] = row
                near_log.append(
                    {
                        "jaccard": round(jaccard(row_tokens, kept_tokens), 4),
                        "kept_original_question_id": chosen["_original_question_id"],
                        "collapsed_original_question_id": discarded["_original_question_id"],
                        "kept_raw_question": chosen["raw_question"],
                        "collapsed_raw_question": discarded["raw_question"],
                    }
                )
                collapsed = True
                break
        if not collapsed:
            near_survivors.append(row)

    target_size = min(150, len(near_survivors))
    target_size = target_size if target_size >= 120 else len(near_survivors)
    max_per_run = math.floor(target_size * 0.45)
    max_per_family = math.floor(target_size * 0.60)
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in near_survivors:
        by_run[row["_source_run_file"]].append(row)
        by_group[(row["_source_run_file"], row["persona"])].append(row)
    for bucket in by_group.values():
        bucket.sort(key=lambda r: (r["selected_item_context"], -messiness_score(r)[0], r["_source_line"]))
    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, int]] = set()
    run_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    group_order = sorted(by_group)
    made_progress = True
    while len(selected) < target_size and made_progress:
        made_progress = False
        for run, persona in group_order:
            if len(selected) >= target_size:
                break
            for row in by_group[(run, persona)]:
                key = (row["_source_run_file"], int(row["_source_line"]))
                if key in selected_keys:
                    continue
                family = row["_model_family"]
                if run_counts[run] >= max_per_run or family_counts[family] >= max_per_family:
                    continue
                selected.append(row)
                selected_keys.add(key)
                run_counts[run] += 1
                family_counts[family] += 1
                made_progress = True
                break

    if len(selected) < target_size:
        for row in near_survivors:
            if len(selected) >= target_size:
                break
            key = (row["_source_run_file"], int(row["_source_line"]))
            family = row["_model_family"]
            if key not in selected_keys and run_counts[row["_source_run_file"]] < max_per_run and family_counts[family] < max_per_family:
                selected.append(row)
                selected_keys.add(key)
                run_counts[row["_source_run_file"]] += 1
                family_counts[family] += 1

    assembled: list[dict[str, Any]] = []
    for index, row in enumerate(selected, 1):
        public = {
            "question_id": f"syn-v0-{index:04d}",
            "source_type": "synthetic_v0_clean_ai",
            "source_session_id": row["source_session_id"],
            "source_run_file": row["_source_run_file"],
            "model_family": row["_model_family"],
            "model_version": row["_model_version"],
            "original_question_id": row["_original_question_id"],
            "persona": row["persona"],
            "selected_item_context": row["selected_item_context"],
            "raw_question": row["raw_question"],
            "normalized_question": None,
            "requires_selected_item_context": None,
            "expected_route_label": None,
            "expected_refusal_class": None,
            "notes": row["notes"],
            "provenance": {
                "source_line": row["_source_line"],
                "source_run_file": row["_source_run_file"],
                "source_session_id": row["source_session_id"],
                "original_question_id": row["_original_question_id"],
            },
        }
        assembled.append(public)

    report = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.assembly.v1",
        "generated_at": now(),
        "input_valid_rows": len(rows),
        "exact_dedup_collapses": len(exact_log),
        "near_dup_threshold_jaccard": 0.8,
        "near_dup_collapses": len(near_log),
        "post_dedup_rows": len(near_survivors),
        "target_size": target_size,
        "final_assembled_rows": len(assembled),
        "dominance_caps": {
            "single_run_max_pct": 45,
            "single_family_max_pct": 60,
            "max_rows_per_run": max_per_run,
            "max_rows_per_model_family": max_per_family,
            "per_run_contribution": dict(sorted(run_counts.items())),
            "per_model_family_contribution": dict(sorted(family_counts.items())),
        },
        "exact_dedup_log": exact_log,
        "near_dup_log": near_log,
        "status": "PASS" if 120 <= len(assembled) <= 150 else "FAIL_TARGET_SIZE",
    }
    return assembled, report


def normalize_question(raw: str) -> str:
    q = raw.strip()
    replacements = {
        "whats": "what is",
        "w/": "with ",
        "chrgr": "charger",
        "scrubs ln": "Scrubbs Lane",
        "ev": "EV",
        "nyc": "NYC",
        "uprn": "UPRN",
        "mvc": "MVC",
    }
    for src, dst in replacements.items():
        q = re.sub(rf"\b{re.escape(src)}\b", dst, q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if q and q[-1] not in "?!.":
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def requires_context(row: dict[str, Any]) -> bool:
    q = str(row["raw_question"]).lower()
    if str(row["selected_item_context"]) == "general_patch_board":
        return False
    explicit = re.search(r"\b(wood lane|scrubbs|scrubs|ev\s*87|charger\s*87|mvc|4463710|uprn|westway|howard|nyc|chicago)\b", q)
    pronoun_or_ellipsis = re.search(r"\b(this|that|it|here|there|selected|these|those|anything|what changed|what happened|missing what)\b", q)
    return bool(pronoun_or_ellipsis and not explicit) or len(q.split()) <= 4


def refuse(label: str) -> tuple[str, str]:
    assert label in REFUSAL_CLASSES
    return f"refuse:{label}", label


def label_row(row: dict[str, Any]) -> tuple[str, str | None]:
    q = str(row["raw_question"]).lower()
    context = str(row.get("selected_item_context", "")).lower()

    if re.search(r"\b(dispatch|route|enforce|approve|create case|create a case|publish alert|take action|assign|notify|call\b|call .*team|call .*operator|send .*email|send .*to|alert someone|alert .*team|escalate|open a ticket|make a case|file a case|case for this)\b", q):
        return refuse("action_shaped")
    if re.search(r"\b(person|who is responsible|identify the|driver|plate|face|biometric|owner name|personal)\b", q):
        return refuse("identity_or_person")
    if re.search(r"\b(budget|emergency database|weather|school|hospital|crime|police|unrelated|outside this board)\b", q):
        return refuse("out_of_scope_entity")
    if re.search(r"\b(will|predict|tomorrow|next week|risk score|probability|liable|legal issue|violation|certify|certified|official finding|fine them|unsafe|urgent)\b", q):
        if re.search(r"\b(can we claim|what can.*claim|what cannot|not prove|does .*prove|only proximity|causality)\b", q):
            return TEMPLATE_REFS["cannot"], None
        return refuse("prediction_or_finding")
    if re.search(r"\b(list|compare|all three|three ranked|all london|all situation|every|count for each|which.*highest|rank.*all|across london and nyc|aggregate)\b", q):
        return refuse("unsupported_aggregate_or_comparison")
    if re.search(r"\b(blocked|available|availability|open now|closed now|live service|service status|currently open|actual access|changed today|new crashes today)\b", q):
        if re.search(r"\b(can we claim|claim|what cannot|not prove|does .*prove|only proximity|causality)\b", q):
            return TEMPLATE_REFS["cannot"], None
        return refuse("insufficient_source_depth")
    if re.search(r"\b(how do i|where do i|can i click|what button|export|copy|add note|mark reviewed|open ask|generate brief|run check|use this board|what does .*panel|why does .*panel|checks panel|mention chicago|what happens if i)\b", q):
        return "ui_help", None
    if re.search(r"\b(can we claim|what can.*claim|what cannot|cannot claim|not prove|prove|only proximity|causality|does this mean|is it only context|boundary|official.*created|anything official|this is official|official from this board|urgency finding|review order|treating .*as live monitoring|live monitoring)\b", q):
        return TEMPLATE_REFS["cannot"], None
    if re.search(r"\b(source records?|records support|evidence|citations?|support|why.*ranked|why.*here|knowns?|on file|what backs|what supports)\b", q):
        return TEMPLATE_REFS["supports"], None
    if re.search(r"\b(missing|uncertain|unknown|gap|what.*not know|no evidence|needs review|what else.*needed|what evidence.*missing)\b", q):
        return TEMPLATE_REFS["uncertain"], None
    if re.search(r"\b(what do we know|look up|about|profile|uprn|ev\s*87|asset 87|crash 4463710|mvc 4463710)\b", q) or context in {"ev_asset_87", "nyc_mvc_candidate_context"}:
        return TEMPLATE_REFS["entity"], None
    if re.search(r"\b(summary|summarize|brief|explain|what changed|what happened|what is going on|priority|worry)\b", q):
        return "gap:selected item summary or situation briefing template needed", None
    return "gap:general operator question needs taxonomy review", None


def first_label_pass(assembled: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    labeled: list[dict[str, Any]] = []
    for row in assembled:
        route, refusal_class = label_row(row)
        new_row = dict(row)
        new_row["normalized_question"] = normalize_question(str(row["raw_question"]))
        new_row["requires_selected_item_context"] = requires_context(row)
        new_row["expected_route_label"] = route
        new_row["expected_refusal_class"] = refusal_class
        labeled.append(new_row)

    route_counts = Counter(row["expected_route_label"] for row in labeled)
    refusal_counts = Counter(row["expected_refusal_class"] for row in labeled if row["expected_refusal_class"])
    persona_route: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in labeled:
        persona_route[row["persona"]][row["expected_route_label"]] += 1
    context_rate = sum(1 for row in labeled if row["requires_selected_item_context"]) / max(len(labeled), 1)
    distribution = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.label_distribution.v1",
        "generated_at": now(),
        "row_count": len(labeled),
        "route_counts": dict(sorted(route_counts.items())),
        "refusal_class_counts": dict(sorted(refusal_counts.items())),
        "persona_route_crosstab": {persona: dict(sorted(counts.items())) for persona, counts in sorted(persona_route.items())},
        "requires_selected_item_context_count": sum(1 for row in labeled if row["requires_selected_item_context"]),
        "requires_selected_item_context_rate": round(context_rate, 4),
        "status": "PASS_PRELIMINARY_CODEX_LABELS_PENDING_DOUBLE_LABEL",
    }
    gap_counts = Counter(
        row["expected_route_label"][4:] for row in labeled if str(row["expected_route_label"]).startswith("gap:")
    )
    gap_examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labeled:
        label = str(row["expected_route_label"])
        if label.startswith("gap:") and len(gap_examples[label[4:]]) < 8:
            gap_examples[label[4:]].append(
                {
                    "question_id": row["question_id"],
                    "persona": row["persona"],
                    "raw_question": row["raw_question"],
                }
            )
    gap_report = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.template_gap_report.v1",
        "generated_at": now(),
        "gap_count": sum(gap_counts.values()),
        "gaps_ranked": [
            {"gap": gap, "count": count, "examples": gap_examples[gap]} for gap, count in gap_counts.most_common()
        ],
        "status": "PASS" if gap_counts else "PASS_NO_GAPS_FOUND",
    }
    return labeled, distribution, gap_report


def blind_double_label_sample(labeled: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target = max(math.ceil(len(labeled) * 0.20), 1)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in labeled:
        groups[(row["persona"], row["expected_route_label"])].append(row)
    for group_rows in groups.values():
        group_rows.sort(key=lambda r: r["question_id"])
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for key in sorted(groups):
        row = groups[key][0]
        selected.append(row)
        selected_ids.add(row["question_id"])
    index = 1
    while len(selected) < target:
        made_progress = False
        for key in sorted(groups):
            if len(selected) >= target:
                break
            rows = groups[key]
            if index < len(rows):
                row = rows[index]
                if row["question_id"] not in selected_ids:
                    selected.append(row)
                    selected_ids.add(row["question_id"])
                    made_progress = True
        if not made_progress:
            break
        index += 1
    selected.sort(key=lambda r: r["question_id"])
    return [
        {
            "row_id": row["question_id"],
            "persona": row["persona"],
            "selected_item_context": row["selected_item_context"],
            "raw_question": row["raw_question"],
        }
        for row in selected
    ]


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return rows, errors
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception as exc:
            errors.append({"line": line_number, "error": str(exc), "raw": line[:160]})
            continue
        if not isinstance(value, dict):
            errors.append({"line": line_number, "error": "json value is not an object"})
            continue
        rows.append(value)
    return rows, errors


def write_pending_double_label_audit(blind_sample: list[dict[str, Any]]) -> dict[str, Any]:
    audit = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.double_label_audit.v1",
        "generated_at": now(),
        "status": "PENDING_INDEPENDENT_LABELS",
        "blind_sample": rel(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_BLIND_SAMPLE.jsonl"),
        "blind_sample_rows": len(blind_sample),
        "required_return_file": rel(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl"),
        "required_fields": [
            "row_id",
            "normalized_question",
            "requires_selected_item_context",
            "expected_route_label",
            "expected_refusal_class",
        ],
        "disagreement_rate": None,
        "split_and_seal_r3_status": "BLOCKED_UNTIL_DOUBLE_LABEL_AUDIT_PASSES",
    }
    write_json(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_AUDIT_PENDING.json", audit)
    return audit


def compare_independent_labels(labeled: list[dict[str, Any]], blind_sample: list[dict[str, Any]]) -> dict[str, Any] | None:
    independent_path = OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl"
    if not independent_path.exists():
        return None

    independent_rows, parse_errors = read_jsonl(independent_path)
    labeled_by_id = {row["question_id"]: row for row in labeled}
    blind_ids = [row["row_id"] for row in blind_sample]
    independent_ids = [str(row.get("row_id", "")) for row in independent_rows]
    required = {"row_id", "normalized_question", "requires_selected_item_context", "expected_route_label", "expected_refusal_class"}
    schema_errors = [
        {"row_index": index, "row_id": row.get("row_id"), "fields": sorted(row)}
        for index, row in enumerate(independent_rows, 1)
        if set(row) != required
    ]
    disagreements: list[dict[str, Any]] = []
    context_disagreements: list[dict[str, Any]] = []
    for row in independent_rows:
        row_id = str(row.get("row_id", ""))
        codex = labeled_by_id.get(row_id)
        if not codex:
            continue
        codex_route = codex.get("expected_route_label")
        independent_route = row.get("expected_route_label")
        codex_refusal = codex.get("expected_refusal_class")
        independent_refusal = row.get("expected_refusal_class")
        if codex_route != independent_route or codex_refusal != independent_refusal:
            disagreements.append(
                {
                    "row_id": row_id,
                    "raw_question": codex.get("raw_question"),
                    "codex_expected_route_label": codex_route,
                    "independent_expected_route_label": independent_route,
                    "codex_expected_refusal_class": codex_refusal,
                    "independent_expected_refusal_class": independent_refusal,
                    "adjudication_status": "NOT_ADJUDICATED_TAXONOMY_AMBIGUOUS",
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

    missing_ids = sorted(set(blind_ids) - set(independent_ids))
    extra_ids = sorted(set(independent_ids) - set(blind_ids))
    row_id_match = independent_ids == blind_ids
    denominator = len(blind_ids) if blind_ids else 1
    disagreement_rate = len(disagreements) / denominator
    status = "PASS_DOUBLE_LABEL_DISAGREEMENT_WITHIN_THRESHOLD" if disagreement_rate <= 0.15 and not parse_errors and not schema_errors and not missing_ids and not extra_ids else "FAIL_TAXONOMY_AMBIGUOUS_DOUBLE_LABEL_DISAGREEMENT_GT_15"
    if parse_errors or schema_errors or missing_ids or extra_ids:
        status = "FAIL_INDEPENDENT_LABEL_FILE_VALIDATION"

    audit = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.double_label_audit.v1",
        "generated_at": now(),
        "status": status,
        "blind_sample": rel(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_BLIND_SAMPLE.jsonl"),
        "independent_labels": rel(independent_path),
        "independent_labels_sha256": sha256_file(independent_path),
        "blind_sample_rows": len(blind_ids),
        "independent_rows": len(independent_rows),
        "row_ids_match_blind_sample_order": row_id_match,
        "missing_row_ids": missing_ids,
        "extra_row_ids": extra_ids,
        "parse_errors": parse_errors,
        "schema_errors": schema_errors,
        "route_or_refusal_disagreement_count": len(disagreements),
        "route_or_refusal_disagreement_rate": round(disagreement_rate, 4),
        "context_dependency_disagreement_count": len(context_disagreements),
        "context_dependency_disagreement_rate": round(len(context_disagreements) / denominator, 4),
        "threshold": 0.15,
        "disagreements": disagreements,
        "context_dependency_disagreements": context_disagreements,
        "adjudication": {
            "status": "BLOCKED_TAXONOMY_AMBIGUOUS" if disagreement_rate > 0.15 else "READY_FOR_ADJUDICATION",
            "rule": "Do not train router or run Split/Seal R3 when route/refusal disagreement exceeds 15%.",
        },
        "split_and_seal_r3_status": "BLOCKED_TAXONOMY_AMBIGUOUS" if disagreement_rate > 0.15 else "READY",
    }
    write_json(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_AUDIT.json", audit)
    return audit


def copy_contract() -> None:
    if CONTRACT.exists():
        shutil.copy2(CONTRACT, OUTPUT_ROOT / CONTRACT.name)


def write_hashes() -> None:
    lines: list[str] = []
    for root in [OUTPUT_ROOT, RAW_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.txt":
                lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUTPUT_ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def write_local_index(status: str) -> None:
    rows = [
        "# Synthetic Corpus v0 Assembly / Labeling / Split Gate",
        "",
        f"Status: `{status}`",
        "",
        "Open these first:",
        "- `CORPUS_V0_RUN_VALIDATION_REPORT.json`",
        "- `CORPUS_V0_ASSEMBLY_REPORT.json`",
        "- `operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl`",
        "- `CORPUS_V0_DOUBLE_LABEL_BLIND_SAMPLE.jsonl`",
        "- `CORPUS_V0_DOUBLE_LABEL_AUDIT_PENDING.json`",
        "",
        "Split/Seal R3 is intentionally blocked until independent blind labels are returned.",
    ]
    write_text(OUTPUT_ROOT / "README.md", "\n".join(rows))
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def main() -> None:
    preserved_files: dict[str, bytes] = {}
    for filename in [
        "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl",
        "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS_REPORT.json",
    ]:
        path = OUTPUT_ROOT / filename
        if path.exists():
            preserved_files[filename] = path.read_bytes()
    clean_dir(OUTPUT_ROOT)
    for filename, data in preserved_files.items():
        (OUTPUT_ROOT / filename).write_bytes(data)
    run_file_records, wrapper_records = derive_raw_jsonl()
    valid_rows, quarantined, validation_report = parse_and_validate(run_file_records)
    assembled, assembly_report = dedup_and_select(valid_rows)
    labeled, distribution_report, gap_report = first_label_pass(assembled)
    blind_sample = blind_double_label_sample(labeled)
    double_label_audit = compare_independent_labels(labeled, blind_sample)
    pending_audit = double_label_audit or write_pending_double_label_audit(blind_sample)

    write_json(OUTPUT_ROOT / "CORPUS_V0_RUN_VALIDATION_REPORT.json", validation_report)
    write_json(OUTPUT_ROOT / "CORPUS_V0_RAW_WRAPPER_NORMALIZATION_REPORT.json", {"status": "PASS" if wrapper_records else "NOT_NEEDED", "records": wrapper_records})
    write_jsonl(OUTPUT_ROOT / "CORPUS_V0_QUARANTINE.jsonl", quarantined)
    write_json(OUTPUT_ROOT / "CORPUS_V0_ASSEMBLY_REPORT.json", assembly_report)
    write_jsonl(OUTPUT_ROOT / "operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl", assembled)
    write_jsonl(OUTPUT_ROOT / "operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl", labeled)
    write_json(OUTPUT_ROOT / "CORPUS_V0_LABEL_DISTRIBUTION_REPORT.json", distribution_report)
    write_json(OUTPUT_ROOT / "CORPUS_V0_TEMPLATE_GAP_REPORT.json", gap_report)
    write_jsonl(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_BLIND_SAMPLE.jsonl", blind_sample)
    write_text(
        OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_INSTRUCTIONS.md",
        """
# Independent Double-Label Instructions

Label `CORPUS_V0_DOUBLE_LABEL_BLIND_SAMPLE.jsonl` without consulting
`operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl`.

Return a JSONL file named `CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl`
in this same output folder. Each row must include:

- `row_id`
- `normalized_question`
- `requires_selected_item_context`
- `expected_route_label`
- `expected_refusal_class`

Valid route labels are `template:ask:entity_360@v1`,
`template:ask:what_supports@v1`, `template:ask:what_is_uncertain@v1`,
`template:ask:cannot_claim@v1`, `ui_help`, `refuse:<class>`, or
`gap:<one-line description>`. Refusal class is required only for refusal rows.
Split/Seal R3 remains blocked until disagreement is <= 15%.
""",
    )

    raw_hashes = {
        "schema_version": "citybrain.d14.synthetic_corpus_v0.raw_hash_manifest.v1",
        "generated_at": now(),
        "files": [
            {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(RAW_ROOT.rglob("*"))
            if path.is_file()
        ],
    }
    write_json(OUTPUT_ROOT / "CORPUS_RAW_HASH_MANIFEST.json", raw_hashes)
    copy_contract()

    if double_label_audit is None:
        status = "PAUSED_D14_SYNTHETIC_CORPUS_V0_AWAITING_INDEPENDENT_DOUBLE_LABELS"
        split_status = "NOT_RUN_BLOCKED_PENDING_INDEPENDENT_DOUBLE_LABEL_AUDIT"
        next_required_input = rel(OUTPUT_ROOT / "CORPUS_V0_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl")
    elif double_label_audit["status"] == "PASS_DOUBLE_LABEL_DISAGREEMENT_WITHIN_THRESHOLD":
        status = "PASS_D14_SYNTHETIC_CORPUS_V0_DOUBLE_LABEL_AUDIT_READY_FOR_SPLIT_SEAL_R3"
        split_status = "READY_FOR_SPLIT_SEAL_R3"
        next_required_input = "rerun split/seal branch after adjudication"
    else:
        status = "PAUSED_D14_SYNTHETIC_CORPUS_V0_TAXONOMY_AMBIGUOUS_DOUBLE_LABEL_DISAGREEMENT_GT_15"
        split_status = "NOT_RUN_BLOCKED_TAXONOMY_AMBIGUOUS"
        next_required_input = "revise taxonomy/labeling rules before router training or split/seal"
    decision = {
        "task": "MAIN-CITYBRAIN-D14-SYNTHETIC-CORPUS-V0-ASSEMBLY-R1-LABELING-R2-SPLIT-SEAL-R3-GATE",
        "status": status,
        "generated_at": now(),
        "repo_root": str(REPO),
        "output_root": rel(OUTPUT_ROOT),
        "corpus_raw_root": rel(RAW_ROOT),
        "contract": str(CONTRACT),
        "assembly_r1": assembly_report["status"],
        "labeling_r2_preliminary": distribution_report["status"],
        "double_label_status": pending_audit["status"],
        "double_label_disagreement_rate": pending_audit.get("route_or_refusal_disagreement_rate"),
        "double_label_disagreement_count": pending_audit.get("route_or_refusal_disagreement_count"),
        "split_and_seal_r3": split_status,
        "raw_valid_rows": validation_report["raw_valid_rows"],
        "quarantined_rows": validation_report["quarantined_rows"],
        "assembled_rows": assembly_report["final_assembled_rows"],
        "preliminary_labeled_rows": distribution_report["row_count"],
        "blind_sample_rows": len(blind_sample),
        "blind_sample_pct": round(len(blind_sample) / max(distribution_report["row_count"], 1), 4),
        "source_type_preserved": all(row["source_type"] == "synthetic_v0_clean_ai" for row in labeled),
        "router_preflight_opened": False,
        "real_operator_validation_claimed": False,
        "limitations": validation_report["limitations"]
        + (
            [
                "Final Labeling R2, Double Label Audit, Split/Seal R3, and router preflight are blocked until independent blind labels are returned.",
            ]
            if double_label_audit is None
            else [
                "Split/Seal R3 and router preflight are blocked because independent double-label disagreement exceeded 15%.",
            ]
            if status.endswith("GT_15")
            else []
        ),
        "next_required_input": next_required_input,
    }
    write_json(OUTPUT_ROOT / "D14_SYNTHETIC_CORPUS_V0_ASSEMBLY_LABELING_SPLIT_GATE_DECISION.json", decision)
    write_local_index(status)
    write_hashes()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
