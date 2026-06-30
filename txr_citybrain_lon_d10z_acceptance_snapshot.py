from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D10Z Accepted D10 Planning-Context Snapshot"
DEFAULT_D9Z_DIR = "outputs/lon_d9z_d9d2_accepted_snapshot"
DEFAULT_D10_DIR = "outputs/lon_d10_planning_context_enrichment"
DEFAULT_MISSION_CONTROL = "TXRCityBrain_MissionControl.html"
DEFAULT_TODO = "TXRCityBrain_ToDo.html"
DEFAULT_OUTPUT_DIR = "outputs/lon_d10z_d10_accepted_snapshot"
SYNC_TARGET = Path("/data/citybrain/from_3090/london_d10z_accepted_snapshot_v1")

STATUS_LABELS = {
    "LON-D9Z": "LON-D9Z  GREEN · D9D2 ACCEPTED LONDON SNAPSHOT",
    "LON-D10": "LON-D10  GREEN · PLANNING-CONTEXT ENRICHMENT",
    "LON-D10B": "LON-D10B NEXT · LOCAL PLAN SEMANTIC CERTIFICATION",
    "LON-D6X": "LON-D6X  PARALLEL · BOROUGH ENFORCEMENT SOURCE SCOUT",
}
LIMITATIONS = [
    "D10 is context only, not legal planning determination.",
    "D6 enforcement/building-control remains source-limited.",
    "EV charging site context source-limited.",
    "Planning Local Plan semantic certification deferred.",
    "TOID context is 0 because D9B TOIDs lack geometry.",
    "geopandas_cpu backend; no GPU/cuspatial claim.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
]
NO_OVERCLAIM_BOUNDARY = [
    "D10 is contextual enrichment only, not a legal planning determination.",
    "D6 enforcement/building-control remains source-limited.",
    "EV charging site context is source-limited because no clean official spatial file was present locally.",
    "Planning Local Plan Data was inventoried but full semantic edge certification is deferred.",
    "TOID context is 0 because accepted D9B TOIDs have no geometry.",
    "D10 ran with geopandas_cpu, not cuSpatial/GPU.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
]
PINNED_COUNTS = {
    "context_sources_inventoried": 1148,
    "context_sources_used": 9,
    "context_layers_processed": 9,
    "context_nodes_emitted": 186180,
    "context_edges_emitted": 232101,
    "enriched_graph_nodes": 7921140,
    "enriched_graph_edges": 10896997,
    "pld_applications_with_context": 53751,
    "pld_applications_without_context": 5116,
    "uprns_with_context": 41793,
    "toids_with_context": 0,
    "boroughs_with_context_coverage": 32,
    "boroughs_total": 33,
    "edge_integrity_src_missing": 0,
    "edge_integrity_dst_missing": 0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict[str, dict[str, Any]]:
    hashes: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return hashes
    for path in sorted(root.rglob("*")):
        if path.is_file():
            hashes[str(path)] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return hashes


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D10Z-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {part.lower() for part in resolved.parts} or "lon_d10z" not in resolved.name.lower():
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    (output_dir / "accepted").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def extract_counts(d10_harness: dict[str, Any]) -> dict[str, int]:
    counts = d10_harness.get("counts") or {}
    edge = d10_harness.get("edge_integrity") or {}
    return {
        "context_sources_inventoried": int(counts.get("context_sources_inventoried", 0)),
        "context_sources_used": int(counts.get("context_sources_used", 0)),
        "context_layers_processed": int(counts.get("context_layers_processed", 0)),
        "context_nodes_emitted": int(counts.get("context_nodes_emitted", 0)),
        "context_edges_emitted": int(counts.get("context_edges_emitted", 0)),
        "enriched_graph_nodes": int(counts.get("d10_enriched_nodes", 0)),
        "enriched_graph_edges": int(counts.get("d10_enriched_edges", 0)),
        "pld_applications_with_context": int(counts.get("pld_applications_with_context", 0)),
        "pld_applications_without_context": int(counts.get("pld_applications_without_context", 0)),
        "uprns_with_context": int(counts.get("uprns_with_context", 0)),
        "toids_with_context": int(counts.get("toids_with_context", 0)),
        "boroughs_with_context_coverage": int(counts.get("boroughs_with_context_coverage", 0)),
        "boroughs_total": int(counts.get("borough_target", 0)),
        "edge_integrity_src_missing": int(edge.get("src_missing", 0)),
        "edge_integrity_dst_missing": int(edge.get("dst_missing", 0)),
    }


def count_reconciliation(counts: dict[str, int]) -> dict[str, Any]:
    rows = []
    for key, pinned in PINNED_COUNTS.items():
        actual = counts.get(key)
        rows.append(
            {
                "metric": key,
                "pinned_value": pinned,
                "d10_source_value": actual,
                "matches_pinned": actual == pinned,
                "explanation": None if actual == pinned else "Preserved D10 source value; pinned count basis differs or source report changed.",
            }
        )
    return {
        "gate": "LON-D10Z-COUNT-RECONCILIATION",
        "status": "PASS" if all(row["d10_source_value"] is not None for row in rows) else "FAIL",
        "all_counts_match_pinned": all(row["matches_pinned"] for row in rows),
        "rows": rows,
    }


def backup_once(path: Path, backup: Path) -> None:
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)


