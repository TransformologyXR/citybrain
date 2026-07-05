#!/usr/bin/env python3
"""Run D14 staged-router schema repair R1.

This supersedes further flat route-label repair after v0.4B. It migrates the
synthetic corpus into staged decisions, exports a blind double-label sample,
and stops before Split/Seal R3, router preflight, router training, or any real
operator validation claim.
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
V04B_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04b_boundary_stability_r1"
V04A_ROOT = OUTPUTS / "main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1"
ASSEMBLY_ROOT = OUTPUTS / "main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate"
ROOT = OUTPUTS / "main_citybrain_d14_staged_router_schema_repair_r1"
PROMPT_ROOT = REPO / "tmp" / "citybrain_d14_staged_router_schema_repair_r1" / "citybrain_d14_staged_router_schema_repair_r1"
TOPUP_ROOT = REPO / "inputs" / "d14_synthetic_operator_questions" / "hard_shaped_topup"

TASK = "MAIN-CITYBRAIN-D14-STAGED-ROUTER-SCHEMA-REPAIR-R1"
STATUS = "PAUSED_D14_STAGED_ROUTER_SCHEMA_AWAITING_INDEPENDENT_DOUBLE_LABELS"

INPUTS = {
    "v04b_labeled": V04B_ROOT / "operator_question_corpus_synthetic_v0_labeled_v04b.jsonl",
    "v04b_audit": V04B_ROOT / "D14_DOUBLE_LABEL_V04B_AUDIT.json",
    "v04b_gate_results": V04B_ROOT / "D14_ROUTE_TAXONOMY_V04B_GATE_RESULTS.json",
    "v04b_closeout": V04B_ROOT / "D14_ROUTE_TAXONOMY_V04B_CLOSEOUT_DECISION.json",
    "v04a_architecture": V04A_ROOT / "SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.json",
    "assembly_unlabeled": ASSEMBLY_ROOT / "operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl",
}
EXPECTED_INPUT_FILES = list(INPUTS.values())

STAGE_A = ["clear", "action_shaped", "prediction_or_finding", "identity_or_person", "out_of_scope_domain", "ambiguous_boundary"]
STAGE_B = [
    "city_subject_question",
    "source_record_question",
    "patch_queue_question",
    "meta_product_question",
    "external_context_question",
    "identity_person_question",
    "out_of_scope_question",
]
STAGE_C = [
    "subject_answer",
    "entity_360",
    "source_record_360_gap",
    "patch_queue_query_gap",
    "external_context_source_gap",
    "ui_help",
    "boundary_explanation",
    "refusal",
]
STAGE_D = ["support", "uncertainty", "claimability", "summary", "not_applicable"]


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_inputs() -> None:
    missing = [path for path in EXPECTED_INPUT_FILES if not path.exists()]
    if missing:
        ROOT.mkdir(parents=True, exist_ok=True)
        write_json(
            ROOT / "D14_STAGED_ROUTER_SCHEMA_CLOSEOUT_DECISION.json",
            {
                "task": TASK,
                "status": "BLOCKED_D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_MISSING_INPUTS",
                "generated_at": now(),
                "missing_inputs": [rel(path) for path in missing],
            },
        )
        raise SystemExit("Missing required staged-router inputs: " + ", ".join(rel(path) for path in missing))


def clean_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


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
    if q and q[-1] not in "?!.":  # operator fragments stay readable
        q += "?"
    return q[:1].upper() + q[1:] if q else q


def flat_label_to_stages(label: str, refusal_class: str | None) -> tuple[str, str, str, str]:
    if label == "refuse:action_shaped":
        return "action_shaped", "meta_product_question", "refusal", "not_applicable"
    if label == "refuse:prediction_or_finding":
        return "prediction_or_finding", "meta_product_question", "refusal", "not_applicable"
    if label == "refuse:identity_or_person":
        return "identity_or_person", "identity_person_question", "refusal", "not_applicable"
    if label == "ui_help":
        return "clear", "meta_product_question", "ui_help", "not_applicable"
    if label == "gap:patch_queue_query_needed":
        return "clear", "patch_queue_question", "patch_queue_query_gap", "not_applicable"
    if label == "gap:source_record_360_needed":
        return "clear", "source_record_question", "source_record_360_gap", "not_applicable"
    if label == "gap:external_context_source_needed":
        return "clear", "external_context_question", "external_context_source_gap", "not_applicable"
    if label == "template:ask:entity_360@v2":
        return "clear", "city_subject_question", "entity_360", "not_applicable"
    if label.startswith("template:ask:subject_answer@v1:lens="):
        lens = label.rsplit("=", 1)[-1]
        return "clear", "city_subject_question", "subject_answer", lens
    return "ambiguous_boundary", "out_of_scope_question", "boundary_explanation", "not_applicable"


def stage_from_text(row: dict[str, Any], base: tuple[str, str, str, str]) -> tuple[str, str, str, str, list[str]]:
    raw = str(row.get("raw_question", ""))
    q = raw.lower()
    a, b, c, d = base
    reasons: list[str] = []

    # Stage A guard overrides for known boundary classes.
    if re.search(r"\b(biometric|identify person|who is|owner name|driver identity|personal identity)\b", q):
        return "identity_or_person", "identity_person_question", "refusal", "not_applicable", ["person_identity_guard"]
    if re.search(r"\b(alert .*now|dispatch|route traffic|route drivers|enforce|approve this|create a case|call the police$|tell drivers now|send this to|publish an alert)\b", q):
        return "action_shaped", b if b != "city_subject_question" else "meta_product_question", "refusal", "not_applicable", ["imperative_external_action_guard"]
    if re.search(r"\b(can we tell drivers|should we notify|can i tell others|who do i call to get|tell others this is urgent)\b", q):
        return "ambiguous_boundary", "meta_product_question", "boundary_explanation", "not_applicable", ["action_adjacent_ambiguous_boundary"]
    if re.search(r"\b(legally non-compliant|certify that|make an official finding|will this cause|predict)\b", q):
        return "prediction_or_finding", "meta_product_question", "refusal", "not_applicable", ["official_prediction_finding_guard"]

    # Product-meta is its own family, not city-subject.
    if re.search(r"\b(this software|the software|the board|this board|the cockpit|this screen|from this screen|export|mark reviewed|notes|ranking|review order|cyber security standards|comply with city cyber)\b", q):
        b = "meta_product_question"
        if re.search(r"\b(comply with city cyber|cyber security standards|legal or official finding|certify a legal|ranking .*urgency|review order)\b", q):
            c = "boundary_explanation"
        else:
            c = "ui_help"
        d = "not_applicable"
        a = "clear"
        reasons.append("product_meta_family")

    if re.search(r"\b(list every queue|list the queue|three ranked|three queue|all open|open items|updated today|updated yesterday|rank over|summarise the three ranked|compare .*review items|queue item)\b", q):
        a, b, c, d = "clear", "patch_queue_question", "patch_queue_query_gap", "not_applicable"
        reasons.append("patch_queue_family")

    if re.search(r"\b(source row actually say|does .*record include|connector counts|power ratings|exact timestamp|when was .*source row recorded|what fields|raw values|record .*details)\b", q):
        a, b, c, d = "clear", "source_record_question", "source_record_360_gap", "not_applicable"
        reasons.append("source_record_details_family")

    if re.search(r"\b(weather|typical daily utilisation|live service-status source|live availability source|external context|external source)\b", q):
        a, b, c, d = "clear", "external_context_question", "external_context_source_gap", "not_applicable"
        reasons.append("external_context_family")

    if re.search(r"\b(rapid or slow|rapid charging|is it rapid charging|what is ev asset|asset attribute)\b", q):
        a, b, c, d = "clear", "city_subject_question", "entity_360", "not_applicable"
        reasons.append("entity_profile_family")

    if c == "subject_answer":
        if re.search(r"\b(support|source supports|records support|linked|evidence and uncertainty|what backs)\b", q):
            d = "support"
        elif re.search(r"\b(missing|uncertain|unknown|why is there no|unavailable because|not ready)\b", q):
            d = "uncertainty"
        elif re.search(r"\b(status|blocked|live|available|unavailable|claim|prove|establish|verify|certify|urgent|working)\b", q):
            d = "claimability"
        elif d not in {"support", "uncertainty", "claimability", "summary"}:
            d = "summary"

    return a, b, c, d, reasons


def requires_context(row: dict[str, Any]) -> bool:
    raw = str(row.get("raw_question", ""))
    q = raw.lower()
    if re.fullmatch(r"\s*(charger status\?\?|is it rapid charging\??|is it working right now\??|what about this\??|what about that\??|run the check\??|what is missing here\??|ev 87 status\??)\s*", q):
        return True
    if re.search(r"\b(ev\s*87|asset\s*87|charger\s*87|wood lane|nyc mvc|4463710|tims-\d+|source row|source record|record|board|screen|software|patch|queue|weather|ranking|police|legal finding|open items|all items)\b", q):
        return False
    if re.search(r"\b(this|that|it|here|selected)\b", q):
        return True
    return bool(row.get("requires_selected_item_context", False))


def ambiguity_reasons(row: dict[str, Any], v04b_audit: dict[str, Any], stages: tuple[str, str, str, str]) -> list[str]:
    row_id = row["question_id"]
    reasons = []
    family_ids = {item["row_id"] for item in v04b_audit.get("family_disagreements_excluding_lens_only", [])}
    refusal_ids = {item["row_id"] for item in v04b_audit.get("refusal_boundary_hard_errors", [])}
    anchor_ids = {item["row_id"] for item in v04b_audit.get("canonical_anchor_disagreements", [])}
    context_ids = {item["row_id"] for item in v04b_audit.get("context_dependency_disagreements", [])}
    if row_id in family_ids:
        reasons.append("v04b_family_disagreement")
    if row_id in refusal_ids:
        reasons.append("v04b_refusal_boundary_hard_error")
    if row_id in anchor_ids:
        reasons.append("v04b_canonical_anchor_disagreement")
    if row_id in context_ids:
        reasons.append("v04b_context_dependency_disagreement")
    q = str(row.get("raw_question", "")).lower()
    if re.search(r"\b(can we tell drivers|should we notify|can i tell others|who do i call|comply with city cyber|software comply|source row|source record|prove|verify|establish|live service-status|live availability source)\b", q):
        reasons.append("known_hard_boundary_shape")
    if stages[0] == "ambiguous_boundary":
        reasons.append("stage_a_ambiguous_boundary")
    return sorted(set(reasons))


def migrate_rows(rows: list[dict[str, Any]], v04b_audit: dict[str, Any]) -> list[dict[str, Any]]:
    migrated = []
    for row in rows:
        out = dict(row)
        base = flat_label_to_stages(str(row.get("expected_route_label")), row.get("expected_refusal_class"))
        stage_a, stage_b, stage_c, stage_d, text_reasons = stage_from_text(row, base)
        stage_e = requires_context(row)
        reasons = sorted(set(text_reasons + ambiguity_reasons(row, v04b_audit, (stage_a, stage_b, stage_c, stage_d))))
        out.update(
            {
                "staged_schema_version": "citybrain.d14.staged_router_schema.r1",
                "stage_a_boundary_class": stage_a,
                "stage_b_intent_family": stage_b,
                "stage_c_route_target": stage_c,
                "stage_d_subject_answer_lens": stage_d if stage_c == "subject_answer" else "not_applicable",
                "stage_e_requires_selected_item_context": stage_e,
                "migration_confidence": "ambiguous" if reasons else "high",
                "migration_reasons": reasons,
                "flat_route_label_source": row.get("expected_route_label"),
                "flat_expected_refusal_class_source": row.get("expected_refusal_class"),
                "normalized_question": normalize_question(str(row.get("raw_question", ""))),
            }
        )
        migrated.append(out)
    return migrated


def preflight_decision(rows: list[dict[str, Any]], v04b_gate: dict[str, Any], v04b_closeout: dict[str, Any]) -> dict[str, Any]:
    split_files = [
        ROOT / "CORPUS_V0_SPLIT_MANIFEST.json",
        V04B_ROOT / "CORPUS_V0_SPLIT_MANIFEST.json",
        V04B_ROOT / "CORPUS_V0_TRAIN.jsonl",
    ]
    return {
        "schema_version": "citybrain.d14.staged_router_schema_preflight_r1",
        "generated_at": now(),
        "status": "PASS_D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_R1",
        "v04b_failed": v04b_gate.get("status", "").startswith("FAIL") or v04b_closeout.get("double_label_gate_status", "").startswith("FAIL"),
        "v04b_exact_disagreement_rate": v04b_closeout.get("exact_route_disagreement_rate"),
        "v04b_refusal_boundary_hard_error_count": v04b_closeout.get("refusal_boundary_hard_error_count"),
        "rows": len(rows),
        "source_type_counts": dict(sorted(Counter(row.get("source_type") for row in rows).items())),
        "source_type_preserved": all(row.get("source_type") == "synthetic_v0_clean_ai" for row in rows),
        "split_seal_r3_run": any(path.exists() for path in split_files),
        "router_preflight_opened": False,
        "router_training_opened": False,
        "real_operator_validation_claimed": False,
    }


def input_inventory() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.staged_router_schema_input_inventory.r1",
        "generated_at": now(),
        "inputs": {
            name: {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path) if path.exists() and path.is_file() else None}
            for name, path in INPUTS.items()
        },
    }


def schema_contract() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.staged_router_schema_contract.r1",
        "generated_at": now(),
        "status": "PASS_D14_STAGED_SCHEMA_CONTRACT_R1",
        "stage_a_boundary_class": STAGE_A,
        "stage_b_intent_family": STAGE_B,
        "stage_c_route_target": STAGE_C,
        "stage_d_subject_answer_lens": STAGE_D,
        "stage_e_requires_selected_item_context": "boolean",
        "composition_rules": [
            "If Stage A is clear, continue to Stage B/C/D/E.",
            "If Stage A is non-clear, normal city-answer routing is blocked.",
            "For non-clear Stage A, later stages may be recorded as diagnostic/onward intent only.",
            "Stage D must be not_applicable unless Stage C is subject_answer.",
            "Full-path exact agreement is informational, not the primary gate.",
        ],
        "subject_answer_preserved": "template:ask:subject_answer@v1(subject,lens)",
    }


def write_decision_tree() -> None:
    text = """# Staged Router Decision Tree R1

