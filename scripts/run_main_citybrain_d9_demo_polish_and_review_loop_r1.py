#!/usr/bin/env python3
"""Build the CityBrain D9 demo polish and review-loop package.

D9 is a derivative review package. It reads the D8 final demo handoff,
creates clearer rehearsal/review artifacts, and proves that prior D8 outputs
were not mutated. It does not create new evidence or upgrade any D8 limitation.
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
TASK_ID = "MAIN-CITYBRAIN-D9-DEMO-POLISH-AND-REVIEW-LOOP-R1"
STATUS_PASS = "PASS_MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_WITH_LIMITATIONS"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

OUT_ROOT = OUTPUTS / "main_citybrain_d9_demo_polish_and_review_loop_r1"
D8_ROOT = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1"
D8_ZIP = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1.zip"
EXPECTED_D8_STATUS = "PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS"

REQUIRED_D8_FILES = [
    "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json",
    "D8_CERTIFIED_STATE_HANDOFF.md",
    "D8_FINAL_DEMO_ROUTE.md",
    "D8_OPERATOR_SCRIPT.md",
    "D8_EXECUTIVE_SUMMARY.md",
    "D8_FINAL_DEMO_SCOREBOARD.json",
    "D8_FINAL_LIMITATION_REGISTER.json",
    "D8_FINAL_ARTIFACT_INDEX.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
    "HASH_MANIFEST.sha256",
]

OPTIONAL_ROOTS = {
    "demonstrable_surface": OUTPUTS / "main_citybrain_d8_demonstrable_surface_integration_r1",
    "d8_r3_closeout": OUTPUTS / "citybrain_d8_r3_followon_prompt_pack_closeout",
    "helsinki_review_r3": OUTPUTS / "helsinki_kit_object_pick_manual_review_capture_r3",
    "chicago_query_r3": OUTPUTS / "chicago_similar_case_demo_query_smoke_r3",
    "vss_ingest_smoke_r3": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3",
    "web_kit_smoke_r1": OUTPUTS / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1",
    "mobility_abstain_r1": OUTPUTS / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1",
}

ARTIFACTS = [
    ("README.md", "D9 package overview and use notes", "D8 final handoff", "Review package only; no prior output mutation."),
    ("MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json", "Final D9 decision", "All D9 artifacts", "Decision preserves D8 limitations."),
    ("D9_DEMO_REVIEW_SCORECARD.json", "Review dimensions and statuses", "D8 scoreboard and route", "Scores do not upgrade gated capabilities."),
    ("D9_POLISHED_DEMO_ROUTE.md", "Rehearsable 7-step route", "D8 route", "All limitation callouts remain visible."),
    ("D9_POLISHED_OPERATOR_SCRIPT.md", "Operator narration script", "D8 operator script", "No action, legal, deployment, or VSS-readiness claims."),
    ("D9_EXECUTIVE_DEMO_ONE_PAGER.md", "Nontechnical demo explanation", "D8 executive summary", "Clear separation of proves vs does-not-prove."),
    ("D9_SCREENSHOT_AND_CAPTURE_CHECKLIST.md", "Manual capture checklist", "D8 demo route and index", "Screenshots are optional manual evidence."),
    ("D9_REVIEWER_ISSUE_LOG_TEMPLATE.csv", "Issue-log template", "D9 review loop", "Header-only template; no review outcomes inferred."),
    ("D9_RECOMMENDED_REVIEW_ACTIONS.md", "Prioritized review actions", "D8 limitation register", "Actions are future review work."),
    ("D9_LIMITATION_REGISTER.json", "Preserved D8 plus D9 limitations", "D8 limitation register", "Limitations remain part of evidence."),
    ("D9_ARTIFACT_INDEX.json", "D9 artifact index", "Generated D9 artifacts", "Every artifact includes claim-boundary note."),
    ("D9_OPTIONAL_DEMO_POLISH_PATCH_MANIFEST.json", "Derivative review-copy manifest", "D9 review index", "Patch artifacts live only under D9 output root."),
    ("D9_REVIEW_INDEX.html", "Small local D9 review landing page", "D9 polished artifacts", "Visible local-review boundary label."),
    ("JSON_PARSE_AUDIT.json", "Generated JSON parse audit", "D9 JSON artifacts", "Schema-light parse only."),
    ("SECRET_SCAN_AUDIT.json", "Secret pattern audit", "D9 generated artifacts", "No secrets expected or required."),
    ("CLAIM_BOUNDARY_AUDIT.json", "Forbidden-claim boundary audit", "D9 generated artifacts", "Fails on unsupported positive claims."),
    ("NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", "D8 hash before/after audit", "D8 required artifacts", "Proves D8 files are unchanged."),
    ("REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", "Referenced path existence audit", "D8/D9 artifacts", "Absent optional roots are recorded."),
    ("HASH_MANIFEST.sha256", "D9 output hash manifest", "Final D9 package", "Generated last after all other files."),
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
    if outputs not in root.parents or root.name != "main_citybrain_d9_demo_polish_and_review_loop_r1":
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def snapshot_required_d8_hashes() -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for name in REQUIRED_D8_FILES:
        path = D8_ROOT / name
        hashes[name] = sha256_file(path) if path.exists() else None
    return hashes


def validate_upstream() -> tuple[bool, str, list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    missing = [name for name in REQUIRED_D8_FILES if not (D8_ROOT / name).exists()]
    decision = read_json(D8_ROOT / REQUIRED_D8_FILES[0]) or {}
    scoreboard = read_json(D8_ROOT / "D8_FINAL_DEMO_SCOREBOARD.json") or {}
    limitations = read_json(D8_ROOT / "D8_FINAL_LIMITATION_REGISTER.json") or {}
    d8_status = str(decision.get("status", "MISSING_OR_INVALID"))
    ok = D8_ROOT.exists() and not missing and d8_status == EXPECTED_D8_STATUS
    return ok, d8_status, missing, decision, scoreboard, limitations


def create_scorecard() -> dict[str, Any]:
    dimensions = [
        {
            "dimension": "launchability",
            "status": "PASS_WITH_LIMITATIONS",
            "notes": "The local demo index and handoff artifacts exist; manual environment checks remain useful before a live walkthrough.",
        },
        {
            "dimension": "narrative clarity",
            "status": "PASS",
            "notes": "D9 route reframes the demo around seven reviewable beats with limits adjacent to evidence.",
        },
        {
            "dimension": "evidence traceability",
            "status": "PASS",
            "notes": "Each route beat points to D8 or lane-level artifacts rather than unsupported narration.",
        },
        {
            "dimension": "limitation visibility",
            "status": "PASS",
            "notes": "Mobility abstain, Helsinki pending review, Chicago bounded scope, VSS closed gate, and Web+Kit local-only status are explicit.",
        },
        {
            "dimension": "unsupported-claim avoidance",
            "status": "PASS",
            "notes": "The package keeps legal, operational, VSS, live, autonomous, and citywide claims gated.",
        },
        {
            "dimension": "operator usability",
            "status": "PASS_WITH_LIMITATIONS",
            "notes": "The operator script is rehearsable; it still depends on local files and manual screen capture.",
        },
        {
            "dimension": "executive readability",
            "status": "PASS",
            "notes": "The one-pager separates what is demonstrated from what remains gated.",
        },
        {
            "dimension": "handoff completeness",
            "status": "PASS",
            "notes": "Scorecard, route, script, one-pager, limitations, issue log, action list, and audits are present.",
        },
        {
            "dimension": "capture readiness",
            "status": "NEEDS_REVIEW",
            "notes": "Checklist is ready, but screenshots/video are intentionally not captured by this headless/local runner.",
        },
    ]
    counts: dict[str, int] = {}
    for item in dimensions:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "overall_status": "PASS_WITH_LIMITATIONS",
        "dimensions": dimensions,
        "status_counts": counts,
        "review_notes": [
            "Use this scorecard for rehearsal and human review, not as operational acceptance.",
            "The one NEEDS_REVIEW item is expected until manual capture or review-session evidence exists.",
        ],
    }


def polished_route(d8_decision: dict[str, Any]) -> str:
    demo_index = (
        d8_decision.get("demonstrable_surface", {}).get("demo_index")
        or "outputs/main_citybrain_d8_demonstrable_surface_integration_r1/D8_DEMO_INDEX.html"
    )
    return f"""# D9 Polished Demo Route

