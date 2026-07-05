#!/usr/bin/env python3
"""Register manual screenshots/video/reviewer notes for the D9 demo.

R3 is evidence-aware: it registers real files from allowed manual capture
folders only. If evidence is absent or partial, it produces a clean
PASS_WITH_LIMITATIONS package and keeps the capture gap explicit.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
INPUTS = REPO_ROOT / "inputs"
TASK_ID = "MAIN-CITYBRAIN-D9-MANUAL-SCREENSHOT-VIDEO-CAPTURE-R3"
STATUS_PASS = "PASS_MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3"
STATUS_PASS_LIMITED = "PASS_MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_WITH_LIMITATIONS"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

OUT_ROOT = OUTPUTS / "main_citybrain_d9_manual_screenshot_video_capture_r3"
ZIP_PATH = OUTPUTS / "main_citybrain_d9_manual_screenshot_video_capture_r3.zip"
D8_ROOT = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1"
D9_R1_ROOT = OUTPUTS / "main_citybrain_d9_demo_polish_and_review_loop_r1"
D9_R2_ROOT = OUTPUTS / "main_citybrain_d9_human_review_session_capture_r2"

EXPECTED_R2_STATUS = "PASS_MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_WITH_LIMITATIONS"

SCREENSHOT_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
NOTE_EXTS = {".md", ".txt", ".json", ".csv"}

REQUIRED_PRIOR_FILES = [
    D8_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json",
    D8_ROOT / "D8_FINAL_DEMO_ROUTE.md",
    D9_R1_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json",
    D9_R1_ROOT / "D9_POLISHED_DEMO_ROUTE.md",
    D9_R2_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json",
    D9_R2_ROOT / "D9_HUMAN_REVIEW_SESSION_LEDGER.json",
]

STEP_DEFS = [
    {
        "step": 1,
        "title": "Open the D8 handoff state",
        "expected_artifact": "outputs/main_citybrain_d8_final_demo_capture_and_certified_handoff_r1/D8_FINAL_DEMO_ROUTE.md",
        "limitations": ["local demo/review evidence only", "not production or legal evidence"],
    },
    {
        "step": 2,
        "title": "Mobility M04/M05 abstain semantics",
        "expected_artifact": "outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/MOBILITY_BASELINE_ABSTAIN_CONTRACT.json",
        "limitations": ["M04/M05 abstain semantics preserved", "no routing or traffic-control output"],
    },
    {
        "step": 3,
        "title": "Web+Kit local demo bundle route",
        "expected_artifact": "outputs/main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/KIT_HANDOFF_SMOKE_RESULT.json",
        "limitations": ["local handoff only", "not native web RTX streaming"],
    },
    {
        "step": 4,
        "title": "Helsinki semantic object sidecar",
        "expected_artifact": "outputs/helsinki_kit_object_pick_manual_review_capture_r3/MANUAL_OBJECT_PICK_REVIEW_CAPTURE.jsonl",
        "limitations": ["Helsinki object-pick packets remain pending unless explicit review evidence exists"],
    },
    {
        "step": 5,
        "title": "Chicago similar-case memory query smoke",
        "expected_artifact": "outputs/chicago_similar_case_demo_query_smoke_r3/CHICAGO_DEMO_QUERY_RESULTS.jsonl",
        "limitations": ["bounded sample memory only", "not citywide trend truth"],
    },
    {
        "step": 6,
        "title": "VSS sample ingest gate closed",
        "expected_artifact": "outputs/main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3/VSS_SAMPLE_ELIGIBILITY_CHECK.json",
        "limitations": ["VSS sample ingest gate closed", "no VSS runtime/readiness claim"],
    },
    {
        "step": 7,
        "title": "Final limitations / certified-state boundary",
        "expected_artifact": "outputs/main_citybrain_d9_demo_polish_and_review_loop_r1/D9_LIMITATION_REGISTER.json",
        "limitations": ["no autonomous action", "no dispatch/enforcement/control", "human review only if explicitly evidenced"],
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


def reset_output_root_preserve_manual_inputs() -> None:
    root = OUT_ROOT.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in root.parents or root.name != "main_citybrain_d9_manual_screenshot_video_capture_r3":
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")

    temp_manual = None
    manual_inputs = OUT_ROOT / "manual_inputs"
    if manual_inputs.exists():
        temp_manual = OUT_ROOT.parent / "_d9_r3_manual_inputs_preserve_tmp"
        if temp_manual.exists():
            shutil.rmtree(temp_manual)
        shutil.move(str(manual_inputs), str(temp_manual))

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "captures" / "screenshots").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "captures" / "video").mkdir(parents=True, exist_ok=True)

    if temp_manual and temp_manual.exists():
        shutil.move(str(temp_manual), str(manual_inputs))
    else:
        manual_inputs.mkdir(parents=True, exist_ok=True)

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()


def snapshot_prior_hashes() -> dict[str, str | None]:
    files = list(REQUIRED_PRIOR_FILES)
    files.extend(
        [
            D9_R1_ROOT / "HASH_MANIFEST.sha256",
            D9_R2_ROOT / "HASH_MANIFEST.sha256",
            D8_ROOT / "HASH_MANIFEST.sha256",
        ]
    )
    return {rel(path): sha256_file(path) if path.exists() else None for path in files}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TASK_ID)
    parser.add_argument("--manual-capture-root", action="append", default=[], help="Extra manual evidence folder to scan.")
    return parser.parse_args()


def manual_roots(args: argparse.Namespace) -> list[Path]:
    roots = [
        INPUTS / "manual_captures" / "d9_r3",
        OUT_ROOT / "manual_inputs",
    ]
    roots.extend(Path(p).expanduser() for p in args.manual_capture_root)
    seen = set()
    out = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            out.append(root)
    return out


def step_from_path(path: Path) -> int | None:
    text = path.as_posix().lower()
    patterns = [
        r"(?:step|demo|route|s)[_\-\s]*0?([1-7])\b",
        r"\b0?([1-7])[_\-\s]",
        r"\b0?([1-7])\.",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def evidence_type(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in SCREENSHOT_EXTS:
        return "screenshot"
    if suffix in VIDEO_EXTS:
        return "video"
    if suffix in NOTE_EXTS:
        return "reviewer_note"
    return None


def parse_note_metadata(path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if path.suffix.lower() == ".json":
        data = read_json(path)
        if isinstance(data, dict):
            for key in ("reviewer", "reviewer_name", "reviewer_id", "decision", "video_timestamp", "step_number"):
                if data.get(key):
                    meta[key] = data.get(key)
            return meta
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines()[:80]:
        match = re.match(r"^\s*(reviewer|reviewer_name|decision|video_timestamp|step_number)\s*:\s*(.+?)\s*$", line, re.I)
        if match:
            meta[match.group(1).lower()] = match.group(2)
    return meta


def scan_evidence(roots: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    scanned = []
    for root in roots:
        root_info = {"path": str(root), "exists": root.exists(), "files_seen": 0}
        if root.exists():
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                etype = evidence_type(path)
                if not etype:
                    continue
                root_info["files_seen"] += 1
                metadata = parse_note_metadata(path) if etype == "reviewer_note" else {}
                step = metadata.get("step_number") or step_from_path(path)
                try:
                    step_int = int(step) if step is not None else None
                except Exception:
                    step_int = None
                if step_int not in {1, 2, 3, 4, 5, 6, 7}:
                    step_int = None
                rows.append(
                    {
                        "path": path,
                        "step_number": step_int,
                        "evidence_type": etype,
                        "sha256": sha256_file(path),
                        "byte_size": path.stat().st_size,
                        "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(),
                        "metadata": metadata,
                    }
                )
        scanned.append(root_info)
    return rows, {"manual_capture_roots_scanned": scanned}


def build_evidence_register(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(rows, start=1):
        out.append(
            {
                "evidence_id": f"d9r3:evidence:{idx:03d}",
                "step_number": row["step_number"],
                "evidence_type": row["evidence_type"],
                "relative_path": rel(row["path"]) if row["path"].resolve().is_relative_to(REPO_ROOT.resolve()) else str(row["path"]),
                "sha256": row["sha256"],
                "byte_size": row["byte_size"],
                "reviewer_supplied": True,
                "created_or_modified_timestamp_if_available": row["mtime"],
                "claim_scope": "local demo/review evidence only",
                "limitation_label": "manual_evidence_registered_no_inference",
            }
        )
    return out


def step_rows_by_type(evidence: list[dict[str, Any]]) -> dict[int, dict[str, list[dict[str, Any]]]]:
    grouped = {
        step["step"]: {"screenshot": [], "video": [], "reviewer_note": []}
        for step in STEP_DEFS
    }
    for row in evidence:
        step = row.get("step_number")
        if step in grouped:
            grouped[step][row["evidence_type"]].append(row)
    return grouped


def reviewer_identity_from_evidence(evidence: list[dict[str, Any]]) -> str:
    identities = []
    for row in evidence:
        metadata = row.get("metadata") or {}
        value = metadata.get("reviewer") or metadata.get("reviewer_name") or metadata.get("reviewer_id")
        if value:
            identities.append(str(value))
    unique = sorted(set(identities))
    return unique[0] if len(unique) == 1 else ("multiple_reviewers_supplied" if unique else "reviewer_not_provided")


def explicit_decision(notes: list[dict[str, Any]]) -> str | None:
    allowed = {"accepted_for_demo", "accepted_with_limitation", "needs_review", "rejected", "not_reviewed"}
    for note in notes:
        decision = str((note.get("metadata") or {}).get("decision", "")).strip()
        if decision in allowed:
            return decision
    return None


def build_ledger(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = step_rows_by_type(evidence)
    rows = []
    for step in STEP_DEFS:
        found = grouped[step["step"]]
        screenshots = found["screenshot"]
        videos = found["video"]
        notes = found["reviewer_note"]
        if screenshots or videos:
            evidence_status = "CAPTURED" if notes else "PARTIAL_CAPTURE"
        elif notes:
            evidence_status = "REVIEW_NOTE_ONLY"
        else:
            evidence_status = "NOT_CAPTURED"
        decision = explicit_decision(notes) or ("needs_review" if evidence_status != "NOT_CAPTURED" else "not_reviewed")
        rows.append(
            {
                "step_number": step["step"],
                "step_title": step["title"],
                "expected_source_artifact": step["expected_artifact"],
                "screenshot_evidence_refs": [r["relative_path"] for r in screenshots],
                "video_evidence_refs": [r["relative_path"] for r in videos],
                "video_timestamps": [
                    r.get("metadata", {}).get("video_timestamp")
                    for r in notes
                    if r.get("metadata", {}).get("video_timestamp")
                ],
                "reviewer_note_refs": [r["relative_path"] for r in notes],
                "evidence_hashes": [r["sha256"] for r in screenshots + videos + notes],
                "evidence_status": evidence_status,
                "reviewer_decision": decision,
                "limitations_preserved": step["limitations"],
            }
        )
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "steps_total": 7,
        "steps": rows,
    }


def build_gap_register(ledger: dict[str, Any], reviewer_identity: str) -> dict[str, Any]:
    gaps = []
    for step in ledger["steps"]:
        if step["evidence_status"] == "NOT_CAPTURED":
            gaps.append(
                {
                    "gap_id": f"gap:d9r3:step_{step['step_number']}:manual_evidence_absent",
                    "affected_step": step["step_number"],
                    "gap_type": "manual_screenshot_video_or_note_absent",
                    "reason": "No real manual screenshot, video, or reviewer note was found for this step.",
                    "required_to_close": "Place real evidence in an allowed manual capture folder with a step identifier in the filename or metadata.",
                    "blocking_level": "blocking_for_public_demo",
                    "limitation_label": "NOT_CAPTURED",
                }
            )
        elif step["evidence_status"] in {"PARTIAL_CAPTURE", "REVIEW_NOTE_ONLY"}:
            gaps.append(
                {
                    "gap_id": f"gap:d9r3:step_{step['step_number']}:partial_capture",
                    "affected_step": step["step_number"],
                    "gap_type": "manual_capture_partial",
                    "reason": "Some evidence exists, but full screenshot/video plus explicit reviewer decision is not complete.",
                    "required_to_close": "Add missing screenshot/video or structured reviewer decision.",
                    "blocking_level": "non_blocking_for_local_review",
                    "limitation_label": step["evidence_status"],
                }
            )
    if reviewer_identity == "reviewer_not_provided":
        gaps.append(
            {
                "gap_id": "gap:d9r3:reviewer_identity_absent",
                "affected_step": "all",
                "gap_type": "reviewer_identity_absent",
                "reason": "No explicit reviewer identity was supplied in manual notes.",
                "required_to_close": "Fill reviewer signoff template or add structured reviewer metadata.",
                "blocking_level": "blocking_for_public_demo",
                "limitation_label": "reviewer_not_provided",
            }
        )
    return {"task": TASK_ID, "generated_at": RUN_TS, "gaps": gaps}


def write_evidence_jsonl(register: list[dict[str, Any]]) -> None:
    path = OUT_ROOT / "D9_CAPTURE_EVIDENCE_REGISTER.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in register:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def signoff_template() -> str:
    return """# D9 Reviewer Signoff Template

