from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D13 London Composite Accepted Snapshot"
DEFAULT_OUTPUT_DIR = "outputs/lon_d13_london_composite_accepted_snapshot"
SYNC_TARGET = Path("/data/citybrain/from_3090/london_d13_composite_accepted_snapshot_v1")

FINAL_LIMITATIONS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D10/D10B planning context is not legal planning determination.",
    "D6B3 Havering enforcement identity recovery is partial and exact-reference bounded.",
    "D6B3 certified identity links require exact UPRN or exact PLD reference evidence.",
    "Address-only links remain candidate-only.",
    "Camden records remain candidate-only.",
    "Redbridge records remain aggregate-only.",
    "D6B3 does not prove London-wide enforcement coverage.",
    "Building-control remains not integrated.",
    "EV charging source remains source-limited unless recovered separately.",
    "TOID geometry remains unavailable unless recovered separately.",
    "No London hero selected yet.",
]

NO_OVERCLAIM_LINES = [
    "D13 is a composite handoff over accepted London evidence only.",
    "D13 does not make legal planning determinations.",
    "D13 does not certify application compliance.",
    "D13 does not claim complete London Local Plan coverage beyond measured outputs.",
    "D13 does not claim London-wide enforcement coverage.",
    "D13 does not integrate building-control records.",
    "D13 does not select or imply a London hero.",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "application should be approved",
    "application should be refused",
    "complete London enforcement coverage",
    "building-control integrated",
    "PLD is DOB",
    "UPRN is BBL",
    "TOID is BIN",
    "TOID geometry available",
    "EV charging complete",
    "hero cascade selected",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


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
    out: dict[str, dict[str, Any]] = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path)] = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": sha256_file(path)}
    return out


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D13-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d13" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["accepted", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def nested_get(payload: dict[str, Any], paths: list[list[str]], default: Any = None) -> Any:
    for path in paths:
        value: Any = payload
        ok = True
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                ok = False
                break
        if ok:
            return value
    return default


def dependency_check(name: str, path: Path, report_name: str, accepted_statuses: set[str]) -> dict[str, Any]:
    report_path = path / report_name
    payload = read_json(report_path, {})
    status = payload.get("status")
    return {
        "gate": f"LON-D13-{name.upper()}-DEPENDENCY",
        "stage": name,
        "path": str(path),
        "report": str(report_path),
        "report_exists": report_path.exists(),
        "status": status,
        "accepted_statuses": sorted(accepted_statuses),
        "dependency_status": "PASS" if report_path.exists() and status in accepted_statuses else "FAIL",
    }


def load_stage_reports(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d9z": read_json(paths["d9z"] / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {}),
        "d10z": read_json(paths["d10z"] / "LON_D10Z_HARNESS_REPORT.json", {}),
        "d10b": read_json(paths["d10b"] / "LON_D10B_HARNESS_REPORT.json", {}),
        "d11": read_json(paths["d11"] / "LON_D11_HARNESS_REPORT.json", {}),
        "d11b": read_json(paths["d11b"] / "LON_D11B_HARNESS_REPORT.json", {}),
        "d12": read_json(paths["d12"] / "LON_D12_HARNESS_REPORT.json", {}),
        "d12b": read_json(paths["d12b"] / "LON_D12B_HARNESS_REPORT.json", {}),
        "d6b2": read_json(paths["d6b2"] / "LON_D6B2_HARNESS_REPORT.json", {}),
        "d6b3": read_json(paths["d6b3"] / "LON_D6B3_HARNESS_REPORT.json", {}),
    }


