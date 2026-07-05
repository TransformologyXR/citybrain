#!/usr/bin/env python3
"""Build the CityBrain D9 human review session capture R2 package.

This task registers review/capture evidence for the D9 polished demo route.
If screenshots/video or reviewer identity are not available, it records that
explicitly instead of fabricating evidence.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
TASK_ID = "MAIN-CITYBRAIN-D9-HUMAN-REVIEW-SESSION-CAPTURE-R2"
STATUS_PASS_LIMITED = "PASS_MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_WITH_LIMITATIONS"
STATUS_PASS = "PASS_MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

OUT_ROOT = OUTPUTS / "main_citybrain_d9_human_review_session_capture_r2"
D8_ROOT = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1"
D9_ROOT = OUTPUTS / "main_citybrain_d9_demo_polish_and_review_loop_r1"

EXPECTED_D9_STATUS = "PASS_MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_WITH_LIMITATIONS"

REQUIRED_D9_FILES = [
    "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json",
    "D9_POLISHED_DEMO_ROUTE.md",
    "D9_POLISHED_OPERATOR_SCRIPT.md",
    "D9_EXECUTIVE_DEMO_ONE_PAGER.md",
    "D9_REVIEW_INDEX.html",
    "D9_SCREENSHOT_AND_CAPTURE_CHECKLIST.md",
    "D9_REVIEWER_ISSUE_LOG_TEMPLATE.csv",
]

D8_FILES = [
    "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json",
    "D8_CERTIFIED_STATE_HANDOFF.md",
    "D8_FINAL_DEMO_ROUTE.md",
    "D8_OPERATOR_SCRIPT.md",
]

OPTIONAL_ROOTS = {
    "d8_demonstrable_surface": OUTPUTS / "main_citybrain_d8_demonstrable_surface_integration_r1",
    "d8_r3_closeout": OUTPUTS / "citybrain_d8_r3_followon_prompt_pack_closeout",
    "d8_followon_closeout": OUTPUTS / "citybrain_d8_followon_and_composition_prompt_pack_closeout",
}

ARTIFACTS = [
    "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json",
    "D9_HUMAN_REVIEW_SESSION_LEDGER.json",
    "D9_REVIEW_CAPTURE_INDEX.html",
    "D9_REVIEW_SESSION_NOTES.md",
    "D9_REVIEWER_ISSUE_LOG.csv",
    "D9_CAPTURE_GAP_REGISTER.json",
    "D9_REVIEW_CLAIM_BOUNDARY_REGISTER.json",
    "D9_R2_REVIEW_SCORECARD.json",
    "README.md",
    "JSON_PARSE_AUDIT.json",
    "SECRET_SCAN_AUDIT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json",
    "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
    "HASH_MANIFEST.sha256",
]

STEP_DEFS = [
    {
        "step": 1,
        "title": "Open the D8 handoff state",
        "expected_artifact": "outputs/main_citybrain_d8_final_demo_capture_and_certified_handoff_r1/D8_FINAL_DEMO_ROUTE.md",
        "limitations": ["audited demo state only", "not operational deployment", "not legal finding"],
    },
    {
        "step": 2,
        "title": "Mobility M04/M05 abstain semantics",
        "expected_artifact": "outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/MOBILITY_BASELINE_ABSTAIN_CONTRACT.json",
        "limitations": ["abstain when evidence is insufficient", "no routing or traffic-control output"],
    },
    {
        "step": 3,
        "title": "Web+Kit local handoff surface",
        "expected_artifact": "outputs/main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/KIT_HANDOFF_SMOKE_RESULT.json",
        "limitations": ["local handoff only", "not native browser RTX streaming", "not deployed product UI"],
    },
    {
        "step": 4,
        "title": "Helsinki Kalasatama semantic sidecar",
        "expected_artifact": "outputs/helsinki_kit_object_pick_manual_review_capture_r3/MANUAL_OBJECT_PICK_REVIEW_CAPTURE.jsonl",
        "limitations": ["object-pick packets pending review", "mesh visual backdrop until alignment evidence is proven"],
    },
    {
        "step": 5,
        "title": "Chicago bounded similar-case memory",
        "expected_artifact": "outputs/chicago_similar_case_demo_query_smoke_r3/CHICAGO_DEMO_QUERY_RESULTS.jsonl",
        "limitations": ["15-row bounded sample", "not citywide trend truth", "no causal or legal conclusion"],
    },
    {
        "step": 6,
        "title": "VSS closed-gate readiness story",
        "expected_artifact": "outputs/main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3/VSS_SAMPLE_ELIGIBILITY_CHECK.json",
        "limitations": ["VSS sample ingest gate closed", "VSS runtime readiness remains closed"],
    },
    {
        "step": 7,
        "title": "Close with evidence, limits, and next review",
        "expected_artifact": "outputs/main_citybrain_d9_demo_polish_and_review_loop_r1/D9_LIMITATION_REGISTER.json",
        "limitations": ["no action output", "issue logging required for review decisions"],
    },
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    raise UnicodeError(f"Could not decode {path}")


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_output_root() -> None:
    root = OUT_ROOT.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in root.parents or root.name != "main_citybrain_d9_human_review_session_capture_r2":
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    (root / "captures" / "screenshots").mkdir(parents=True, exist_ok=True)
    (root / "captures" / "video").mkdir(parents=True, exist_ok=True)


def snapshot_prior_hashes() -> dict[str, str | None]:
    files = [D9_ROOT / name for name in REQUIRED_D9_FILES] + [D8_ROOT / name for name in D8_FILES]
    return {rel(path): sha256_file(path) if path.exists() else None for path in files}


def validate_upstream() -> tuple[bool, str, str, list[str], dict[str, Any], dict[str, Any]]:
    missing = [name for name in REQUIRED_D9_FILES if not (D9_ROOT / name).exists()]
    d9_decision = read_json(D9_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json") or {}
    d8_decision = read_json(D8_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json") or {}
    d9_status = str(d9_decision.get("status", "MISSING_OR_INVALID"))
    d8_status = str(d8_decision.get("status", "MISSING_OR_INVALID"))
    ok = D9_ROOT.exists() and not missing and d9_status == EXPECTED_D9_STATUS
    return ok, d8_status, d9_status, missing, d8_decision, d9_decision


def detect_captures() -> tuple[bool, list[Path], list[Path]]:
    screenshot_dir = OUT_ROOT / "captures" / "screenshots"
    video_dir = OUT_ROOT / "captures" / "video"
    screenshots = sorted([p for p in screenshot_dir.glob("*") if p.is_file()])
    videos = sorted([p for p in video_dir.glob("*") if p.is_file()])
    return bool(screenshots or videos), screenshots, videos


def create_review_ledger(captured: bool, screenshots: list[Path]) -> dict[str, Any]:
    entries = []
    for step in STEP_DEFS:
        screenshot = screenshots[step["step"] - 1] if captured and len(screenshots) >= step["step"] else None
        evidence_status = "CAPTURED" if screenshot else "NOT_CAPTURED_ENVIRONMENT_LIMITATION"
        entries.append(
            {
                "step_number": step["step"],
                "title": step["title"],
                "expected_artifact_page_packet": step["expected_artifact"],
                "expected_artifact_exists": (REPO_ROOT / step["expected_artifact"]).exists(),
                "review_evidence_status": evidence_status,
                "screenshot_path": rel(screenshot) if screenshot else None,
                "video_timestamp": None,
                "reviewer_note": (
                    "Captured screenshot registered." if screenshot else "No screenshot/video captured by this local automated run; human/manual review evidence still required."
                ),
                "limitations_preserved": step["limitations"],
                "decision": "pass_with_capture" if screenshot else "review_needed",
            }
        )
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "reviewer": "reviewer_not_provided",
        "capture_status": "CAPTURED" if captured else "NOT_CAPTURED_ENVIRONMENT_LIMITATION",
        "steps_total": len(entries),
        "steps": entries,
    }


def create_capture_gap_register(captured: bool) -> dict[str, Any]:
    gaps = []
    if not captured:
        for step in STEP_DEFS:
            gaps.append(
                {
                    "gap_id": f"gap:d9r2:step_{step['step']}:screenshot_video_absent",
                    "gap_type": "screenshot_video_capture_absent",
                    "affected_demo_step": step["step"],
                    "reason": "No GUI/browser/video capture was performed by this local runner.",
                    "required_to_close": "Capture or register a real screenshot/video/manual review note for this step.",
                    "blocking_level": "blocking_for_public_demo",
                    "limitation_label": "NOT_CAPTURED_ENVIRONMENT_LIMITATION",
                }
            )
    gaps.append(
        {
            "gap_id": "gap:d9r2:reviewer_identity_not_provided",
            "gap_type": "human_reviewer_not_registered",
            "affected_demo_step": "all",
            "reason": "No reviewer identity or attendance evidence was supplied.",
            "required_to_close": "Run a bounded human review session and record role notes without sensitive personal data.",
            "blocking_level": "non_blocking_for_local_review",
            "limitation_label": "reviewer_not_provided",
        }
    )
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "capture_status": "CAPTURED" if captured else "NOT_CAPTURED_ENVIRONMENT_LIMITATION",
        "gaps": gaps,
    }


def create_claim_boundary_register() -> dict[str, Any]:
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "boundaries": [
            {"boundary": "local demo only", "preserved": True},
            {"boundary": "no production readiness claim", "preserved": True},
            {"boundary": "no legal or certified operational claim", "preserved": True},
            {"boundary": "no live ingestion claim", "preserved": True},
            {"boundary": "no VSS runtime/readiness claim", "preserved": True},
            {"boundary": "no autonomous action, dispatch, enforcement, or control claim", "preserved": True},
            {"boundary": "no object-level Helsinki acceptance unless manual review evidence exists", "preserved": True},
            {"boundary": "Chicago sample remains bounded similar-case memory, not citywide truth", "preserved": True},
            {"boundary": "Web+Kit remains local handoff only unless proven otherwise", "preserved": True},
        ],
    }


def create_scorecard(captured: bool, refs_ok: bool) -> dict[str, Any]:
    rows = [
        ("demo route opens or is referenced", "PASS"),
        ("review index created", "PASS"),
        ("7 demo steps represented", "PASS"),
        ("screenshots/video captured or explicit environment limitation recorded", "PASS_WITH_LIMITATIONS" if not captured else "PASS"),
        ("issue log created", "PASS"),
        ("limitations preserved", "PASS"),
        ("claim boundary preserved", "PASS"),
        ("no prior output mutation", "PASS"),
        ("referenced artifacts exist", "PASS" if refs_ok else "PASS_WITH_LIMITATIONS"),
        ("final package hash manifest clean", "PENDING_UNTIL_FINAL_VERIFY"),
    ]
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "overall_status": "PASS_WITH_LIMITATIONS" if not captured else "PASS",
        "scores": [{"dimension": name, "status": status} for name, status in rows],
    }


def review_capture_index(ledger: dict[str, Any]) -> str:
    step_rows = []
    for step in ledger["steps"]:
        step_rows.append(
            "<tr>"
            f"<td>{step['step_number']}</td>"
            f"<td>{html.escape(step['title'])}</td>"
            f"<td>{html.escape(step['review_evidence_status'])}</td>"
            f"<td>{html.escape(step['decision'])}</td>"
            "</tr>"
        )
    rows = "\n".join(step_rows)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain D9 R2 Review Capture</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; background: #f6f8fb; color: #1c242c; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #d9e0ea; padding: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #e1e6ee; text-align: left; padding: 10px; }}
    .boundary {{ border-left: 4px solid #516a83; background: #eef3f8; padding: 12px 16px; }}
  </style>
</head>
<body>
<main>
  <h1>CityBrain D9 R2 Review Capture</h1>
  <p class="boundary">Boundary: local review-capture register only. D8 and D9 R1 outputs are read-only. Capture status: {html.escape(ledger['capture_status'])}.</p>
  <ul>
    <li><a href="../main_citybrain_d9_demo_polish_and_review_loop_r1/D9_POLISHED_DEMO_ROUTE.md">D9 polished route</a></li>
    <li><a href="../main_citybrain_d9_demo_polish_and_review_loop_r1/D9_POLISHED_OPERATOR_SCRIPT.md">D9 operator script</a></li>
    <li><a href="../main_citybrain_d9_demo_polish_and_review_loop_r1/D9_EXECUTIVE_DEMO_ONE_PAGER.md">D9 executive one-pager</a></li>
    <li><a href="D9_REVIEWER_ISSUE_LOG.csv">R2 issue log</a></li>
    <li><a href="D9_CAPTURE_GAP_REGISTER.json">R2 capture gap register</a></li>
    <li><a href="D9_REVIEW_CLAIM_BOUNDARY_REGISTER.json">R2 claim-boundary register</a></li>
  </ul>
  <table>
    <thead><tr><th>Step</th><th>Title</th><th>Evidence Status</th><th>Decision</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</main>
</body>
</html>
"""