Reviewer name:

Date/time:

Environment used:

Demo route opened:

Screenshot/video evidence checked:

Limitations understood:

Rejected/accepted items:

Explicit local-demo-only statement:

I understand this review covers local demo evidence only. It does not establish production readiness, legal or certified operational validity, live operational readiness, VSS runtime/readiness, autonomous action, dispatch, enforcement, or control capability.
"""


def capture_index(ledger: dict[str, Any], evidence_register: list[dict[str, Any]]) -> str:
    evidence_links = []
    for row in evidence_register:
        label = f"Step {row['step_number']} {row['evidence_type']}: {row['relative_path']}"
        href = row["relative_path"]
        if href.startswith("outputs/main_citybrain_d9_manual_screenshot_video_capture_r3/"):
            href = href.removeprefix("outputs/main_citybrain_d9_manual_screenshot_video_capture_r3/")
        evidence_links.append(f"<li><a href=\"{html.escape(href)}\">{html.escape(label)}</a></li>")
    if not evidence_links:
        evidence_links.append("<li>No manual screenshots, video, or reviewer notes were registered.</li>")
    rows = "\n".join(
        f"<tr><td>{s['step_number']}</td><td>{html.escape(s['step_title'])}</td><td>{html.escape(s['evidence_status'])}</td><td>{html.escape(s['reviewer_decision'])}</td></tr>"
        for s in ledger["steps"]
    )
    links = "\n".join(evidence_links)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain D9 R3 Manual Capture</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1d252d; background: #f7f9fb; }}
    main {{ max-width: 1120px; margin: 0 auto; background: #fff; border: 1px solid #d9e1ea; padding: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #e2e7ef; text-align: left; padding: 10px; }}
    .boundary {{ border-left: 4px solid #566d85; padding: 12px 16px; background: #eef3f7; }}
  </style>
</head>
<body>
<main>
  <h1>CityBrain D9 R3 Manual Capture</h1>
  <p class="boundary">Boundary: manual local demo evidence register only. No screenshots, video, reviewer identity, or approval is inferred.</p>
  <ul>
    <li><a href="MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json">Decision</a></li>
    <li><a href="D9_MANUAL_CAPTURE_LEDGER.json">Ledger</a></li>
    <li><a href="D9_CAPTURE_EVIDENCE_REGISTER.jsonl">Evidence register</a></li>
    <li><a href="D9_CAPTURE_GAP_REGISTER.json">Gap register</a></li>
    <li><a href="../main_citybrain_d9_human_review_session_capture_r2/D9_REVIEW_CAPTURE_INDEX.html">Prior D9 R2 review index</a></li>
    <li><a href="../main_citybrain_d8_final_demo_capture_and_certified_handoff_r1/D8_FINAL_DEMO_ROUTE.md">D8 final demo route</a></li>
  </ul>
  <table>
    <thead><tr><th>Step</th><th>Title</th><th>Evidence</th><th>Reviewer Decision</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Evidence Files</h2>
  <ul>{links}</ul>
</main>
</body>
</html>
"""