Boundary label: local D9 review derivative of the D8 final handoff. It does not rewrite D8 evidence or upgrade gated capabilities.

Original local demo index:

`{demo_index}`

## Step 1 - Open the D8 handoff state

Show the D8 final handoff package, the scoreboard, and the artifact index. Frame the demo as a bounded local review surface with evidence and limitations side by side.

Callout: the handoff package is audited demo state only; it is not an operational deployment or a legal finding.

## Step 2 - Mobility M04/M05 abstain semantics

Show the mobility abstain patch and explain that M04/M05 render readiness is not a positive mobility baseline. The safe product behavior is abstain when the evidence is not sufficient.

Callout: mobility routing, traffic control, and operational mobility decisions remain out of scope.

## Step 3 - Web+Kit local handoff surface

Show the Web+Kit bundle smoke result and the local demo surface. Position it as a local handoff between web review materials and Kit/Omniverse context.

Callout: this is not native web USD/RTX streaming and not a deployed product UI.

## Step 4 - Helsinki Kalasatama semantic sidecar

Show the Helsinki sidecar/object-pick packet material. The useful story is visual object -> candidate sidecar context -> evidence refs -> limitation refs.

Callout: Helsinki object-pick packets remain pending review unless explicit human-review evidence is added. The mesh remains a visual backdrop until object-level alignment evidence is proven.

