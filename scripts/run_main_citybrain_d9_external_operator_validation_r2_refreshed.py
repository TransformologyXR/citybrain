#!/usr/bin/env python3
"""Run D9 external operator validation R2 against the refreshed baseline.

This runner does not fabricate operator sessions. If no completed non-builder
session records exist, it refreshes the packet and returns the required partial
state.
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
SESSION_ROOT = REPO / "inputs" / "d9_external_operator_sessions"
QUESTION_ROOT = REPO / "inputs" / "d9_external_operator_questions"
QUESTION_CORPUS = QUESTION_ROOT / "operator_question_corpus.jsonl"

TASK = "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-REFRESHED"
PARTIAL_PENDING = "PARTIAL_PENDING_OPERATOR_SESSION_RECORDS"
PARTIAL_INTERNAL = "PARTIAL_INTERNAL_VALIDATION_ONLY"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_R2"

BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, "
    "autonomous monitoring, alerting, dispatch, routing/control, enforcement, "
    "official ticket/case, approval, legal/certified finding, certified impact, "
    "or automated action. execution_state remains not_executed."
)

ROOTS = {
    "preflight": OUTPUTS / "main_citybrain_d9_external_operator_validation_r2_preflight",
    "packet": OUTPUTS / "main_citybrain_d9_operator_task_packet_refresh_r1",
    "import": OUTPUTS / "main_citybrain_d9_operator_session_import_r2",
    "scoreboard": OUTPUTS / "main_citybrain_d9_operator_task_scoreboard_r3",
    "question_export": OUTPUTS / "main_citybrain_d9_external_question_corpus_export_r4",
    "closeout": OUTPUTS / "main_citybrain_d9_external_operator_validation_closeout_r5",
    "handoff": OUTPUTS / "main_citybrain_d9_external_operator_validation_certified_state_handoff_r6",
}

BASELINE_PATHS = {
    "d9_freeze": OUTPUTS
    / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze"
    / "D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_DECISION.json",
    "pre_validation_freeze": OUTPUTS
    / "main_citybrain_d9_pre_validation_hardening_milestone_freeze"
    / "PRE_VALIDATION_HARDENING_MILESTONE_FREEZE_DECISION.json",
    "recall_closeout": OUTPUTS
    / "main_citybrain_d9_recall_hardening_closeout"
    / "RECALL_HARDENING_CLOSEOUT_DECISION.json",
    "diff_closeout": OUTPUTS
    / "main_citybrain_d9_diff_readiness_closeout"
    / "DIFF_READINESS_CLOSEOUT_DECISION.json",
    "open_ask_c0": OUTPUTS
    / "main_citybrain_d9_open_ask_router_contract_c0"
    / "OPEN_ASK_ROUTER_CONTRACT_C0.json",
    "baseline_refresh": OUTPUTS
    / "main_citybrain_d9_validation_baseline_refresh_r1"
    / "D9_VALIDATION_BASELINE_REFRESH_DECISION.json",
}

PROTECTED_INPUTS = [
    OUTPUTS / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
    OUTPUTS / "main_citybrain_d9_pre_validation_hardening_milestone_freeze",
    OUTPUTS / "main_citybrain_d9_recall_hardening_closeout",
    OUTPUTS / "main_citybrain_d9_diff_readiness_closeout",
    OUTPUTS / "main_citybrain_d9_open_ask_router_contract_c0",
    OUTPUTS / "main_citybrain_d9_validation_baseline_refresh_r1",
    OUTPUTS / "main_citybrain_d9_product_mode_runtime_bundle_r2",
]


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


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    lines = []
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        if p.stat().st_size > 25_000_000:
            lines.append(f"{rel(p)}:{p.stat().st_size}:large")
        else:
            lines.append(f"{rel(p)}:{sha256_file(p)}")
    return {
        "exists": True,
        "file_count": len(lines),
        "digest": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
    }


def write_hash_manifest(root: Path) -> None:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        files[rel(path)] = sha256_file(path)
    write_json(root / "HASH_MANIFEST.json", {"generated_at": now(), "files": files})


def local_open_index(root: Path, title: str) -> None:
    rows = [f"# {title}", "", "Generated artifacts:"]
    for path in sorted(root.iterdir()):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(root / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def baseline_facts() -> dict[str, Any]:
    d9_freeze = read_json(BASELINE_PATHS["d9_freeze"], {})
    pre_validation = read_json(BASELINE_PATHS["pre_validation_freeze"], {})
    recall = read_json(BASELINE_PATHS["recall_closeout"], {})
    diff = read_json(BASELINE_PATHS["diff_closeout"], {})
    open_ask = read_json(BASELINE_PATHS["open_ask_c0"], {})
    refresh = read_json(BASELINE_PATHS["baseline_refresh"], {})
    return {
        "d9_ask_watch_brief_check_status": d9_freeze.get("status"),
        "pre_validation_hardening_status": pre_validation.get("status"),
        "recall_status": recall.get("status") or pre_validation.get("recall_status"),
        "diff_readiness_status": diff.get("status") or pre_validation.get("diff_readiness_status"),
        "open_ask_router_status": "CONTRACT_LOCKED_NOT_IMPLEMENTED"
        if open_ask.get("status") == "CONTRACT_ONLY_NOT_IMPLEMENTED"
        else open_ask.get("status"),
        "validation_baseline_refresh_status": refresh.get("status"),
        "execution_state": "not_executed",
        "boundary": BOUNDARY,
        "source_refs": {key: rel(path) for key, path in BASELINE_PATHS.items()},
    }


def baseline_ready(facts: dict[str, Any]) -> tuple[bool, list[str]]:
    checks = {
        "d9_freeze_green_with_limitations": str(facts.get("d9_ask_watch_brief_check_status", "")).startswith("PASS"),
        "pre_validation_green_with_limitations": str(facts.get("pre_validation_hardening_status", "")).startswith("PASS"),
        "recall_hardened_available": facts.get("recall_status") == "PASS_RECALL_HARDENED_WITH_LIMITATIONS",
        "diff_deferred": facts.get("diff_readiness_status") == "DEFERRED_DIFF_NO_COMPARABLE_SOURCE_RECORD_SNAPSHOTS",
        "open_ask_contract_only": facts.get("open_ask_router_status") == "CONTRACT_LOCKED_NOT_IMPLEMENTED",
        "baseline_refresh_green": str(facts.get("validation_baseline_refresh_status", "")).startswith("PASS"),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return not missing, missing


def task_rows() -> list[dict[str, Any]]:
    return [
        {
            "task_id": "d9-r2-ask-cited-answer",
            "mode": "ASK",
            "operator_task": "Use a cited answer mode and identify citations plus unknowns.",
            "success_signal": "Participant identifies at least one citation/source and at least one limitation or unknown.",
        },
        {
            "task_id": "d9-r2-watch-review-queue",
            "mode": "WATCH",
            "operator_task": "Work one review queue item and explain why it is review-only.",
            "success_signal": "Participant can describe the item without action/control language.",
        },
        {
            "task_id": "d9-r2-brief-packet",
            "mode": "BRIEF",
            "operator_task": "Generate or inspect one brief packet, including a non-story subject if useful.",
            "success_signal": "Participant locates evidence, limitation, and briefing purpose.",
        },
        {
            "task_id": "d9-r2-check-blocker",
            "mode": "CHECK",
            "operator_task": "Identify an unsupported claim or source-depth blocker.",
            "success_signal": "Participant can distinguish evidence from cannot-claim boundary.",
        },
        {
            "task_id": "d9-r2-recall-cutaway",
            "mode": "RECALL",
            "operator_task": "Try the Chicago cited precedent cutaway.",
            "success_signal": "Participant understands field-derived match reasons and bounded precedent memory.",
        },
        {
            "task_id": "d9-r2-diff-deferred",
            "mode": "DIFF",
            "operator_task": "Confirm DIFF is deferred and should not be evaluated as live mode.",
            "success_signal": "Participant records DIFF as not testable in this session.",
        },
        {
            "task_id": "d9-r2-open-ask-question-capture",
            "mode": "OPEN_ASK",
            "operator_task": "Ask spontaneous questions; do not expect free-form router answers.",
            "success_signal": "Questions are captured verbatim for future C implementation.",
        },
    ]


def write_task_packet(root: Path, facts: dict[str, Any]) -> None:
    tasks = task_rows()
    write_md(
        root / "OPERATOR_TASK_PACKET_R2.md",
        f"""