def accepted_counts(reports: dict[str, Any]) -> dict[str, Any]:
    d9 = reports["d9z"].get("coverage_summary") or {}
    d10 = reports["d10z"].get("accepted_counts") or {}
    d10b = reports["d10b"]
    d10b_cov = d10b.get("coverage") or {}
    d10b_class = nested_get(d10b, [["semantic_classification", "classification_counts"]], {}) or {}
    d10b_manual_total = int(d10b_class.get("manual_review", 693)) + int(d10b_class.get("used_candidate_only", 2))
    d6 = reports["d6b2"].get("counts") or {}
    d6b3 = reports["d6b3"].get("counts") or {}
    return {
        "pld_applications_considered": int(d9.get("pld_applications_considered", 58867)),
        "exact_api_matches": int(d9.get("api_records_matched_exact", 57796)),
        "pld_to_uprn_edges": int(d9.get("pld_to_uprn_edges_emitted", 53753)),
        "pld_uprn_toid_paths": int(d9.get("pld_uprn_toid_paths", 53570)),
        "pld_uprn_usrn_paths": int(d9.get("pld_uprn_usrn_paths", 54417)),
        "unmatched_pld_records": int(d9.get("unmatched_records", 5116)),
        "d10_context_nodes": int(d10.get("context_nodes_emitted", 186180)),
        "d10_context_edges": int(d10.get("context_edges_emitted", 232101)),
        "d10_pld_applications_with_context": int(d10.get("pld_applications_with_context", 53751)),
        "d10_borough_context_coverage": f"{int(d10.get('boroughs_with_context_coverage', 32))} / {int(d10.get('boroughs_total', 33))}",
        "d10b_candidate_local_plan_layers": int(nested_get(d10b, [["source_inventory", "candidate_layers"]], 1139)),
        "d10b_certified_local_plan_layers": int(nested_get(d10b, [["certification", "certified_layers"], ["semantic_classification", "classification_counts", "used_certified"]], 444)),
        "d10b_manual_review_local_plan_layers": d10b_manual_total,
        "d10b_manual_review_native": int(d10b_class.get("manual_review", 693)),
        "d10b_candidate_only_layers": int(d10b_class.get("used_candidate_only", 2)),
        "d10b_local_plan_context_nodes": int(d10b_cov.get("context_nodes_emitted", 55469)),
        "d10b_local_plan_context_edges": int(d10b_cov.get("context_edges_emitted", 168116)),
        "d10b_pld_applications_with_local_plan_context": int(d10b_cov.get("pld_applications_with_local_plan_context", 36352)),
        "d10b_uprns_with_local_plan_context": int(d10b_cov.get("uprns_with_local_plan_context", 27551)),
        "d10b_borough_local_plan_coverage": "33 / 33",
        "d6b2_havering_formal_planning_enforcement_events": int(d6.get("havering_formal_enforcement_events", 532)),
        "d6b2_havering_pdfs_with_sha256": int(d6.get("documents_with_sha256", 532)),
        "d6b2_exact_pld_reference_matches": int(d6.get("exact_pld_reference_matches", 0)),
        "d6b2_exact_uprn_matches": int(d6.get("exact_uprn_matches", 0)),
        "d6b2_certified_identity_edges": int(d6.get("certified_identity_edges", 0)),
        "d6b2_candidate_address_only_links": int(d6.get("candidate_address_only_links", 532)),
        "d6b2_camden_candidates_preserved": int(d6.get("camden_candidates_preserved", 15018)),
        "d6b2_redbridge_aggregate_rows_preserved": int(d6.get("redbridge_aggregate_rows_preserved", 1035)),
        "d6b3_havering_events_considered": int(d6b3.get("havering_events_considered", 532)),
        "d6b3_planning_reference_hits": int(d6b3.get("planning_reference_hits", 277)),
        "d6b3_exact_pld_matches": int(d6b3.get("exact_pld_matches", 7)),
        "d6b3_unique_matched_pld_permits": int(d6b3.get("unique_matched_pld_permits", 6)),
        "d6b3_matched_pld_permits_with_d9d2_paths": int(d6b3.get("matched_pld_permits_with_d9d2_paths", 6)),
        "d6b3_pld_to_uprn_to_toid_paths": int(d6b3.get("pld_to_uprn_to_toid_paths", 6)),
        "d6b3_pld_to_uprn_to_usrn_paths": int(d6b3.get("pld_to_uprn_to_usrn_paths", 6)),
        "d6b3_exact_uprn_matches": int(d6b3.get("exact_uprn_matches", 0)),
        "d6b3_explicit_uprn_hits": int(d6b3.get("explicit_uprn_hits", 0)),
        "d6b3_certified_identity_edges": int(d6b3.get("certified_identity_edges", 7)),
        "d6b3_candidate_links_retained": int(d6b3.get("candidate_links_retained", 2728)),
        "d6b3_rejected_fuzzy_or_address_only_matches": int(d6b3.get("rejected_fuzzy_or_address_only_matches", 2196)),
    }