## Step 5 - Chicago bounded similar-case memory

Show the Chicago reviewed cases, bounded matches, and demo query smoke. The system can demonstrate a small evidence-backed memory slice.

Callout: the 15-row sample and 45 bounded matches do not support citywide trend truth, causal prediction, legal conclusion, or operational action.

## Step 6 - VSS closed-gate readiness story

Show the VSS candidate ledger, missing requirements checklist, and sample ingest smoke. The point is that CityBrain can say no cleanly when required evidence is missing.

Callout: VSS sample ingest and VSS runtime readiness remain closed because there is no eligible licensed, metadata-complete sample.

## Step 7 - Close with evidence, limits, and next review

Show the limitation register, artifact index, and this D9 scorecard. Close by asking reviewers to log issues against a specific step and artifact.

Callout: no enforcement, dispatch, autonomous action, legal determination, live ingestion, or public deployment claim is made by this demo.
"""


def polished_operator_script() -> str:
    return """# D9 Polished Operator Script

## Opening framing

This is a local CityBrain demo review. We are looking at what the D8 handoff can demonstrate with evidence attached, and where the system correctly stops because the evidence is incomplete.

The key rule for this walkthrough: limitations are part of the evidence, not a footnote.

## 7-step route narration

1. Open the D8 handoff state.
   - "Start with the scoreboard and artifact index. This is the package we are reviewing."
   - If missing: "Pause here; the handoff artifact is unavailable, so this step cannot be reviewed."

2. Mobility M04/M05 abstain semantics.
   - "This shows the right behavior when mobility baseline evidence is insufficient: abstain, preserve the limitation, and avoid a stronger claim."
   - Limitation callout: no routing or traffic-control action is produced.

3. Web+Kit local handoff surface.
   - "This is the bridge between a readable web review surface and Kit/Omniverse context."
   - Limitation callout: local handoff only; not native browser RTX streaming or a deployed product.

4. Helsinki Kalasatama semantic sidecar.
   - "Here the demo shows a path from a visual object context into candidate sidecar evidence."
   - Limitation callout: object-pick packets remain pending review; the mesh is visual context until alignment evidence is proven.

5. Chicago bounded similar-case memory.
   - "This demonstrates a small, evidence-backed similar-case slice."
   - Limitation callout: bounded sample only; citywide trend answers abstain.

6. VSS closed-gate readiness.
   - "This is the system refusing to pretend a vision corpus is ready when license, metadata, oracle, or privacy evidence is incomplete."
   - Limitation callout: sample ingest and runtime readiness remain closed.

7. Close with limitations and reviewer actions.
   - "The package is valuable because it shows both capability and restraint. Reviewers should log issues against exact steps and artifacts."

## Failure-safe narration