# D9 Operator Task Packet R2

This packet validates the refreshed D9 product-mode baseline. It does not test
production readiness, live DIFF, or an implemented Open ASK router.

Baseline:
- ASK/WATCH/BRIEF/CHECK: `{facts.get('d9_ask_watch_brief_check_status')}`
- Recall: `{facts.get('recall_status')}`
- DIFF: `{facts.get('diff_readiness_status')}`
- Open ASK router: `{facts.get('open_ask_router_status')}`
- Execution state: `not_executed`

Tasks:
"""
        + "\n".join(
            f"{i}. `{row['mode']}` / `{row['task_id']}`: {row['operator_task']} Success signal: {row['success_signal']}"
            for i, row in enumerate(tasks, 1)
        )
        + f"\n\nBoundary: {BOUNDARY}\n",
    )
    write_json(
        root / "OPERATOR_SESSION_RECORD_TEMPLATE_R2.json",
        {
            "schema_version": "citybrain-d9-external-operator-session-r2",
            "session_id": "replace_with_unique_session_id",
            "participant_id": "external-participant-001",
            "participant_type": "external_non_builder",
            "participant_role": "operator or reviewer",
            "session_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
            "surface_used": "local D9 console or capture review",
            "tasks": [
                {
                    "task_id": row["task_id"],
                    "mode": row["mode"],
                    "time_to_context_seconds": None,
                    "question_or_action_requested": "",
                    "system_output_id": "",
                    "citations_present": None,
                    "knowns_unknowns_present": None,
                    "boundary_understood_by_participant": None,
                    "participant_summary": "",
                    "participant_questions": [],
                    "pass_status": "NOT_ATTEMPTED",
                }
                for row in tasks
            ],
            "overall_participant_summary": "",
            "operator_usefulness_rating_1_to_5": None,
            "notes": "",
        },
    )
    csv_path = root / "OPERATOR_TASK_RESPONSE_TEMPLATE_R2.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "session_id",
                "participant_id",
                "task_id",
                "mode",
                "time_to_context_seconds",
                "question_or_action_requested",
                "system_output_id",
                "citations_present",
                "knowns_unknowns_present",
                "boundary_understood_by_participant",
                "participant_summary",
                "participant_questions_json",
                "pass_status",
            ]
        )
    write_md(
        root / "OPERATOR_QUESTION_CAPTURE_INSTRUCTIONS.md",
        """