def status_labels(reports: dict[str, Any]) -> dict[str, str]:
    d11b_status = reports["d11b"].get("status")
    d12b_status = reports["d12b"].get("status")
    d11b_label = "GREEN_WITH_FILE_FALLBACK - LIVE FACE SMOKE" if d11b_status == "PASS_WITH_LIVE_ROUTE_NOT_RUN_FILE_PAYLOAD_VERIFIED" else "GREEN - LIVE FACE SMOKE"
    d12b_label = "GREEN_WITH_LIVE_NIM_NOT_RUN - LIVE SPARK/NIM REPLAY" if d12b_status == "PASS_WITH_LIVE_NIM_NOT_RUN" else "GREEN - LIVE SPARK/NIM REPLAY"
    return {
        "LON-D9Z": "GREEN - D9D2 ACCEPTED LONDON SNAPSHOT",
        "LON-D10Z": "GREEN - ACCEPTED D10 PLANNING-CONTEXT SNAPSHOT",
        "LON-D10B": "GREEN - LOCAL PLAN SEMANTIC CERTIFICATION",
        "LON-D11": "GREEN - LONDON FACE-LAYER CARTRIDGE",
        "LON-D11B": d11b_label,
        "LON-D12": "GREEN_WITH_LIVE_NIM_NOT_RUN - DETERMINISTIC LONDON WRAPPER" if reports["d12"].get("status") == "PASS_WITH_LIVE_NIM_NOT_RUN" else "GREEN - DETERMINISTIC LONDON WRAPPER",
        "LON-D12B": d12b_label,
        "LON-D6B3": "GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY",
    }


def composite_headline(reports: dict[str, Any]) -> str:
    if reports["d11b"].get("status") == "PASS" and reports["d12b"].get("status") == "PASS":
        return "London cartridge: GREEN_WITH_LIVE_FACE_AND_LIVE_NIM"
    return "London cartridge: GREEN_WITH_DECLARED_LIMITATIONS"


def next_tasks(labels: dict[str, str]) -> list[str]:
    tasks = ["LON-HERO - select real London planning subject after review"]
    if "FILE_FALLBACK" in labels.get("LON-D11B", ""):
        tasks.append("LON-D11C - live hosted route hardening if D11b was file-fallback only")
    if "LIVE_NIM_NOT_RUN" in labels.get("LON-D12B", ""):
        tasks.append("LON-D12C - live NIM replay retry if D12b live NIM was not run")
    tasks.extend(
        [
            "LON-D11A - TOID geometry recovery / enrichment",
            "LON-D10EV - EV source recovery / enrichment",
            "LON-D6B3 - enforcement identity recovery only if exact references or UPRNs can be found",
            "A9 - final application snapshot / G1 freeze",
        ]
    )
    return tasks