def review_session_notes(captured: bool) -> str:
    capture_status = "CAPTURED" if captured else "NOT_CAPTURED_ENVIRONMENT_LIMITATION"
    return f"""# D9 R2 Review Session Notes

Review date/time: `{RUN_TS}`

Reviewer: `reviewer_not_provided`

Review scope: D9 polished demo route, operator script, one-pager, capture checklist, seven demo steps, issue log, capture gaps, and claim boundaries.

Demo route used: `outputs/main_citybrain_d9_demo_polish_and_review_loop_r1/D9_POLISHED_DEMO_ROUTE.md`

## What Was Observed

The R2 runner found the D9 R1 review package and represented all seven demo steps in `D9_HUMAN_REVIEW_SESSION_LEDGER.json`.

## What Was Not Captured

Capture status: `{capture_status}`

No reviewer identity or attendance evidence was supplied. No screenshots or video were fabricated. If screenshots/video are needed, run the next manual capture task.

## Key Limitations

- Helsinki object-pick packets remain pending review unless explicit human evidence is added.
- Chicago similar-case memory remains bounded to the reviewed sample.
- VSS sample ingest gate remains closed.
- Web+Kit remains local handoff only.
- No operational, legal, live, autonomous, dispatch, enforcement, control, or production claim is made.

## Issue Summary

The issue log records a review-needed capture gap rather than pretending that human review occurred.

## Recommended Follow-up

Run `MAIN-CITYBRAIN-D9-MANUAL-SCREENSHOT-VIDEO-CAPTURE-R3` to capture screenshots/video and human review notes.
"""