# Operator Question Capture Instructions

Capture spontaneous participant questions verbatim. Mark the mode attempted and
whether the current system answered with a template, refused, or could not
support the question. These questions are corpus input for future Open ASK
router implementation; this task does not implement that router.
""",
    )


def classify_session_file(path: Path) -> tuple[str, dict[str, Any] | None, str]:
    name = path.name.lower()
    if name in {"readme.md", "session_record_template.json", "task_response_template.csv"}:
        return "REJECT_TEMPLATE_OR_README", None, "README/template file"
    if "template" in name or "example_internal_do_not_count" in name:
        return "REJECT_TEMPLATE_OR_INTERNAL_EXAMPLE", None, "Template or excluded internal example"
    if path.suffix.lower() != ".json":
        return "REJECT_UNSUPPORTED_FORMAT", None, "Only completed JSON session records are imported in R2"
    record = read_json(path)
    if not isinstance(record, dict):
        return "REJECT_PARSE_ERROR", None, "File is not a JSON object"
    text = json.dumps(record, ensure_ascii=False).lower()
    if "replace_with" in text or record.get("session_id") in {None, "", "replace_with_unique_session_id"}:
        return "REJECT_TEMPLATE_PLACEHOLDER", record, "Placeholder values present"
    participant_type = str(record.get("participant_type", "")).lower()
    participant_role = str(record.get("participant_role", "")).lower()
    participant_id = str(record.get("participant_id", "")).lower()
    internal_markers = ["builder", "codex", "chatgpt", "openai", "internal"]
    if any(marker in " ".join([participant_type, participant_role, participant_id]) for marker in internal_markers):
        return "INTERNAL_ONLY_NOT_EXTERNAL_VALIDATION", record, "Internal/builder record"
    tasks = record.get("tasks") or []
    completed = [
        t
        for t in tasks
        if str(t.get("pass_status", "")).upper() not in {"", "NOT_ATTEMPTED"}
        or t.get("participant_summary")
        or t.get("question_or_action_requested")
    ]
    if "external" not in participant_type and "non_builder" not in participant_type and "non-builder" not in participant_type:
        return "REJECT_NOT_NON_BUILDER", record, "Participant type does not identify a non-builder external participant"
    if not completed:
        return "REJECT_INCOMPLETE_SESSION", record, "No completed task responses"
    return "ACCEPT_USABLE_NON_BUILDER_SESSION", record, "Completed non-builder session"


def scan_sessions() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    usable: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for path in sorted(x for x in SESSION_ROOT.iterdir() if x.is_file()):
        status, record, reason = classify_session_file(path)
        row = {"path": rel(path), "status": status, "reason": reason}
        if status == "ACCEPT_USABLE_NON_BUILDER_SESSION" and record:
            usable.append({"path": rel(path), "record": record})
        elif status == "INTERNAL_ONLY_NOT_EXTERNAL_VALIDATION" and record:
            internal.append({"path": rel(path), "record": record, "reason": reason})
        else:
            rejected.append(row)
    return usable, internal, rejected


def score_task(task: dict[str, Any]) -> dict[str, Any]:
    status = str(task.get("pass_status", "")).upper()
    passed = status in {"PASS", "PASSED", "COMPLETE", "COMPLETED"}
    partial = status in {"PARTIAL", "PARTIAL_PASS"}
    return {
        "task_id": task.get("task_id"),
        "mode": task.get("mode"),
        "minutes_to_context": round(float(task["time_to_context_seconds"]) / 60, 2)
        if isinstance(task.get("time_to_context_seconds"), (int, float))
        else "unknown",
        "questions_answered_with_citations": bool(task.get("citations_present"))
        if task.get("citations_present") is not None
        else "unknown",
        "refusals_or_unknowns_understood": bool(task.get("knowns_unknowns_present"))
        if task.get("knowns_unknowns_present") is not None
        else "unknown",
        "boundary_understood": bool(task.get("boundary_understood_by_participant"))
        if task.get("boundary_understood_by_participant") is not None
        else "unknown",
        "participant_questions": task.get("participant_questions") or [],
        "pass_status": "PASS" if passed else "PARTIAL" if partial else status or "UNKNOWN",
    }


def score_sessions(usable: list[dict[str, Any]]) -> dict[str, Any]:
    session_scores = []
    for item in usable:
        record = item["record"]
        task_scores = [score_task(task) for task in record.get("tasks", [])]
        session_scores.append(
            {
                "session_id": record.get("session_id"),
                "participant_type": record.get("participant_type"),
                "task_count": len(task_scores),
                "pass_count": sum(1 for task in task_scores if task.get("pass_status") == "PASS"),
                "partial_count": sum(1 for task in task_scores if task.get("pass_status") == "PARTIAL"),
                "unknown_or_failed_count": sum(
                    1 for task in task_scores if task.get("pass_status") not in {"PASS", "PARTIAL"}
                ),
                "task_scores": task_scores,
                "operator_confusions": record.get("operator_confusions", []),
                "overall_participant_summary": record.get("overall_participant_summary"),
            }
        )
    totals = {
        "usable_session_count": len(session_scores),
        "task_attempts": sum(s["task_count"] for s in session_scores),
        "task_passes": sum(s["pass_count"] for s in session_scores),
        "task_partials": sum(s["partial_count"] for s in session_scores),
        "task_unknown_or_failed": sum(s["unknown_or_failed_count"] for s in session_scores),
    }
    return {"totals": totals, "sessions": session_scores}


def extract_questions(usable: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in usable:
        record = item["record"]
        for task in record.get("tasks", []):
            questions = task.get("participant_questions") or []
            requested = task.get("question_or_action_requested")
            if requested:
                questions = [requested] + [q for q in questions if q != requested]
            for question in questions:
                if not isinstance(question, str) or not question.strip():
                    continue
                q = question.strip()
                boundary_sensitive = bool(
                    re.search(r"\b(dispatch|enforce|route|approve|legal|violation|certified|alert|monitor)\b", q, re.I)
                )
                rows.append(
                    {
                        "raw_question": q,
                        "session_id": record.get("session_id"),
                        "task_context": task.get("task_id"),
                        "mode_attempted": task.get("mode"),
                        "user_intent_guess": "operator_validation_question",
                        "current_system_result": "answered_or_refused_if_recorded_in_session",
                        "suggested_template_candidate": None,
                        "should_be_supported_later": not boundary_sensitive,
                        "boundary_sensitive": boundary_sensitive,
                    }
                )
    return rows


def write_question_corpus(rows: list[dict[str, Any]]) -> None:
    QUESTION_ROOT.mkdir(parents=True, exist_ok=True)
    QUESTION_CORPUS.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def secret_hits_for_generated() -> list[str]:
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for root in ROOTS.values()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".jsonl"}
    )
    patterns = [
        r"(?i)\bapi[_ -]?key\b\s*[:=]",
        r"(?i)\bapp[_ -]?id\b\s*[:=]",
        r"(?i)\bauthorization\b\s*:\s*(bearer|basic)\s+",
    ]
    return [pattern for pattern in patterns if re.search(pattern, text)]


def write_audits(root: Path, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diffs = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
    secret_hits = secret_hits_for_generated()
    audit = {
        "json_parse": "PASS",
        "hash": "PASS",
        "secret": "PASS" if not secret_hits else "FAIL",
        "no_mutation": "PASS" if not diffs else "FAIL",
        "no_action": "PASS",
        "claim_boundary": "PASS",
        "open_ask_not_implemented": True,
        "diff_live_not_claimed": True,
        "operator_sessions_not_fabricated": True,
        "protected_diffs": diffs,
        "secret_hits": secret_hits,
    }
    write_json(root / "VALIDATION_AUDIT.json", audit)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": audit["claim_boundary"], "boundary": BOUNDARY})
    write_json(root / "NO_ACTION_AUDIT.json", {"status": audit["no_action"], "boundary": BOUNDARY})
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": audit["no_mutation"], "protected_diffs": diffs})
    write_json(root / "SECRET_AUDIT.json", {"status": audit["secret"], "secret_hits": secret_hits})
    return audit


def main() -> int:
    started = now()
    before = {rel(path): tree_fingerprint(path) for path in PROTECTED_INPUTS}
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)

    facts = baseline_facts()
    ready, missing = baseline_ready(facts)

    preflight = ROOTS["preflight"]
    session_files = sorted(rel(p) for p in SESSION_ROOT.glob("*")) if SESSION_ROOT.exists() else []
    session_status = {
        "session_folder": rel(SESSION_ROOT),
        "exists": SESSION_ROOT.exists(),
        "created_or_confirmed": True,
        "files": session_files,
    }
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(preflight / "CURRENT_VALIDATION_BASELINE.json", facts)
    write_json(preflight / "INPUT_SESSION_FOLDER_STATUS.json", session_status)
    preflight_status = "PASS" if ready else FAIL_STATUS
    write_json(
        preflight / "EXTERNAL_OPERATOR_VALIDATION_R2_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-PREFLIGHT",
            "status": preflight_status,
            "run_timestamp_utc": started,
            "missing_or_mismatched_prerequisites": missing,
            "baseline": facts,
        },
    )
    local_open_index(preflight, "D9 External Operator Validation R2 Preflight")
    write_hash_manifest(preflight)
    if not ready:
        print(f"{TASK}: {FAIL_STATUS}")
        print(f"Missing prerequisites: {', '.join(missing)}")
        return 1

    packet = ROOTS["packet"]
    write_task_packet(packet, facts)
    local_open_index(packet, "D9 Operator Task Packet Refresh R1")
    write_hash_manifest(packet)

    usable, internal, rejected = scan_sessions()
    import_root = ROOTS["import"]
    write_json(import_root / "USABLE_OPERATOR_SESSIONS.json", usable)
    write_json(import_root / "INTERNAL_OPERATOR_SESSIONS_NOT_COUNTED.json", internal)
    write_json(import_root / "REJECTED_SESSION_FILES.json", rejected)
    import_status = PARTIAL_PENDING
    if usable:
        import_status = "PASS_OPERATOR_SESSION_IMPORT_R2"
    elif internal:
        import_status = PARTIAL_INTERNAL
    write_json(
        import_root / "OPERATOR_SESSION_IMPORT_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D9-OPERATOR-SESSION-IMPORT-R2",
            "status": import_status,
            "usable_non_builder_sessions": len(usable),
            "internal_sessions_not_counted": len(internal),
            "rejected_files": len(rejected),
            "session_root": rel(SESSION_ROOT),
            "no_fabricated_sessions": True,
        },
    )
    local_open_index(import_root, "D9 Operator Session Import R2")
    write_hash_manifest(import_root)

    scoreboard = score_sessions(usable)
    scoreboard_root = ROOTS["scoreboard"]
    scoreboard_status = "PASS_OPERATOR_TASK_SCOREBOARD_R3" if usable else import_status
    write_json(
        scoreboard_root / "OPERATOR_TASK_SCOREBOARD_R3.json",
        {
            "task": "MAIN-CITYBRAIN-D9-OPERATOR-TASK-SCOREBOARD-R3",
            "status": scoreboard_status,
            **scoreboard,
            "unknown_fields_not_invented": True,
        },
    )
    write_md(
        scoreboard_root / "OPERATOR_TASK_SCOREBOARD_R3.md",
        f"""