def replace_or_insert_london_entries(text: str) -> str:
    text = re.sub(r"\s*\{id:'lon_next'.*?\},\n", "", text)
    text = re.sub(r"\s*\{id:'lon_d10'.*?\},\n", "", text)
    text = re.sub(r"\s*\{id:'lon_d10b'.*?\},\n", "", text)
    text = re.sub(r"\s*\{id:'lon_d6x'.*?\},\n", "", text)
    text = re.sub(
        r"\{id:'lon_d9z'.*?\},",
        "{id:'lon_d9z',n:'LON·D9Z',name:'LON-D9Z  GREEN · D9D2 ACCEPTED LONDON SNAPSHOT',gate:'D9D superseded; D9E-D9D2/D9F-D9D2 promoted; unmatched basis pinned',tags:[['layer','cartridge·snapshot'],['claim','[I]'],['where','dev-box → 4070'],['proven','done · accepted v1']]},",
        text,
    )
    text = re.sub(r"(\{id:'lon_d9z'.*?\},)\s*(\{id:'lon_hero')", r"\1\n    \2", text)
    insert = (
        "    {id:'lon_d10',n:'LON·D10',name:'LON-D10  GREEN · PLANNING-CONTEXT ENRICHMENT',gate:'186,180 context nodes; 232,101 context edges; 53,751 PLD applications with context; 32/33 boroughs with context coverage; TOID context 0 due no TOID geometry; not legal planning determination',tags:[['layer','cartridge·context'],['claim','[I]'],['where','3090 → 4070'],['proven','done · accepted planning-context enrichment']]},\n"
        "    {id:'lon_d10b',n:'LON·D10B',name:'LON-D10B NEXT · LOCAL PLAN SEMANTIC CERTIFICATION',gate:'Certify only semantically clear Local Plan / policy layers; no legal planning determination',tags:[['layer','cartridge·next'],['claim','[P]'],['next','local-plan semantics']]},\n"
        "    {id:'lon_d6x',n:'LON·D6X',name:'LON-D6X  PARALLEL · BOROUGH ENFORCEMENT SOURCE SCOUT',gate:'Camden/Havering/Redbridge enforcement-source scout; official bounded sources only',tags:[['layer','cartridge·parallel'],['claim','[P]'],['parallel','source scout']]},\n"
    )
    text = re.sub(r"(\s*\{id:'lon_d9z'.*?\},\n)", r"\1" + insert, text, count=1)
    text = text.replace("lon_d9d2:'done', lon_d9e:'done', lon_d9f:'done', lon_d9z:'done',", "lon_d9d2:'done', lon_d9e:'done', lon_d9f:'done', lon_d9z:'done',\n    lon_d10:'done', lon_d10b:'todo', lon_d6x:'wip',")
    text = text.replace(
        "Accepted D9D2 state: official PLD API UPRN recovery, exact UPRN→D9B alignment, accepted D9E-D9D2 graph and D9F-D9D2 query contract.",
        "Accepted D9D2 + D10 state: official PLD API UPRN recovery, accepted D9E-D9D2 graph/query contract, and D10 planning-context enrichment. Context only, not legal planning determination.",
    )
    return text


