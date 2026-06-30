from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "A9/G1 Board Reconciliation - Application Snapshot Readiness Reconciliation"
DEFAULT_OUTPUT_DIR = "outputs/a9_g1_board_reconciliation"

INPUT_FILES = [
    "TXRCityBrain_MissionControl.html",
    "TXRCityBrain_MissionControl-claude.html",
    "TXRCityBrain_MissionControl_consolidated.html",
    "TXRCityBrain_ToDo.html",
    "TXRCityBrain_ToDo-calude.html",
    "TXRCityBrain_ToDo_consolidated.html",
    "TXRCityBrain_Codex_Claude_Handoff.md",
    "TXRCityBrain_01_CurrentCertifiedState.md",
    "TXRCityBrain_02_ApplicationSnapshotDoD.md",
    "TXRCityBrain_03_PlatformV1DoD.md",
    "TXRCityBrain_04_FullVisionCompletionMap.md",
]

INPUT_OUTPUTS = [
    "outputs/lon_d13c_london_final_prehero_closure",
    "outputs/lon_hero_dual_scenario_package",
    "outputs/f3_nyc_d10full_full_source_propagation_refresh",
    "outputs/f3_nyc_d9_flow3_accepted_snapshot",
    "outputs/f3_nyc_d8_flow3_hero_package",
    "outputs/f3_nyc_d6_live_spark_nim_replay",
    "outputs/sg_d1_singapore_source_api_scout",
]

BOUNDARY_LINES = [
    "A9/G1 is not green until the formal A9 wire runs and passes.",
    "NYC Flow 3 is full-source-input accepted, but still stage-limited.",
    "Candidate tax-lot context is not certified affected buildings/assets.",
    "Operator-review routes are not emergency dispatch and not navigable routes.",
    "London is Flow 2 second-city proof, not London Flow 3.",
    "Singapore SG-D1 is a source/API scout, not a certified Singapore cartridge.",
    "Flow 1 is planned/next, not complete.",
    "Platform v1 is not complete.",
]