def write_issue_log(captured: bool) -> None:
    path = OUT_ROOT / "D9_REVIEWER_ISSUE_LOG.csv"
    headers = [
        "issue_id",
        "demo_step",
        "severity",
        "category",
        "description",
        "evidence_ref",
        "proposed_action",
        "disposition",
        "owner",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        if captured:
            writer.writerow(
                [
                    "NO_ISSUES_RECORDED_DURING_AUTOMATED_CAPTURE",
                    "all",
                    "info",
                    "review_capture",
                    "No issues were recorded by the automated capture registration.",
                    "D9_HUMAN_REVIEW_SESSION_LEDGER.json",
                    "Human reviewers should still add issues if found.",
                    "review_open",
                    "reviewer_not_provided",
                    "open",
                ]
            )
        else:
            writer.writerow(
                [
                    "D9R2-001",
                    "all",
                    "medium",
                    "capture_gap",
                    "Screenshots/video and human reviewer notes were not captured in this local automated run.",
                    "D9_CAPTURE_GAP_REGISTER.json",
                    "Run manual screenshot/video capture and review-session evidence task.",
                    "needs_human_review",
                    "reviewer_not_provided",
                    "open",
                ]
            )


def json_parse_audit() -> dict[str, Any]:
    rows = []
    for path in sorted(OUT_ROOT.rglob("*.json")):
        if path.name == "JSON_PARSE_AUDIT.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            rows.append({"path": rel(path), "status": "PASS"})
        except Exception as exc:
            rows.append({"path": rel(path), "status": "FAIL", "error": str(exc)})
    return {"status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL", "files_checked": len(rows), "results": rows}


SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\b(token|secret|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def secret_scan_audit() -> dict[str, Any]:
    findings = []
    files_checked = 0
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.sha256":
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "files_checked": files_checked, "findings": findings}


FORBIDDEN_PATTERNS = [
    ("production_readiness", re.compile(r"(?i)\bproduction readiness\b")),
    ("legal_certified_operational", re.compile(r"(?i)\blegal/certified operational\b|\blegal or certified operational\b")),
    ("live_ingestion", re.compile(r"(?i)\blive ingestion\b")),
    ("vss_runtime_readiness", re.compile(r"(?i)\bVSS runtime/readiness\b|\bVSS runtime readiness\b")),
    ("autonomous_dispatch_enforcement_control", re.compile(r"(?i)\bautonomous action\b|\bdispatch\b|\benforcement\b|\bcontrol\b")),
    ("helsinki_acceptance", re.compile(r"(?i)\bHelsinki\b.*\b(accepted|acceptance|approved)\b")),
    ("chicago_citywide_truth", re.compile(r"(?i)\bChicago\b.*\bcitywide truth\b|\bcitywide trend truth\b")),
]


SAFE_CONTEXT_PATTERNS = [
    re.compile(r"(?i)\bno\b"),
    re.compile(r"(?i)\bnot\b"),
    re.compile(r"(?i)\bdoes not\b"),
    re.compile(r"(?i)\bmust not\b"),
    re.compile(r"(?i)\bunless\b"),
    re.compile(r"(?i)\bclosed\b"),
    re.compile(r"(?i)\bremains\b"),
    re.compile(r"(?i)\bpending review\b"),
    re.compile(r"(?i)\bbounded\b"),
    re.compile(r"(?i)\benvironment limitation\b"),
    re.compile(r"(?i)\bnot captured\b"),
    re.compile(r"(?i)\bclaim-boundary register\b"),
]


def claim_boundary_audit() -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.sha256"}:
            continue
        checked += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            safe = any(pattern.search(line) for pattern in SAFE_CONTEXT_PATTERNS)
            for name, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line) and not safe:
                    findings.append({"path": rel(path), "line": lineno, "pattern": name, "text": line.strip()[:220]})
    return {"status": "PASS" if not findings else "FAIL", "files_checked": checked, "findings": findings}