## Stage A — Boundary / Guard

Closed vocabulary: `clear`, `action_shaped`, `prediction_or_finding`, `identity_or_person`,
`out_of_scope_domain`, `ambiguous_boundary`.

Stage A is a guard. Any non-clear value blocks normal city-answer routing and goes to refusal or
boundary-explanation behavior. Downstream stages can still be recorded diagnostically.

## Stage B — Intent Family

Closed vocabulary: `city_subject_question`, `source_record_question`, `patch_queue_question`,
`meta_product_question`, `external_context_question`, `identity_person_question`,
`out_of_scope_question`.

Product/software/board questions such as export, notes, board alerts, officialness, and cyber
compliance are `meta_product_question`, not city-subject answers.

## Stage C — Route Target

Closed vocabulary: `subject_answer`, `entity_360`, `source_record_360_gap`,
`patch_queue_query_gap`, `external_context_source_gap`, `ui_help`, `boundary_explanation`,
`refusal`.

## Stage D — Subject-Answer Lens

Closed vocabulary: `support`, `uncertainty`, `claimability`, `summary`, `not_applicable`.

Use a real lens only when Stage C is `subject_answer`. The lens changes section ordering, not the
assembled answer object.

## Stage E — Context Required

Boolean. True only when the question cannot be interpreted without the selected item or prior
context. False if the question names the asset, board, patch, record, weather, ranking, police,
export, legal finding, or item scope.
"""
    write_text(ROOT / "STAGED_ROUTER_DECISION_TREE_R1.md", text)


def gate_policy() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.d14.staged_router_gate_policy.r1",
        "generated_at": now(),
        "status": "PASS_D14_STAGED_GATE_POLICY_DEFINED",
        "stage_a_disagreement_threshold": 0.05,
        "refusal_boundary_hard_error_max": 1,
        "stage_b_disagreement_threshold": 0.15,
        "stage_c_disagreement_threshold": 0.20,
        "stage_d_disagreement_threshold": 0.25,
        "stage_d_blocking": False,
        "stage_e_disagreement_threshold": 0.15,
        "full_path_exact_agreement": "INFORMATIONAL_ONLY",
        "report_on_policy_and_all_stage_agreement_separately": True,
    }


def migration_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ambiguous = [row for row in rows if row.get("migration_confidence") == "ambiguous"]
    return {
        "schema_version": "citybrain.d14.flat_label_to_staged_migration_report.r1",
        "generated_at": now(),
        "status": "PASS_D14_FLAT_LABEL_MIGRATION_TO_STAGED_R1_WITH_AMBIGUITIES_RECORDED",
        "rows": len(rows),
        "ambiguous_migration_rows": len(ambiguous),
        "stage_a_counts": dict(sorted(Counter(row["stage_a_boundary_class"] for row in rows).items())),
        "stage_b_counts": dict(sorted(Counter(row["stage_b_intent_family"] for row in rows).items())),
        "stage_c_counts": dict(sorted(Counter(row["stage_c_route_target"] for row in rows).items())),
        "stage_d_counts": dict(sorted(Counter(row["stage_d_subject_answer_lens"] for row in rows).items())),
        "source_type_counts": dict(sorted(Counter(row.get("source_type") for row in rows).items())),
        "real_operator_validation_claimed": False,
    }


def write_topup_protocol() -> dict[str, Any]:
    topup_available = TOPUP_ROOT.exists() and any(TOPUP_ROOT.rglob("*.jsonl"))
    prompt = """# Hard-Shaped Top-Up Clean-Session Prompt R2

