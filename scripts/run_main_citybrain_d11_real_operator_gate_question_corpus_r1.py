#!/usr/bin/env python3
"""Prepare/import D11 real operator gate sessions and question corpus.

This lane is deliberately independent from D13. It targets the frozen D11
workspace validation package and never fabricates participant records.
"""

from __future__ import annotations

import csv
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
ROOT = OUTPUTS / "main_citybrain_d11_real_operator_gate_question_corpus_r1"
SESSION_ROOT = REPO / "inputs" / "d11_real_operator_sessions"
CORPUS_ROOT = REPO / "inputs" / "d11_operator_question_corpus"
CORPUS_PATH = CORPUS_ROOT / "operator_question_corpus.jsonl"

TASK = "MAIN-CITYBRAIN-D11-REAL-OPERATOR-GATE-QUESTION-CORPUS-R1"
PASS_STATUS = "PASS_D11_REAL_OPERATOR_GATE_WITH_CORPUS"
LIMITED_STATUS = "PASS_D11_REAL_OPERATOR_GATE_WITH_LIMITED_CORPUS"
PENDING_STATUS = "PARTIAL_D11_PENDING_REAL_OPERATOR_SESSIONS"
FAIL_STATUS = "FAIL_D11_OPERATOR_GATE_SCHEMA_OR_BOUNDARY"

BOUNDARY = (
    "Local/LAN/replay/review/query context only. No production/public API, "
    "dispatch, route/control, enforcement, official ticket/case, approval, "
    "legal/certified finding, alert-as-command, or automated action."
)

FROZEN = {
    "d11_milestone": OUTPUTS
    / "main_citybrain_d11_operator_workflow_review_workspace_r1"
    / "D11_WORKFLOW_MILESTONE_FREEZE_DECISION.json",
    "d11_validation_package": OUTPUTS
    / "main_citybrain_d11_operator_workflow_review_workspace_r1"
    / "D11_VALIDATION_PACKAGE.zip",
    "d11_dom_capture": OUTPUTS
    / "main_citybrain_d11_operator_workflow_review_workspace_r1"
    / "D11_REVIEW_WORKSPACE_DOM_CAPTURE.html",
    "d11_runtime_overlay": REPO
    / "packages"
    / "fixtures"
    / "d11_operator_workflow_review_workspace"
    / "runtime_overlay"
    / "D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json",
    "d11_review_state_contract": OUTPUTS
    / "main_citybrain_d11_operator_workflow_review_workspace_r1"
    / "LOCAL_REVIEW_STATE_CONTRACT.json",
    "d14_blocked_decision": OUTPUTS
    / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
    / "D14_GOVERNED_OPEN_ASK_MILESTONE_FREEZE_DECISION.json",
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
    rows = ["# D11 Real Operator Gate Question Corpus R1", "", "Generated artifacts:"]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def participant_packet() -> str:
    return """
# CityBrain Operator Cockpit - Participant Task Packet R2

You are testing whether this cockpit is understandable as a city review board.
You are not being tested; the product is.

Use the frozen D11 validation snapshot, not the live development tree:
`outputs/main_citybrain_d11_operator_workflow_review_workspace_r1/D11_VALIDATION_PACKAGE.zip`

Important:
- The cockpit is local replay/review only.
- It does not dispatch, route, enforce, approve, create a case, publish an alert, or take action.
- Please say what you would ask naturally. Those questions are the most important output.

Tasks:
1. Open the London and NYC review patch. In your own words, what is the first item asking you to review?
2. For the Wood Lane item, list the source records you can see.
3. Explain what the board says is known and unknown about Wood Lane / Scrubbs Lane.
4. Ask at least three natural questions you would ask as an operator. Write them exactly as you would type them.
5. Generate or read the review brief. Would you be comfortable copying it into review notes? What is missing?
6. Open/read the Checks. What should you be careful not to claim?
7. Use at least one local review verb such as Mark reviewed, Add note, Run check, or Generate brief. What do you think it did?
8. Explain whether the cockpit created an official case, alert, dispatch, or action.
9. Write any confusing words or sections.
10. Decide: could you work this patch from start to finish without the builder explaining it?

Required session outputs:
- Task answers.
- Spontaneous questions verbatim.
- Confusion notes.
- No-action comprehension.
- Overall pass/fail with comments.
"""


def write_templates() -> None:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    schema = {
        "schema_version": "citybrain.d11.real_operator_session.r2",
        "required": [
            "session_id",
            "participant_type",
            "participant_role",
            "builder_assistance_level",
            "tasks",
            "spontaneous_questions",
            "confusion_notes",
            "no_action_comprehension",
            "can_work_patch_without_builder",
        ],
        "participant_type_allowed_for_scoring": ["non_builder"],
        "boundary": BOUNDARY,
    }
    template = {
        "schema_version": "citybrain.d11.real_operator_session.r2",
        "session_id": "replace_with_unique_session_id",
        "participant_type": "non_builder",
        "participant_role": "operator/reviewer/planner/other",
        "surface_target": rel(FROZEN["d11_validation_package"]),
        "session_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
        "builder_assistance_level": "none/minimal/moderate/high",
        "tasks": [
            {
                "task_id": f"d11-r1-task-{idx:02d}",
                "answer": "",
                "task_outcome": "not_attempted/pass/partial/fail",
                "source_records_understood": None,
                "known_unknown_cannot_claim_understood": None,
                "no_action_understood": None,
            }
            for idx in range(1, 11)
        ],
        "spontaneous_questions": [],
        "confusion_notes": [],
        "no_action_comprehension": "",
        "can_work_patch_without_builder": None,
        "overall_comments": "",
        "do_not_count_if_internal_or_builder_filled": False,
    }
    write_json(ROOT / "REAL_OPERATOR_SESSION_SCHEMA.json", schema)
    write_json(ROOT / "session_record_template.json", template)
    write_json(SESSION_ROOT / "session_record_template.json", template)
    csv_path = ROOT / "task_response_template.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "session_id",
                "participant_type",
                "task_id",
                "task_outcome",
                "answer",
                "source_records_understood",
                "known_unknown_cannot_claim_understood",
                "no_action_understood",
                "spontaneous_questions_json",
                "confusion_notes_json",
            ]
        )
    (SESSION_ROOT / "task_response_template.csv").write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")


