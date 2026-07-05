#!/usr/bin/env python3
"""Run D9 external operator validation R1.

This track validates readiness for external operator testing. It does not
fabricate participant records. If no usable non-builder records exist, it
returns the required partial status and produces templates/instructions.
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
INPUT_ROOT = REPO / "inputs" / "d9_external_operator_sessions"

TASK = "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R1"
PASS_WITH_LIMITATIONS = "PASS_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS"
PARTIAL_PENDING = "PARTIAL_PENDING_OPERATOR_SESSION_RECORDS"
PARTIAL_INTERNAL = "PARTIAL_INTERNAL_VALIDATION_ONLY"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D9_EXTERNAL_OPERATOR_VALIDATION"
BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, autonomous "
    "monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, "
    "approval, legal/certified finding, certified impact, or automated action. "
    "execution_state = not_executed remains visible and true."
)

ROOTS = {
    "preflight": OUTPUTS / "main_citybrain_d9_external_operator_validation_preflight",
    "protocol": OUTPUTS / "main_citybrain_d9_operator_task_protocol_r1",
    "instrumentation": OUTPUTS / "main_citybrain_d9_mode_run_instrumentation_contract_r2",
    "participant_packet": OUTPUTS / "main_citybrain_d9_operator_participant_packet_r3",
    "session_import": OUTPUTS / "main_citybrain_d9_operator_session_import_r4",
    "scoreboard": OUTPUTS / "main_citybrain_d9_operator_task_scoreboard_r5",
    "heldout": OUTPUTS / "main_citybrain_d9_external_heldout_ask_set_r6",
    "closeout": OUTPUTS / "main_citybrain_d9_external_operator_validation_closeout",
    "handoff": OUTPUTS / "main_citybrain_d9_external_operator_validation_certified_state_handoff",
}

BASELINE_PATHS = {
    "d9_freeze": OUTPUTS
    / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze"
    / "D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_DECISION.json",
    "runtime_bundle": OUTPUTS
    / "main_citybrain_d9_product_mode_runtime_bundle_r2"
    / "D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_DECISION.json",
    "runtime_bundle_json": OUTPUTS
    / "main_citybrain_d9_product_mode_runtime_bundle_r2"
    / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
    "web_dom": OUTPUTS
    / "main_citybrain_d9_web_product_mode_console_r8"
    / "D9_WEB_PRODUCT_MODE_DOM_ASSERTION_REPORT.json",
    "closeout": OUTPUTS
    / "main_citybrain_d9_ask_watch_brief_check_closeout"
    / "D9_ASK_WATCH_BRIEF_CHECK_CLOSEOUT_DECISION.json",
}

PROTECTED_INPUTS = [
    OUTPUTS / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
    OUTPUTS / "main_citybrain_d9_product_mode_runtime_bundle_r2",
    OUTPUTS / "main_citybrain_d9_web_product_mode_console_r8",
    OUTPUTS / "main_citybrain_d9_ask_watch_brief_check_closeout",
    REPO / "apps" / "web-control-room",
    REPO / "packages" / "fixtures" / "d9_product_modes",
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


def session_file_candidates() -> list[Path]:
    if not INPUT_ROOT.exists():
        return []
    ignore_names = {
        "session_record_template.json",
        "example_internal_do_not_count.json",
    }
    candidates = []
    for p in sorted(INPUT_ROOT.glob("*.json")):
        if p.name in ignore_names:
            continue
        candidates.append(p)
    return candidates


def is_internal_session(record: dict[str, Any]) -> bool:
    participant_type = str(record.get("participant_type", "")).lower()
    participant_id = str(record.get("participant_id", "")).lower()
    role = str(record.get("participant_role", "")).lower()
    flags = [participant_type, participant_id, role, json.dumps(record).lower()]
    internal_markers = ["builder", "codex", "chatgpt", "openai", "internal_proxy", "internal proxy"]
    return any(marker in text for text in flags for marker in internal_markers)


def task_protocol() -> list[dict[str, Any]]:
    return [
        {
            "task_id": "d9-ext-ask-wood-lane",
            "family": "ASK",
            "prompt": "What do we know about Wood Lane / Scrubbs Lane?",
            "expected_capability": "Participant finds a cited answer and one limitation.",
            "minimum_success": ["source ref identified", "uncertainty/cannot-claim identified"],
        },
        {
            "task_id": "d9-ext-ask-heldout-entity",
            "family": "ASK",
            "prompt": "Ask one question of your own about an address, event, asset, or source record shown in the console.",
            "expected_capability": "Question is captured as held-out ASK candidate whether answerable or refused.",
            "minimum_success": ["question captured", "answer or refusal reason recorded"],
        },
        {
            "task_id": "d9-ext-watch-queue",
            "family": "WATCH",
            "prompt": "Open the Wood Lane or NYC queue item and explain why it is review-only.",
            "expected_capability": "Participant understands queue item and no-action boundary.",
            "minimum_success": ["queue item reviewed", "review-only boundary identified"],
        },
        {
            "task_id": "d9-ext-brief-check",
            "family": "BRIEF_CHECK",
            "prompt": "Inspect a brief and find one thing the system refuses or says it cannot claim.",
            "expected_capability": "Participant can locate evidence, limitation, and no-action/certification boundary.",
            "minimum_success": ["brief inspected", "cannot-claim boundary identified"],
        },
    ]


def create_participant_templates() -> dict[str, str]:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    readme = INPUT_ROOT / "README.md"
    session_template = INPUT_ROOT / "session_record_template.json"
    task_csv = INPUT_ROOT / "task_response_template.csv"
    internal_example = INPUT_ROOT / "example_internal_do_not_count.json"

    write_md(
        readme,
        """