Use only the frozen operator-visible text stimulus. Do not mention router stages, labels, templates,
gaps, taxonomy, or implementation details.

Generate JSONL rows with realistic operator questions around:

- action-adjacent communication: can we tell drivers, should we notify, can the board alert
- product-meta/security/compliance: does this software comply, is this official, can this be shared
- source support vs source-row details
- EV live/blocked/availability claimability
- weather/live/external context gaps
- patch queue aggregate/list/filter questions

Leave normalized and label fields null. Mark rows as `source_type =
synthetic_v0_clean_ai_hard_topup`. This is synthetic only, never real operator validation.
"""
    write_text(ROOT / "HARD_SHAPED_TOPUP_CLEAN_SESSION_PROMPT_R2.md", prompt)
    write_json(
        ROOT / "HARD_SHAPED_TOPUP_RUN_LOG_TEMPLATE.json",
        {
            "schema_version": "citybrain.d14.hard_shaped_topup_run_log_template.r2",
            "stimulus_sha256": None,
            "runs": [],
            "labels_left_null": True,
            "source_type": "synthetic_v0_clean_ai_hard_topup",
        },
    )
    decision = {
        "schema_version": "citybrain.d14.hard_shaped_topup_protocol_decision.r2",
        "generated_at": now(),
        "status": "PASS_D14_HARD_SHAPED_TOPUP_ROWS_IMPORTED" if topup_available else "PASS_D14_HARD_SHAPED_TOPUP_PROTOCOL_READY_NOT_RUN",
        "topup_rows_available": bool(topup_available),
        "real_operator_validation_claimed": False,
    }
    write_json(ROOT / "HARD_SHAPED_TOPUP_PROTOCOL_DECISION.json", decision)
    return decision


def clean_blind_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["question_id"],
        "raw_question": row.get("raw_question"),
        "persona": row.get("persona"),
        "selected_item_context": row.get("selected_item_context"),
        "source_type": row.get("source_type"),
        "source_session_id": row.get("source_session_id"),
        "provenance": row.get("provenance"),
    }


def select_blind_sample(rows: list[dict[str, Any]], v04b_audit: dict[str, Any], target: int = 72) -> list[dict[str, Any]]:
    selected_ids: set[str] = set()
    selected: list[dict[str, Any]] = []
    row_by_id = {row["question_id"]: row for row in rows}

    hard_ids = set()
    for key in ["refusal_boundary_hard_errors", "canonical_anchor_disagreements", "family_disagreements_excluding_lens_only"]:
        hard_ids.update(item["row_id"] for item in v04b_audit.get(key, []))
    hard_ids.update(row["question_id"] for row in rows if row.get("migration_confidence") == "ambiguous")

    for row_id in sorted(hard_ids):
        row = row_by_id.get(row_id)
        if row and row_id not in selected_ids:
            selected.append(row)
            selected_ids.add(row_id)

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["question_id"] not in selected_ids:
            groups[(row["stage_a_boundary_class"], row["stage_b_intent_family"], str(row.get("persona")))].append(row)
    for key in sorted(groups):
        if len(selected) >= target:
            break
        row = sorted(groups[key], key=lambda item: item["question_id"])[0]
        selected.append(row)
        selected_ids.add(row["question_id"])

    stage_counts = Counter(row["stage_c_route_target"] for row in selected)
    candidates = [row for row in rows if row["question_id"] not in selected_ids]
    for row in sorted(candidates, key=lambda item: (stage_counts[item["stage_c_route_target"]], item["stage_c_route_target"], item.get("persona"), item["question_id"])):
        if len(selected) >= target:
            break
        selected.append(row)
        selected_ids.add(row["question_id"])
        stage_counts[row["stage_c_route_target"]] += 1

    return [clean_blind_row(row) for row in sorted(selected, key=lambda item: item["question_id"])]


def write_staged_instructions() -> None:
    text = """# Staged Double-Label Instructions