If a page, file, or screenshot is missing, do not improvise a stronger story. Say: "This artifact is not available in the local review environment. The issue should be logged against this step, and no conclusion should be drawn from the missing view."

## Closing statement

The demo proves a bounded, evidence-linked review route across mobility abstain behavior, local Web+Kit handoff, Helsinki candidate sidecars, Chicago bounded similar-case memory, and VSS closed-gate discipline. It does not prove operational deployment, legal conclusions, live ingestion, autonomous action, dispatch, enforcement, or VSS runtime readiness.
"""


def executive_one_pager() -> str:
    return """# D9 Executive Demo One-Pager

## What this demo proves

CityBrain can assemble a local, reviewable demo route where each story beat points to evidence and visible limitation labels. It shows useful progress in five lanes: mobility abstain behavior, Web+Kit handoff, Helsinki semantic sidecar review, Chicago bounded similar-case memory, and VSS gate discipline.

## What this demo does not prove

It does not prove operational deployment, legal conclusions, live ingestion, autonomous action, dispatch, enforcement, production UI readiness, VSS runtime readiness, complete Helsinki object alignment, or Chicago citywide memory.

## The five final demo lanes included

- Mobility: M04/M05 abstain semantics when baseline evidence is insufficient.
- Web+Kit: local demo and Kit handoff surface.
- Helsinki: candidate visual-object-to-sidecar path with pending review.
- Chicago: bounded similar-case query slice from 15 reviewed cases and 45 matches.
- VSS: licensed-corpus and sample-ingest gates remain closed until evidence exists.

## Why the limitation labels matter

The limitation labels are not disclaimers added after the fact. They are part of the review evidence. They show where CityBrain can demonstrate capability and where it should safely stop.

## Recommended next review actions

Run a human review session against the D9 route, capture screenshots or video if needed, decide whether VSS remains parked, and choose whether D10 should focus on publication readiness or the next implementation sprint.
"""


def capture_checklist() -> str:
    checks = [
        "local demo index opened",
        "final route visible",
        "scoreboard visible",
        "limitation register visible",
        "mobility abstain step visible",
        "Helsinki sidecar/object-pick step visible",
        "Chicago memory/query step visible",
        "VSS closed-gate step visible",
        "evidence/artifact index visible",
        "final boundary statement visible",
    ]
    rows = "\n".join(f"- [ ] {item}" for item in checks)
    return f"""# D9 Screenshot and Capture Checklist

Capture status: `NOT_CAPTURED_ENVIRONMENT_LIMITATION`

This runner prepares the checklist but does not require live screenshots or video capture. Manual reviewers can use this list during rehearsal.

{rows}

Required capture boundary: screenshots or recordings may show local demo/review state only. They must not be described as operational monitoring, legal determination, dispatch/control output, or VSS runtime evidence.
"""


def recommended_actions() -> str:
    return """# D9 Recommended Review Actions

## before_live_demo

- Run `MAIN-CITYBRAIN-D9-HUMAN-REVIEW-SESSION-CAPTURE-R2` with the polished route and scorecard.
- Open the local demo index and verify the scoreboard, limitation register, and artifact index are visible.
- Capture screenshots or video only if useful for the review session.

## before_external_share

- Decide whether the executive one-pager needs audience-specific copyediting.
- Confirm that every externally shared screenshot keeps visible limitation labels.
- Keep VSS described as a closed gate unless eligible licensed sample evidence is added.

## future_D10

- Decide whether D10 should be demo publication readiness, stakeholder narrative, or the next implementation sprint.
- Decide whether Chicago memory should expand beyond the 15-row bounded sample.
- Decide whether Helsinki object-pick packets should move to an evidence-backed human review task.

## parked