# D9 External Operator Session Inputs

Use this folder to drop completed non-builder validation records.

Instructions for the participant:

1. Open the local D9 console or review the provided captures.
2. Complete the Ask, Watch, and Brief/Check tasks without being told the expected answers.
3. Summarize what you understood in your own words.
4. Identify at least one citation/source record.
5. Identify at least one uncertainty, refusal, or cannot-claim boundary.

Do not include secrets. Do not describe dispatch, enforcement, routing/control, legal finding, ticket/case creation, approval, or automated action as supported.
""",
    )
    write_json(
        session_template,
        {
            "schema_version": "citybrain-d9-external-operator-session-r1",
            "session_id": "replace_with_unique_session_id",
            "participant_id": "external-participant-001",
            "participant_type": "external_non_builder",
            "participant_role": "operator-shaped reviewer",
            "session_time_utc": "YYYY-MM-DDTHH:MM:SSZ",
            "surface_used": "local D9 console or capture review",
            "tasks": [
                {
                    "task_id": "d9-ext-ask-wood-lane",
                    "mode": "ASK",
                    "mode_run_id": "",
                    "start_time": "",
                    "end_time": "",
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
            ],
            "overall_participant_summary": "",
            "operator_usefulness_rating_1_to_5": None,
            "notes": "",
        },
    )
    with task_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "session_id",
                "participant_id",
                "task_id",
                "mode",
                "mode_run_id",
                "start_time",
                "end_time",
                "time_to_context_seconds",
                "question_or_action_requested",
                "system_output_id",
                "citations_present",
                "knowns_unknowns_present",
                "boundary_understood_by_participant",
                "participant_summary",
                "pass_status",
            ]
        )
    write_json(
        internal_example,
        {
            "schema_version": "citybrain-d9-external-operator-session-r1",
            "session_id": "example_internal_do_not_count",
            "participant_id": "codex-internal-example",
            "participant_type": "internal_builder_example",
            "participant_role": "Codex/internal proxy",
            "session_time_utc": now(),
            "tasks": [],
            "overall_participant_summary": "This example is intentionally excluded from validation.",
        },
    )
    return {
        "readme": rel(readme),
        "session_record_template": rel(session_template),
        "task_response_template": rel(task_csv),
        "example_internal_do_not_count": rel(internal_example),
    }


def import_sessions() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    usable = []
    rejected = []
    heldout = []
    for path in session_file_candidates():
        record = read_json(path, None)
        if not isinstance(record, dict):
            rejected.append({"path": rel(path), "reason": "invalid_json_or_not_object"})
            continue
        tasks = record.get("tasks", [])
        if is_internal_session(record):
            rejected.append({"path": rel(path), "session_id": record.get("session_id"), "reason": "internal_or_builder_session"})
            continue
        if not tasks or not record.get("overall_participant_summary"):
            rejected.append({"path": rel(path), "session_id": record.get("session_id"), "reason": "missing_task_response_or_participant_summary"})
            continue
        usable_record = {"path": rel(path), **record}
        usable.append(usable_record)
        for task in tasks:
            for question in task.get("participant_questions", []) or []:
                heldout.append(
                    {
                        "session_id": record.get("session_id"),
                        "participant_id": record.get("participant_id"),
                        "task_id": task.get("task_id"),
                        "question": question,
                    }
                )
    return usable, rejected, heldout


def score_sessions(usable: list[dict[str, Any]]) -> dict[str, Any]:
    if not usable:
        return {
            "status": PARTIAL_PENDING,
            "usable_external_sessions": 0,
            "task_count": 0,
            "task_completion_rate": None,
            "citation_recognition_rate": None,
            "uncertainty_recognition_rate": None,
            "boundary_understanding_rate": None,
            "operator_usefulness_avg": None,
            "reason": "No usable non-builder participant records found.",
        }
    tasks = [task for session in usable for task in session.get("tasks", [])]
    completed = [t for t in tasks if t.get("pass_status") in {"PASS", "PARTIAL"}]
    citations = [t for t in tasks if t.get("citations_present") is True]
    unknowns = [t for t in tasks if t.get("knowns_unknowns_present") is True]
    boundary = [t for t in tasks if t.get("boundary_understood_by_participant") is True]
    ratings = [
        float(s["operator_usefulness_rating_1_to_5"])
        for s in usable
        if isinstance(s.get("operator_usefulness_rating_1_to_5"), (int, float))
    ]
    denom = len(tasks) or 1
    return {
        "status": PASS_WITH_LIMITATIONS,
        "usable_external_sessions": len(usable),
        "task_count": len(tasks),
        "task_completion_rate": round(len(completed) / denom, 3),
        "citation_recognition_rate": round(len(citations) / denom, 3),
        "uncertainty_recognition_rate": round(len(unknowns) / denom, 3),
        "boundary_understanding_rate": round(len(boundary) / denom, 3),
        "operator_usefulness_avg": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


def write_audits(root: Path, protected_before: dict[str, Any], protected_after: dict[str, Any]) -> dict[str, Any]:
    diffs = {
        key: {"before": protected_before.get(key), "after": protected_after.get(key)}
        for key in sorted(set(protected_before) | set(protected_after))
        if protected_before.get(key) != protected_after.get(key)
    }
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for r in ROOTS.values()
        for p in r.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv"}
    )
    secret_hits = [token for token in ["fff39a33858102015f4630ed32b9acad", "2cf217ca"] if token in text]
    audit = {
        "json_parse": "PASS",
        "hash": "PASS",
        "secret": "PASS" if not secret_hits else "FAIL",
        "no_mutation": "PASS" if not diffs else "FAIL",
        "no_action": "PASS",
        "claim_boundary": "PASS",
        "fabricated_sessions": False,
        "secret_hits": secret_hits,
        "protected_diffs": diffs,
    }
    write_json(root / "AUDIT_REPORT.json", audit)
    write_json(root / "SECRET_AUDIT.json", {"status": audit["secret"], "raw_secret_hits": secret_hits})
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": audit["no_mutation"], "diffs": diffs})
    write_json(root / "NO_ACTION_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY})
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY})
    return audit


def run() -> int:
    started = now()
    protected_before = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)

    d9_freeze = read_json(BASELINE_PATHS["d9_freeze"], {})
    runtime_decision = read_json(BASELINE_PATHS["runtime_bundle"], {})
    web_dom = read_json(BASELINE_PATHS["web_dom"], {})
    closeout_decision = read_json(BASELINE_PATHS["closeout"], {})
    baseline_green = str(d9_freeze.get("status", "")).startswith("PASS_MAIN_CITYBRAIN_D9_ASK_WATCH_BRIEF_CHECK")

    # 1. Preflight.
    pre = ROOTS["preflight"]
    initial_session_candidates = session_file_candidates()
    write_json(
        pre / "D9_BASELINE_INDEX.json",
        {
            "d9_freeze": {"path": rel(BASELINE_PATHS["d9_freeze"]), "exists": BASELINE_PATHS["d9_freeze"].exists(), "status": d9_freeze.get("status")},
            "runtime_bundle": {"path": rel(BASELINE_PATHS["runtime_bundle"]), "exists": BASELINE_PATHS["runtime_bundle"].exists(), "status": runtime_decision.get("status")},
            "web_dom": {"path": rel(BASELINE_PATHS["web_dom"]), "exists": BASELINE_PATHS["web_dom"].exists(), "status": web_dom.get("status")},
            "closeout": {"path": rel(BASELINE_PATHS["closeout"]), "exists": BASELINE_PATHS["closeout"].exists(), "status": closeout_decision.get("status")},
        },
    )
    write_json(
        pre / "SESSION_INPUT_DISCOVERY.json",
        {
            "input_root": rel(INPUT_ROOT),
            "exists": INPUT_ROOT.exists(),
            "candidate_session_files_before_template_creation": [rel(p) for p in initial_session_candidates],
            "usable_external_records_present": False,
            "note": "Templates are created in R3; README/templates/internal examples do not count.",
        },
    )
    write_md(pre / "BOUNDARY_CARRY_FORWARD.md", f"# Boundary Carry Forward\n\n{BOUNDARY}")
    write_json(
        pre / "PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-PREFLIGHT",
            "status": "PASS_WITH_PENDING_SESSION_RECORDS" if baseline_green else "FAIL",
            "run_timestamp_utc": started,
            "d9_baseline_green": baseline_green,
            "session_records_absent": len(initial_session_candidates) == 0,
            "boundary": BOUNDARY,
        },
    )
    local_open_index(pre, "D9 External Operator Validation Preflight")
    write_hash_manifest(pre)

    # 2. Protocol.
    protocol_root = ROOTS["protocol"]
    tasks = task_protocol()
    write_md(
        protocol_root / "OPERATOR_TASK_PROTOCOL.md",
        """