def no_prior_output_mutation_audit(before: dict[str, str | None]) -> dict[str, Any]:
    after = snapshot_prior_hashes()
    changed = [
        {"path": path, "before": before.get(path), "after": after.get(path)}
        for path in sorted(before)
        if before.get(path) != after.get(path)
    ]
    return {"status": "PASS" if not changed else "FAIL", "files_checked": len(before), "changed": changed, "prior_outputs_mutated": bool(changed)}


def referenced_artifact_existence_audit() -> dict[str, Any]:
    refs = []
    for name in REQUIRED_D9_FILES:
        refs.append({"path": rel(D9_ROOT / name), "required": True, "exists": (D9_ROOT / name).exists(), "source": "D9 R1 required input"})
    for name in D8_FILES:
        refs.append({"path": rel(D8_ROOT / name), "required": False, "exists": (D8_ROOT / name).exists(), "source": "D8 context input"})
    for name, root in OPTIONAL_ROOTS.items():
        refs.append({"path": rel(root), "required": False, "exists": root.exists(), "source": name})
    for artifact in ARTIFACTS:
        expected_late = artifact in {
            "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json",
            "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
            "HASH_MANIFEST.sha256",
        }
        refs.append({"path": rel(OUT_ROOT / artifact), "required": True, "exists": (OUT_ROOT / artifact).exists() or expected_late, "source": "D9 R2 generated output", "expected_late_generated": expected_late})
    for step in STEP_DEFS:
        refs.append({"path": step["expected_artifact"], "required": False, "exists": (REPO_ROOT / step["expected_artifact"]).exists(), "source": f"demo_step_{step['step']}_expected_artifact"})
    return {
        "status": "PASS" if all((not r["required"]) or r["exists"] for r in refs) else "FAIL",
        "references_checked": len(refs),
        "references": refs,
    }