Label every row independently across five stages. Do not infer any Codex label from row order.

## Output Schema

Return JSONL with:

- `row_id`
- `normalized_question`
- `stage_a_boundary_class`
- `stage_b_intent_family`
- `stage_c_route_target`
- `stage_d_subject_answer_lens`
- `stage_e_requires_selected_item_context`

## Stage A — Boundary / Guard

Allowed: `clear`, `action_shaped`, `prediction_or_finding`, `identity_or_person`,
`out_of_scope_domain`, `ambiguous_boundary`.

If Stage A is non-clear, it blocks normal city-answer routing. Still label later stages
diagnostically where possible.

## Stage B — Intent Family

Allowed: `city_subject_question`, `source_record_question`, `patch_queue_question`,
`meta_product_question`, `external_context_question`, `identity_person_question`,
`out_of_scope_question`.

Product/software/board questions are `meta_product_question`.

## Stage C — Route Target

Allowed: `subject_answer`, `entity_360`, `source_record_360_gap`, `patch_queue_query_gap`,
`external_context_source_gap`, `ui_help`, `boundary_explanation`, `refusal`.

## Stage D — Lens

Allowed: `support`, `uncertainty`, `claimability`, `summary`, `not_applicable`.

Use a non-`not_applicable` lens only when Stage C is `subject_answer`.