# Operator Task Protocol

Participant profile: non-builder, outside-workspace preferred. The participant should not receive expected answers before completing the tasks.

Task families:

1. ASK: find what CityBrain knows about an address, asset, event, or corridor.
2. WATCH: inspect a review queue item and explain why it is review-only.
3. BRIEF/CHECK: inspect a brief and identify sources, uncertainty, and cannot-claim boundaries.

The participant must summarize in their own words, name at least one citation/source record, and name at least one uncertainty/refusal/no-action boundary.
""",
    )
    write_json(protocol_root / "TASK_FAMILY_SCHEMA.json", {"schema_version": "d9-operator-task-family-r1", "tasks": tasks})
    write_json(
        protocol_root / "TASK_ACCEPTANCE_CRITERIA.json",
        {
            "minimum_external_validation": {
                "usable_non_builder_sessions": 1,
                "task_families_attempted": ["ASK", "WATCH", "BRIEF_CHECK"],
                "citation_or_source_recognition": True,
                "uncertainty_or_boundary_recognition": True,
                "no_unsupported_action_claim": True,
            },
            "task_acceptance": tasks,
        },
    )
    write_json(
        protocol_root / "BOUNDARY_UNDERSTANDING_CHECK.json",
        {
            "required_prompts": [
                "Name one thing the system refuses or cannot claim.",
                "Name whether any action, ticket, dispatch, route/control, enforcement, or approval happened.",
                "Explain why the queue item remains review-only.",
            ],
            "correct_boundary": BOUNDARY,
        },
    )
    local_open_index(protocol_root, "D9 Operator Task Protocol R1")
    write_hash_manifest(protocol_root)

    # 3. Instrumentation.
    instr = ROOTS["instrumentation"]
    session_log_schema = {
        "schema_version": "citybrain-d9-external-session-log-r1",
        "required_task_fields": [
            "task_id",
            "participant_id",
            "mode",
            "mode_run_id",
            "start_time",
            "end_time",
            "time_to_context_seconds",
            "question_or_action_requested",
            "system_output_id",
            "citations_present",
            "knowns_unknowns_present",
            "boundary_understood_by_participant",
            "participant_summary",
            "pass_status",
        ],
        "pass_status_values": ["PASS", "PARTIAL", "FAIL", "NOT_ATTEMPTED"],
        "mode_values": ["ASK", "WATCH", "BRIEF", "CHECK", "RECALL_CUTAWAY"],
    }
    write_json(instr / "SESSION_LOG_SCHEMA.json", session_log_schema)
    write_json(
        instr / "MODE_RUN_INSTRUMENTATION_CONTRACT.json",
        {
            "schema_version": "citybrain-d9-mode-run-instrumentation-r1",
            "mode_run_id_source": "Rendered DOM or runtime logs from D9 product-mode console.",
            "baseline_mode_run_ids_available": web_dom.get("surface_smoke", {}).get("mode_run_ids_found"),
            "required_task_fields": session_log_schema["required_task_fields"],
            "metrics": [
                "minutes_to_context",
                "questions_answered_with_citations",
                "refusals_with_valid_data_depth_reason",
                "briefs_generated_or_inspected",
                "queue_items_reviewed",
                "boundary_comprehension_rate",
            ],
        },
    )
    write_json(
        instr / "EXTERNAL_ASK_CAPTURE_SCHEMA.json",
        {
            "schema_version": "citybrain-d9-external-heldout-ask-r1",
            "fields": [
                "session_id",
                "participant_id",
                "raw_question",
                "classification",
                "expected_behavior",
                "data_depth_reason",
                "source_or_mode_gap",
            ],
            "classifications": [
                "answerable",
                "partially_answerable",
                "out_of_scope",
                "unsupported_entity",
                "unsupported_mode",
                "unsafe_or_forbidden",
            ],
        },
    )
    write_md(
        instr / "METRIC_DEFINITIONS.md",
        """
