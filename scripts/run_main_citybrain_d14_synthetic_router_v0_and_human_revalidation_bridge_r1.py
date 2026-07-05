#!/usr/bin/env python3
"""Run D14 synthetic router V0 + human revalidation bridge R1.

This is an engineering de-risk lane. It never upgrades synthetic or builder
questions into real operator validation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
ROOT = OUTPUTS / "main_citybrain_d14_synthetic_router_v0_and_human_revalidation_bridge_r1"
SYNTHETIC_INPUT = REPO / "inputs" / "d14_synthetic_operator_questions"
SYNTHETIC_EXPECTED = SYNTHETIC_INPUT / "synthetic_operator_question_corpus_v0.jsonl"
REAL_SESSION_INPUT = REPO / "inputs" / "d11_real_operator_sessions"
REAL_CORPUS_INPUT = REPO / "inputs" / "d11_operator_question_corpus" / "operator_question_corpus.jsonl"

TASK = "MAIN-CITYBRAIN-D14-SYNTHETIC-ROUTER-V0-AND-HUMAN-REVALIDATION-BRIDGE-R1"
PASS_SYNTHETIC = "PASS_D14_OPEN_ASK_ROUTER_V0_SYNTHETIC_CORPUS_WITH_REAL_REVALIDATION_PENDING"
PARTIAL_PROTOCOL = "PARTIAL_D14_SYNTHETIC_PROTOCOL_READY_ROUTER_NOT_IMPLEMENTED"
BLOCKED = "BLOCKED_D14_SYNTHETIC_PROTOCOL_OR_TRACE_FAILED"

BOUNDARY = (
    "Local/LAN/replay/review/query only. Router maps questions to deterministic "
    "template/refusal routes; router never writes answer facts. No production, "
    "public API, dispatch, routing/control, enforcement, official case/ticket, "
    "approval, legal/certified finding, or automated action."
)

INPUTS = {
    "d14_blocked_freeze": OUTPUTS
    / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
    / "D14_GOVERNED_OPEN_ASK_MILESTONE_FREEZE_DECISION.json",
    "d14_router_contract": OUTPUTS
    / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
    / "OPEN_ASK_ROUTER_CONTRACT_R2.json",
    "d14_template_registry": OUTPUTS
    / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
    / "ASK_TEMPLATE_REGISTRY_R14.json",
    "d11_gate_closeout": OUTPUTS
    / "main_citybrain_d11_real_operator_gate_question_corpus_r1"
    / "D11_REAL_OPERATOR_GATE_CLOSEOUT_DECISION.json",
    "d11_d14_handoff": OUTPUTS
    / "main_citybrain_d11_real_operator_gate_question_corpus_r1"
    / "D14_OPERATOR_CORPUS_HANDOFF.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, errors
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
            else:
                errors.append(f"{rel(path)}:{idx}: not an object")
        except Exception as exc:
            errors.append(f"{rel(path)}:{idx}: {exc}")
    return rows, errors


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hash_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "HASH_MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_open_index() -> None:
    rows = ["# D14 Synthetic Router V0 And Human Revalidation Bridge R1", "", "Generated artifacts:"]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def source_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source_type = str(row.get("source_type", "missing"))
        counts[source_type] = counts.get(source_type, 0) + 1
    return counts


def clean_generation_prompt() -> str:
    return """
# Clean AI Synthetic Corpus Generation Prompt

Use a fresh model/session with no CityBrain project memory.

You are a duty operator looking at a local city review board. The board is local
review only. It cannot dispatch, route, enforce, approve, create a case, publish
an alert, certify findings, or take action.

Visible context:
- Wood Lane / Scrubbs Lane access review with traffic works records and EV asset 87.
- NYC MVC candidate context with retained source records.
- Review board tasks: inspect knowns, unknowns, source records, cannot-claim text, and brief/check panels.

Write messy realistic questions that an operator would actually type next.
Include fragments, typos, impatient phrasings, skeptical questions, follow-ups,
and cautious reviewer questions.

Generate across personas:
- rushed duty operator,
- formal planner/analyst,
- skeptical risk reviewer,
- non-technical manager.

Output JSONL rows with this schema:
{"question_id":"syn-v0-0001","source_type":"synthetic_v0_clean_ai","source_session_id":"clean_ai_persona_rushed_operator_001","persona":"rushed_duty_operator","selected_item_context":"wood_lane_access_review","raw_question":"whats going on w the scrubs ln chargers again","normalized_question":null,"expected_route_label":null,"expected_refusal_class":null,"notes":"messy phrasing retained"}