## Stage E — Context

Boolean. True only if the question cannot be interpreted without selected item or prior context.
False if it names the asset, board, patch, record, weather, ranking, police, export, legal finding,
or item scope.

## Gates

Stage A disagreement <= 5%, refusal-boundary hard errors <= 1.
Stage B <= 15%, Stage C <= 20%, Stage D <= 25% and mostly non-blocking, Stage E <= 15%.
Full-path exact agreement is informational only.
"""
    write_text(ROOT / "CORPUS_V0_STAGED_DOUBLE_LABEL_INSTRUCTIONS.md", text)


def sample_report(sample: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["question_id"]: row for row in rows}
    sample_ids = {row["row_id"] for row in sample}
    forbidden = {
        "stage_a_boundary_class",
        "stage_b_intent_family",
        "stage_c_route_target",
        "stage_d_subject_answer_lens",
        "stage_e_requires_selected_item_context",
        "expected_route_label",
        "expected_refusal_class",
        "flat_route_label_source",
        "migration_confidence",
        "migration_reasons",
    }
    leaks = [{"row_id": row.get("row_id"), "field": field} for row in sample for field in forbidden if field in row]
    return {
        "schema_version": "citybrain.d14.staged_double_label_sample_report.r1",
        "generated_at": now(),
        "status": STATUS,
        "sample_rows": len(sample),
        "target_range": "50-80",
        "ambiguous_migration_rows_included": sum(1 for row_id in sample_ids if by_id[row_id].get("migration_confidence") == "ambiguous"),
        "hidden_stage_a_counts": dict(sorted(Counter(by_id[row_id]["stage_a_boundary_class"] for row_id in sample_ids).items())),
        "hidden_stage_b_counts": dict(sorted(Counter(by_id[row_id]["stage_b_intent_family"] for row_id in sample_ids).items())),
        "hidden_stage_c_counts": dict(sorted(Counter(by_id[row_id]["stage_c_route_target"] for row_id in sample_ids).items())),
        "codex_label_or_stage_field_leaks": leaks,
        "next_expected_file": rel(ROOT / "CORPUS_V0_STAGED_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl"),
    }


def write_cold_probe(sample: list[dict[str, Any]]) -> dict[str, Any]:
    probe = sample[:20]
    write_jsonl(ROOT / "COLD_LABELER_STAGED_PROBE_PACKET.jsonl", probe)
    write_text(ROOT / "COLD_LABELER_STAGED_PROBE_INSTRUCTIONS.md", "Use the staged schema instructions. Return the same Stage A-E output fields. Do not consult prior labels.")
    manifest = {
        "schema_version": "citybrain.d14.cold_labeler_staged_probe_manifest.r1",
        "generated_at": now(),
        "status": "PASS_D14_COLD_LABELER_PROBE_PACKET_READY",
        "probe_rows": len(probe),
        "expected_output": "CORPUS_V0_COLD_LABELER_STAGED_LABELS.jsonl",
        "must_review_before_split_seal": True,
    }
    write_json(ROOT / "COLD_LABELER_STAGED_PROBE_MANIFEST.json", manifest)
    return manifest


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
    return {"schema_version": "citybrain.d14.staged_router_json_parse_audit.r1", "generated_at": now(), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "files": rows}


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
    return {"schema_version": "citybrain.d14.staged_router_secret_audit.r1", "generated_at": now(), "status": "PASS" if not hits else "FAIL", "hits": hits}


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "HASH_MANIFEST.txt", "\n".join(lines))


def package_outputs() -> None:
    package_path = ROOT / "D14_STAGED_ROUTER_SCHEMA_REPAIR_R1_PACKAGE.zip"
    if package_path.exists():
        package_path.unlink()
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                archive.write(path, rel(path))


def write_local_index() -> None:
    text = """# D14 Staged Router Schema Repair R1