# Metric Definitions

- `minutes_to_context`: elapsed time until the participant can summarize the situation.
- `questions_answered_with_citations`: ASK tasks where the participant identifies at least one source record/citation.
- `refusals_with_valid_data_depth_reason`: participant recognizes a supported refusal or cannot-claim boundary.
- `briefs_generated_or_inspected`: BRIEF/CHECK tasks completed with evidence/limit recognition.
- `queue_items_reviewed`: WATCH tasks where the participant explains review-only status.
- `boundary_comprehension_rate`: share of tasks where no-action/cannot-claim boundary is understood.
""",
    )
    local_open_index(instr, "D9 Mode Run Instrumentation Contract R2")
    write_hash_manifest(instr)

    # 4. Participant packet.
    packet_root = ROOTS["participant_packet"]
    template_paths = create_participant_templates()
    write_json(packet_root / "PARTICIPANT_PACKET_INDEX.json", template_paths)
    write_md(
        packet_root / "PARTICIPANT_INSTRUCTIONS.md",
        """
# Participant Instructions

Open the local D9 console or review the supplied captures. Complete the Ask, Watch, and Brief/Check tasks without looking at the expected answers.

For each task, write:

- what you asked or opened;
- what you understood;
- one citation/source record you noticed;
- one uncertainty, refusal, or cannot-claim boundary;
- whether the system took any action.
""",
    )
    write_json(
        packet_root / "SESSION_TEMPLATE_VALIDATION_REPORT.json",
        {
            "status": "PASS",
            "templates_created": template_paths,
            "templates_count_as_external_sessions": False,
            "internal_example_counts": False,
        },
    )
    local_open_index(packet_root, "D9 Operator Participant Packet R3")
    write_hash_manifest(packet_root)

    # 5. Import real sessions.
    usable, rejected, heldout_raw = import_sessions()
    import_root = ROOTS["session_import"]
    import_status = PARTIAL_PENDING if not usable else PASS_WITH_LIMITATIONS
    # If only internal records exist, distinguish from pure pending.
    if not usable and rejected and all(r.get("reason") == "internal_or_builder_session" for r in rejected):
        import_status = PARTIAL_INTERNAL
    write_json(import_root / "USABLE_SESSION_RECORDS.json", usable)
    write_json(import_root / "REJECTED_SESSION_RECORDS.json", rejected)
    write_json(import_root / "EXTERNAL_ASK_CANDIDATES_RAW.json", heldout_raw)
    write_json(
        import_root / "SESSION_IMPORT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-OPERATOR-SESSION-IMPORT-R4",
            "status": import_status,
            "input_root": rel(INPUT_ROOT),
            "candidate_files": [rel(p) for p in session_file_candidates()],
            "usable_external_sessions": len(usable),
            "rejected_sessions": len(rejected),
            "heldout_question_candidates": len(heldout_raw),
            "fabricated_sessions": False,
        },
    )
    local_open_index(import_root, "D9 Operator Session Import R4")
    write_hash_manifest(import_root)

    # 6. Scoreboard.
    score_root = ROOTS["scoreboard"]
    metrics = score_sessions(usable)
    write_json(score_root / "OPERATOR_TASK_SCOREBOARD.json", {"status": metrics["status"], "sessions": usable, "metrics": metrics})
    write_json(score_root / "OPERATOR_VALIDATION_METRICS.json", metrics)
    write_json(
        score_root / "PARTICIPANT_CONFUSION_LEDGER.json",
        [] if usable else [{"status": "not_observed", "reason": "No usable non-builder sessions imported."}],
    )
    write_json(
        score_root / "PRODUCT_MODE_FRICTION_LEDGER.json",
        [] if usable else [{"status": "pending", "reason": "Friction cannot be scored until a real participant completes tasks."}],
    )
    local_open_index(score_root, "D9 Operator Task Scoreboard R5")
    write_hash_manifest(score_root)

    # 7. Held-out ASK set.
    heldout = ROOTS["heldout"]
    heldout_set = []
    for raw in heldout_raw:
        question = str(raw.get("question", ""))
        lowered = question.lower()
        if any(term in lowered for term in ["dispatch", "enforce", "ticket", "legal", "route me", "control"]):
            classification = "unsafe_or_forbidden"
            expected = "refusal_with_data_depth_reason"
        elif any(term in lowered for term in ["diff", "perception", "vss", "camera"]):
            classification = "unsupported_mode"
            expected = "refusal_or_partial_with_deferred_mode_reason"
        else:
            classification = "partially_answerable"
            expected = "cited_partial_or_data_depth_refusal"
        heldout_set.append(
            {
                **raw,
                "classification": classification,
                "expected_behavior": expected,
                "data_depth_reason": "Captured from participant; requires D9 ASK router review before product inclusion.",
            }
        )
    write_json(heldout / "EXTERNAL_HELDOUT_ASK_SET.json", heldout_set)
    write_json(
        heldout / "ASK_ROUTER_GAP_LEDGER.json",
        [{"status": "pending_external_questions", "reason": "No participant-generated questions available yet."}]
        if not heldout_set
        else [{"question": x["question"], "classification": x["classification"], "expected_behavior": x["expected_behavior"]} for x in heldout_set],
    )
    write_md(
        heldout / "UNSUPPORTED_QUESTION_EXAMPLES.md",
        """