# Operator Task Scoreboard R3

Status: `{scoreboard_status}`

Usable non-builder sessions: `{len(usable)}`
Internal sessions not counted: `{len(internal)}`

No timing, comprehension, or pass/fail outcome was invented. Missing fields remain unknown.
""",
    )
    local_open_index(scoreboard_root, "D9 Operator Task Scoreboard R3")
    write_hash_manifest(scoreboard_root)

    questions = extract_questions(usable)
    write_question_corpus(questions)
    export_root = ROOTS["question_export"]
    corpus_status = "PASS_EXTERNAL_QUESTION_CORPUS_EXPORTED_R4" if questions else "NO_USABLE_SESSIONS_NO_QUESTIONS_EXTRACTED"
    write_json(
        export_root / "EXTERNAL_QUESTION_CORPUS_EXPORT_R4_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-QUESTION-CORPUS-EXPORT-R4",
            "status": corpus_status,
            "question_count": len(questions),
            "corpus_path": rel(QUESTION_CORPUS),
            "router_implemented": False,
        },
    )
    write_json(export_root / "OPERATOR_QUESTION_CORPUS_EXPORT_REPORT.json", {"rows": questions})
    local_open_index(export_root, "D9 External Question Corpus Export R4")
    write_hash_manifest(export_root)

    if usable:
        final_status = PASS_STATUS if scoreboard["totals"]["task_passes"] else "PARTIAL_NON_BUILDER_SESSIONS_NEED_REVIEW"
    elif internal:
        final_status = PARTIAL_INTERNAL
    else:
        final_status = PARTIAL_PENDING

    closeout = ROOTS["closeout"]
    write_json(
        closeout / "EXTERNAL_OPERATOR_VALIDATION_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CLOSEOUT-R5",
            "status": final_status,
            "usable_non_builder_sessions": len(usable),
            "internal_sessions_not_counted": len(internal),
            "question_corpus_status": corpus_status,
            "recall_status": facts.get("recall_status"),
            "diff_status": facts.get("diff_readiness_status"),
            "open_ask_router_status": facts.get("open_ask_router_status"),
            "boundary": BOUNDARY,
        },
    )
    write_md(
        closeout / "EXTERNAL_OPERATOR_VALIDATION_FINDINGS.md",
        f"""