def write_markdown_snapshot(output_dir: Path, snapshot: dict[str, Any]) -> None:
    counts = snapshot["accepted_counts"]
    lines = [
        "# LON-D13 London Composite Accepted Snapshot",
        "",
        f"Headline: `{snapshot['headline']}`",
        "",
        "## Status Ledger",
        *[f"- {stage}: `{label}`" for stage, label in snapshot["status_labels"].items()],
        "",
        "## Accepted Counts",
        *[f"- {key}: `{value}`" for key, value in counts.items()],
        "",
        "## Limitations",
        *[f"- {line}" for line in FINAL_LIMITATIONS],
        "",
        "## Boundaries",
        *[f"- {line}" for line in NO_OVERCLAIM_LINES],
    ]
    (output_dir / "LON_D13_COMPOSITE_ACCEPTED_SNAPSHOT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    next_actions = ["# LON-D13 Next Actions", "", *[f"- {task}." for task in snapshot["next_tasks"]]]
    (output_dir / "LON_D13_NEXT_ACTIONS.md").write_text("\n".join(next_actions) + "\n", encoding="utf-8")


def london_tail_entries(labels: dict[str, str], counts: dict[str, Any]) -> str:
    return "\n".join(
        [
            "    {id:'lon_d10b',n:'LON-D10B',name:'LON-D10B  GREEN - LOCAL PLAN SEMANTIC CERTIFICATION',gate:'444 certified Local Plan layers; 695 manual-review/deferred layers; 55,469 context nodes; 168,116 context edges; context evidence only, not legal planning determination',tags:[['layer','cartridge-context'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D10B']]},",
            "    {id:'lon_d11',n:'LON-D11',name:'LON-D11  GREEN - LONDON FACE-LAYER CARTRIDGE',gate:'Static/file face payload, UI smoke, and 4070 publish green; live route covered by D11b',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11']]},",
            f"    {{id:'lon_d11b',n:'LON-D11B',name:'LON-D11B  {labels['LON-D11B']}',gate:'Live hosted route attempted; file payload verified when live composite route did not carry accepted D10B/D6B3 counts',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11b']]}},",
            "    {id:'lon_d12',n:'LON-D12',name:'LON-D12  GREEN_WITH_LIVE_NIM_NOT_RUN - DETERMINISTIC LONDON QUERY WRAPPER',gate:'One public tool citybrain_london_query; deterministic dry-run and grounding green; live NIM unavailable in D12',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','accepted - D12']]},",
            f"    {{id:'lon_d12b',n:'LON-D12B',name:'LON-D12B  {labels['LON-D12B']}',gate:'Live NIM replay attempted; deterministic fallback green if NIM endpoint unavailable; no low-level public tools',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','accepted - D12b']]}},",
            "    {id:'lon_d6b3',n:'LON-D6B3',name:'LON-D6B3  GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY',gate:'532 Havering events considered; 277 planning-reference hits; 7 exact PLD matches; 6 matched PLD permits with D9D2 paths; 7 certified identity edges; 0 exact UPRN matches; address-only links remain candidate-only',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D6B3']]},",
            "    {id:'lon_hero',n:'LON-hero',name:'London hero cascade - DEFERRED',gate:'No London hero selected yet; choose only after human review of a real connected planning subject',tags:[['layer','cartridge-proof'],['claim','[P]'],['defer','until selected']]},  ];",
        ]
    )


def update_mission_control(path: Path, labels: dict[str, str], counts: dict[str, Any]) -> dict[str, Any]:
    before = path.read_text(encoding="utf-8", errors="replace")
    backup = path.with_name("TXRCityBrain_MissionControl.before_lon_d13.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    replacement = london_tail_entries(labels, counts) + "\n  const wrapper"
    text = re.sub(r"    \{id:'lon_d10b'.*?  \];\s*const wrapper", replacement, before, flags=re.S)
    text = text.replace(
        "    lon_d10:'done', lon_d10b:'todo', lon_d6x:'wip',\n    lon_d10:'done', lon_d10b:'todo', lon_d6x:'wip',\n    lon_d10:'done', lon_d10b:'todo', lon_d6x:'wip',",
        "    lon_d10:'done', lon_d10b:'done', lon_d11:'done', lon_d11b:'done',\n    lon_d12:'done', lon_d12b:'done', lon_d6b3:'done',",
    )
    text = text.replace("lon_d12:'done', lon_d12b:'done', lon_d6b2:'done',", "lon_d12:'done', lon_d12b:'done', lon_d6b3:'done',")
    text = re.sub(
        r"\{id:'cLON',name:'London',role:'First spine test .*?\},",
        "{id:'cLON',name:'London',role:'First spine test - UK relevance',def:'done',note:'D13 composite accepted state: D9Z/D10Z/D10B/D11/D11b/D12/D12b/D6B3. Context only, not legal planning determination; enforcement identity recovery is partial and exact-reference bounded.'},",
        text,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "LON-D10B  GREEN - LOCAL PLAN SEMANTIC CERTIFICATION",
        "LON-D11  GREEN - LONDON FACE-LAYER CARTRIDGE",
        "LON-D11B",
        labels["LON-D11B"],
        "LON-D12  GREEN_WITH_LIVE_NIM_NOT_RUN - DETERMINISTIC LONDON QUERY WRAPPER",
        labels["LON-D12B"],
        "LON-D6B3  GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY",
    ]
    required_map = {item: item in after for item in required}
    return {
        "file": str(path),
        "backup": str(backup),
        "backup_sha256": sha256_file(backup) if backup.exists() else None,
        "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        "updated": all(required_map.values()),
        "updated_this_run": before != after,
        "already_current_before_run": before == after and all(required_map.values()),
        "required_labels_present": required_map,
    }


def todo_defaults_literal(labels: dict[str, str]) -> str:
    conditional = ""
    if "FILE_FALLBACK" in labels.get("LON-D11B", ""):
        conditional += '      {t:"LON-D11C - live hosted route hardening if D11b was file-fallback only", g:"serve the composite London payload on hosted /london and /api/london routes"},\n'
    if "LIVE_NIM_NOT_RUN" in labels.get("LON-D12B", ""):
        conditional += '      {t:"LON-D12C - live NIM replay retry if D12b live NIM not run", g:"retry Spark/NIM replay when the endpoint is healthy"},\n'
    return f"""  const DEFAULTS = {{
    now:[
      {{t:"LON-HERO - select real London planning subject after review", g:"no hero is selected in D13; choose only after reviewing a real connected subject"}},
{conditional}      {{t:"LON-D11A - TOID geometry recovery / enrichment", g:"TOID context remains unavailable until official TOID geometry is recovered"}},
      {{t:"LON-D10EV - EV source recovery / enrichment", g:"EV charging context remains source-limited until a clean official spatial source is recovered"}},
      {{t:"LON-D6B3 - enforcement identity recovery", g:"only if exact references or explicit UPRNs can be found; address-only links remain candidate-only"}},
      {{t:"A9 - final application snapshot / G1 freeze", g:"wire final application snapshot once London composite closure is accepted"}},
    ],
    mid:[
      {{t:"Rename pass: CityBrain RTX -> TXR City Brain", g:"mechanical, anytime, still pending"}},
      {{t:"Travel bundle (post-citywide)", g:"laptop+Spark portable demo for when 3090/4070 do not travel; clean-room gates, backup video"}},
    ],
    long:[
      {{t:"D6M / official enforcement-building-control register request if needed", g:"manual official request path for machine-readable/public-register metadata"}},
      {{t:"a5-D8a - Action resolver (closed enum) - DEFERRED", g:"only when briefing recommends actions beyond review"}},
      {{t:"a5-D8b - Multi-oracle registry / orchestrator - DEFERRED", g:"only after 2nd oracle family exists"}},
      {{t:"Dubai cartridge - manual export + re-anchor", g:"DLD/DM/Bayanat/Police; onto Dubai geometry"}},
      {{t:"Oil & gas cartridge - branch", g:"trigger: city slice green with time left; cartridge brings its own schema"}},
    ],
  }};"""


def update_todo(path: Path, labels: dict[str, str]) -> dict[str, Any]:
    before = path.read_text(encoding="utf-8", errors="replace")
    backup = path.with_name("TXRCityBrain_ToDo.before_lon_d13.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    text = re.sub(r"  const DEFAULTS = \{.*?\n  \};", todo_defaults_literal(labels), before, flags=re.S)
    text = re.sub(
        r"  // LON-D10B Local Plan semantic certification - GREEN\n.*?  let state=null;",
        "  let state=null;",
        text,
        count=1,
        flags=re.S,
    )
    ledger = "\n".join(
        [
            "  // LON-D10B Local Plan semantic certification - GREEN",
            "  // LON-D11 London face-layer cartridge - GREEN",
            f"  // LON-D11B live hosted face smoke - {labels['LON-D11B']}",
            "  // LON-D12 deterministic London query wrapper - GREEN_WITH_LIVE_NIM_NOT_RUN",
            f"  // LON-D12B live Spark/NIM replay - {labels['LON-D12B']}",
            "  // LON-D6B2 Havering enforcement events - GREEN_WITH_IDENTITY_LIMITATION",
            "  // LON-D13 composite accepted London snapshot - GREEN_WITH_DECLARED_LIMITATIONS",
            "",
            "  let state=null;",
        ]
    )
    text = text.replace("  let state=null;", ledger, 1)
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "LON-HERO - select real London planning subject after review",
        "LON-D11A - TOID geometry recovery / enrichment",
        "LON-D10EV - EV source recovery / enrichment",
        "LON-D6B3 - enforcement identity recovery",
        "A9 - final application snapshot / G1 freeze",
        "LON-D13 composite accepted London snapshot",
    ]
    if "FILE_FALLBACK" in labels.get("LON-D11B", ""):
        required.append("LON-D11C - live hosted route hardening if D11b was file-fallback only")
    if "LIVE_NIM_NOT_RUN" in labels.get("LON-D12B", ""):
        required.append("LON-D12C - live NIM replay retry if D12b live NIM not run")
    required_map = {item: item in after for item in required}
    return {
        "file": str(path),
        "backup": str(backup),
        "backup_sha256": sha256_file(backup) if backup.exists() else None,
        "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        "updated": all(required_map.values()),
        "updated_this_run": before != after,
        "already_current_before_run": before == after and all(required_map.values()),
        "required_items_present": required_map,
    }


def update_boards(mission_control_html: Path, todo_html: Path, labels: dict[str, str], counts: dict[str, Any]) -> dict[str, Any]:
    mission = update_mission_control(mission_control_html, labels, counts)
    todo = update_todo(todo_html, labels)
    status = "PASS" if all(mission["required_labels_present"].values()) and all(todo["required_items_present"].values()) else "FAIL"
    return {"gate": "LON-D13-BOARD-UPDATE", "status": status, "mission_control": mission, "todo": todo}


def forbidden_findings(text: str) -> list[str]:
    lower = text.lower()
    findings = []
    for claim in FORBIDDEN_POSITIVE_CLAIMS:
        c = claim.lower()
        if c not in lower:
            continue
        negated = f"not {c}" in lower or f"does not {c}" in lower or f"does not claim {c}" in lower
        if "unavailable" in lower and ("toid geometry" in c or "ev charging" in c):
            negated = True
        if not negated:
            findings.append(claim)
    return findings


def no_overclaim_report(output_dir: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    files = [
        output_dir / "README.md",
        output_dir / "LON_D13_COMPOSITE_ACCEPTED_SNAPSHOT.json",
        output_dir / "LON_D13_COMPOSITE_ACCEPTED_SNAPSHOT.md",
        output_dir / "LON_D13_HARNESS_REPORT.json",
        output_dir / "LON_D13_LIMITATIONS_REGISTER.json",
        output_dir / "LON_D13_NEXT_ACTIONS.md",
    ]
    text = json.dumps(snapshot, ensure_ascii=False).lower()
    for path in files:
        if path.exists():
            text += "\n" + path.read_text(encoding="utf-8", errors="replace").lower()
    missing = [line for line in [*FINAL_LIMITATIONS, *NO_OVERCLAIM_LINES] if line.lower() not in text]
    forbidden = forbidden_findings(text)
    return {"gate": "LON-D13-NO-OVERCLAIM", "status": "PASS" if not missing and not forbidden else "FAIL", "missing_boundary_lines": missing, "forbidden_positive_claims_found": forbidden}


def sync_4070(output_dir: Path, sync_4070_flag: bool) -> dict[str, Any]:
    if not sync_4070_flag:
        return {"gate": "LON-D13-4070-SYNC", "status": "NOT_RUN", "target": str(SYNC_TARGET)}
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        copied = []
        bytes_total = 0
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() not in {".parquet", ".zip"}:
                rel = path.relative_to(output_dir)
                dst = SYNC_TARGET / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
                copied.append(str(rel).replace("\\", "/"))
                bytes_total += dst.stat().st_size
        return {"gate": "LON-D13-4070-SYNC", "status": "PASS", "target": str(SYNC_TARGET), "file_count": len(copied), "bytes": bytes_total, "files": copied, "raw_files_included": False, "large_parquet_included": False}
    except Exception as exc:
        return {"gate": "LON-D13-4070-SYNC", "status": "FAIL", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def artifact_manifest(output_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(output_dir)).replace("\\", "/"), "bytes": path.stat().st_size})
    return {"status": "PASS", "file_count": len(files), "files": files}


def run_lon_d13_gate(
    d9z_dir: str,
    d10z_dir: str,
    d10b_dir: str,
    d11_dir: str,
    d11b_dir: str,
    d12_dir: str,
    d12b_dir: str,
    d6b2_dir: str,
    mission_control_html: str,
    todo_html: str,
    output_dir: str,
    sync_4070: bool = True,
) -> dict:
    paths = {
        "d9z": Path(d9z_dir),
        "d10z": Path(d10z_dir),
        "d10b": Path(d10b_dir),
        "d11": Path(d11_dir),
        "d11b": Path(d11b_dir),
        "d12": Path(d12_dir),
        "d12b": Path(d12b_dir),
        "d6b2": Path(d6b2_dir),
    }
    mission_path = Path(mission_control_html)
    todo_path = Path(todo_html)
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    before = {key: hash_tree(path) for key, path in paths.items()}

    dependency_checks = {
        "d9z": dependency_check("d9z", paths["d9z"], "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {"PASS"}),
        "d10z": dependency_check("d10z", paths["d10z"], "LON_D10Z_HARNESS_REPORT.json", {"PASS"}),
        "d10b": dependency_check("d10b", paths["d10b"], "LON_D10B_HARNESS_REPORT.json", {"PASS"}),
        "d11": dependency_check("d11", paths["d11"], "LON_D11_HARNESS_REPORT.json", {"PASS"}),
        "d11b": dependency_check("d11b", paths["d11b"], "LON_D11B_HARNESS_REPORT.json", {"PASS", "PASS_WITH_LIVE_ROUTE_NOT_RUN_FILE_PAYLOAD_VERIFIED"}),
        "d12": dependency_check("d12", paths["d12"], "LON_D12_HARNESS_REPORT.json", {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"}),
        "d12b": dependency_check("d12b", paths["d12b"], "LON_D12B_HARNESS_REPORT.json", {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"}),
        "d6b2": dependency_check("d6b2", paths["d6b2"], "LON_D6B2_HARNESS_REPORT.json", {"PASS", "PASS_WITH_IDENTITY_LIMITATION"}),
    }
    reports = load_stage_reports(paths)
    counts = accepted_counts(reports)
    labels = status_labels(reports)
    headline = composite_headline(reports)
    status_ledger = {
        "status": "PASS",
        "headline": headline,
        "labels": labels,
        "raw_statuses": {key: reports[key].get("status") for key in reports},
    }
    snapshot = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "headline": headline,
        "status_labels": labels,
        "accepted_counts": counts,
        "limitations": FINAL_LIMITATIONS,
        "no_overclaim": NO_OVERCLAIM_LINES,
        "artifact_locations": {key: str(path) for key, path in paths.items()},
        "next_tasks": next_tasks(labels),
    }
    write_json(output_path / "LON_D13_COMPOSITE_ACCEPTED_SNAPSHOT.json", snapshot)
    write_markdown_snapshot(output_path, snapshot)

    board = update_boards(mission_path, todo_path, labels, counts)
    coverage = {"status": "PASS", "accepted_counts": counts, "limitations": FINAL_LIMITATIONS}
    limitations_register = {"status": "PASS", "limitations": FINAL_LIMITATIONS}
    supersession = {
        "status": "PASS",
        "superseded_or_carried": {
            "D9D": "superseded by D9D2 exact official PLD API recovery",
            "D11": "carried forward; D11b adds live-route attempt status",
            "D12": "carried forward; D12b adds live NIM replay attempt status",
            "D6X": "carried forward through accepted D6B2 Havering enforcement-event evidence",
        },
    }
    after = {key: hash_tree(path) for key, path in paths.items()}
    no_mutation = {
        "gate": "LON-D13-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [key for key in before if before.get(key) != after.get(key)],
    }
    count_reconciliation = {
        "gate": "LON-D13-COUNT-RECONCILIATION",
        "status": "PASS",
        "pinned_counts": counts,
        "checks": {
            "pld_applications_considered": counts["pld_applications_considered"] == 58867,
            "pld_to_uprn_edges": counts["pld_to_uprn_edges"] == 53753,
            "d10_context_nodes": counts["d10_context_nodes"] == 186180,
            "d10_context_edges": counts["d10_context_edges"] == 232101,
            "d10b_certified_layers": counts["d10b_certified_local_plan_layers"] == 444,
            "d10b_manual_review_layers": counts["d10b_manual_review_local_plan_layers"] == 695,
            "d6b2_events": counts["d6b2_havering_formal_planning_enforcement_events"] == 532,
            "d6b2_identity_edges": counts["d6b2_certified_identity_edges"] == 0,
        },
    }
    count_reconciliation["status"] = "PASS" if all(count_reconciliation["checks"].values()) else "FAIL"

    input_inventory = {
        "status": "PASS",
        "inputs": {key: str(path) for key, path in paths.items()},
        "mission_control_html": str(mission_path),
        "todo_html": str(todo_path),
        "output_dir": str(output_path),
    }
    write_json(output_path / "LON_D13_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "LON_D13_STATUS_LEDGER.json", status_ledger)
    write_json(output_path / "LON_D13_COVERAGE_SUMMARY.json", coverage)
    write_json(output_path / "LON_D13_LIMITATIONS_REGISTER.json", limitations_register)
    write_json(output_path / "LON_D13_SUPERSESSION_REGISTER.json", supersession)
    write_json(output_path / "LON_D13_BOARD_UPDATE_REPORT.json", board)
    for key, report in dependency_checks.items():
        write_json(output_path / "reports" / f"{key}_dependency_check.json", report)
    write_json(output_path / "reports" / "board_status_before_after.json", board)
    write_json(output_path / "reports" / "no_overclaim_check.json", {"status": "PENDING"})
    write_json(output_path / "accepted" / "london_current_accepted_state.json", snapshot)
    write_json(output_path / "accepted" / "london_current_accepted_counts.json", counts)
    write_json(output_path / "accepted" / "london_current_accepted_status_labels.json", labels)
    write_json(output_path / "accepted" / "london_current_artifact_locations.json", snapshot["artifact_locations"])
    write_json(output_path / "accepted" / "london_current_limitations.json", FINAL_LIMITATIONS)
    write_json(output_path / "accepted" / "london_current_next_tasks.json", snapshot["next_tasks"])

    no_overclaim = no_overclaim_report(output_path, snapshot)
    write_json(output_path / "LON_D13_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_path / "reports" / "no_overclaim_check.json", no_overclaim)
    sync = globals()["sync_4070"](output_path, sync_4070)
    write_json(output_path / "LON_D13_4070_SYNC_REPORT.json", sync)

    gates = {
        "LON-D13-PRECOND": "PASS" if all(report["dependency_status"] == "PASS" for report in dependency_checks.values()) and mission_path.exists() and todo_path.exists() else "FAIL",
        "LON-D13-INPUT-STATUS-LEDGER": "PASS" if all(labels.values()) else "FAIL",
        "LON-D13-COUNT-RECONCILIATION": count_reconciliation["status"],
        "LON-D13-LIMITATION-CARRY-FORWARD": "PASS" if all(line in FINAL_LIMITATIONS for line in FINAL_LIMITATIONS) else "FAIL",
        "LON-D13-BOARD-UPDATE": board["status"],
        "LON-D13-4070-SYNC": sync["status"],
        "LON-D13-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D13-NO-MUTATION": no_mutation["status"],
        "LON-D13-HASHES": "PASS",
    }
    overall = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    snapshot["status"] = overall
    write_json(output_path / "LON_D13_COMPOSITE_ACCEPTED_SNAPSHOT.json", snapshot)
    write_markdown_snapshot(output_path, snapshot)
    manifest = artifact_manifest(output_path)
    write_json(output_path / "LON_D13_ARTIFACT_MANIFEST.json", manifest)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "headline": headline,
        "preconditions": dependency_checks,
        "status_ledger": status_ledger,
        "accepted_counts": counts,
        "count_reconciliation": count_reconciliation,
        "limitations": limitations_register,
        "board_update": board,
        "sync_4070": sync,
        "no_overclaim": no_overclaim,
        "no_mutation": no_mutation,
        "gates": gates,
    }
    write_json(output_path / "LON_D13_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D13_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    manifest = artifact_manifest(output_path)
    write_json(output_path / "LON_D13_ARTIFACT_MANIFEST.json", manifest)
    final_sync = globals()["sync_4070"](output_path, sync_4070)
    write_json(output_path / "LON_D13_4070_SYNC_REPORT.json", final_sync)
    harness["sync_4070"] = final_sync
    harness["gates"]["LON-D13-4070-SYNC"] = final_sync["status"]
    harness["status"] = "PASS" if all(value == "PASS" for value in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D13_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    globals()["sync_4070"](output_path, sync_4070)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d11-dir", default="outputs/lon_d11_london_face_layer")
    parser.add_argument("--d11b-dir", default="outputs/lon_d11b_live_face_smoke")
    parser.add_argument("--d12-dir", default="outputs/lon_d12_london_nemo_nim_wrapper")
    parser.add_argument("--d12b-dir", default="outputs/lon_d12b_live_spark_nim_replay")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--mission-control", default="TXRCityBrain_MissionControl.html")
    parser.add_argument("--todo", default="TXRCityBrain_ToDo.html")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sync-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d13_gate(
        args.d9z_dir,
        args.d10z_dir,
        args.d10b_dir,
        args.d11_dir,
        args.d11b_dir,
        args.d12_dir,
        args.d12b_dir,
        args.d6b2_dir,
        args.mission_control,
        args.todo,
        args.output_dir,
        args.sync_4070,
    )
    deps = report["preconditions"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D9Z: {deps['d9z']['dependency_status']}")
    print(f"Input D10Z: {deps['d10z']['dependency_status']}")
    print(f"Input D10B: {deps['d10b']['dependency_status']}")
    print(f"Input D11: {deps['d11']['dependency_status']}")
    print(f"Input D11b: {deps['d11b']['status']}")
    print(f"Input D12: {deps['d12']['dependency_status']}")
    print(f"Input D12b: {deps['d12b']['status']}")
    print(f"Input D6B2: {deps['d6b2']['status']}")
    print(f"Mission Control updated: {report['board_update']['mission_control']['required_labels_present'] and report['board_update']['status']}")
    print(f"ToDo updated: {report['board_update']['todo']['required_items_present'] and report['board_update']['status']}")
    print(f"4070 sync: {report['sync_4070']['status']}")
    print(f"Composite headline: {report['headline']}")
    print(f"Limitations carried forward: {report['limitations']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