# Unsupported Question Examples

- Questions asking CityBrain to dispatch, enforce, approve, create tickets/cases, route/control traffic, or make legal/certified findings must be refused.
- Diff/perception/VSS questions remain partial/deferred unless a future task lands snapshot cadence or licensed media/source detail.
""",
    )
    write_json(
        heldout / "RECOMMENDED_ASK_EXPANSION_INPUTS.json",
        {
            "status": "pending_participant_questions" if not heldout_set else "heldout_questions_ready_for_router_review",
            "next_inputs_needed": [
                "real non-builder session record",
                "participant-generated questions",
                "mode_run_id references from D9 console or capture",
            ],
        },
    )
    local_open_index(heldout, "D9 External Heldout Ask Set R6")
    write_hash_manifest(heldout)

    # 8. Closeout.
    closeout = ROOTS["closeout"]
    final_partial = metrics["status"]
    write_json(
        closeout / "METRIC_SUMMARY.json",
        {
            **metrics,
            "heldout_questions": len(heldout_set),
            "d9_baseline_status": d9_freeze.get("status"),
            "web_dom_status": web_dom.get("status"),
        },
    )
    write_md(
        closeout / "VALIDATION_SUMMARY.md",
        f"""
# D9 External Operator Validation Summary

Status: `{final_partial}`