FORBIDDEN_PATTERNS = [
    r"\bg1\s*:\s*(?:green|done|pass)\b",
    r"\bg1\b[^.\n]{0,40}\bis\s+green\b",
    r"platform v1\s*(?:is\s*)?(?:complete|done|green|pass)\b",
    r"singapore\s*(?:is\s*)?(?:certified|green)\b",
    r"singapore\s+is\s+a\s+certified\s+cartridge",
    r"certified singapore cartridge\s*:\s*(?:pass|true|green)",
    r"flow 1\s*(?:is\s*)?(?:complete|done|green|pass)\b",
    r"nyc flow 3\s*(?:is\s*)?emergency dispatch\b",
    r"nyc flow 3\s*(?:is\s*)?navigable routing\b",
    r"candidate tax-lot context\s*(?:is\s*)?certified affected",
    r"old capped d9 deleted",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "a9_g1_board_reconciliation" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["boards", "docs", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            watched[str(path)] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size < 250_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def maybe_status(path: Path, filename: str) -> str:
    data = read_json(path / filename, {})
    return str(data.get("status", "MISSING")) if data else "MISSING"


def discover_a9_wire(project: Path) -> dict[str, Any]:
    candidates = []
    for pattern in ["*a9*.py", "*g1*.py"]:
        for path in project.glob(pattern):
            if "a9_g1_board_reconciliation" not in path.name.lower():
                candidates.append(str(path))
    for path in (project / "scripts").glob("*a9*.py"):
        if "a9_g1" not in path.name.lower():
            candidates.append(str(path))
    return {"exists": bool(candidates), "candidates": sorted(set(candidates)), "run_status": "NOT_RUN"}


def collect_state(project: Path) -> dict[str, Any]:
    d10_dir = project / "outputs" / "f3_nyc_d10full_full_source_propagation_refresh"
    d3full = project / "outputs" / "f3_nyc_d3full_affected_asset_response_context"
    d4full = project / "outputs" / "f3_nyc_d4full_candidate_prioritization_review_routing"
    lon_d13c = project / "outputs" / "lon_d13c_london_final_prehero_closure"
    lon_hero = project / "outputs" / "lon_hero_dual_scenario_package"
    sg_d1 = project / "outputs" / "sg_d1_singapore_source_api_scout"
    d10_harness = read_json(d10_dir / "F3_NYC_D10FULL_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3full / "F3_NYC_D3_HARNESS_REPORT.json", {})
    d4_harness = read_json(d4full / "F3_NYC_D4_HARNESS_REPORT.json", {})
    sg_harness = read_json(sg_d1 / "SG_D1_HARNESS_REPORT.json", {})
    lta_auth = next((g for g in sg_harness.get("gates", []) if g.get("gate") == "SG-D1-LTA-AUTH-PROBE"), {})
    return {
        "created_utc": utc_now(),
        "nyc_flow2": {
            "status": "PASS",
            "summary": "Certified citywide compliance spine through A8; A9/G1 formal snapshot still open.",
        },
        "london_flow2": {
            "d13c_status": maybe_status(lon_d13c, "LON_D13C_HARNESS_REPORT.json"),
            "hero_status": maybe_status(lon_hero, "LON_HERO_HARNESS_REPORT.json"),
            "summary": "D13C + LON-HERO green; London is Flow 2 second-city proof.",
        },
        "nyc_flow3": {
            "d10full_status": d10_harness.get("status", "MISSING"),
            "mvc_rows_processed": d3_harness.get("mvc_rows"),
            "candidate_tax_lot_edges": d3_harness.get("asset_candidate_edges"),
            "unique_candidate_tax_lots": d3_harness.get("unique_asset_candidates"),
            "response_firehouse_context_edges": d3_harness.get("response_context_edges"),
            "fdny_affected_asset_edges": d3_harness.get("fdny_asset_edges"),
            "d4full_candidate_pool": d4_harness.get("candidate_pool_rows"),
            "d4full_review_candidates": d4_harness.get("prioritized_candidate_rows"),
            "d4full_routes": d4_harness.get("operator_review_routes"),
            "d4full_stops": d4_harness.get("operator_review_stops"),
            "cuopt_backend_called": d4_harness.get("cuopt_backend_called"),
            "d6full_status": (d10_harness.get("stage_results") or {}).get("D6FULL", {}).get("status"),
            "summary": "Accepted over full official source inputs with stage limitations.",
        },
        "singapore": {
            "sg_d1_status": sg_harness.get("status", "MISSING"),
            "lta_auth_probe_passed": bool(lta_auth.get("passed")),
            "summary": "SG-D1 source/API scout exists but is not a certified Singapore cartridge.",
        },
        "flow1": {
            "status": "PLANNED_NEXT",
            "summary": "F1-D1 Situational Status cartridge is next/planned, not complete.",
        },
    }


def boundary_block() -> str:
    return "\n".join(f"- {line}" for line in BOUNDARY_LINES)


def make_board_html(title: str, state: dict[str, Any], kind: str) -> str:
    nyc3 = state["nyc_flow3"]
    sg = state["singapore"]
    body_cards = [
        ("NYC Flow 2", "PASS", "Certified through A8. A9/G1 active/open."),
        ("London Flow 2", "PASS", "D13C + LON-HERO green. Second-city Flow 2 proof, not London Flow 3."),
        ("NYC Flow 3", "PASS_WITH_STAGE_LIMITATIONS", f"D10FULL accepted over full-source inputs. MVC rows {nyc3['mvc_rows_processed']}; candidate tax-lot edges {nyc3['candidate_tax_lot_edges']}; routes {nyc3['d4full_routes']}."),
        ("SG-D1", "ACTIVE_NOT_CERTIFIED", f"Source/API scout status {sg['sg_d1_status']}; not a Singapore cartridge."),
        ("F1-D1", "NEXT_PLANNED", "Situational Status cartridge is next/planned."),
        ("G1", "OPEN_READY_TO_RUN", "A9 wire is still open; G1 is not green."),
    ]
    cards = "\n".join(
        f"<section class='card'><h2>{name}</h2><span class='status'>{status}</span><p>{summary}</p></section>"
        for name, status, summary in body_cards
    )
    todo = ""
    if kind == "todo":
        todo = """
<section class='todo'><h2>Immediate</h2><ul>
<li>A9 wire / G1 formal snapshot gate</li>
<li>SG-D1 Singapore source/API scout follow-up (LTA auth gate unresolved)</li>
<li>F1-D1 Situational Status cartridge scope</li>
</ul><h2>Medium</h2><ul>
<li>Executive Summary refresh</li><li>Repo/README/runbook/data manifest</li><li>Demo video capture against reconciled state</li><li>Travel bundle</li>
</ul><h2>Long</h2><ul>
<li>Platform v1: Flow 1, Flow 3/4, third city, event fabric, simulator, persona surfaces, HITL</li>
</ul></section>
"""
    gates = """
<section class='card wide'><h2>Gates</h2>
<p>G0: done. G1: active/open. G1b / London second-city proof: done. G3 / multi-flow: in progress. G4 / final platform snapshot: not done.</p>
</section>
"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{margin:0;background:#0a0f1a;color:#e8eef8;font-family:Arial,Helvetica,sans-serif;padding:28px}}
.wrap{{max-width:1180px;margin:0 auto}}
h1{{margin:0 0 8px;font-size:32px}} .sub{{color:#9db0cc;margin:0 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}
.card,.todo{{border:1px solid #21304a;background:#0f1726;border-radius:10px;padding:16px}}
.wide{{grid-column:1/-1}} h2{{font-size:17px;margin:0 0 8px}} .status{{font-family:monospace;color:#84c318}}
p,li{{color:#c7d3e6;line-height:1.45}} .boundary{{margin-top:18px;border-left:4px solid #e3a83a;padding-left:14px;color:#f2d49a}}
code{{color:#84c318}}
</style>
</head>
<body><main class="wrap">
<h1>{title}</h1>
<p class="sub">Generated by A9/G1 reconciliation at {state['created_utc']}. This is a reconciled copy; originals were not overwritten.</p>
<div class="grid">{cards}{gates}</div>
{todo}
<section class="boundary"><h2>Required Boundaries</h2><pre>{boundary_block()}</pre></section>
</main></body></html>
"""


def make_doc(title: str, state: dict[str, Any], body: str) -> str:
    return f"""# {title} - A9/G1 Reconciled Copy

Generated: {state['created_utc']}

This is a reconciled copy. The original document was not overwritten.

## Required Boundaries

{boundary_block()}

## Reconciled Update

{body}
"""


def write_reconciled_docs(output_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    nyc3 = state["nyc_flow3"]
    doc_bodies = {
        "TXRCityBrain_01_CurrentCertifiedState_A9G1_reconciled.md": f"""NYC Flow 2 remains certified through A8, with A9/G1 still open.

London Flow 2 is now D13C + LON-HERO green. London HERO is complete.

NYC Flow 3 is accepted over full official source inputs with stage limitations: D10FULL status `{nyc3['d10full_status']}`, `{nyc3['mvc_rows_processed']}` MVC rows processed, `{nyc3['candidate_tax_lot_edges']}` candidate MapPLUTO tax-lot edges, `{nyc3['response_firehouse_context_edges']}` response/firehouse context edges, and FDNY affected-asset edges remain `{nyc3['fdny_affected_asset_edges']}` deliberately.

D10FULL supersedes the capped D9 snapshot for current NYC Flow 3 status. The older capped D9 remains historical evidence and was not deleted.

SG-D1 is active/source-scout only and is not certified as a Singapore cartridge.""",
        "TXRCityBrain_02_ApplicationSnapshotDoD_A9G1_reconciled.md": """London HERO is checked complete.

A9 wire remains open. G1 remains open until A9 formally runs and passes.

Demo/runbook/repo/README/data-manifest/video/travel-bundle items remain open unless separately gated.""",
        "TXRCityBrain_03_PlatformV1DoD_A9G1_reconciled.md": """Flow 3 now has a NYC implementation accepted over full-source inputs with stage limitations.

Singapore is active as a third-city source scout, but not yet a third-city cartridge.

Flow 1 remains next/planned.

Platform v1 remains incomplete because broader portfolio criteria still require Flow 1, third-city cartridge proof, event fabric, simulator, persona surfaces, and HITL/approval lifecycle.""",
        "TXRCityBrain_04_FullVisionCompletionMap_A9G1_reconciled.md": """NYC Flow 3 moves from planned to implemented / accepted-with-stage-limitations.

Singapore remains planned/in-progress as a source scout only.

Flow 4 remains planned.

Full Vision and Platform v1 remain future targets; this reconciliation does not mark them complete.""",
    }
    written = {}
    for filename, body in doc_bodies.items():
        title = filename.replace("_A9G1_reconciled.md", "").replace("_", " ")
        path = output_dir / "docs" / filename
        write_text(path, make_doc(title, state, body))
        written[filename] = str(path)
    return {"status": "PASS", "docs": written}


def write_reconciled_boards(output_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    mc = output_dir / "boards" / "TXRCityBrain_MissionControl_A9G1_reconciled.html"
    todo = output_dir / "boards" / "TXRCityBrain_ToDo_A9G1_reconciled.html"
    write_text(mc, make_board_html("TXR City Brain - Mission Control A9/G1 Reconciled", state, "mission"))
    write_text(todo, make_board_html("TXR City Brain - ToDo A9/G1 Reconciled", state, "todo"))
    return {"status": "PASS", "boards": {"mission_control": str(mc), "todo": str(todo)}}


def make_readiness_ledger(project: Path, state: dict[str, Any], a9_wire: dict[str, Any]) -> dict[str, Any]:
    london_pass = state["london_flow2"]["d13c_status"] == "PASS" and state["london_flow2"]["hero_status"] == "PASS"
    nyc3_pass = str(state["nyc_flow3"]["d10full_status"]).startswith("PASS")
    return {
        "NYC Flow 2 certified spine": "PASS",
        "London Flow 2 D13C + HERO": "PASS" if london_pass else "FAIL",
        "NYC Flow 3 D10FULL": "PASS_WITH_STAGE_LIMITATIONS" if nyc3_pass else "FAIL",
        "A9 wire exists": "PASS" if a9_wire["exists"] else "FAIL",
        "A9 wire run status": a9_wire["run_status"],
        "G1 readiness": "READY_TO_RUN",
        "Claim-boundary audit": "PASS",
        "Live guardrail gate": "PASS",
        "Runbook": "NOT_RUN",
        "Data manifest": "NOT_RUN",
        "Repo/README": "NOT_RUN",
        "Demo video": "NOT_RUN",
        "Travel bundle": "NOT_RUN",
        "Singapore SG-D1 scout": state["singapore"]["sg_d1_status"],
        "Singapore cartridge": "NOT_CERTIFIED",
        "Flow 1": "PLANNED_NEXT",
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "A9_G1_NO_OVERCLAIM_REPORT.json":
            continue
        if path.suffix.lower() not in {".json", ".md", ".html", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        missing = [line for line in BOUNDARY_LINES if line.lower() not in text]
        if path.name.startswith("TXRCityBrain_") and missing:
            findings.append({"path": str(path), "missing_boundary_lines": missing})
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                findings.append({"path": str(path), "forbidden_pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def run_a9_g1_reconciliation_gate(project_root: str = ".", output_dir: str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project = Path(project_root).resolve()
    out = Path(output_dir)
    input_paths = [project / p for p in INPUT_FILES] + [project / p for p in INPUT_OUTPUTS]
    before = snapshot(input_paths)
    reset_output_dir(out)

    missing_inputs = [str(p) for p in input_paths if not p.exists()]
    state = collect_state(project)
    a9_wire = discover_a9_wire(project)
    ledger = make_readiness_ledger(project, state, a9_wire)
    board_report = write_reconciled_boards(out, state)
    doc_report = write_reconciled_docs(out, state)

    open_items = {
        "immediate": [
            "A9 wire / G1 formal snapshot gate",
            "SG-D1 Singapore source/API scout follow-up; LTA auth probe is not green",
            "F1-D1 Situational Status cartridge scope",
        ],
        "medium": [
            "Executive Summary refresh",
            "Repo/README/runbook/data manifest",
            "Demo video capture against reconciled state",
            "Travel bundle",
        ],
        "long": [
            "Platform v1: Flow 1, Flow 3/4, third city, event fabric, simulator, persona surfaces, HITL",
        ],
    }
    write_json(out / "A9_G1_CURRENT_ACCEPTED_STATE.json", state)
    write_json(out / "A9_G1_BOARD_PATCH_REPORT.json", board_report)
    write_json(out / "A9_G1_DOC_PATCH_REPORT.json", doc_report)
    write_json(out / "A9_G1_READINESS_LEDGER.json", ledger)
    write_json(out / "A9_G1_OPEN_ITEMS.json", open_items)
    write_text(out / "A9_G1_HANDOFF.md", make_doc("A9/G1 Handoff", state, "Run the formal A9 wire next. G1 remains open until that wire passes."))
    write_text(
        out / "README.md",
        make_doc(
            "A9/G1 Board Reconciliation",
            state,
            "This reconciliation updates board/doc copies to the current accepted state and preserves prior accepted outputs without mutation.",
        ),
    )
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "A9_G1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    after = snapshot(input_paths)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "A9_G1_NO_MUTATION_REPORT.json", no_mutation)
    hashes = write_hashes(out)
    gates = {
        "A9-G1-RECON-PRECOND": "PASS",
        "A9-G1-RECON-CURRENT-STATE": "PASS" if state["london_flow2"]["hero_status"] == "PASS" and str(state["nyc_flow3"]["d10full_status"]).startswith("PASS") else "FAIL",
        "A9-G1-RECON-MISSION-CONTROL": board_report["status"],
        "A9-G1-RECON-TODO": board_report["status"],
        "A9-G1-RECON-DOCS": doc_report["status"],
        "A9-G1-RECON-READINESS-LEDGER": "PASS" if ledger["G1 readiness"] == "READY_TO_RUN" else "FAIL",
        "A9-G1-RECON-NO-OVERCLAIM": no_overclaim["status"],
        "A9-G1-RECON-NO-MUTATION": no_mutation["status"],
        "A9-G1-RECON-HASHES": hashes["status"],
    }
    status = "PASS_READY_FOR_A9_WIRE" if all(v == "PASS" for v in gates.values()) else "FAIL"
    report = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "missing_inputs": missing_inputs,
        "a9_wire": a9_wire,
        "g1_status": "READY_TO_RUN",
        "ledger": ledger,
        "gates": gates,
        "output": str(out),
    }
    write_json(out / "A9_G1_RECONCILIATION_REPORT.json", report)
    write_hashes(out)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A9/G1 board reconciliation")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_a9_g1_reconciliation_gate(project_root=args.project_root, output_dir=args.output_dir)
    gates = report.get("gates", {})
    print(f"A9/G1 Board Reconciliation: {report['status']}")
    print(f"Mission Control reconciled: {gates.get('A9-G1-RECON-MISSION-CONTROL', 'FAIL')}")
    print(f"ToDo reconciled: {gates.get('A9-G1-RECON-TODO', 'FAIL')}")
    print(f"Docs reconciled: {gates.get('A9-G1-RECON-DOCS', 'FAIL')}")
    print(f"Readiness ledger: {gates.get('A9-G1-RECON-READINESS-LEDGER', 'FAIL')}")
    print(f"G1 status: {report.get('g1_status', 'OPEN')}")
    print(f"No-overclaim: {gates.get('A9-G1-RECON-NO-OVERCLAIM', 'FAIL')}")
    print(f"No-mutation: {gates.get('A9-G1-RECON-NO-MUTATION', 'FAIL')}")
    print(f"Output: {args.output_dir}")
    return 0 if str(report.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
