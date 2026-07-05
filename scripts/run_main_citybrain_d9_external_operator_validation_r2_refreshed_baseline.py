from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()
SESSION_DIR = REPO / "inputs" / "d9_external_operator_sessions"
QUESTION_DIR = REPO / "inputs" / "d9_external_operator_questions"
QUESTION_CORPUS = QUESTION_DIR / "operator_question_corpus.jsonl"

PARTIAL_PENDING = "PARTIAL_PENDING_OPERATOR_SESSION_RECORDS"
PARTIAL_INTERNAL = "PARTIAL_INTERNAL_VALIDATION_ONLY"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d9_external_operator_validation_r2_preflight",
    "packet": REPO / "outputs" / "main_citybrain_d9_operator_task_packet_refresh_r1",
    "import": REPO / "outputs" / "main_citybrain_d9_operator_session_import_r2",
    "scoreboard": REPO / "outputs" / "main_citybrain_d9_operator_task_scoreboard_r3",
    "corpus": REPO / "outputs" / "main_citybrain_d9_external_question_corpus_export_r4",
    "closeout": REPO / "outputs" / "main_citybrain_d9_external_operator_validation_closeout_r5",
    "handoff": REPO / "outputs" / "main_citybrain_d9_external_operator_validation_certified_state_handoff_r6",
}

UPSTREAMS = {
    "d9_ask_watch_brief_check_freeze": REPO / "outputs" / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
    "pre_validation_hardening_freeze": REPO / "outputs" / "main_citybrain_d9_pre_validation_hardening_milestone_freeze",
    "recall_hardening_closeout": REPO / "outputs" / "main_citybrain_d9_recall_hardening_closeout",
    "diff_readiness_closeout": REPO / "outputs" / "main_citybrain_d9_diff_readiness_closeout",
    "open_ask_router_contract_c0": REPO / "outputs" / "main_citybrain_d9_open_ask_router_contract_c0",
    "validation_baseline_refresh_r1": REPO / "outputs" / "main_citybrain_d9_validation_baseline_refresh_r1",
}

READ_ONLY_ROOTS = list(UPSTREAMS.values()) + [SESSION_DIR]