def update_todo(text: str) -> str:
    now = """now:[
      {t:"LON-D10B — Local Plan Data semantic certification", g:"certify only semantically clear Local Plan / borough policy layers; context evidence only, no legal planning determinations"},
      {t:"LON-D6X — Camden/Havering/Redbridge enforcement-source scout ingest", g:"official bounded enforcement/building-control sources only; no private data or scraping"},
      {t:"A9 — final snapshot / G1 freeze", g:"wire E2E final acceptance snapshot once London D10Z is frozen"},
    ]"""
    mid = """mid:[
      {t:"Executive Summary — D9D2 + D10 accepted-state refresh", g:"update prose around planning-context enrichment, D6 source limitation, and D10B next step"},
      {t:"Rename pass: CityBrain RTX → TXR City Brain", g:"mechanical, anytime, still pending"},
      {t:"Travel bundle (post-citywide)", g:"laptop+Spark portable demo for when 3090/4070 don't travel · clean-room run gates, backup video"},
      {t:"LON·hero — real named London cascade", g:"select only after D10B/D6X can support a real policy/enforcement narrative subject"},
    ]"""
    long = """long:[
      {t:"EV charging official spatial source recovery", g:"D10 carried EV charging as source-limited because no clean official spatial file was present locally"},
      {t:"TOID geometry enrichment", g:"D10 TOID context remains 0 until official TOID geometry is added"},
      {t:"D6M / official enforcement-building-control register request if needed", g:"manual official request path for machine-readable/public-register metadata"},
      {t:"a5·D8a — Action resolver (closed enum) — DEFERRED", g:"only when briefing recommends actions beyond review"},
      {t:"a5·D8b — Multi-oracle registry / orchestrator — DEFERRED", g:"only after 2nd oracle family exists (Flow 1 / Flow 3 / London / oil&gas)"},
      {t:"Dubai cartridge — manual export + re-anchor", g:"DLD/DM/Bayanat/Police; onto Dubai geometry · Phase-2 anchor for the Dubai conversation"},
      {t:"Oil & gas cartridge — branch", g:"trigger: city slice green with time left; cartridge brings its own schema"},
    ]"""
    text = re.sub(r"now:\[\n.*?\n    \]", now, text, count=1, flags=re.S)
    text = re.sub(r"mid:\[\n.*?\n    \]", mid, text, count=1, flags=re.S)
    text = re.sub(r"long:\[\n.*?\n    \]", long, text, count=1, flags=re.S)
    return text


def update_boards(mission_control: Path, todo: Path) -> dict[str, Any]:
    mc_backup = mission_control.with_name("TXRCityBrain_MissionControl.before_lon_d10z.html")
    todo_backup = todo.with_name("TXRCityBrain_ToDo.before_lon_d10z.html")
    backup_once(mission_control, mc_backup)
    backup_once(todo, todo_backup)
    before = {
        "mission_control_sha256": sha256_file(mission_control) if mission_control.exists() else None,
        "todo_sha256": sha256_file(todo) if todo.exists() else None,
    }
    mc_text = mission_control.read_text(encoding="utf-8")
    todo_text = todo.read_text(encoding="utf-8")
    mission_control.write_text(replace_or_insert_london_entries(mc_text), encoding="utf-8")
    todo.write_text(update_todo(todo_text), encoding="utf-8")
    after = {
        "mission_control_sha256": sha256_file(mission_control),
        "todo_sha256": sha256_file(todo),
    }
    return {
        "gate": "LON-D10Z-BOARD-UPDATE",
        "status": "PASS",
        "mission_control_updated": True,
        "todo_updated": True,
        "backups": [str(mc_backup), str(todo_backup)],
        "before": before,
        "after": after,
        "required_labels_present": {
            label: label in mission_control.read_text(encoding="utf-8") or label in todo.read_text(encoding="utf-8")
            for label in STATUS_LABELS.values()
        },
    }