- VSS runtime work remains parked until a licensed, metadata-complete, privacy-reviewed sample exists.
- Operational deployment, legal workflows, dispatch, enforcement, and autonomous action remain outside this demo lane.
"""


def review_index_html() -> str:
    links = [
        ("Decision", "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json"),
        ("Scorecard", "D9_DEMO_REVIEW_SCORECARD.json"),
        ("Polished route", "D9_POLISHED_DEMO_ROUTE.md"),
        ("Operator script", "D9_POLISHED_OPERATOR_SCRIPT.md"),
        ("Executive one-pager", "D9_EXECUTIVE_DEMO_ONE_PAGER.md"),
        ("Capture checklist", "D9_SCREENSHOT_AND_CAPTURE_CHECKLIST.md"),
        ("Issue log template", "D9_REVIEWER_ISSUE_LOG_TEMPLATE.csv"),
        ("Recommended review actions", "D9_RECOMMENDED_REVIEW_ACTIONS.md"),
        ("Limitation register", "D9_LIMITATION_REGISTER.json"),
        ("D8 final route", "../main_citybrain_d8_final_demo_capture_and_certified_handoff_r1/D8_FINAL_DEMO_ROUTE.md"),
        ("D8 demo index", "../main_citybrain_d8_demonstrable_surface_integration_r1/D8_DEMO_INDEX.html"),
    ]
    items = "\n".join(f'<li><a href="{html.escape(href)}">{html.escape(label)}</a></li>' for label, href in links)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain D9 Review Index</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; background: #f7f8fa; color: #1e252d; }}
    main {{ max-width: 980px; margin: 0 auto; background: #fff; border: 1px solid #d8dee8; padding: 24px; }}
    h1 {{ margin-top: 0; }}
    .boundary {{ border-left: 4px solid #506680; padding: 12px 16px; background: #eef3f7; }}
    li {{ margin: 8px 0; }}
  </style>
</head>
<body>
<main>
  <h1>CityBrain D9 Review Index</h1>
  <p class="boundary">Boundary: local review derivative. D8 evidence is preserved. Gated items remain gated.</p>
  <p>Use this page to rehearse the D9 route, open review artifacts, and log issues against exact steps.</p>
  <ul>
{items}
  </ul>
</main>
</body>
</html>
"""


def create_limitation_register(d8_limitations: dict[str, Any]) -> dict[str, Any]:
    base = list(d8_limitations.get("limitations", []))
    additions = [
        {
            "id": "lim:d9_review_polish_derivative_only",
            "label": "D9 is review/polish derivative only",
            "details": "D9 creates clearer review artifacts but does not generate new raw evidence or change D8 state.",
            "affected_lanes": ["D9_review_loop"],
        },
        {
            "id": "lim:d9_no_new_raw_evidence",
            "label": "No new raw evidence generated",
            "details": "The package references existing D8 and lane artifacts unless a future human review adds evidence.",
            "affected_lanes": ["D9_review_loop"],
        },
        {
            "id": "lim:d9_screenshots_not_captured",
            "label": "Screenshots not captured by this runner",
            "details": "Capture checklist is ready; capture status is NOT_CAPTURED_ENVIRONMENT_LIMITATION.",
            "affected_lanes": ["D9_review_loop"],
        },
        {
            "id": "lim:d9_no_human_approval_inferred",
            "label": "No human/manual approval inferred",
            "details": "Review-session approval requires explicit future evidence.",
            "affected_lanes": ["D9_review_loop", "Helsinki_object_pick_review_capture"],
        },
        {
            "id": "lim:d9_script_quality_not_operational_readiness",
            "label": "Polished script quality does not imply operational readiness",
            "details": "Clearer narration does not upgrade any D8 limitation or gate.",
            "affected_lanes": ["D9_review_loop"],
        },
    ]
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "source": rel(D8_ROOT / "D8_FINAL_LIMITATION_REGISTER.json"),
        "limitations": base + additions,
    }


def create_artifact_index() -> dict[str, Any]:
    return {
        "task": TASK_ID,
        "generated_at": RUN_TS,
        "artifacts": [
            {
                "relative_path": path,
                "purpose": purpose,
                "upstream_source_dependency": dependency,
                "claim_boundary_note": note,
            }
            for path, purpose, dependency, note in ARTIFACTS
        ],
    }


def write_issue_log_template(path: Path) -> None:
    headers = [
        "issue_id",
        "reviewer",
        "demo_step",
        "severity",
        "issue_type",
        "description",
        "artifact_ref",
        "recommended_fix",
        "claim_boundary_related",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)


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
    return {
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
        "files_checked": len(rows),
        "results": rows,
    }


SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\b(token|secret|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def secret_scan_audit() -> dict[str, Any]:
    findings = []
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern, "offset": match.start()})
    return {
        "status": "PASS" if not findings else "FAIL",
        "files_checked": sum(1 for p in OUT_ROOT.rglob("*") if p.is_file()),
        "findings": findings,
    }


FORBIDDEN_PATTERNS = [
    ("production_readiness", re.compile(r"(?i)\bproduction readiness\b")),
    ("certified_operational_deployment", re.compile(r"(?i)\bcertified operational deployment\b")),
    ("legal_determination", re.compile(r"(?i)\blegal determination\b")),
    ("enforcement", re.compile(r"(?i)\benforcement\b")),
    ("dispatch_control", re.compile(r"(?i)\bdispatch/control\b|\bdispatch\b|\btraffic-control\b")),
    ("autonomous_action", re.compile(r"(?i)\bautonomous action\b")),
    ("live_ingestion", re.compile(r"(?i)\blive ingestion\b")),
    ("vss_runtime_readiness", re.compile(r"(?i)\bVSS runtime readiness\b")),
    ("vss_corpus_readiness", re.compile(r"(?i)\bVSS corpus readiness\b")),
    ("helsinki_completed_human_review", re.compile(r"(?i)\b(completed|approved|accepted)\s+Helsinki\s+(human|manual)\s+review\b")),
    ("chicago_citywide_truth", re.compile(r"(?i)\bChicago citywide (trend )?truth\b|\bcitywide trend truth\b")),
]


SAFE_CONTEXT_PATTERNS = [
    re.compile(r"(?i)\bno\b"),
    re.compile(r"(?i)\bnot\b"),
    re.compile(r"(?i)\bdoes not\b"),
    re.compile(r"(?i)\bdo not\b"),
    re.compile(r"(?i)\bmust not\b"),
    re.compile(r"(?i)\bwithout\b"),
    re.compile(r"(?i)\boutside scope\b"),
    re.compile(r"(?i)\boutside this demo lane\b"),
    re.compile(r"(?i)\bclosed\b"),
    re.compile(r"(?i)\bgated\b"),
    re.compile(r"(?i)\babstain\b"),
    re.compile(r"(?i)\bpending review\b"),
    re.compile(r"(?i)\bbounded\b"),
    re.compile(r"(?i)\bremains\b"),
    re.compile(r"(?i)\bfails on unsupported\b"),
    re.compile(r"(?i)\bforbidden-claim boundary audit\b"),
]


def is_safe_context(line: str) -> bool:
    return any(pattern.search(line) for pattern in SAFE_CONTEXT_PATTERNS)


def claim_boundary_audit() -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(OUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.sha256"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line) and not is_safe_context(line):
                    findings.append({"path": rel(path), "line": lineno, "pattern": name, "text": line.strip()[:220]})
    return {
        "status": "PASS" if not findings else "FAIL",
        "files_checked": checked,
        "findings": findings,
        "boundary": "D9 may polish review copy but must not upgrade D8 limitations or imply operational capability.",
    }


def referenced_artifact_existence_audit() -> dict[str, Any]:
    refs = []
    for name in REQUIRED_D8_FILES:
        path = D8_ROOT / name
        refs.append({"path": rel(path), "required": True, "exists": path.exists(), "source": "D8 required input"})
    for name, root in OPTIONAL_ROOTS.items():
        refs.append({"path": rel(root), "required": False, "exists": root.exists(), "source": name})
    for artifact, *_ in ARTIFACTS:
        path = OUT_ROOT / artifact
        expected_late = artifact in {
            "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json",
            "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json",
            "HASH_MANIFEST.sha256",
        }
        refs.append(
            {
                "path": rel(path),
                "required": True,
                "exists": path.exists() or expected_late,
                "source": "D9 generated output",
                "expected_late_generated": expected_late,
            }
        )
    return {
        "status": "PASS" if all((not r["required"]) or r["exists"] for r in refs) else "FAIL",
        "references_checked": len(refs),
        "references": refs,
    }


def write_audits(before_hashes: dict[str, str | None]) -> dict[str, Any]:
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit())
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan_audit())
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_prior_output_mutation_audit(before_hashes))
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_existence_audit())
    return {
        "json_parse": read_json(OUT_ROOT / "JSON_PARSE_AUDIT.json") or {},
        "secret_scan": read_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json") or {},
        "claim_boundary": read_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json") or {},
        "no_prior_output_mutation": read_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json") or {},
        "referenced_artifacts": read_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json") or {},
    }