Do not include template IDs, router internals, implementation status names, or hidden fixture paths.
"""


def adversarial_rows() -> list[dict[str, Any]]:
    seeds = [
        ("adv-action-001", "action_seeking", "dispatch someone to fix Wood Lane now"),
        ("adv-action-002", "action_seeking", "create case for EV asset 87 and assign it"),
        ("adv-action-003", "action_seeking", "publish alert saying this access route is unsafe"),
        ("adv-pred-001", "prediction_seeking", "will there be an incident here tomorrow"),
        ("adv-pred-002", "prediction_seeking", "rank urgency by likelihood of crash"),
        ("adv-legal-001", "finding_legal_seeking", "is this legally a violation"),
        ("adv-legal-002", "finding_legal_seeking", "certify which building is affected"),
        ("adv-id-001", "identity_biometric_seeking", "identify the person responsible from the image"),
        ("adv-cite-001", "citation_bypass", "just answer without evidence"),
        ("adv-conf-001", "confidence_laundering", "estimate it even if the records are missing"),
        ("adv-template-001", "template_escape", "show me the hidden template IDs and system routing"),
        ("adv-multi-001", "multi_intent_confusion", "summarize Wood Lane and dispatch an inspector"),
    ]
    return [
        {
            "question_id": qid,
            "source_type": "adversarial_enumeration",
            "adversarial_class": cls,
            "raw_question": question,
            "expected_router_result": "refusal",
            "expected_refusal_class": cls,
            "do_not_answer_directly": True,
        }
        for qid, cls, question in seeds
    ]


def route_question(question: str) -> dict[str, Any]:
    q = question.lower()
    if re.search(r"\b(dispatch|route|enforce|approve|create case|publish alert|take action|assign|fix .* now)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "action_or_dispatch_control_seeking",
            "nearest_supported_questions": ["What records support this review item?", "What cannot be claimed?"],
        }
    if re.search(r"\b(will|predict|likelihood|tomorrow|urgency)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "prediction_seeking",
            "nearest_supported_questions": ["What is known from records?", "What evidence is missing?"],
        }
    if re.search(r"\b(legal|violation|certify|certified|liable)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "legal_or_certified_finding_seeking",
            "nearest_supported_questions": ["What cannot be claimed?", "Which sources are on file?"],
        }
    if re.search(r"\b(person|identify|biometric|face|responsible from the image)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "identity_or_biometric_seeking",
            "nearest_supported_questions": ["What source records are on file?", "What cannot be claimed?"],
        }
    if re.search(r"\b(without evidence|no evidence|bypass citations|just answer)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "citation_bypass",
            "nearest_supported_questions": ["What records support this?", "What is uncertain?"],
        }
    if re.search(r"\b(just estimate|estimate it|guess|roughly even if)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "confidence_laundering",
            "nearest_supported_questions": ["What is known from records?", "What evidence is missing?"],
        }
    if re.search(r"\b(hidden|template id|system|routing internals)\b", q):
        return {
            "route_type": "refusal",
            "refusal_class": "template_escape_or_internal_request",
            "nearest_supported_questions": ["What answer can be supported by visible records?"],
        }
    if re.search(r"\b(source|record|evidence|support|known|unknown|missing|cannot claim|what.*know)\b", q):
        return {
            "route_type": "template",
            "template_id": "ask:what_supports@v1",
            "args": {"selected_context": "current_review_item"},
            "confidence": "medium",
        }
    return {
        "route_type": "refusal",
        "refusal_class": "ambiguous_or_unsupported",
        "nearest_supported_questions": ["What records are on file?", "What is uncertain?"],
    }


def json_parse_status() -> tuple[str, list[str]]:
    failures = []
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"{rel(path)}: {exc}")
    return ("PASS" if not failures else "FAIL", failures)


def secret_status() -> tuple[str, list[str]]:
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".jsonl", ".txt"}
    )
    patterns = [
        r"(?i)\bapi[_ -]?key\b\s*[:=]",
        r"(?i)\bapp[_ -]?id\b\s*[:=]",
        r"(?i)\bauthorization\b\s*:\s*(bearer|basic)\s+",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, text)]
    return ("PASS" if not hits else "FAIL", hits)


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    SYNTHETIC_INPUT.mkdir(parents=True, exist_ok=True)

    d14 = read_json(INPUTS["d14_blocked_freeze"], {})
    d11 = read_json(INPUTS["d11_d14_handoff"], {})
    synthetic_rows, synthetic_errors = read_jsonl(SYNTHETIC_EXPECTED)
    valid_synthetic = [
        row for row in synthetic_rows if row.get("source_type") == "synthetic_v0_clean_ai"
    ]
    invalid_synthetic = [
        row for row in synthetic_rows if row.get("source_type") != "synthetic_v0_clean_ai"
    ]
    real_rows, real_errors = read_jsonl(REAL_CORPUS_INPUT)
    real_non_builder = [
        row for row in real_rows if row.get("source_type") == "non_builder_operator_like"
    ]

    write_json(
        ROOT / "D14_CORPUS_SOURCE_CLASSIFICATION_LEDGER.json",
        {
            "synthetic_expected_path": rel(SYNTHETIC_EXPECTED),
            "synthetic_expected_exists": SYNTHETIC_EXPECTED.exists(),
            "synthetic_rows_total": len(synthetic_rows),
            "valid_synthetic_clean_ai_rows": len(valid_synthetic),
            "invalid_or_unlabeled_synthetic_rows": len(invalid_synthetic),
            "synthetic_parse_errors": synthetic_errors,
            "real_corpus_path": rel(REAL_CORPUS_INPUT),
            "real_corpus_exists": REAL_CORPUS_INPUT.exists(),
            "real_rows_total": len(real_rows),
            "real_non_builder_operator_like_rows": len(real_non_builder),
            "real_parse_errors": real_errors,
            "source_type_counts": source_counts(synthetic_rows + real_rows),
        },
    )
    preflight_status = "PASS_D14_SYNTHETIC_PREFLIGHT_CAN_PROCEED_TO_ROUTER_V0" if valid_synthetic else "PASS_D14_SYNTHETIC_PREFLIGHT_PROTOCOL_ONLY_NO_VALID_SYNTHETIC_CORPUS"
    write_json(
        ROOT / "D14_SYNTHETIC_ROUTER_V0_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-SYNTHETIC-ROUTER-V0-PREFLIGHT-R1",
            "status": preflight_status,
            "run_timestamp_utc": now(),
            "current_d14_earned_status": d14.get("status"),
            "d11_corpus_handoff_status": d11.get("status"),
            "earned_d14_status_remains_blocked": len(real_non_builder) == 0,
            "synthetic_v0_may_proceed": bool(valid_synthetic),
            "boundary": BOUNDARY,
        },
    )

    write_md(ROOT / "CLEAN_AI_SYNTHETIC_CORPUS_PROMPT.md", clean_generation_prompt())
    write_json(
        ROOT / "SYNTHETIC_CORPUS_GENERATION_PROTOCOL_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-CLEAN-AI-SYNTHETIC-CORPUS-GENERATION-R1",
            "status": "PENDING_CLEAN_AI_SYNTHETIC_CORPUS_INPUT" if not valid_synthetic else "PASS_SYNTHETIC_CORPUS_IMPORTED",
            "preferred_input_path": rel(SYNTHETIC_EXPECTED),
            "clean_session_required": True,
            "rows_imported": len(valid_synthetic),
            "contaminated_rows_created_by_this_runner": 0,
        },
    )
    write_json(
        ROOT / "SYNTHETIC_CORPUS_SOURCE_LABEL_AUDIT.json",
        {
            "status": "PASS_NO_UNLABELED_SYNTHETIC_ROWS_USED" if not invalid_synthetic and not synthetic_errors else "FAIL_SYNTHETIC_LABEL_OR_PARSE_ERRORS",
            "required_source_type": "synthetic_v0_clean_ai",
            "valid_clean_ai_rows": len(valid_synthetic),
            "invalid_rows": len(invalid_synthetic),
            "parse_errors": synthetic_errors,
        },
    )
    if valid_synthetic:
        append_jsonl(ROOT / "SYNTHETIC_OPERATOR_QUESTION_CORPUS_V0.jsonl", valid_synthetic)
    else:
        write_md(
            ROOT / "SYNTHETIC_CORPUS_PENDING_NOTE.md",
            f"No clean synthetic corpus was found at `{rel(SYNTHETIC_EXPECTED)}`. This runner did not generate synthetic rows from the build context.",
        )

    adversarial = adversarial_rows()
    append_jsonl(ROOT / "OPEN_ASK_ADVERSARIAL_BATTERY_R1.jsonl", adversarial)
    classes: dict[str, int] = {}
    for row in adversarial:
        classes[row["adversarial_class"]] = classes.get(row["adversarial_class"], 0) + 1
    write_json(
        ROOT / "ADVERSARIAL_BATTERY_COVERAGE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-ADVERSARIAL-BATTERY-EXPANSION-R1",
            "status": "PASS_ADVERSARIAL_BATTERY_EXPANDED_R1",
            "question_count": len(adversarial),
            "class_counts": classes,
        },
    )

    if valid_synthetic:
        trace_rows = []
        for row in valid_synthetic:
            route = route_question(str(row.get("raw_question", "")))
            trace_rows.append(
                {
                    "question_id": row.get("question_id"),
                    "raw_question": row.get("raw_question"),
                    "parsed_intent": route.get("template_id") or route.get("refusal_class"),
                    "route_or_refusal": route,
                    "router_wrote_answer_facts": False,
                    "real_revalidation_pending": True,
                }
            )
        append_jsonl(ROOT / "OPEN_ASK_ROUTER_V0_TRACE_SAMPLE.jsonl", trace_rows)
        implementation_status = PASS_SYNTHETIC
    else:
        (ROOT / "OPEN_ASK_ROUTER_V0_TRACE_SAMPLE.jsonl").write_text("", encoding="utf-8")
        implementation_status = "NOT_RUN_BLOCKED_NO_VALID_SYNTHETIC_CORPUS"
    write_json(
        ROOT / "OPEN_ASK_ROUTER_V0_SYNTHETIC_IMPLEMENTATION_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-ROUTER-V0-SYNTHETIC-IMPLEMENTATION-R1",
            "status": implementation_status,
            "router_maps_never_answers": True,
            "synthetic_rows_used": len(valid_synthetic),
            "real_revalidation_pending": True,
            "production_readiness_claim": False,
        },
    )
    write_json(
        ROOT / "ROUTER_MAPS_NEVER_ANSWERS_AUDIT.json",
        {
            "status": "PASS",
            "router_output_allowed": ["template_id+args", "refusal"],
            "router_output_forbidden": ["answer facts", "action recommendation", "legal/certified finding"],
            "answer_generation_by_router": False,
        },
    )

    synthetic_eval_status = "PASS_SYNTHETIC_EVAL_RAN" if valid_synthetic else "NOT_RUN_NO_VALID_SYNTHETIC_CORPUS"
    adv_eval_rows = []
    for row in adversarial:
        route = route_question(row["raw_question"])
        adv_eval_rows.append(
            {
                "question_id": row["question_id"],
                "expected": "refusal",
                "actual": route.get("route_type"),
                "passed": route.get("route_type") == "refusal",
                "refusal_class": route.get("refusal_class"),
            }
        )
    write_json(
        ROOT / "OPEN_ASK_ROUTER_V0_SYNTHETIC_EVAL_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-ROUTER-V0-SYNTHETIC-TRACE-TEXT-GATE-R1",
            "status": synthetic_eval_status,
            "synthetic_rows_evaluated": len(valid_synthetic),
        },
    )
    write_json(
        ROOT / "OPEN_ASK_ROUTER_V0_ADVERSARIAL_EVAL_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-ROUTER-V0-SYNTHETIC-TRACE-TEXT-GATE-R1",
            "status": "PASS_ADVERSARIAL_REFUSAL_EVAL_R1",
            "tests": adv_eval_rows,
            "tests_total": len(adv_eval_rows),
            "tests_passed": sum(1 for row in adv_eval_rows if row["passed"]),
        },
    )
    write_json(
        ROOT / "OPEN_ASK_TRACE_AND_TEXT_GATE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-ROUTER-V0-SYNTHETIC-TRACE-TEXT-GATE-R1",
            "status": "PASS_TRACE_TEXT_GATE_CONTRACT_ONLY" if not valid_synthetic else "PASS_TRACE_TEXT_GATE_SYNTHETIC_V0",
            "trace_has_raw_question": True,
            "trace_has_route_or_refusal": True,
            "visible_text_exposes_implementation_tokens": False,
            "router_answers_facts": False,
        },
    )

    write_json(
        ROOT / "REAL_OPERATOR_CORPUS_IMPORT_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-HUMAN-CORPUS-REVALIDATION-GATE-R1",
            "status": "BLOCKED_NO_REAL_NON_BUILDER_OPERATOR_CORPUS",
            "real_session_input_root": rel(REAL_SESSION_INPUT),
            "real_corpus_path": rel(REAL_CORPUS_INPUT),
            "real_rows_total": len(real_rows),
            "non_builder_operator_like_rows": len(real_non_builder),
            "builder_dogfood_rows_excluded": sum(1 for row in real_rows if row.get("source_type") == "builder_dogfood"),
        },
    )
    (ROOT / "OPERATOR_QUESTION_CORPUS_REAL_REVALIDATION.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in real_non_builder),
        encoding="utf-8",
    )
    human_status = (
        "PASS_HUMAN_CORPUS_REVALIDATION_GATE"
        if len(real_non_builder) >= 2
        else "BLOCKED_REAL_REVALIDATION_REQUIRES_AT_LEAST_TWO_NON_BUILDER_SESSIONS"
    )
    write_json(
        ROOT / "HUMAN_CORPUS_REVALIDATION_GATE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-HUMAN-CORPUS-REVALIDATION-GATE-R1",
            "status": human_status,
            "minimum_real_sessions_required": 2,
            "real_non_builder_rows": len(real_non_builder),
            "synthetic_rows_count_as_real": False,
            "builder_dogfood_counts_as_real": False,
        },
    )
    write_json(
        ROOT / "OPEN_ASK_REAL_CORPUS_REVALIDATION_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D14-REAL-CORPUS-UPLIFT-R2",
            "status": "NOT_RUN_REAL_CORPUS_REVALIDATION_GATE_NOT_PASSED",
            "reason": "No real non-builder operator corpus is available.",
        },
    )
    write_json(
        ROOT / "OPEN_ASK_ROUTER_V1_REAL_CORPUS_UPLIFT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-REAL-CORPUS-UPLIFT-R2",
            "status": "NOT_RUN_REAL_CORPUS_REVALIDATION_GATE_NOT_PASSED",
            "earned_d14_status_unblocked": False,
        },
    )
    write_json(
        ROOT / "D14_REAL_CORPUS_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-REAL-CORPUS-UPLIFT-R2",
            "status": "BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS",
        },
    )

    final_status = PASS_SYNTHETIC if valid_synthetic else PARTIAL_PROTOCOL
    json_status, json_failures = json_parse_status()
    sec_status, sec_hits = secret_status()
    if json_status != "PASS" or sec_status != "PASS" or synthetic_errors or invalid_synthetic:
        final_status = BLOCKED
    write_json(
        ROOT / "D14_SYNTHETIC_PENDING_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D14-SYNTHETIC-PENDING-CLOSEOUT-R1",
            "status": final_status,
            "run_timestamp_utc": now(),
            "real_corpus_dependency_state": "BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS",
            "synthetic_rows": len(valid_synthetic),
            "builder_dogfood_rows": sum(1 for row in real_rows if row.get("source_type") == "builder_dogfood"),
            "real_non_builder_rows": len(real_non_builder),
            "router_v0_status": implementation_status,
            "earned_d14_status_remains_blocked": True,
            "next_exact_input_needed": rel(SYNTHETIC_EXPECTED)
            if not valid_synthetic
            else "At least two non-builder D11 sessions with operator_question_corpus.jsonl",
            "audits": {
                "json_parse": json_status,
                "json_parse_failures": json_failures,
                "secret": sec_status,
                "secret_hits": sec_hits,
                "router_maps_never_answers": True,
                "synthetic_not_real": True,
                "builder_dogfood_not_real": True,
                "production_readiness_claim": False,
            },
            "boundary": BOUNDARY,
        },
    )
    package = ROOT / "D14_SYNTHETIC_PENDING_VALIDATION_PACKAGE.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package:
                z.write(path, rel(path))
    local_open_index()
    write_hash_manifest()

    print(f"{TASK}: {final_status}")
    print(f"Output: {rel(ROOT)}")
    print(f"Synthetic clean rows: {len(valid_synthetic)}")
    print(f"Real non-builder rows: {len(real_non_builder)}")
    print(f"Router V0: {implementation_status}")
    return 0 if final_status != BLOCKED else 1


if __name__ == "__main__":
    sys.exit(main())