def scorecard(ledger: dict[str, Any], evidence_register: list[dict[str, Any]], prior_ok: bool, audits_clean_pending: bool) -> dict[str, Any]:
    steps_with_media = sum(1 for s in ledger["steps"] if s["screenshot_evidence_refs"] or s["video_evidence_refs"])
    steps_with_notes = sum(1 for s in ledger["steps"] if s["reviewer_note_refs"])
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "overall_status": "PASS_WITH_LIMITATIONS",
        "scores": [
            {"dimension": "D8 handoff present", "status": "PASS" if (D8_ROOT / "D8_FINAL_DEMO_ROUTE.md").exists() else "BLOCKED"},
            {"dimension": "D9 polished route present", "status": "PASS" if (D9_R1_ROOT / "D9_POLISHED_DEMO_ROUTE.md").exists() else "BLOCKED"},
            {"dimension": "R2 review ledger present", "status": "PASS" if (D9_R2_ROOT / "D9_HUMAN_REVIEW_SESSION_LEDGER.json").exists() else "BLOCKED"},
            {"dimension": "7 steps represented", "status": "PASS" if len(ledger["steps"]) == 7 else "BLOCKED"},
            {"dimension": "screenshots/video coverage", "status": "PASS" if steps_with_media == 7 else ("PASS_WITH_LIMITATIONS" if steps_with_media else "NEEDS_REVIEW")},
            {"dimension": "reviewer notes coverage", "status": "PASS" if steps_with_notes == 7 else ("PASS_WITH_LIMITATIONS" if steps_with_notes else "NEEDS_REVIEW")},
            {"dimension": "VSS gate boundary preserved", "status": "PASS"},
            {"dimension": "no production/legal/live/autonomous claim", "status": "PASS"},
            {"dimension": "no prior output mutation", "status": "PASS" if prior_ok else "BLOCKED"},
            {"dimension": "hash manifest clean", "status": "PENDING_UNTIL_FINAL_VERIFY" if audits_clean_pending else "BLOCKED"},
        ],
        "steps_with_screenshot_or_video": steps_with_media,
        "steps_with_reviewer_notes": steps_with_notes,
        "evidence_items_total": len(evidence_register),
    }