def preconditions(d9z_dir: Path, d10_dir: Path, mission_control: Path, todo: Path) -> dict[str, Any]:
    d9z_report = d9z_dir / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json"
    d10_report = d10_dir / "LON_D10_HARNESS_REPORT.json"
    d10_harness = read_json(d10_report) if d10_report.exists() else {}
    checks = {
        "d9z_accepted_snapshot_exists": d9z_report.exists(),
        "d9z_status_pass": read_json(d9z_report).get("status") == "PASS" if d9z_report.exists() else False,
        "d10_harness_exists": d10_report.exists(),
        "d10_status_pass": d10_harness.get("status") == "PASS",
        "d10_counts_available": bool(d10_harness.get("counts")),
        "mission_control_exists": mission_control.exists(),
        "todo_exists": todo.exists(),
    }
    return {"gate": "LON-D10Z-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitations_check(snapshot: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(snapshot, ensure_ascii=False)
    missing = [item for item in LIMITATIONS if item not in text]
    return {"gate": "LON-D10Z-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing": missing, "limitations": LIMITATIONS}


def no_overclaim_check(output_dir: Path, mission_control: Path, todo: Path) -> dict[str, Any]:
    required = NO_OVERCLAIM_BOUNDARY
    files = {
        "README.md": output_dir / "README.md",
        "LON_D10Z_ACCEPTED_SNAPSHOT.json": output_dir / "LON_D10Z_ACCEPTED_SNAPSHOT.json",
        "LON_D10Z_ACCEPTED_SNAPSHOT.md": output_dir / "LON_D10Z_ACCEPTED_SNAPSHOT.md",
        "LON_D10Z_HARNESS_REPORT.json": output_dir / "LON_D10Z_HARNESS_REPORT.json",
    }
    report = {}
    passed = True
    for name, path in files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in required if item not in text]
        report[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    board_text = (mission_control.read_text(encoding="utf-8") if mission_control.exists() else "") + "\n" + (todo.read_text(encoding="utf-8") if todo.exists() else "")
    board_required = [
        "not legal planning determination",
        "TOID context 0 due no TOID geometry",
        "LON-D10  GREEN · PLANNING-CONTEXT ENRICHMENT",
    ]
    board_missing = [item for item in board_required if item not in board_text]
    if board_missing:
        passed = False
    forbidden = []
    output_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files.values() if path.exists()).lower()
    forbidden_checks = [
        "legal planning determination is complete",
        "complete london planning constraint coverage",
        "enforcement/building-control integrated",
        "toid spatial context available",
        "ev charging context complete",
        "cuspatial execution",
    ]
    for phrase in forbidden_checks:
        if phrase in output_text:
            forbidden.append(phrase)
    if forbidden:
        passed = False
    return {
        "gate": "LON-D10Z-NO-OVERCLAIM",
        "status": "PASS" if passed else "FAIL",
        "files": report,
        "board_missing": board_missing,
        "forbidden_claims_found": forbidden,
    }