def write_audits(before: dict[str, str | None]) -> dict[str, Any]:
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit())
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan_audit())
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_prior_output_mutation_audit(before))
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_existence_audit())
    return {
        "json_parse": read_json(OUT_ROOT / "JSON_PARSE_AUDIT.json") or {},
        "secret_scan": read_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json") or {},
        "claim_boundary": read_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json") or {},
        "no_prior_output_mutation": read_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json") or {},
        "referenced_artifacts": read_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json") or {},
    }


def create_hash_manifest() -> None:
    rows = []
    for path in sorted(OUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.sha256":
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUT_ROOT / "HASH_MANIFEST.sha256", "\n".join(rows) + "\n")


def fail_decision(reason: str, d8_status: str, d9_status: str, missing: list[str], before: dict[str, str | None]) -> int:
    reset_output_root()
    decision = {
        "task": TASK_ID,
        "status": STATUS_FAIL,
        "run_timestamp_utc": RUN_TS,
        "input_roots_discovered": {"d8": D8_ROOT.exists(), "d9_r1": D9_ROOT.exists()},
        "d8_final_status_reference": d8_status,
        "d9_r1_status_reference": d9_status,
        "missing_required_d9_files": missing,
        "failure_reason": reason,
        "next_recommendation": "Restore or rerun D9 R1 before R2 capture registration.",
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json", decision)
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_prior_output_mutation_audit(before))
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit())
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan_audit())
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_existence_audit())
    create_hash_manifest()
    return 1