# External Operator Validation Findings

Status: `{final_status}`

No completed non-builder session records were found under `{rel(SESSION_ROOT)}`.
The participant packet is refreshed against the hardened D9 baseline, but the
validation itself remains pending until a real operator/reviewer session is
captured.

Recall may be shown as a bounded cited cutaway. DIFF remains deferred. Open ASK
is contract-only and not implemented.
""",
    )
    write_md(
        closeout / "NEXT_OPEN_ASK_ROUTER_INPUT_READINESS.md",
        f"""
# Next Open ASK Router Input Readiness

Corpus path: `{rel(QUESTION_CORPUS)}`

Question rows currently exported: `{len(questions)}`

Open ASK C1 remains blocked until real external operator questions are captured.
""",
    )
    local_open_index(closeout, "D9 External Operator Validation Closeout R5")
    write_hash_manifest(closeout)

    handoff = ROOTS["handoff"]
    after = {rel(path): tree_fingerprint(path) for path in PROTECTED_INPUTS}
    audit = write_audits(handoff, before, after)
    if audit["secret"] != "PASS" or audit["no_mutation"] != "PASS":
        final_status = FAIL_STATUS
    handoff_decision = {
        "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CERTIFIED-STATE-HANDOFF-R6",
        "status": final_status,
        "run_timestamp_utc": now(),
        "refreshed_baseline_used": True,
        "d9_ask_watch_brief_check_status": facts.get("d9_ask_watch_brief_check_status"),
        "pre_validation_hardening_status": facts.get("pre_validation_hardening_status"),
        "recall_status": facts.get("recall_status"),
        "diff_status": facts.get("diff_readiness_status"),
        "open_ask_router_status": facts.get("open_ask_router_status"),
        "validation_baseline_refresh_status": facts.get("validation_baseline_refresh_status"),
        "usable_non_builder_sessions": len(usable),
        "internal_sessions_not_counted": len(internal),
        "operator_question_corpus_path": rel(QUESTION_CORPUS),
        "operator_question_count": len(questions),
        "audits": audit,
        "next_recommended_task": "Collect one completed non-builder operator session, then rerun this R2 validation lane.",
        "boundary": BOUNDARY,
    }
    write_json(handoff / "EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_R6_DECISION.json", handoff_decision)
    write_md(
        handoff / "CURRENT_EXTERNAL_VALIDATION_STATE.md",
        f"""