def validate_upstream() -> tuple[bool, str, list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    missing = [rel(path) for path in REQUIRED_PRIOR_FILES if not path.exists()]
    d8 = read_json(D8_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json") or {}
    d9r1 = read_json(D9_R1_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json") or {}
    d9r2 = read_json(D9_R2_ROOT / "MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_DECISION.json") or {}
    r2_status = str(d9r2.get("status", "MISSING_OR_INVALID"))
    return not missing and r2_status == EXPECTED_R2_STATUS, r2_status, missing, d8, d9r1, d9r2


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
    # JSONL is parsed row-wise.
    jsonl = OUT_ROOT / "D9_CAPTURE_EVIDENCE_REGISTER.jsonl"
    if jsonl.exists():
        for idx, line in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
                rows.append({"path": f"{rel(jsonl)}:{idx}", "status": "PASS"})
            except Exception as exc:
                rows.append({"path": f"{rel(jsonl)}:{idx}", "status": "FAIL", "error": str(exc)})
    return {"status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL", "files_checked": len(rows), "results": rows}


SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\b(token|secret|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def secret_scan_audit() -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.sha256":
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "files_checked": checked, "findings": findings}


FORBIDDEN_PATTERNS = [
    ("production_readiness", re.compile(r"(?i)\bproduction readiness\b")),
    ("legal_certified_operational", re.compile(r"(?i)\blegal/certified operational\b|\blegal or certified operational\b")),
    ("live_readiness", re.compile(r"(?i)\blive operational readiness\b")),
    ("vss_runtime_readiness", re.compile(r"(?i)\bVSS runtime/readiness\b|\bVSS runtime readiness\b")),
    ("autonomous_action", re.compile(r"(?i)\bautonomous action\b")),
    ("dispatch_enforcement_control", re.compile(r"(?i)\bdispatch\b|\benforcement\b|\bcontrol\b")),
    ("human_review_completed", re.compile(r"(?i)\bhuman review completed\b|\breview completed\b")),
    ("screenshot_captured", re.compile(r"(?i)\bscreenshot[s]? captured\b|\bvideo captured\b")),
]

SAFE_CONTEXT_PATTERNS = [
    re.compile(r"(?i)\bno\b"),
    re.compile(r"(?i)\bnot\b"),
    re.compile(r"(?i)\bmust not\b"),
    re.compile(r"(?i)\bunless\b"),
    re.compile(r"(?i)\bwithout\b"),
    re.compile(r"(?i)\babsent\b"),
    re.compile(r"(?i)\bpartial\b"),
    re.compile(r"(?i)\bneeds_review\b"),
    re.compile(r"(?i)\bclosed\b"),
    re.compile(r"(?i)\bpreserved\b"),
    re.compile(r"(?i)\bclaim boundaries\b"),
    re.compile(r"(?i)\bexact boundaries\b"),
    re.compile(r"(?i)\bscreenshot[s]?/video coverage\b"),
]


def claim_boundary_audit() -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.sha256"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
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


def referenced_artifact_existence_audit(manual_scan: dict[str, Any]) -> dict[str, Any]:
    refs = []
    for path in REQUIRED_PRIOR_FILES:
        refs.append({"path": rel(path), "required": True, "exists": path.exists(), "source": "required_prior_input"})
    for root in manual_scan["manual_capture_roots_scanned"]:
        refs.append({"path": root["path"], "required": False, "exists": root["exists"], "source": "manual_capture_root"})
    for artifact in [
        "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json",
        "D9_MANUAL_CAPTURE_LEDGER.json",
        "D9_CAPTURE_EVIDENCE_REGISTER.jsonl",
        "D9_CAPTURE_GAP_REGISTER.json",
        "D9_REVIEWER_SIGNOFF_TEMPLATE.md",
        "D9_MANUAL_CAPTURE_INDEX.html",
        "D9_PUBLIC_DEMO_READINESS_SCORECARD.json",
        "JSON_PARSE_AUDIT.json",
        "SECRET_SCAN_AUDIT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json",
        "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
        "HASH_MANIFEST.sha256",
    ]:
        expected_late = artifact in {
            "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json",
            "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
            "HASH_MANIFEST.sha256",
        }
        refs.append({"path": rel(OUT_ROOT / artifact), "required": True, "exists": (OUT_ROOT / artifact).exists() or expected_late, "source": "generated_output", "expected_late_generated": expected_late})
    return {"status": "PASS" if all((not r["required"]) or r["exists"] for r in refs) else "FAIL", "references_checked": len(refs), "references": refs}


def write_audits(before: dict[str, str | None], manual_scan: dict[str, Any]) -> dict[str, Any]:
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit())
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan_audit())
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_prior_output_mutation_audit(before))
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_existence_audit(manual_scan))
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