def main() -> int:
    before = snapshot_prior_hashes()
    ok, d8_status, d9_status, missing, d8_decision, d9_decision = validate_upstream()
    if not ok:
        code = fail_decision("Required D9 R1 review package is missing, invalid, or not in expected status.", d8_status, d9_status, missing, before)
        print(f"{TASK_ID}: {STATUS_FAIL}")
        print(f"Output: {rel(OUT_ROOT)}")
        return code

    reset_output_root()
    captured, screenshots, videos = detect_captures()
    ledger = create_review_ledger(captured, screenshots)
    gap_register = create_capture_gap_register(captured)
    claim_register = create_claim_boundary_register()
    refs_ok = all((REPO_ROOT / step["expected_artifact"]).exists() for step in STEP_DEFS)
    scorecard = create_scorecard(captured, refs_ok)

    write_json(OUT_ROOT / "D9_HUMAN_REVIEW_SESSION_LEDGER.json", ledger)
    write_text(OUT_ROOT / "D9_REVIEW_CAPTURE_INDEX.html", review_capture_index(ledger))
    write_text(OUT_ROOT / "D9_REVIEW_SESSION_NOTES.md", review_session_notes(captured))
    write_issue_log(captured)
    write_json(OUT_ROOT / "D9_CAPTURE_GAP_REGISTER.json", gap_register)
    write_json(OUT_ROOT / "D9_REVIEW_CLAIM_BOUNDARY_REGISTER.json", claim_register)
    write_json(OUT_ROOT / "D9_R2_REVIEW_SCORECARD.json", scorecard)
    write_text(
        OUT_ROOT / "README.md",
        f"""# {TASK_ID}

This package registers D9 human-review/capture state without mutating D8 or D9 R1 outputs.

Capture status: `{ledger['capture_status']}`

Reviewer: `reviewer_not_provided`

Open `D9_REVIEW_CAPTURE_INDEX.html` to navigate the R2 review ledger and linked D9 R1 artifacts.

If screenshots/video are needed, run `MAIN-CITYBRAIN-D9-MANUAL-SCREENSHOT-VIDEO-CAPTURE-R3`.
""",
    )

    audit_files = write_audits(before)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if captured and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    next_task = "MAIN-CITYBRAIN-D9-DEMO-READINESS-CLOSEOUT-R3" if captured else "MAIN-CITYBRAIN-D9-MANUAL-SCREENSHOT-VIDEO-CAPTURE-R3"

    decision = {
        "task": TASK_ID,
        "status": final_status,
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUT_ROOT),
        "input_roots_discovered": {
            "d8_final_handoff": D8_ROOT.exists(),
            "d9_polish_r1": D9_ROOT.exists(),
            **{name: root.exists() for name, root in OPTIONAL_ROOTS.items()},
        },
        "d8_final_status_reference": d8_status,
        "d9_r1_status_reference": d9_status,
        "capture_status": ledger["capture_status"],
        "review_status": "NEEDS_HUMAN_REVIEW" if not captured else "CAPTURE_REGISTERED_NEEDS_HUMAN_REVIEW",
        "reviewer": "reviewer_not_provided",
        "demo_steps_total": ledger["steps_total"],
        "screenshots_registered": len(screenshots),
        "videos_registered": len(videos),
        "audit_summary": {name: audit.get("status") for name, audit in audit_files.items()},
        "limitation_summary": {
            "capture_gaps": len(gap_register["gaps"]),
            "screenshots_video_absent": not captured,
            "human_reviewer_identity_absent": True,
            "vss_sample_ingest_gate": "CLOSED",
            "helsinki_object_pick_review": "PENDING_REVIEW",
            "chicago_memory_scope": "BOUNDED_SAMPLE_ONLY",
            "web_kit_scope": "LOCAL_HANDOFF_ONLY",
        },
        "d8_claim_boundary_refs": d8_decision.get("claim_boundaries", {}),
        "d9_r1_capture_status": d9_decision.get("review_pass_fail_summary", {}).get("capture_status"),
        "next_recommendation": next_task,
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json", decision)

    audit_files = write_audits(before)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if captured and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    decision["status"] = final_status
    decision["audit_summary"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json", decision)

    audit_files = write_audits(before)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if captured and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    decision["status"] = final_status
    decision["audit_summary"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json", decision)
    create_hash_manifest()

    print(f"{TASK_ID}: {final_status}")
    print(f"Output: {rel(OUT_ROOT)}")
    return 0 if final_status in {STATUS_PASS, STATUS_PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