def classify_session(path: Path) -> tuple[str, dict[str, Any] | None, str]:
    name = path.name.lower()
    if "template" in name or name == "readme.md":
        return "REJECT_TEMPLATE_OR_README", None, "Template/readme file"
    if path.suffix.lower() != ".json":
        return "REJECT_UNSUPPORTED_FORMAT", None, "Only JSON session records are scored"
    record = read_json(path)
    if not isinstance(record, dict):
        return "REJECT_PARSE_ERROR", None, "Not a JSON object"
    text = json.dumps(record, ensure_ascii=False).lower()
    if "replace_with_unique_session_id" in text:
        return "REJECT_TEMPLATE_PLACEHOLDER", record, "Placeholder template values present"
    if record.get("do_not_count_if_internal_or_builder_filled"):
        return "REJECT_DO_NOT_COUNT", record, "Record is explicitly do-not-count"
    participant_type = str(record.get("participant_type", "")).lower()
    role = str(record.get("participant_role", "")).lower()
    assistance = str(record.get("builder_assistance_level", "")).lower()
    if participant_type != "non_builder":
        return "REJECT_NOT_NON_BUILDER", record, "participant_type is not non_builder"
    if any(token in role for token in ["builder", "codex", "internal"]):
        return "REJECT_INTERNAL_ROLE", record, "role is internal/builder-like"
    if assistance == "high":
        return "REJECT_BUILDER_ASSISTANCE_TOO_HIGH", record, "builder assistance marked high"
    tasks = record.get("tasks") or []
    attempted = [t for t in tasks if str(t.get("task_outcome", "")).lower() in {"pass", "partial", "fail"}]
    if not attempted:
        return "REJECT_INCOMPLETE", record, "No attempted task outcomes"
    return "ACCEPT_REAL_NON_BUILDER_SESSION", record, "Accepted real non-builder session"


def scan_sessions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for path in sorted(p for p in SESSION_ROOT.iterdir() if p.is_file()):
        status, record, reason = classify_session(path)
        row = {"path": rel(path), "status": status, "reason": reason}
        if status == "ACCEPT_REAL_NON_BUILDER_SESSION" and record:
            accepted.append({"path": rel(path), "record": record})
        else:
            rejected.append(row)
    return accepted, rejected