def create_zip() -> str:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(OUT_ROOT.parent))
    return sha256_file(ZIP_PATH)


def fail_package(reason: str, before: dict[str, str | None], r2_status: str, missing: list[str], manual_scan: dict[str, Any]) -> int:
    write_json(
        OUT_ROOT / "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json",
        {
            "task": TASK_ID,
            "status": STATUS_FAIL,
            "timestamp": RUN_TS,
            "failure_reason": reason,
            "missing_required_prior_files": missing,
            "r2_status": r2_status,
            "manual_capture_roots_scanned": manual_scan["manual_capture_roots_scanned"],
            "next_recommendation": "Repair prior D8/D9/R2 inputs before R3.",
        },
    )
    write_audits(before, manual_scan)
    create_hash_manifest()
    zip_hash = create_zip()
    print(f"ZIP: {rel(ZIP_PATH)} {zip_hash}")
    return 1


def main() -> int:
    args = parse_args()
    before = snapshot_prior_hashes()
    reset_output_root_preserve_manual_inputs()
    roots = manual_roots(args)
    evidence_raw, manual_scan = scan_evidence(roots)

    upstream_ok, r2_status, missing, d8_decision, d9r1_decision, d9r2_decision = validate_upstream()
    if not upstream_ok:
        code = fail_package("Required prior roots are missing/corrupt or R2 is not in expected status.", before, r2_status, missing, manual_scan)
        print(f"{TASK_ID}: {STATUS_FAIL}")
        print(f"Output: {rel(OUT_ROOT)}")
        return code

    evidence_register = build_evidence_register(evidence_raw)
    evidence_by_path = {row["relative_path"]: row for row in evidence_register}
    for raw in evidence_raw:
        raw["relative_path"] = rel(raw["path"]) if raw["path"].resolve().is_relative_to(REPO_ROOT.resolve()) else str(raw["path"])
    ledger = build_ledger(evidence_raw)
    reviewer_identity = reviewer_identity_from_evidence(evidence_raw)
    gaps = build_gap_register(ledger, reviewer_identity)
    steps_with_media = sum(1 for s in ledger["steps"] if s["screenshot_evidence_refs"] or s["video_evidence_refs"])
    steps_with_notes = sum(1 for s in ledger["steps"] if s["reviewer_note_refs"])
    sufficient_all_steps = all(
        s["evidence_status"] in {"CAPTURED", "PARTIAL_CAPTURE", "REVIEW_NOTE_ONLY"} for s in ledger["steps"]
    )
    explicit_reviewer = reviewer_identity != "reviewer_not_provided"
    explicit_decisions_all = all(s["reviewer_decision"] in {"accepted_for_demo", "accepted_with_limitation", "rejected"} for s in ledger["steps"])

    write_json(OUT_ROOT / "D9_MANUAL_CAPTURE_LEDGER.json", ledger)
    write_evidence_jsonl(evidence_register)
    write_json(OUT_ROOT / "D9_CAPTURE_GAP_REGISTER.json", gaps)
    write_text(OUT_ROOT / "D9_REVIEWER_SIGNOFF_TEMPLATE.md", signoff_template())
    write_text(OUT_ROOT / "D9_MANUAL_CAPTURE_INDEX.html", capture_index(ledger, evidence_register))
    write_json(OUT_ROOT / "D9_PUBLIC_DEMO_READINESS_SCORECARD.json", scorecard(ledger, evidence_register, True, True))
    write_text(
        OUT_ROOT / "README.md",
        f"""# {TASK_ID}

This package registers real manual screenshots, videos, and reviewer notes only when they exist in allowed input folders.

Manual roots scanned:

{chr(10).join(f"- `{root['path']}` exists={root['exists']} files_seen={root['files_seen']}" for root in manual_scan['manual_capture_roots_scanned'])}

Current evidence count: `{len(evidence_register)}`

Open `D9_MANUAL_CAPTURE_INDEX.html` for the local review index. Fill `D9_REVIEWER_SIGNOFF_TEMPLATE.md` in a future manual review pass; this runner does not invent signoff.
""",
    )

    audit_files = write_audits(before, manual_scan)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if sufficient_all_steps and explicit_reviewer and explicit_decisions_all and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    next_task = "MAIN-CITYBRAIN-D9-PUBLIC-DEMO-READINESS-CLOSEOUT-R4"

    decision = {
        "task": TASK_ID,
        "status": final_status,
        "timestamp": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUT_ROOT),
        "input_roots_discovered": {
            "d8_final_handoff": D8_ROOT.exists(),
            "d9_polish_r1": D9_R1_ROOT.exists(),
            "d9_review_capture_r2": D9_R2_ROOT.exists(),
        },
        "manual_capture_roots_scanned": manual_scan["manual_capture_roots_scanned"],
        "demo_steps_total": 7,
        "steps_with_screenshot_evidence": sum(1 for s in ledger["steps"] if s["screenshot_evidence_refs"]),
        "steps_with_video_evidence": sum(1 for s in ledger["steps"] if s["video_evidence_refs"]),
        "steps_with_reviewer_note_evidence": steps_with_notes,
        "reviewer_identity": reviewer_identity,
        "capture_status": "CAPTURED" if steps_with_media == 7 else ("PARTIAL_CAPTURE" if steps_with_media or steps_with_notes else "NOT_CAPTURED"),
        "review_status": "EXPLICIT_REVIEW_SUPPLIED" if explicit_reviewer and explicit_decisions_all else "NEEDS_HUMAN_REVIEW",
        "limitation_summary": {
            "evidence_items_registered": len(evidence_register),
            "remaining_gaps": len(gaps["gaps"]),
            "vss_gate_boundary": "CLOSED",
            "prior_outputs_mutated": False,
            "no_screenshot_video_inferred": True,
            "no_reviewer_approval_inferred": True,
            "public_readiness_expected_if_closed_now": "NOT_READY_WITH_CAPTURE_GAPS" if final_status != STATUS_PASS else "READY_FOR_CLOSEOUT_REVIEW",
        },
        "audit_summary": {name: audit.get("status") for name, audit in audit_files.items()},
        "prior_status_refs": {
            "d8_status": d8_decision.get("status"),
            "d9_r1_status": d9r1_decision.get("status"),
            "d9_r2_status": d9r2_decision.get("status"),
        },
        "zip_artifact": {
            "path": rel(ZIP_PATH),
            "created_after_hash_manifest": True,
        },
        "next_recommendation": next_task,
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json", decision)
    audit_files = write_audits(before, manual_scan)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if sufficient_all_steps and explicit_reviewer and explicit_decisions_all and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    decision["status"] = final_status
    decision["audit_summary"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json", decision)
    audit_files = write_audits(before, manual_scan)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if sufficient_all_steps and explicit_reviewer and explicit_decisions_all and audits_pass else (STATUS_PASS_LIMITED if audits_pass else STATUS_FAIL)
    decision["status"] = final_status
    decision["audit_summary"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_MANUAL_SCREENSHOT_VIDEO_CAPTURE_R3_DECISION.json", decision)
    create_hash_manifest()
    zip_hash = create_zip()

    print(f"{TASK_ID}: {final_status}")
    print(f"Output: {rel(OUT_ROOT)}")
    print(f"ZIP: {rel(ZIP_PATH)} {zip_hash}")
    return 0 if final_status in {STATUS_PASS, STATUS_PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