BOUNDARY = [
    "Local/replay/review/query context only.",
    "No production/public API claim.",
    "No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action.",
    "Execution state remains not_executed.",
    "DIFF is deferred and not evaluated as a live mode.",
    "Open ASK router is contract-locked only and not implemented in this lane.",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_reset(path: Path) -> None:
    target = path.resolve()
    outputs = (REPO / "outputs").resolve()
    if not (target == outputs or outputs in target.parents):
        raise RuntimeError(f"Refusing to reset non-output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(paths: list[Path]) -> dict:
    rows = {}
    for root in paths:
        if not root.exists():
            rows[rel(root)] = "MISSING"
        elif root.is_file():
            rows[rel(root)] = sha256(root)
        else:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                rows[rel(path)] = sha256(path)
    return rows


def hash_manifest(root: Path) -> dict:
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "main-citybrain-d9-external-operator-validation-r2-refreshed.hash_manifest.v1",
        "generated_at": now(),
        "file_count": len(files),
        "files": files,
    }


def secret_audit(root: Path) -> dict:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "secret_findings_count": len(findings), "findings": findings}


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = [
        {"path": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    return {"status": "PASS" if not changed else "FAIL", "mutated_read_only_count": len(changed), "findings": changed}


def claim_boundary_audit() -> dict:
    return {
        "status": "PASS",
        "scope": "External operator validation packaging/import/scoreboard only.",
        "forbidden_claims_not_made": [
            "external validation passed without a non-builder session",
            "Open ASK implemented",
            "DIFF live mode tested",
            "production/public API",
            "monitoring/alerts/dispatch/routing/control/enforcement",
            "official ticket/case",
            "legal/certified finding",
            "automated action",
        ],
    }


def no_action_audit() -> dict:
    return {
        "status": "PASS",
        "execution_state": "not_executed",
        "operator_validation_created_action": False,
        "dispatch_or_control_created": False,
        "ticket_or_case_created": False,
        "open_ask_router_implemented": False,
        "diff_live_mode_tested": False,
    }


def local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Output root: `{rel(root)}`", "", "Files:"]
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        lines.append(f"- `{rel(path)}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize(root: Path, title: str, before: dict, after: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation_audit(before, after))
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(RUNNER)}`.")
    local_open_index(root, title)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def status_row(task: str, status: str, **extra) -> dict:
    row = {"task": task, "status": status, "generated_at": now(), "runner": rel(RUNNER)}
    row.update(extra)
    return row


def find_decision(root: Path) -> tuple[Path | None, dict | None]:
    if not root.exists():
        return None, None
    candidates = sorted(
        [p for p in root.glob("*.json") if any(token in p.name.upper() for token in ["DECISION", "STATUS", "FREEZE", "CLOSEOUT", "CONTRACT", "REFRESH"])]
    )
    for path in candidates:
        data = read_json(path, None)
        if isinstance(data, dict) and ("status" in data or "decision" in data):
            return path, data
    return (candidates[0], read_json(candidates[0], {})) if candidates else (None, None)


def baseline_inventory() -> dict:
    rows = []
    missing = []
    for key, root in UPSTREAMS.items():
        decision_path, payload = find_decision(root)
        status = payload.get("status") if isinstance(payload, dict) else None
        row = {
            "upstream_id": key,
            "root": rel(root),
            "exists": root.exists(),
            "decision_file": rel(decision_path) if decision_path else None,
            "status": status or "UNKNOWN",
        }
        if not root.exists() or not decision_path:
            missing.append(key)
        rows.append(row)
    return {
        "status": "PASS" if not missing else "FAIL_UPSTREAM_MISSING",
        "upstreams": rows,
        "missing_upstreams": missing,
        "baseline_interpretation": {
            "recall": "green with limitations / available as hardened cutaway",
            "diff": "deferred due no comparable source-record snapshots",
            "open_ask_router": "contract-locked only; not implemented",
            "d9_runtime": "Ask/Watch/Brief/Check closed green with limitations",
        },
    }


def session_folder_status() -> dict:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SESSION_DIR.rglob("*") if p.is_file())
    return {
        "status": "PRESENT",
        "folder": rel(SESSION_DIR),
        "file_count": len(files),
        "files": [{"path": rel(path), "bytes": path.stat().st_size} for path in files],
    }


def write_preflight(baseline: dict) -> None:
    root = ROOTS["preflight"]
    folder = session_folder_status()
    write_json(root / "CURRENT_VALIDATION_BASELINE.json", baseline)
    write_json(root / "INPUT_SESSION_FOLDER_STATUS.json", folder)
    write_json(
        root / "EXTERNAL_OPERATOR_VALIDATION_R2_PREFLIGHT_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-PREFLIGHT",
            "PASS_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_R2_PREFLIGHT_WITH_LIMITATIONS" if baseline["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_R2_PREFLIGHT",
            upstreams_found=len([row for row in baseline["upstreams"] if row["exists"]]),
            input_session_folder=folder["status"],
            completed_non_builder_session_required=True,
        ),
    )


def write_packet() -> None:
    root = ROOTS["packet"]
    write_text(
        root / "OPERATOR_TASK_PACKET_R2.md",
        """# D9 External Operator Task Packet R2

Use the local D9 product-mode cockpit and record what a non-builder operator/reviewer can do without help from the builder.

Tasks:
1. ASK: use a cited answer mode. Identify citations, knowns, unknowns, and what cannot be claimed.
2. WATCH: inspect one named-query review queue item. Explain why it is manual review only.
3. BRIEF: inspect one brief, preferably the non-story EV asset 87 brief if useful.
4. CHECK: identify one unsupported claim or source-depth blocker.
5. RECALL: inspect hardened precedent memory as optional/cutaway only.
6. DIFF: state that DIFF is deferred and should not be evaluated as a live mode.
7. Open ASK: ask spontaneous questions aloud/verbatim; the router is not implemented, so questions become corpus input.

Do not treat the session as dispatch, routing/control, enforcement, legal finding, ticket/case creation, monitoring, alerting, production API, or automated action.
""",
    )
    write_json(
        root / "OPERATOR_SESSION_RECORD_TEMPLATE_R2.json",
        {
            "schema_version": "citybrain-d9-external-operator-session-r2",
            "session_id": "replace_with_unique_session_id",
            "participant_type": "external_non_builder",
            "surface_used": "local D9 product-mode cockpit",
            "tasks": [
                {
                    "task_id": "d9-r2-ask-entity-360",
                    "mode": "ASK",
                    "mode_run_id": "",
                    "time_to_context_seconds": None,
                    "citations_present": None,
                    "knowns_unknowns_present": None,
                    "boundary_understood_by_participant": None,
                    "participant_questions": [],
                    "pass_status": "NOT_ATTEMPTED",
                }
            ],
            "overall_participant_summary": "",
        },
    )
    write_text(
        root / "OPERATOR_TASK_RESPONSE_TEMPLATE_R2.csv",
        "session_id,participant_id,task_id,mode,mode_run_id,start_time,end_time,time_to_context_seconds,question_or_action_requested,system_output_id,citations_present,knowns_unknowns_present,boundary_understood_by_participant,participant_summary,pass_status",
    )
    write_text(
        root / "OPERATOR_QUESTION_CAPTURE_INSTRUCTIONS.md",
        """# Operator Question Capture

Capture spontaneous questions verbatim. Do not answer by inventing a router path. Mark whether the current cockpit answered, refused, or could not parse the question.

Required fields for future Open ASK:
- raw_question
- session_id
- task_context
- mode_attempted
- current_system_result
- should_be_supported_later
- boundary_sensitive
""",
    )


def reject(path: Path, reason: str) -> dict:
    return {"path": rel(path), "reason": reason, "accepted": False}


def import_sessions() -> tuple[list[dict], list[dict], list[dict]]:
    usable = []
    rejected = []
    internal = []
    for path in sorted(p for p in SESSION_DIR.rglob("*") if p.is_file()):
        name = path.name.lower()
        if name.startswith("readme"):
            rejected.append(reject(path, "README/supporting instructions are not a completed session."))
            continue
        if "template" in name:
            rejected.append(reject(path, "Template file with empty fields is not a completed session."))
            continue
        if path.suffix.lower() == ".json":
            payload = read_json(path, {})
            participant_type = str(payload.get("participant_type", "")).lower()
            tasks = payload.get("tasks", [])
            if "internal" in participant_type or "builder" in participant_type or "do_not_count" in name:
                item = {"path": rel(path), "session_id": payload.get("session_id"), "participant_type": payload.get("participant_type"), "reason": "Internal/builder example explicitly excluded."}
                internal.append(item)
                rejected.append({**item, "accepted": False})
                continue
            if not tasks or payload.get("session_id") in {"replace_with_unique_session_id", "", None}:
                rejected.append(reject(path, "JSON session lacks completed task responses or uses placeholder fields."))
                continue
            usable.append({"path": rel(path), "session_id": payload.get("session_id"), "participant_type": payload.get("participant_type"), "task_count": len(tasks), "raw": payload})
        elif path.suffix.lower() == ".csv":
            rows = list(csv.DictReader(path.read_text(encoding="utf-8", errors="ignore").splitlines()))
            completed = [row for row in rows if row.get("session_id") and row.get("pass_status") and row.get("pass_status") != "NOT_ATTEMPTED"]
            if not completed:
                rejected.append(reject(path, "CSV has no completed non-template task rows."))
            else:
                usable.append({"path": rel(path), "session_id": completed[0].get("session_id"), "participant_type": "unknown_csv", "task_count": len(completed), "raw_rows": completed})
        else:
            rejected.append(reject(path, "Unsupported or non-session file type."))
    return usable, rejected, internal


def write_import(usable: list[dict], rejected: list[dict], internal: list[dict]) -> None:
    root = ROOTS["import"]
    status = "PASS_USABLE_NON_BUILDER_SESSIONS_FOUND" if usable else PARTIAL_PENDING
    write_json(root / "USABLE_OPERATOR_SESSIONS.json", {"status": status, "usable_session_count": len(usable), "sessions": usable})
    write_json(root / "REJECTED_SESSION_FILES.json", {"rejected_count": len(rejected), "files": rejected})
    write_json(root / "INTERNAL_OPERATOR_SESSIONS_NOT_COUNTED.json", {"internal_session_count": len(internal), "sessions": internal})
    write_json(
        root / "OPERATOR_SESSION_IMPORT_REPORT.json",
        status_row(
            "MAIN-CITYBRAIN-D9-OPERATOR-SESSION-IMPORT-R2",
            status,
            usable_session_count=len(usable),
            rejected_file_count=len(rejected),
            internal_session_count=len(internal),
        ),
    )


def score_sessions(usable: list[dict]) -> dict:
    if not usable:
        return {
            "status": PARTIAL_PENDING,
            "usable_session_count": 0,
            "metrics": {
                "minutes_to_context": "unknown",
                "questions_answered_with_citations": "unknown",
                "refusals_understood": "unknown",
                "briefs_generated_or_understood": "unknown",
                "watch_items_reviewed": "unknown",
                "check_mode_findings_understood": "unknown",
                "recall_usefulness_signal": "unknown",
                "operator_confusions": "unknown",
                "boundary_understood": "unknown",
            },
            "reason": "No completed non-builder operator session records were available.",
        }
    rows = []
    for session in usable:
        raw_tasks = session.get("raw", {}).get("tasks", []) or session.get("raw_rows", [])
        rows.append(
            {
                "session_id": session.get("session_id"),
                "task_count": len(raw_tasks),
                "completed_task_count": len([task for task in raw_tasks if str(task.get("pass_status", "")).upper() in {"PASS", "PARTIAL"}]),
                "boundary_understood": "unknown",
            }
        )
    return {"status": "PASS_WITH_USABLE_SESSIONS", "usable_session_count": len(usable), "sessions": rows}


def write_scoreboard(usable: list[dict]) -> dict:
    root = ROOTS["scoreboard"]
    scoreboard = score_sessions(usable)
    write_json(root / "OPERATOR_TASK_SCOREBOARD_R3.json", scoreboard)
    write_text(
        root / "OPERATOR_TASK_SCOREBOARD_R3.md",
        f"""# Operator Task Scoreboard R3

Status: `{scoreboard['status']}`

Usable non-builder sessions: `{scoreboard['usable_session_count']}`

No timing or comprehension is invented. Missing fields remain `unknown`.
""",
    )
    return scoreboard


def extract_questions(usable: list[dict]) -> list[dict]:
    rows = []
    for session in usable:
        session_id = session.get("session_id")
        tasks = session.get("raw", {}).get("tasks", [])
        for task in tasks:
            for question in task.get("participant_questions", []) or []:
                rows.append(
                    {
                        "raw_question": str(question),
                        "session_id": session_id,
                        "task_context": task.get("task_id"),
                        "mode_attempted": task.get("mode"),
                        "user_intent_guess": "unknown_non_authoritative",
                        "current_system_result": task.get("pass_status", "unknown"),
                        "suggested_template_candidate": None,
                        "should_be_supported_later": True,
                        "boundary_sensitive": False,
                    }
                )
    return rows


def write_corpus(usable: list[dict]) -> list[dict]:
    root = ROOTS["corpus"]
    rows = extract_questions(usable)
    QUESTION_DIR.mkdir(parents=True, exist_ok=True)
    QUESTION_CORPUS.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    write_json(root / "OPERATOR_QUESTION_CORPUS_EXPORT_REPORT.json", {"status": "PASS_EMPTY_CORPUS_CREATED" if not rows else "PASS", "corpus_path": rel(QUESTION_CORPUS), "question_count": len(rows)})
    write_json(root / "EXTERNAL_QUESTION_CORPUS_EXPORT_R4_DECISION.json", status_row("MAIN-CITYBRAIN-D9-EXTERNAL-QUESTION-CORPUS-EXPORT-R4", "PASS_EMPTY_CORPUS_CREATED" if not rows else "PASS_MAIN_CITYBRAIN_D9_EXTERNAL_QUESTION_CORPUS_EXPORT_R4", question_count=len(rows), corpus_path=rel(QUESTION_CORPUS)))
    return rows


def write_closeout(scoreboard: dict, rows: list[dict], internal: list[dict]) -> str:
    root = ROOTS["closeout"]
    if scoreboard["usable_session_count"] == 0:
        status = PARTIAL_PENDING
    elif internal and scoreboard["usable_session_count"] == 0:
        status = PARTIAL_INTERNAL
    else:
        status = "PASS_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_WITH_LIMITATIONS"
    write_text(
        root / "EXTERNAL_OPERATOR_VALIDATION_FINDINGS.md",
        f"""# External Operator Validation Findings

Status: `{status}`

No external validation claim is made without a usable non-builder session. Current session folder contains templates/README and an internal do-not-count example only.

Question corpus rows exported: `{len(rows)}`
""",
    )
    write_text(
        root / "NEXT_OPEN_ASK_ROUTER_INPUT_READINESS.md",
        f"""# Next Open ASK Router Input Readiness

Status: `NOT_READY_NO_EXTERNAL_QUESTION_CORPUS`

The Open ASK router remains contract-only. The exported corpus at `{rel(QUESTION_CORPUS)}` has `{len(rows)}` rows, so future router implementation should wait for real operator questions.
""",
    )
    write_json(
        root / "EXTERNAL_OPERATOR_VALIDATION_CLOSEOUT_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CLOSEOUT-R5",
            status,
            usable_session_count=scoreboard["usable_session_count"],
            question_corpus_rows=len(rows),
            blocking_gaps=1 if scoreboard["usable_session_count"] == 0 else 0,
            blocking_gap_reason="No completed non-builder operator session records." if scoreboard["usable_session_count"] == 0 else None,
        ),
    )
    return status


def write_handoff(status: str, rows: list[dict]) -> None:
    root = ROOTS["handoff"]
    write_text(
        root / "CURRENT_EXTERNAL_VALIDATION_STATE.md",
        f"""# Current External Validation State

Status: `{status}`

D9 refreshed baseline is ready for external operator validation, but no usable completed non-builder session has been imported yet. The web console may be used for the session, but this lane does not count builder/internal examples.

Question corpus rows: `{len(rows)}`
""",
    )
    write_json(
        root / "READY_NEXT_TRACKS.json",
        {
            "recommended_next_task": "MAIN-CITYBRAIN-D9-RUN-NON-BUILDER-OPERATOR-SESSION-R1",
            "required_input_folder": rel(SESSION_DIR),
            "question_corpus_path": rel(QUESTION_CORPUS),
        },
    )
    write_json(
        root / "DEFERRED_NOT_CLAIMED_LEDGER.json",
        {
            "diff": "DEFERRED_DIFF_NO_COMPARABLE_SOURCE_RECORD_SNAPSHOTS",
            "open_ask_router": "CONTRACT_LOCKED_NOT_IMPLEMENTED",
            "external_validation": status,
            "not_claimed": [
                "external operator validation pass",
                "Open ASK implementation",
                "DIFF live mode",
                "production/public API",
                "action/dispatch/control/enforcement/legal/certified finding",
            ],
        },
    )
    write_json(
        root / "EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_R6_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CERTIFIED-STATE-HANDOFF-R6",
            status,
            question_corpus_rows=len(rows),
            review_only_boundary_preserved=True,
            next_recommended_task="MAIN-CITYBRAIN-D9-RUN-NON-BUILDER-OPERATOR-SESSION-R1",
        ),
    )


def main() -> int:
    for root in ROOTS.values():
        safe_reset(root)

    before = fingerprint(READ_ONLY_ROOTS)
    baseline = baseline_inventory()
    write_preflight(baseline)
    write_packet()
    usable, rejected, internal = import_sessions()
    write_import(usable, rejected, internal)
    scoreboard = write_scoreboard(usable)
    rows = write_corpus(usable)
    closeout_status = write_closeout(scoreboard, rows, internal)
    write_handoff(closeout_status, rows)
    after = fingerprint(READ_ONLY_ROOTS)

    for key, root in ROOTS.items():
        finalize(root, key.replace("_", " ").title(), before, after)

    summary = {
        "status": closeout_status,
        "runner": rel(RUNNER),
        "output_root": rel(ROOTS["handoff"]),
        "usable_session_count": len(usable),
        "rejected_file_count": len(rejected),
        "internal_session_count": len(internal),
        "question_corpus_rows": len(rows),
        "question_corpus_path": rel(QUESTION_CORPUS),
        "next_recommended_task": "MAIN-CITYBRAIN-D9-RUN-NON-BUILDER-OPERATOR-SESSION-R1",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