Status: `PAUSED_D14_STAGED_ROUTER_SCHEMA_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Send for independent staged labeling:

- `CORPUS_V0_STAGED_DOUBLE_LABEL_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_STAGED_DOUBLE_LABEL_INSTRUCTIONS.md`

No Split/Seal R3, router preflight, router training, or real operator validation claim has been made.
"""
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", text)
    write_text(ROOT / "README.md", text)


def main() -> None:
    validate_inputs()
    clean_root()
    copy_prompt_pack()

    v04b_rows = read_jsonl(INPUTS["v04b_labeled"])
    v04b_audit = read_json(INPUTS["v04b_audit"])
    v04b_gate = read_json(INPUTS["v04b_gate_results"])
    v04b_closeout = read_json(INPUTS["v04b_closeout"])

    preflight = preflight_decision(v04b_rows, v04b_gate, v04b_closeout)
    write_json(ROOT / "D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_DECISION.json", preflight)
    write_json(ROOT / "D14_STAGED_ROUTER_SCHEMA_INPUT_INVENTORY.json", input_inventory())
    write_json(ROOT / "STAGED_ROUTER_SCHEMA_CONTRACT_R1.json", schema_contract())
    write_decision_tree()
    write_json(ROOT / "STAGED_ROUTER_GATE_POLICY_R1.json", gate_policy())

    migrated = migrate_rows(v04b_rows, v04b_audit)
    ambiguous = [row for row in migrated if row.get("migration_confidence") == "ambiguous"]
    write_jsonl(ROOT / "STAGED_CORPUS_V0_MIGRATED_PRELIM.jsonl", migrated)
    write_json(ROOT / "STAGED_MIGRATION_REPORT_R1.json", migration_report(migrated))
    write_jsonl(ROOT / "STAGED_AMBIGUOUS_MIGRATION_ROWS.jsonl", ambiguous)
    write_jsonl(ROOT / "STAGED_PREDICTED_HARD_SAMPLE_SEED.jsonl", ambiguous[:80])

    topup = write_topup_protocol()
    sample = select_blind_sample(migrated, v04b_audit, target=72)
    write_jsonl(ROOT / "CORPUS_V0_STAGED_DOUBLE_LABEL_BLIND_SAMPLE.jsonl", sample)
    write_staged_instructions()
    sample_meta = sample_report(sample, migrated)
    write_json(ROOT / "CORPUS_V0_STAGED_DOUBLE_LABEL_SAMPLE_REPORT.json", sample_meta)
    cold_probe = write_cold_probe(sample)

    parse_audit = json_parse_audit()
    secret = secret_audit()
    write_json(ROOT / "JSON_PARSE_AUDIT.json", parse_audit)
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)
    write_json(
        ROOT / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "real_operator_validation_claimed": False,
            "router_training_opened": False,
            "split_seal_r3_run": False,
            "production_claim_made": False,
        },
    )
    write_json(
        ROOT / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS",
            "scope": "new staged-router output root and runner only",
            "prior_outputs_mutated": False,
            "split_seal_r3_run": False,
        },
    )

    decision = {
        "task": TASK,
        "status": STATUS,
        "generated_at": now(),
        "input_root": rel(V04B_ROOT),
        "output_root": rel(ROOT),
        "v04b_flat_route_failure_consumed": True,
        "staged_schema_contract_created": True,
        "stage_a_vocab": STAGE_A,
        "stage_b_vocab": STAGE_B,
        "stage_c_vocab": STAGE_C,
        "stage_d_vocab": STAGE_D,
        "rows_migrated": len(migrated),
        "ambiguous_migration_rows": len(ambiguous),
        "blind_sample_rows": len(sample),
        "blind_sample_stage_field_leaks": len(sample_meta["codex_label_or_stage_field_leaks"]),
        "hard_topup_status": topup["status"],
        "cold_labeler_probe_ready": cold_probe["status"],
        "json_parse_audit": parse_audit["status"],
        "secret_audit": secret["status"],
        "split_seal_r3": "NOT_RUN",
        "router_preflight": "NOT_OPENED",
        "router_training": "NOT_OPENED",
        "real_operator_validation_claimed": False,
        "next_required_file": rel(ROOT / "CORPUS_V0_STAGED_DOUBLE_LABEL_INDEPENDENT_LABELS.jsonl"),
    }
    write_json(ROOT / "D14_STAGED_ROUTER_SCHEMA_CLOSEOUT_DECISION.json", decision)
    write_local_index()
    package_outputs()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