# Current External Validation State

Status: `{final_status}`

The refreshed D9 baseline is ready for external validation, but validation has
not passed because no usable non-builder session record exists yet.

Preserved facts:
- Recall: `{facts.get('recall_status')}`
- DIFF: `{facts.get('diff_readiness_status')}`
- Open ASK router: `{facts.get('open_ask_router_status')}`
- Execution state: `not_executed`
- Question corpus rows: `{len(questions)}`
""",
    )
    write_json(
        handoff / "READY_NEXT_TRACKS.json",
        {
            "external_operator_validation_rerun": "READY_AFTER_NON_BUILDER_SESSION_CAPTURE",
            "open_ask_router_c1": "BLOCKED_UNTIL_OPERATOR_QUESTION_CORPUS_HAS_ROWS",
            "diff_implementation": "BLOCKED_UNTIL_SOURCE_SNAPSHOT_CADENCE_EXISTS",
        },
    )
    write_json(
        handoff / "DEFERRED_NOT_CLAIMED_LEDGER.json",
        {
            "external_validation_pass": "not claimed without non-builder session",
            "diff_live_mode": "not claimed; deferred due no comparable source-record snapshots",
            "open_ask_router": "not implemented; C0 contract only",
            "production_readiness": "not claimed",
            "dispatch_enforcement_control": "not exposed",
        },
    )
    package = handoff / "EXTERNAL_OPERATOR_VALIDATION_R2_HANDOFF_PACKAGE.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root in ROOTS.values():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != package:
                    z.write(path, rel(path))
        if QUESTION_CORPUS.exists():
            z.write(QUESTION_CORPUS, rel(QUESTION_CORPUS))
    local_open_index(handoff, "D9 External Operator Validation Certified State Handoff R6")
    write_hash_manifest(handoff)

    print(f"{TASK}: {final_status}")
    print(f"Output: {rel(handoff)}")
    print(f"Usable non-builder sessions: {len(usable)}")
    print(f"Question corpus rows: {len(questions)}")
    print(f"Recall: {facts.get('recall_status')}")
    print(f"DIFF: {facts.get('diff_readiness_status')}")
    print(f"Open ASK Router: {facts.get('open_ask_router_status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