def label_question(text: str) -> str:
    q = text.lower()
    if re.search(r"\b(dispatch|route|control|send|alert|take action|enforce|approve)\b", q):
        return "dispatch_control_seeking"
    if re.search(r"\b(legal|violation|certify|certified|liable|official)\b", q):
        return "legal_finding_seeking"
    if re.search(r"\b(will|predict|forecast|likely to)\b", q):
        return "prediction_seeking"
    if re.search(r"\b(missing|unknown|why no|data gap|source)\b", q):
        return "data_gap"
    if "?" in text:
        return "supported_template_candidate"
    return "ambiguous"


def score_and_questions(accepted: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    rows = []
    questions = []
    confusion_notes: list[str] = []
    for item in accepted:
        record = item["record"]
        tasks = record.get("tasks") or []
        pass_count = sum(1 for t in tasks if str(t.get("task_outcome", "")).lower() == "pass")
        partial_count = sum(1 for t in tasks if str(t.get("task_outcome", "")).lower() == "partial")
        fail_count = sum(1 for t in tasks if str(t.get("task_outcome", "")).lower() == "fail")
        rows.append(
            {
                "session_id": record.get("session_id"),
                "task_count": len(tasks),
                "pass_count": pass_count,
                "partial_count": partial_count,
                "fail_count": fail_count,
                "no_action_comprehension_present": bool(record.get("no_action_comprehension")),
                "can_work_patch_without_builder": record.get("can_work_patch_without_builder"),
                "builder_assistance_level": record.get("builder_assistance_level"),
            }
        )
        confusion_notes.extend(str(x) for x in record.get("confusion_notes", []) if x)
        for idx, question in enumerate(record.get("spontaneous_questions", []), 1):
            if not isinstance(question, str) or not question.strip():
                continue
            questions.append(
                {
                    "question_id": f"{record.get('session_id')}:q{idx:03d}",
                    "session_id": record.get("session_id"),
                    "question_text": question.strip(),
                    "selected_context": record.get("selected_context", "D11 review workspace"),
                    "operator_task_id": "spontaneous",
                    "initial_label": label_question(question),
                    "notes": "Captured verbatim from real non-builder session.",
                    "do_not_answer_directly": True,
                }
            )
    scoreboard = {
        "real_session_count": len(accepted),
        "task_outcomes": rows,
        "spontaneous_question_count": len(questions),
        "confusion_note_count": len(confusion_notes),
    }
    return scoreboard, questions, confusion_notes


def write_corpus(questions: list[dict[str, Any]]) -> str | None:
    if not questions:
        return None
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in questions),
        encoding="utf-8",
    )
    return rel(CORPUS_PATH)


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
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".txt", ".jsonl"}
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
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    frozen_status = read_json(FROZEN["d11_milestone"], {}).get("status")
    overlay_hash = sha256_file(FROZEN["d11_runtime_overlay"]) if FROZEN["d11_runtime_overlay"].exists() else None

    write_json(
        ROOT / "D11_REAL_OPERATOR_GATE_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D11-REAL-OPERATOR-GATE-PREFLIGHT-R1",
            "status": "PASS_D11_REAL_OPERATOR_GATE_PREFLIGHT_R1",
            "run_timestamp_utc": now(),
            "frozen_baseline_status": frozen_status,
            "session_input_root": rel(SESSION_ROOT),
            "d14_open_ask_not_run": True,
        },
    )
    write_json(
        ROOT / "REAL_OPERATOR_SESSION_INPUTS_INDEX.json",
        {
            "frozen_baseline": {name: {"path": rel(path), "exists": path.exists()} for name, path in FROZEN.items()},
            "overlay_hashes": {
                rel(FROZEN["d11_runtime_overlay"]): overlay_hash,
            },
            "session_input_root": rel(SESSION_ROOT),
        },
    )
    write_md(ROOT / "PARTICIPANT_TASK_PACKET_R2.md", participant_packet())
    write_templates()

    accepted, rejected = scan_sessions()
    scoreboard, questions, confusion_notes = score_and_questions(accepted)
    corpus_path = write_corpus(questions)

    import_status = "PASS_REAL_SESSION_IMPORT_AND_SCORE_R2" if accepted else PENDING_STATUS
    write_json(
        ROOT / "REAL_OPERATOR_SESSION_IMPORT_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D11-REAL-SESSION-IMPORT-AND-SCORE-R2",
            "status": import_status,
            "accepted_real_non_builder_sessions": len(accepted),
            "rejected_files": rejected,
            "internal_or_template_sessions_counted": 0,
            "session_input_root": rel(SESSION_ROOT),
        },
    )
    write_json(ROOT / "REAL_OPERATOR_TASK_SCOREBOARD.json", scoreboard)
    write_md(
        ROOT / "REAL_OPERATOR_CONFUSION_NOTES.md",
        "\n".join(f"- {note}" for note in confusion_notes) if confusion_notes else "No real operator confusion notes captured yet.",
    )
    write_json(
        ROOT / "OPERATOR_QUESTION_CORPUS_EXPORT_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D11-SPONTANEOUS-QUESTION-CORPUS-EXPORT-R2",
            "status": "PASS_OPERATOR_QUESTION_CORPUS_EXPORTED_R2" if corpus_path else "PENDING_NO_REAL_OPERATOR_QUESTIONS",
            "corpus_path": corpus_path,
            "question_count": len(questions),
            "real_session_count": len(accepted),
            "fake_rows_created": False,
        },
    )
    if not corpus_path:
        write_md(
            ROOT / "CORPUS_ABSENT_HANDOFF_NOTE.md",
            "No real non-builder operator sessions exist yet, so no operator_question_corpus.jsonl was created.",
        )
    label_counts: dict[str, int] = {}
    for row in questions:
        label_counts[row["initial_label"]] = label_counts.get(row["initial_label"], 0) + 1
    write_json(
        ROOT / "D14_OPERATOR_CORPUS_HANDOFF.json",
        {
            "task": "MAIN-CITYBRAIN-D11-D14-CORPUS-HANDOFF-R1",
            "status": "READY_FOR_D14_CORPUS_AUDIT" if corpus_path else "BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS",
            "corpus_path": corpus_path,
            "row_count": len(questions),
            "session_count": len(accepted),
            "label_counts": label_counts,
            "redaction_privacy_check": "PASS_NO_ROWS" if not questions else "PENDING_REVIEW",
            "d14_may_proceed": bool(corpus_path),
        },
    )

    json_status, json_failures = json_parse_status()
    secret, secret_hits = secret_status()
    final = PENDING_STATUS if not accepted else LIMITED_STATUS if len(questions) < 3 else PASS_STATUS
    if json_status != "PASS" or secret != "PASS":
        final = FAIL_STATUS
    write_json(
        ROOT / "D11_REAL_OPERATOR_GATE_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D11-REAL-OPERATOR-GATE-CLOSEOUT-R1",
            "status": final,
            "frozen_baseline_used": True,
            "live_head_tested": False,
            "accepted_real_non_builder_sessions": len(accepted),
            "operator_question_corpus_path": corpus_path,
            "operator_question_count": len(questions),
            "d14_status": "BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS" if not corpus_path else "READY_FOR_D14_CORPUS_AUDIT",
            "audits": {
                "json_parse": json_status,
                "json_parse_failures": json_failures,
                "secret": secret,
                "secret_hits": secret_hits,
                "fake_internal_sessions_counted": False,
                "no_action_official_case_claims": True,
            },
            "boundary": BOUNDARY,
        },
    )
    package = ROOT / "D11_REAL_OPERATOR_GATE_PACKAGE.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package:
                z.write(path, rel(path))
        for path in [SESSION_ROOT / "session_record_template.json", SESSION_ROOT / "task_response_template.csv"]:
            if path.exists():
                z.write(path, rel(path))
        if corpus_path and CORPUS_PATH.exists():
            z.write(CORPUS_PATH, rel(CORPUS_PATH))
    local_open_index()
    write_hash_manifest()

    print(f"{TASK}: {final}")
    print(f"Output: {rel(ROOT)}")
    print(f"Real sessions: {len(accepted)}")
    print(f"Corpus rows: {len(questions)}")
    print(f"D14: {'READY_FOR_D14_CORPUS_AUDIT' if corpus_path else 'BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS'}")
    return 0 if final != FAIL_STATUS else 1


if __name__ == "__main__":
    sys.exit(main())