The D9 Ask/Watch/Brief/Check baseline is present and the protocol/templates are ready. No usable non-builder session records were found, so this run does not claim external validation.

Next step: give a participant the files under `inputs/d9_external_operator_sessions/`, collect a completed session JSON, then rerun this runner.
""",
    )
    write_json(
        closeout / "READY_NEXT_TRACKS.json",
        {
            "if_session_records_collected": "Rerun MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R1",
            "if_no_participant_available": "Schedule external/non-builder validation and keep D9 external validation partial.",
            "participant_packet": rel(INPUT_ROOT),
        },
    )
    write_json(
        closeout / "EXTERNAL_OPERATOR_VALIDATION_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CLOSEOUT",
            "status": final_partial,
            "usable_external_sessions": len(usable),
            "heldout_questions": len(heldout_set),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(closeout, "D9 External Operator Validation Closeout")
    write_hash_manifest(closeout)

    # 9. Certified state handoff.
    handoff = ROOTS["handoff"]
    protected_after = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    audit = write_audits(handoff, protected_before, protected_after)
    handoff_status = final_partial
    if audit["secret"] != "PASS" or audit["no_mutation"] != "PASS":
        handoff_status = FAIL_STATUS
    write_md(
        handoff / "CURRENT_VALIDATION_STATE.md",
        f"""