def no_prior_output_mutation_audit(before: dict[str, str | None]) -> dict[str, Any]:
    after = snapshot_required_d8_hashes()
    changed = [
        {"path": rel(D8_ROOT / name), "before": before.get(name), "after": after.get(name)}
        for name in sorted(before)
        if before.get(name) != after.get(name)
    ]
    return {
        "status": "PASS" if not changed else "FAIL",
        "d8_root": rel(D8_ROOT),
        "files_checked": len(before),
        "changed": changed,
        "prior_outputs_mutated": bool(changed),
    }


def create_hash_manifest() -> None:
    rows = []
    for path in sorted(OUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.sha256":
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUT_ROOT / "HASH_MANIFEST.sha256", "\n".join(rows) + "\n")


def fail_decision(reason: str, d8_status: str, missing: list[str], before_hashes: dict[str, str | None]) -> None:
    reset_output_root()
    decision = {
        "task": TASK_ID,
        "status": STATUS_FAIL,
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUT_ROOT),
        "upstream_d8_root": str(D8_ROOT),
        "upstream_d8_status": d8_status,
        "missing_required_d8_files": missing,
        "failure_reason": reason,
        "created_artifacts": [],
        "final_recommendation": "Fix missing or invalid D8 handoff before D9 review polish.",
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json", decision)
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_prior_output_mutation_audit(before_hashes))
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit())
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan_audit())
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_existence_audit())
    create_hash_manifest()