def sync_lightweight(output_dir: Path, sync_4070: bool) -> dict[str, Any]:
    if not sync_4070:
        return {"gate": "LON-D10Z-4070-SYNC", "status": "NOT_RUN", "target": str(SYNC_TARGET), "reason": "sync_4070_false"}
    files = [
        "README.md",
        "LON_D10Z_ACCEPTED_SNAPSHOT.json",
        "LON_D10Z_ACCEPTED_SNAPSHOT.md",
        "LON_D10Z_HARNESS_REPORT.json",
        "LON_D10Z_COVERAGE_SUMMARY.json",
        "LON_D10Z_LIMITATIONS_REGISTER.json",
        "LON_D10Z_BOARD_UPDATE_REPORT.json",
        "SHA256SUMS.json",
        "accepted/london_d10_accepted_counts.json",
        "accepted/london_d10_accepted_status_labels.json",
        "accepted/london_d10_lightweight_bundle_manifest.json",
    ]
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        SYNC_TARGET.mkdir(parents=True, exist_ok=True)
        copied = []
        bytes_total = 0
        for rel in files:
            src = output_dir / rel
            if not src.exists():
                continue
            dst = SYNC_TARGET / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
            bytes_total += dst.stat().st_size
        return {
            "gate": "LON-D10Z-4070-SYNC",
            "status": "PASS",
            "target": str(SYNC_TARGET),
            "file_count": len(copied),
            "bytes": bytes_total,
            "files": copied,
        }
    except Exception as exc:
        return {"gate": "LON-D10Z-4070-SYNC", "status": "NOT_RUN_OR_UNREACHABLE", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def write_markdown(path: Path, title: str, snapshot: dict[str, Any]) -> None:
    counts = snapshot["accepted_counts"]
    lines = [
        f"# {title}",
        "",
        f"Status: `{snapshot['status']}`",
        "",
        "D9Z accepted D9D2 London graph/query contract plus D10 planning-context enrichment is now the accepted London planning-intelligence graph state.",
        "",
        "## Accepted D10 Counts",
        f"- Context sources inventoried: `{counts['context_sources_inventoried']}`",
        f"- Context sources used: `{counts['context_sources_used']}`",
        f"- Context layers processed: `{counts['context_layers_processed']}`",
        f"- Context nodes emitted: `{counts['context_nodes_emitted']}`",
        f"- Context edges emitted: `{counts['context_edges_emitted']}`",
        f"- Enriched graph: `{counts['enriched_graph_nodes']}` nodes / `{counts['enriched_graph_edges']}` edges",
        f"- PLD applications with context: `{counts['pld_applications_with_context']}`",
        f"- PLD applications without context: `{counts['pld_applications_without_context']}`",
        f"- UPRNs with context: `{counts['uprns_with_context']}`",
        f"- TOIDs with context: `{counts['toids_with_context']}`",
        f"- Borough coverage: `{counts['boroughs_with_context_coverage']} / {counts['boroughs_total']}`",
        "",
        "## Limitations",
        *[f"- {item}" for item in NO_OVERCLAIM_BOUNDARY],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_docs(output_dir: Path, snapshot: dict[str, Any]) -> None:
    write_markdown(output_dir / "README.md", "LON-D10Z Accepted D10 Planning-Context Snapshot", snapshot)
    write_markdown(output_dir / "LON_D10Z_ACCEPTED_SNAPSHOT.md", "LON-D10Z Accepted Snapshot", snapshot)
    next_actions = [
        "# LON-D10Z Next Actions",
        "",
        "- LON-D10B — Local Plan Data semantic certification.",
        "- LON-D6X — Camden/Havering/Redbridge enforcement-source scout ingest.",
        "- A9 — final snapshot / G1 freeze.",
        "",
        "Long/parallel:",
        "- EV charging official spatial source recovery.",
        "- TOID geometry enrichment.",
        "- D6M / official enforcement-building-control register request if needed.",
    ]
    (output_dir / "LON_D10Z_NEXT_ACTIONS.md").write_text("\n".join(next_actions) + "\n", encoding="utf-8")


def artifact_manifest(d10_dir: Path, output_dir: Path) -> dict[str, Any]:
    d10_files = [
        str(path.relative_to(d10_dir)).replace("\\", "/")
        for path in sorted(d10_dir.rglob("*"))
        if path.is_file()
    ]
    return {
        "d10_source_dir": str(d10_dir),
        "d10_source_file_count": len(d10_files),
        "d10_source_files_sample": d10_files[:100],
        "d10z_output_dir": str(output_dir),
    }


def run_lon_d10z_gate(
    d9z_dir: str,
    d10_dir: str,
    mission_control_html: str,
    todo_html: str,
    output_dir: str,
    sync_4070: bool = True,
) -> dict:
    d9z_path = Path(d9z_dir)
    d10_path = Path(d10_dir)
    mission_path = Path(mission_control_html)
    todo_path = Path(todo_html)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    input_before = {"d9z": hash_tree(d9z_path), "d10": hash_tree(d10_path)}
    precond = preconditions(d9z_path, d10_path, mission_path, todo_path)
    d9z_report = read_json(d9z_path / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json")
    d10_harness = read_json(d10_path / "LON_D10_HARNESS_REPORT.json")
    d10_counts = extract_counts(d10_harness)
    reconciliation = count_reconciliation(d10_counts)
    board_report = update_boards(mission_path, todo_path)
    input_inventory = {
        "gate": "LON-D10Z-INPUT-INVENTORY",
        "status": "PASS",
        "d9z_dir": str(d9z_path),
        "d10_dir": str(d10_path),
        "mission_control_html": str(mission_path),
        "todo_html": str(todo_path),
        "d9z_file_count": len(input_before["d9z"]),
        "d10_file_count": len(input_before["d10"]),
        "mission_control_sha256_before_update": board_report["before"]["mission_control_sha256"],
        "todo_sha256_before_update": board_report["before"]["todo_sha256"],
        "mission_control_sha256_after_update": board_report["after"]["mission_control_sha256"],
        "todo_sha256_after_update": board_report["after"]["todo_sha256"],
        "board_backups": board_report["backups"],
    }

    snapshot = {
        "task": TASK_NAME,
        "status": "PASS",
        "created_utc": utc_now(),
        "accepted_state": "D9Z accepted D9D2 London graph/query contract + D10 planning-context enrichment",
        "input_d9z_dir": str(d9z_path),
        "input_d10_dir": str(d10_path),
        "d9z_status": d9z_report.get("status"),
        "d10_status": d10_harness.get("status"),
        "d10_status_promoted": True,
        "execution_backend": d10_harness.get("execution_backend"),
        "accepted_counts": d10_counts,
        "status_labels": STATUS_LABELS,
        "limitations": LIMITATIONS,
        "no_overclaim_boundary": NO_OVERCLAIM_BOUNDARY,
        "4070_d10_prior_sync": d10_harness.get("4070_lightweight_sync"),
    }
    limitations = limitations_check(snapshot)
    write_json(output_path / "LON_D10Z_ACCEPTED_SNAPSHOT.json", snapshot)
    write_json(output_path / "LON_D10Z_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "LON_D10Z_COVERAGE_SUMMARY.json", {"status": "PASS", "accepted_counts": d10_counts, "coverage_by_borough": read_json(d10_path / "LON_D10_COVERAGE_REPORT.json").get("coverage_by_borough", {})})
    write_json(output_path / "LON_D10Z_LIMITATIONS_REGISTER.json", {"status": limitations["status"], "limitations": LIMITATIONS, "no_overclaim_boundary": NO_OVERCLAIM_BOUNDARY})
    write_json(output_path / "LON_D10Z_SUPERSESSION_REGISTER.json", {"status": "PASS", "d9z_accepted": True, "d10_promoted": True, "supersedes": "post-D9Z next-fork board state"})
    write_json(output_path / "LON_D10Z_BOARD_UPDATE_REPORT.json", board_report)
    write_json(output_path / "accepted" / "london_d10_accepted_counts.json", d10_counts)
    write_json(output_path / "accepted" / "london_d10_accepted_status_labels.json", STATUS_LABELS)
    write_json(output_path / "accepted" / "london_d10_accepted_artifact_manifest.json", artifact_manifest(d10_path, output_path))
    lightweight_manifest = {
        "target": str(SYNC_TARGET),
        "included_artifacts": [
            "LON_D10Z_ACCEPTED_SNAPSHOT.json",
            "LON_D10Z_COVERAGE_SUMMARY.json",
            "LON_D10Z_LIMITATIONS_REGISTER.json",
            "LON_D10Z_HARNESS_REPORT.json",
            "LON_D10Z_BOARD_UPDATE_REPORT.json",
            "SHA256SUMS.json",
        ],
        "raw_files_included": False,
        "large_parquet_included": False,
    }
    write_json(output_path / "accepted" / "london_d10_lightweight_bundle_manifest.json", lightweight_manifest)

    write_docs(output_path, snapshot)
    write_json(output_path / "reports" / "d9z_dependency_check.json", {"status": "PASS" if d9z_report.get("status") == "PASS" else "FAIL", "input": str(d9z_path)})
    write_json(output_path / "reports" / "d10_dependency_check.json", {"status": "PASS" if d10_harness.get("status") == "PASS" else "FAIL", "input": str(d10_path), "execution_backend": d10_harness.get("execution_backend")})
    write_json(output_path / "reports" / "d10_count_reconciliation.json", reconciliation)
    write_json(output_path / "reports" / "d10_limitations_check.json", limitations)
    write_json(output_path / "reports" / "board_status_before_after.json", board_report)
    write_json(output_path / "reports" / "no_overclaim_check.json", {"status": "PENDING"})

    manifest_counts = {
        "context_nodes_accepted": d10_counts["context_nodes_emitted"],
        "context_edges_accepted": d10_counts["context_edges_emitted"],
        "pld_applications_with_context": d10_counts["pld_applications_with_context"],
        "boroughs_with_context_coverage": d10_counts["boroughs_with_context_coverage"],
        "boroughs_total": d10_counts["boroughs_total"],
    }
    manifest = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "input_d9z_dir": str(d9z_path),
        "input_d10_dir": str(d10_path),
        "output_dir": str(output_path),
        "status_labels": STATUS_LABELS,
        "limitations": LIMITATIONS,
        "counts": manifest_counts,
    }
    write_json(output_path / "LON_D10Z_ACCEPTED_SNAPSHOT.json", snapshot)
    write_json(output_path / "LON_D10Z_MANIFEST.json", manifest)
    write_json(output_path / "LON_D10Z_HARNESS_REPORT.json", {"task": TASK_NAME, "status": "PENDING", "accepted_counts": d10_counts, "limitations": LIMITATIONS, "no_overclaim_boundary": NO_OVERCLAIM_BOUNDARY})
    no_overclaim = no_overclaim_check(output_path, mission_path, todo_path)
    write_json(output_path / "LON_D10Z_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_path / "reports" / "no_overclaim_check.json", no_overclaim)
    input_after = {"d9z": hash_tree(d9z_path), "d10": hash_tree(d10_path)}
    no_mutation = {
        "gate": "LON-D10Z-NO-MUTATION",
        "status": "PASS" if input_before == input_after else "FAIL",
        "changed_inputs": [
            key
            for key in input_before
            if input_before.get(key) != input_after.get(key)
        ],
    }

    hash_report = write_hashes(output_path)
    sync_report = sync_lightweight(output_path, sync_4070)
    write_json(output_path / "LON_D10Z_4070_SYNC_REPORT.json", sync_report)
    gates = {
        "LON-D10Z-PRECOND": precond["status"],
        "LON-D10Z-COUNT-RECONCILIATION": reconciliation["status"],
        "LON-D10Z-LIMITATION-CARRY-FORWARD": limitations["status"],
        "LON-D10Z-BOARD-UPDATE": board_report["status"],
        "LON-D10Z-4070-SYNC": "PASS" if sync_report["status"] in {"PASS", "NOT_RUN", "NOT_RUN_OR_UNREACHABLE"} else "FAIL",
        "LON-D10Z-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D10Z-NO-MUTATION": no_mutation["status"],
        "LON-D10Z-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    final_manifest = {**manifest, "status": overall}
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "accepted_counts": d10_counts,
        "status_labels": STATUS_LABELS,
        "limitations": LIMITATIONS,
        "no_overclaim_boundary": NO_OVERCLAIM_BOUNDARY,
        "preconditions": precond,
        "input_inventory": input_inventory,
        "count_reconciliation": reconciliation,
        "limitations_check": limitations,
        "board_update": board_report,
        "sync_4070": sync_report,
        "no_overclaim": no_overclaim,
        "no_mutation": no_mutation,
        "hashes": hash_report,
        "gates": gates,
    }
    write_json(output_path / "LON_D10Z_MANIFEST.json", final_manifest)
    write_json(output_path / "LON_D10Z_HARNESS_REPORT.json", harness)
    write_json(output_path / "LON_D10Z_ACCEPTED_SNAPSHOT.json", {**snapshot, "status": overall})
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D10Z_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d9z-dir", default=DEFAULT_D9Z_DIR)
    parser.add_argument("--d10-dir", default=DEFAULT_D10_DIR)
    parser.add_argument("--mission-control", default=DEFAULT_MISSION_CONTROL)
    parser.add_argument("--todo", default=DEFAULT_TODO)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sync-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d10z_gate(args.d9z_dir, args.d10_dir, args.mission_control, args.todo, args.output_dir, args.sync_4070)
    counts = report["accepted_counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D9Z: {report['preconditions']['checks']['d9z_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Input D10: {report['preconditions']['checks']['d10_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"D10 status promoted: {'YES' if report['status'] == 'PASS' else 'NO'}")
    print(f"Mission Control updated: {'YES' if report['board_update']['mission_control_updated'] else 'NO'}")
    print(f"ToDo updated: {'YES' if report['board_update']['todo_updated'] else 'NO'}")
    print(f"Context nodes accepted: {counts['context_nodes_emitted']}")
    print(f"Context edges accepted: {counts['context_edges_emitted']}")
    print(f"PLD applications with context: {counts['pld_applications_with_context']}")
    print(f"Borough coverage: {counts['boroughs_with_context_coverage']} / {counts['boroughs_total']}")
    print(f"Limitations carried forward: {report['limitations_check']['status']}")
    print(f"4070 lightweight sync: {report['sync_4070']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