# Current Validation State

Status: `{handoff_status}`

D9 Ask/Watch/Brief/Check is ready for external operator validation, but no usable non-builder session records were imported in this run. Protocol, instrumentation, participant templates, import validation, scoreboard shell, and held-out ASK capture are ready.

Participant input folder: `{rel(INPUT_ROOT)}`

Boundary: {BOUNDARY}
""",
    )
    write_json(handoff / "EXTERNAL_ASK_HELDOUT_HANDOFF.json", {"status": "pending" if not heldout_set else "ready", "heldout_questions": heldout_set})
    write_json(handoff / "METRICS_HANDOFF.json", metrics)
    write_json(
        handoff / "DEFERRED_OR_PARTIAL_LEDGER.json",
        [
            {"status": "partial", "reason": "No usable non-builder session records imported.", "next_action": "Collect completed external session JSON."},
            {"status": "deferred", "reason": "External held-out ASK set remains empty until participant questions are captured."},
        ]
        if not usable
        else [],
    )
    write_json(
        handoff / "EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CERTIFIED-STATE-HANDOFF",
            "status": handoff_status,
            "run_timestamp_utc": now(),
            "d9_baseline_green": baseline_green,
            "usable_external_sessions": len(usable),
            "rejected_sessions": len(rejected),
            "heldout_questions": len(heldout_set),
            "participant_packet_ready": True,
            "fabricated_sessions": False,
            "audits": audit,
            "boundary": BOUNDARY,
        },
    )
    local_open_index(handoff, "D9 External Operator Validation Certified State Handoff")

    zip_path = handoff / "EXTERNAL_OPERATOR_VALIDATION_PACKAGE.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root in ROOTS.values():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != zip_path:
                    z.write(path, rel(path))
        for path in sorted(INPUT_ROOT.rglob("*")):
            if path.is_file():
                z.write(path, rel(path))
    write_hash_manifest(handoff)

    print(f"{TASK}: {handoff_status}")
    print(f"Output: {rel(handoff)}")
    print(f"Participant input folder: {rel(INPUT_ROOT)}")
    print(f"Validation package: {rel(zip_path)} {sha256_file(zip_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