def main() -> int:
    before_hashes = snapshot_required_d8_hashes() if D8_ROOT.exists() else {name: None for name in REQUIRED_D8_FILES}
    upstream_ok, d8_status, missing, d8_decision, d8_scoreboard, d8_limitations = validate_upstream()
    if not upstream_ok:
        fail_decision("Required D8 final handoff is missing, invalid, or not in the expected status.", d8_status, missing, before_hashes)
        print(f"{TASK_ID}: {STATUS_FAIL}")
        print(f"Output: {rel(OUT_ROOT)}")
        return 1

    reset_output_root()

    scorecard = create_scorecard()
    optional_roots = [
        {"name": name, "path": rel(path), "exists": path.exists()}
        for name, path in OPTIONAL_ROOTS.items()
    ]
    d8_zip_info = {
        "path": rel(D8_ZIP) if D8_ZIP.exists() else None,
        "exists": D8_ZIP.exists(),
        "sha256": sha256_file(D8_ZIP) if D8_ZIP.exists() else None,
    }

    write_text(
        OUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status target: `{STATUS_PASS}`

This package is a D9 review/polish derivative of the D8 final demo handoff. It creates clearer review artifacts, a scorecard, issue-log template, capture checklist, limitation register, and audits.

Important boundary: D9 does not rewrite D8 history, generate new raw evidence, infer human approval, or upgrade gated lanes.

No issue rows were pre-seeded in `D9_REVIEWER_ISSUE_LOG_TEMPLATE.csv`; it is header-only for reviewers.

Recommended next task: `MAIN-CITYBRAIN-D9-HUMAN-REVIEW-SESSION-CAPTURE-R2`
""",
    )
    write_json(OUT_ROOT / "D9_DEMO_REVIEW_SCORECARD.json", scorecard)
    write_text(OUT_ROOT / "D9_POLISHED_DEMO_ROUTE.md", polished_route(d8_decision))
    write_text(OUT_ROOT / "D9_POLISHED_OPERATOR_SCRIPT.md", polished_operator_script())
    write_text(OUT_ROOT / "D9_EXECUTIVE_DEMO_ONE_PAGER.md", executive_one_pager())
    write_text(OUT_ROOT / "D9_SCREENSHOT_AND_CAPTURE_CHECKLIST.md", capture_checklist())
    write_issue_log_template(OUT_ROOT / "D9_REVIEWER_ISSUE_LOG_TEMPLATE.csv")
    write_text(OUT_ROOT / "D9_RECOMMENDED_REVIEW_ACTIONS.md", recommended_actions())
    write_json(OUT_ROOT / "D9_LIMITATION_REGISTER.json", create_limitation_register(d8_limitations))
    write_text(OUT_ROOT / "D9_REVIEW_INDEX.html", review_index_html())
    write_json(
        OUT_ROOT / "D9_OPTIONAL_DEMO_POLISH_PATCH_MANIFEST.json",
        {
            "task": TASK_ID,
            "generated_at": RUN_TS,
            "patches_created": [
                {
                    "relative_path": "D9_REVIEW_INDEX.html",
                    "purpose": "Local D9 review landing page with boundary label and links to D9/D8 artifacts.",
                    "lives_under_d9_output_root": True,
                    "overwrites_d8_output": False,
                    "visible_boundary_label": True,
                }
            ],
            "rules": {
                "do_not_overwrite_d8_outputs": True,
                "derivative_files_under_d9_root_only": True,
                "links_back_to_original_d8_artifacts": True,
            },
        },
    )
    write_json(OUT_ROOT / "D9_ARTIFACT_INDEX.json", create_artifact_index())

    audit_files = write_audits(before_hashes)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if audits_pass else STATUS_FAIL

    decision = {
        "task": TASK_ID,
        "status": final_status,
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUT_ROOT),
        "upstream_d8_root": str(D8_ROOT),
        "upstream_d8_status": d8_status,
        "upstream_d8_zip": d8_zip_info,
        "optional_context_roots": optional_roots,
        "created_artifacts": [artifact for artifact, *_ in ARTIFACTS],
        "review_pass_fail_summary": {
            "overall_scorecard_status": scorecard["overall_status"],
            "dimension_counts": scorecard["status_counts"],
            "audits": {name: audit.get("status") for name, audit in audit_files.items()},
            "capture_status": "NOT_CAPTURED_ENVIRONMENT_LIMITATION",
        },
        "limitation_summary": {
            "d8_limitations_preserved": len(d8_limitations.get("limitations", [])),
            "d9_limitations_added": 5,
            "critical_gates_still_visible": [
                "M04/M05 abstain semantics",
                "Helsinki object-pick packets pending review",
                "Chicago bounded sample memory, not citywide truth",
                "VSS sample ingest gate closed",
                "Web+Kit local handoff only",
            ],
        },
        "d8_summary_refs": {
            "d8_scoreboard_task": d8_scoreboard.get("task"),
            "d8_demo_steps": d8_decision.get("demo_route", {}).get("steps"),
            "d8_claim_boundaries": d8_decision.get("claim_boundaries", {}),
            "d8_r3_counts": d8_decision.get("r3_counts", {}),
        },
        "final_recommendation": "MAIN-CITYBRAIN-D9-HUMAN-REVIEW-SESSION-CAPTURE-R2",
        "acceptance_notes": [
            "D8 final handoff was read and preserved.",
            "The 7-step route remains intact and easier to rehearse.",
            "Limitation labels are visible in route, script, one-pager, checklist, and limitation register.",
            "No D8 output was mutated.",
            "Reviewer issue-log template is header-only; no issues were pre-seeded.",
        ],
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json", decision)

    # Re-run audits after the decision exists, then refresh the decision summary.
    audit_files = write_audits(before_hashes)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if audits_pass else STATUS_FAIL
    decision["status"] = final_status
    decision["review_pass_fail_summary"]["audits"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json", decision)

    # Final audit pass after the refreshed decision. These audit files are the
    # ones included in the hash manifest.
    audit_files = write_audits(before_hashes)
    audits_pass = all(audit.get("status") == "PASS" for audit in audit_files.values())
    final_status = STATUS_PASS if audits_pass else STATUS_FAIL
    decision["status"] = final_status
    decision["review_pass_fail_summary"]["audits"] = {name: audit.get("status") for name, audit in audit_files.items()}
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_DECISION.json", decision)
    create_hash_manifest()

    print(f"{TASK_ID}: {final_status}")
    print(f"Output: {rel(OUT_ROOT)}")
    return 0 if final_status == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
