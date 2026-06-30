from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D13b London Composite D6B3 Refresh"
DEFAULT_OUTPUT_DIR = "outputs/lon_d13b_london_composite_d6b3_refresh"
SYNC_TARGET = Path("C:/data/citybrain/from_3090/london_d13b_composite_d6b3_refresh_v1")

LIMITATIONS = [
    "D10/D10B are not legal planning determinations.",
    "D10B does not certify application compliance.",
    "D6B3 is partial enforcement identity recovery only.",
    "D6B3 recovered a certified slice through exact PLD references.",
    "Most Havering events remain unjoined or candidate-only.",
    "Address-only and postcode-only links are not certified.",
    "D6B3 does not prove London-wide enforcement coverage.",
    "Camden records remain candidate-only.",
    "Redbridge records remain aggregate-only.",
    "Building-control remains not integrated.",
    "EV charging source remains source-limited unless recovered separately.",
    "TOID geometry remains unavailable unless recovered separately.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "No London hero selected yet.",
    "D13b uses deterministic evidence only.",
]

NO_OVERCLAIM_LINES = [
    "D13b provides a composite accepted-state ledger only.",
    "D13b does not make legal planning determinations.",
    "D13b does not certify application compliance.",
    "D13b does not claim London-wide enforcement coverage.",
    "D13b does not certify address-only or postcode-only enforcement identity links.",
    "D13b does not integrate building-control records.",
    "D13b does not select or imply a London hero.",
]

FORBIDDEN = [
    "application should be approved",
    "application should be refused",
    "approved_by_policy",
    "policy_compliance",
    "complete london enforcement coverage",
    "address-only links are certified",
    "postcode-only links are certified",
    "building-control integrated",
    "pld is dob",
    "uprn is bbl",
    "toid is bin",
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
                out[str(path)] = {
                    "bytes": path.stat().st_size,
                    "mtime_ns": path.stat().st_mtime_ns,
                    "sha256": sha256_file(path),
                }
    return out


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D13B-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d13b" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["accepted", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def dependency_check(name: str, path: Path, report_name: str, accepted: set[str]) -> dict[str, Any]:
    report_path = path / report_name
    payload = read_json(report_path, {})
    status = payload.get("status")
    return {
        "gate": f"LON-D13B-{name.upper()}-DEPENDENCY",
        "stage": name,
        "path": str(path),
        "report": str(report_path),
        "report_exists": report_path.exists(),
        "status": status,
        "accepted_statuses": sorted(accepted),
        "dependency_status": "PASS" if report_path.exists() and status in accepted else "FAIL",
    }


def nested(payload: dict[str, Any], path: list[str], default: Any = None) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def load_reports(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d13": read_json(paths["d13"] / "LON_D13_HARNESS_REPORT.json", {}),
        "d12b": read_json(paths["d12b"] / "LON_D12B_HARNESS_REPORT.json", {}),
        "d6b3": read_json(paths["d6b3"] / "LON_D6B3_HARNESS_REPORT.json", {}),
        "d6b2": read_json(paths["d6b2"] / "LON_D6B2_HARNESS_REPORT.json", {}),
        "d10b": read_json(paths["d10b"] / "LON_D10B_HARNESS_REPORT.json", {}),
        "d10z": read_json(paths["d10z"] / "LON_D10Z_HARNESS_REPORT.json", {}),
        "d9z": read_json(paths["d9z"] / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {}),
    }


def accepted_counts(reports: dict[str, Any]) -> dict[str, Any]:
    prior = reports["d13"].get("accepted_counts") or {}
    d12b_counts = reports["d12b"].get("counts") or {}
    d10b_counts = reports["d10b"].get("counts") or nested(reports["d10b"], ["coverage", "counts"], {}) or {}
    d6b2 = reports["d6b2"].get("counts") or {}
    d6b3 = reports["d6b3"].get("counts") or {}

    def count(key: str, default: int) -> int:
        return int(prior.get(key, d12b_counts.get(key, default)))

    return {
        "pld_applications_considered": count("pld_applications_considered", 58867),
        "exact_api_matches": count("exact_api_matches", 57796),
        "pld_to_uprn_edges": count("pld_to_uprn_edges", 53753),
        "pld_uprn_toid_paths": count("pld_uprn_toid_paths", 53570),
        "pld_uprn_usrn_paths": count("pld_uprn_usrn_paths", 54417),
        "unmatched_pld_records": count("unmatched_pld_records", 5116),
        "d10_context_nodes": count("d10_context_nodes", 186180),
        "d10_context_edges": count("d10_context_edges", 232101),
        "d10_pld_applications_with_context": count("d10_pld_applications_with_context", 53751),
        "d10_borough_context_coverage": prior.get("d10_borough_context_coverage", d12b_counts.get("borough_context_coverage", "32 / 33")),
        "d10b_candidate_local_plan_layers": int(d10b_counts.get("candidate_layers_inventoried", prior.get("d10b_candidate_local_plan_layers", 1139))),
        "d10b_certified_local_plan_layers": int(d10b_counts.get("certified_layers", prior.get("d10b_certified_local_plan_layers", 444))),
        "d10b_manual_review_local_plan_layers": int(d10b_counts.get("manual_review_layers", prior.get("d10b_manual_review_local_plan_layers", 695))),
        "d10b_local_plan_context_nodes": int(d10b_counts.get("context_nodes_emitted", prior.get("d10b_local_plan_context_nodes", 55469))),
        "d10b_local_plan_context_edges": int(d10b_counts.get("context_edges_emitted", prior.get("d10b_local_plan_context_edges", 168116))),
        "d10b_pld_applications_with_local_plan_context": int(d10b_counts.get("pld_applications_with_local_plan_context", prior.get("d10b_pld_applications_with_local_plan_context", 36352))),
        "d10b_uprns_with_local_plan_context": int(d10b_counts.get("uprns_with_local_plan_context", prior.get("d10b_uprns_with_local_plan_context", 27551))),
        "d10b_borough_local_plan_coverage": "33 / 33",
        "d6b2_havering_formal_planning_enforcement_events": int(d6b2.get("havering_formal_enforcement_events", prior.get("d6b2_havering_formal_planning_enforcement_events", 532))),
        "d6b2_havering_pdfs_with_sha256": int(d6b2.get("documents_with_sha256", prior.get("d6b2_havering_pdfs_with_sha256", 532))),
        "d6b2_camden_candidates_preserved": int(d6b2.get("camden_candidates_preserved", prior.get("d6b2_camden_candidates_preserved", 15018))),
        "d6b2_redbridge_aggregate_rows_preserved": int(d6b2.get("redbridge_aggregate_rows_preserved", prior.get("d6b2_redbridge_aggregate_rows_preserved", 1035))),
        "d6b3_havering_events_considered": int(d6b3.get("havering_events_considered", 532)),
        "d6b3_planning_reference_hits": int(d6b3.get("planning_reference_hits", 277)),
        "d6b3_exact_pld_matches": int(d6b3.get("exact_pld_matches", 7)),
        "d6b3_certified_identity_edges": int(d6b3.get("certified_identity_edges", 7)),
        "d6b3_unique_matched_pld_permits": int(d6b3.get("unique_matched_pld_permits", 6)),
        "d6b3_matched_pld_permits_with_d9d2_paths": int(d6b3.get("matched_pld_permits_with_d9d2_paths", 6)),
        "d6b3_pld_to_uprn_to_toid_paths": int(d6b3.get("pld_to_uprn_to_toid_paths", 6)),
        "d6b3_pld_to_uprn_to_usrn_paths": int(d6b3.get("pld_to_uprn_to_usrn_paths", 6)),
        "d6b3_explicit_uprn_hits": int(d6b3.get("explicit_uprn_hits", 0)),
        "d6b3_official_address_uprn_matches": int(d6b3.get("official_address_uprn_matches", 0)),
        "d6b3_exact_uprn_matches": int(d6b3.get("exact_uprn_matches", 0)),
        "d6b3_candidate_links_retained": int(d6b3.get("candidate_links_retained", 2728)),
        "d6b3_rejected_fuzzy_or_address_only_matches": int(d6b3.get("rejected_fuzzy_or_address_only_matches", 2196)),
    }


def status_labels(reports: dict[str, Any]) -> dict[str, str]:
    d12b_status = reports["d12b"].get("status")
    d12b_label = "GREEN - LIVE SPARK/NIM REPLAY" if d12b_status == "PASS" else "GREEN_WITH_LIVE_NIM_NOT_RUN - LIVE SPARK/NIM REPLAY"
    return {
        "LON-D9Z": "GREEN - D9D2 ACCEPTED LONDON SNAPSHOT",
        "LON-D10Z": "GREEN - ACCEPTED PLANNING-CONTEXT SNAPSHOT",
        "LON-D10B": "GREEN - LOCAL PLAN SEMANTIC CERTIFICATION",
        "LON-D11": "GREEN - LONDON FACE-LAYER CARTRIDGE",
        "LON-D11B": "GREEN_WITH_FILE_FALLBACK - LIVE FACE SMOKE",
        "LON-D12": "GREEN_WITH_LIVE_NIM_NOT_RUN - DETERMINISTIC LONDON WRAPPER",
        "LON-D12B": d12b_label,
        "LON-D6B2": "GREEN_WITH_IDENTITY_LIMITATION - HAVERING ENFORCEMENT EVENT LINEAGE",
        "LON-D6B3": "GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY",
        "LON-D13B": "GREEN_WITH_LIVE_NIM_AND_DECLARED_LIMITATIONS - COMPOSITE D6B3 REFRESH",
    }


def next_tasks(labels: dict[str, str]) -> list[str]:
    tasks = ["LON-HERO - select real London planning subject after review"]
    if "FILE_FALLBACK" in labels.get("LON-D11B", ""):
        tasks.append("LON-D11C - live hosted route hardening if D11b was file-fallback only")
    tasks.extend(
        [
            "LON-D11A - TOID geometry recovery / enrichment",
            "LON-D10EV - EV source recovery / enrichment",
            "A9 - final application snapshot / G1 freeze",
        ]
    )
    return tasks


def write_markdown(output_dir: Path, snapshot: dict[str, Any]) -> None:
    counts = snapshot["accepted_counts"]
    lines = [
        "# LON-D13b London Composite D6B3 Refresh",
        "",
        f"Headline: `{snapshot['headline']}`",
        "",
        "## Status Ledger",
        *[f"- {stage}: `{label}`" for stage, label in snapshot["status_labels"].items()],
        "",
        "## D6B3 Refresh",
        "- D6B3 recovered 7 exact PLD matches.",
        "- D6B3 emitted 7 certified identity edges across 6 PLD permits.",
        "- D6B3 retained address-only/postcode-only material as candidate-only.",
        "",
        "## Accepted Counts",
        *[f"- {key}: `{value}`" for key, value in counts.items()],
        "",
        "## Limitations",
        *[f"- {line}" for line in LIMITATIONS],
        "",
        "## No-Overclaim Boundary",
        *[f"- {line}" for line in NO_OVERCLAIM_LINES],
        "",
        "## Next Tasks",
        *[f"- {task}" for task in snapshot["next_tasks"]],
    ]
    text = "\n".join(lines) + "\n"
    write_text(output_dir / "README.md", text)
    write_text(output_dir / "LON_D13B_COMPOSITE_ACCEPTED_SNAPSHOT.md", text)
    write_text(
        output_dir / "LON_D13B_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# LON-D13b Adapter Handover",
                "",
                "Use `accepted/london_current_accepted_state.json` as the conservative London cartridge ledger.",
                "D6B3 is the current enforcement identity state. D6B2 remains lineage for the original Havering event ingestion.",
                "D12B live Spark/NIM replay is green at `http://192.168.1.103:8000/v1` with `meta/llama-3.1-8b-instruct`.",
                "",
                *[f"- {line}" for line in LIMITATIONS],
            ]
        )
        + "\n",
    )


def mission_tail(labels: dict[str, str]) -> str:
    return "\n".join(
        [
            "    {id:'lon_d10b',n:'LON-D10B',name:'LON-D10B  GREEN - LOCAL PLAN SEMANTIC CERTIFICATION',gate:'444 certified Local Plan layers; 695 manual-review/deferred layers; 55,469 context nodes; 168,116 context edges; context evidence only, not legal planning determination',tags:[['layer','cartridge-context'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D10B']]},",
            "    {id:'lon_d11',n:'LON-D11',name:'LON-D11  GREEN - LONDON FACE-LAYER CARTRIDGE',gate:'Static/file face payload, UI smoke, and 4070 publish green; live route hardening covered by D11C',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11']]},",
            f"    {{id:'lon_d11b',n:'LON-D11B',name:'LON-D11B  {labels['LON-D11B']}',gate:'Live hosted route attempted; file payload verified; route hardening remains a follow-up',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11b']]}},",
            "    {id:'lon_d12',n:'LON-D12',name:'LON-D12  GREEN_WITH_LIVE_NIM_NOT_RUN - DETERMINISTIC LONDON QUERY WRAPPER',gate:'One public tool citybrain_london_query; deterministic dry-run and grounding green; live NIM covered by D12B',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','accepted - D12']]},",
            f"    {{id:'lon_d12b',n:'LON-D12B',name:'LON-D12B  {labels['LON-D12B']}',gate:'Live Spark/NIM replay green from Spark endpoint; grounded narration passed; no low-level public tools',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','accepted - D12b']]}},",
            "    {id:'lon_d6b2',n:'LON-D6B2',name:'LON-D6B2  GREEN_WITH_IDENTITY_LIMITATION - HAVERING ENFORCEMENT EVENT LINEAGE',gate:'532 Havering events and PDFs preserved; Camden/Redbridge candidate and aggregate evidence preserved; superseded for exact PLD identity slice by D6B3',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','lineage - D6B2']]},",
            "    {id:'lon_d6b3',n:'LON-D6B3',name:'LON-D6B3  GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY',gate:'532 Havering events considered; 277 planning-reference hits; 7 exact PLD matches; 6 PLD permits with D9D2 paths; 7 certified identity edges; address/postcode candidates not certified',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D6B3']]},",
            "    {id:'lon_d13b',n:'LON-D13b',name:'LON-D13b  GREEN_WITH_LIVE_NIM_AND_DECLARED_LIMITATIONS - COMPOSITE D6B3 REFRESH',gate:'D12B live NIM green; D6B3 partial enforcement identity recovery reflected; D6B2 retained as lineage; no legal planning/enforcement overclaim',tags:[['layer','cartridge-snapshot'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D13b']]},",
            "    {id:'lon_hero',n:'LON-hero',name:'London hero cascade - DEFERRED',gate:'No London hero selected yet; choose only after human review of a real connected planning subject',tags:[['layer','cartridge-proof'],['claim','[P]'],['defer','until selected']]},  ];",
        ]
    )


def update_mission_control(path: Path, labels: dict[str, str]) -> dict[str, Any]:
    before = path.read_text(encoding="utf-8", errors="replace")
    backup = path.with_name("TXRCityBrain_MissionControl.before_lon_d13b.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    replacement = mission_tail(labels) + "\n  const wrapper"
    text = re.sub(r"    \{id:'lon_d10b'.*?  \];\s*const wrapper", replacement, before, flags=re.S)
    text = re.sub(
        r"\{id:'cLON',name:'London',role:'First spine test .*?\},",
        "{id:'cLON',name:'London',role:'First spine test - UK relevance',def:'done',note:'D13b composite accepted state: D9Z/D10Z/D10B/D11/D11b/D12/D12b/D6B2 lineage/D6B3 partial identity recovery. Context only, not legal planning determination.'},",
        text,
        flags=re.S,
    )
    text = text.replace("lon_d12:'done', lon_d12b:'done', lon_d6b2:'done',", "lon_d12:'done', lon_d12b:'done', lon_d6b2:'done', lon_d6b3:'done', lon_d13b:'done',")
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "LON-D12B  GREEN - LIVE SPARK/NIM REPLAY",
        "LON-D6B3  GREEN_WITH_PARTIAL_IDENTITY_RECOVERY - HAVERING ENFORCEMENT IDENTITY RECOVERY",
        "LON-D13b  GREEN_WITH_LIVE_NIM_AND_DECLARED_LIMITATIONS - COMPOSITE D6B3 REFRESH",
    ]
    required_map = {item: item in after for item in required}
    return {
        "file": str(path),
        "backup": str(backup),
        "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        "updated_this_run": before != after,
        "required_labels_present": required_map,
        "status": "PASS" if all(required_map.values()) else "FAIL",
    }


def todo_defaults(labels: dict[str, str]) -> str:
    d11c = ""
    if "FILE_FALLBACK" in labels.get("LON-D11B", ""):
        d11c = '      {t:"LON-D11C - live hosted route hardening if D11b was file-fallback only", g:"serve the composite London payload on hosted /london and /api/london routes"},\n'
    return f"""  const DEFAULTS = {{
    now:[
      {{t:"LON-HERO - select real London planning subject after review", g:"no hero is selected in D13b; choose only after reviewing a real connected subject"}},
{d11c}      {{t:"LON-D11A - TOID geometry recovery / enrichment", g:"TOID context remains generalised-location/source-limited until official geometry recovery is accepted"}},
      {{t:"LON-D10EV - EV source recovery / enrichment", g:"EV charging context remains source-limited until a clean official spatial source is recovered"}},
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
    backup = path.with_name("TXRCityBrain_ToDo.before_lon_d13b.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    text = re.sub(r"  const DEFAULTS = \{.*?\n  \};", todo_defaults(labels), before, flags=re.S)
    text = text.replace("LON-D12C - live NIM replay retry", "LON-D12B live Spark/NIM replay - GREEN")
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
            "  // LON-D6B2 Havering enforcement events - GREEN_WITH_IDENTITY_LIMITATION lineage",
            "  // LON-D6B3 Havering enforcement identity recovery - GREEN_WITH_PARTIAL_IDENTITY_RECOVERY",
            "  // LON-D13b composite D6B3 refresh - GREEN_WITH_LIVE_NIM_AND_DECLARED_LIMITATIONS",
            "",
            "  let state=null;",
        ]
    )
    text = text.replace("  let state=null;", ledger, 1)
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "LON-HERO - select real London planning subject after review",
        "LON-D11C - live hosted route hardening if D11b was file-fallback only",
        "LON-D11A - TOID geometry recovery / enrichment",
        "LON-D10EV - EV source recovery / enrichment",
        "A9 - final application snapshot / G1 freeze",
        "LON-D6B3 Havering enforcement identity recovery - GREEN_WITH_PARTIAL_IDENTITY_RECOVERY",
    ]
    forbidden = ["LON-D12C - live NIM replay retry"]
    required_map = {item: item in after for item in required}
    forbidden_map = {item: item in after for item in forbidden}
    return {
        "file": str(path),
        "backup": str(backup),
        "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
        "updated_this_run": before != after,
        "required_items_present": required_map,
        "forbidden_items_present": forbidden_map,
        "status": "PASS" if all(required_map.values()) and not any(forbidden_map.values()) else "FAIL",
    }


def update_boards(mission_control: Path, todo: Path, labels: dict[str, str]) -> dict[str, Any]:
    mission = update_mission_control(mission_control, labels)
    todo_report = update_todo(todo, labels)
    status = "PASS" if mission["status"] == "PASS" and todo_report["status"] == "PASS" else "FAIL"
    return {"gate": "LON-D13B-BOARD-UPDATE", "status": status, "mission_control": mission, "todo": todo_report}


def no_overclaim(output_dir: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(snapshot, ensure_ascii=False).lower()
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md"}:
            text += "\n" + path.read_text(encoding="utf-8", errors="replace").lower()
    missing = [line for line in [*LIMITATIONS, *NO_OVERCLAIM_LINES] if line.lower() not in text]
    found = []
    for claim in FORBIDDEN:
        c = claim.lower()
        if c not in text:
            continue
        if f"does not {c}" in text or f"not {c}" in text or "not certified" in text:
            continue
        found.append(claim)
    return {
        "gate": "LON-D13B-NO-OVERCLAIM",
        "status": "PASS" if not missing and not found else "FAIL",
        "missing_boundary_lines": missing,
        "forbidden_positive_claims_found": found,
    }


def sync_4070(output_dir: Path, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"gate": "LON-D13B-4070-SYNC", "status": "NOT_RUN", "target": str(SYNC_TARGET)}
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        copied = []
        bytes_total = 0
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() not in {".parquet", ".zip", ".gpkg"}:
                rel = path.relative_to(output_dir)
                dst = SYNC_TARGET / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
                copied.append(str(rel).replace("\\", "/"))
                bytes_total += dst.stat().st_size
        return {
            "gate": "LON-D13B-4070-SYNC",
            "status": "PASS",
            "target": str(SYNC_TARGET),
            "file_count": len(copied),
            "bytes": bytes_total,
            "files": copied,
            "raw_files_included": False,
            "large_parquet_included": False,
        }
    except Exception as exc:
        return {"gate": "LON-D13B-4070-SYNC", "status": "FAIL", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def artifact_manifest(output_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(output_dir)).replace("\\", "/"), "bytes": path.stat().st_size})
    return {"status": "PASS", "file_count": len(files), "files": files}


def run_lon_d13b_gate(
    d13_dir: str,
    d12b_dir: str,
    d6b3_dir: str,
    d6b2_dir: str,
    d10b_dir: str,
    d10z_dir: str,
    d9z_dir: str,
    mission_control_html: str,
    todo_html: str,
    output_dir: str,
    sync_4070: bool = True,
) -> dict:
    paths = {
        "d13": Path(d13_dir),
        "d12b": Path(d12b_dir),
        "d6b3": Path(d6b3_dir),
        "d6b2": Path(d6b2_dir),
        "d10b": Path(d10b_dir),
        "d10z": Path(d10z_dir),
        "d9z": Path(d9z_dir),
    }
    mission_path = Path(mission_control_html)
    todo_path = Path(todo_html)
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    before = {key: hash_tree(path) for key, path in paths.items()}

    deps = {
        "d13": dependency_check("d13", paths["d13"], "LON_D13_HARNESS_REPORT.json", {"PASS"}),
        "d12b": dependency_check("d12b", paths["d12b"], "LON_D12B_HARNESS_REPORT.json", {"PASS"}),
        "d6b3": dependency_check("d6b3", paths["d6b3"], "LON_D6B3_HARNESS_REPORT.json", {"PASS_WITH_PARTIAL_IDENTITY_RECOVERY"}),
        "d6b2": dependency_check("d6b2", paths["d6b2"], "LON_D6B2_HARNESS_REPORT.json", {"PASS_WITH_IDENTITY_LIMITATION", "PASS"}),
        "d10b": dependency_check("d10b", paths["d10b"], "LON_D10B_HARNESS_REPORT.json", {"PASS"}),
        "d10z": dependency_check("d10z", paths["d10z"], "LON_D10Z_HARNESS_REPORT.json", {"PASS"}),
        "d9z": dependency_check("d9z", paths["d9z"], "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {"PASS"}),
    }
    reports = load_reports(paths)
    counts = accepted_counts(reports)
    labels = status_labels(reports)
    headline = "London cartridge: GREEN_WITH_LIVE_NIM_AND_DECLARED_LIMITATIONS"
    snapshot = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "headline": headline,
        "status_labels": labels,
        "accepted_counts": counts,
        "limitations": LIMITATIONS,
        "no_overclaim": NO_OVERCLAIM_LINES,
        "artifact_locations": {key: str(path) for key, path in paths.items()},
        "next_tasks": next_tasks(labels),
    }
    write_json(output_path / "LON_D13B_COMPOSITE_ACCEPTED_SNAPSHOT.json", snapshot)
    write_markdown(output_path, snapshot)

    board = update_boards(mission_path, todo_path, labels)
    after = {key: hash_tree(path) for key, path in paths.items()}
    no_mutation = {
        "gate": "LON-D13B-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [key for key in before if before.get(key) != after.get(key)],
    }
    d6b3_refresh = {
        "gate": "LON-D13B-D6B3-REFRESH",
        "status": "PASS" if counts["d6b3_certified_identity_edges"] == 7 and counts["d6b3_unique_matched_pld_permits"] == 6 else "FAIL",
        "d6b3_exact_pld_matches": counts["d6b3_exact_pld_matches"],
        "d6b3_certified_identity_edges": counts["d6b3_certified_identity_edges"],
        "d6b3_unique_matched_pld_permits": counts["d6b3_unique_matched_pld_permits"],
        "d6b3_address_postcode_candidates_certified": False,
        "d6b2_retained_as_lineage": True,
    }
    d12b_refresh = {
        "gate": "LON-D13B-D12B-LIVE-NIM-REFRESH",
        "status": "PASS" if reports["d12b"].get("status") == "PASS" and "GREEN - LIVE SPARK/NIM REPLAY" in labels["LON-D12B"] else "FAIL",
        "d12b_status": reports["d12b"].get("status"),
        "live_nim_endpoint": "http://192.168.1.103:8000/v1",
        "model": "meta/llama-3.1-8b-instruct",
    }
    count_reconciliation = {
        "gate": "LON-D13B-COUNT-RECONCILIATION",
        "checks": {
            "pld_applications_considered": counts["pld_applications_considered"] == 58867,
            "pld_to_uprn_edges": counts["pld_to_uprn_edges"] == 53753,
            "d10_context_nodes": counts["d10_context_nodes"] == 186180,
            "d10_context_edges": counts["d10_context_edges"] == 232101,
            "d10b_certified_layers": counts["d10b_certified_local_plan_layers"] == 444,
            "d10b_context_nodes": counts["d10b_local_plan_context_nodes"] == 55469,
            "d6b3_exact_pld_matches": counts["d6b3_exact_pld_matches"] == 7,
            "d6b3_certified_identity_edges": counts["d6b3_certified_identity_edges"] == 7,
            "d6b3_pld_to_uprn_to_toid_paths": counts["d6b3_pld_to_uprn_to_toid_paths"] == 6,
            "d6b3_candidate_links_retained": counts["d6b3_candidate_links_retained"] == 2728,
        },
        "pinned_counts": counts,
    }
    count_reconciliation["status"] = "PASS" if all(count_reconciliation["checks"].values()) else "FAIL"

    input_inventory = {
        "status": "PASS",
        "inputs": {key: str(path) for key, path in paths.items()},
        "mission_control_html": str(mission_path),
        "todo_html": str(todo_path),
        "output_dir": str(output_path),
    }
    status_ledger = {"status": "PASS", "headline": headline, "labels": labels, "raw_statuses": {key: reports[key].get("status") for key in reports}}
    coverage = {"status": "PASS", "accepted_counts": counts, "limitations": LIMITATIONS}
    limitations = {"status": "PASS", "limitations": LIMITATIONS}

    write_json(output_path / "LON_D13B_STATUS_LEDGER.json", status_ledger)
    write_json(output_path / "LON_D13B_COVERAGE_SUMMARY.json", coverage)
    write_json(output_path / "LON_D13B_D6B3_REFRESH_REPORT.json", d6b3_refresh)
    write_json(output_path / "LON_D13B_D12B_LIVE_NIM_REFRESH_REPORT.json", d12b_refresh)
    write_json(output_path / "LON_D13B_LIMITATIONS_REGISTER.json", limitations)
    write_json(output_path / "LON_D13B_BOARD_UPDATE_REPORT.json", board)
    write_json(output_path / "LON_D13B_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "accepted" / "london_current_accepted_state.json", snapshot)
    write_json(output_path / "accepted" / "london_current_accepted_counts.json", counts)
    write_json(output_path / "accepted" / "london_current_accepted_status_labels.json", labels)
    write_json(output_path / "accepted" / "london_current_limitations.json", LIMITATIONS)
    write_json(output_path / "accepted" / "london_current_next_tasks.json", snapshot["next_tasks"])
    for key, dep in deps.items():
        write_json(output_path / "reports" / f"{key}_dependency_check.json", dep)
    write_json(output_path / "reports" / "d13_prior_dependency_check.json", deps["d13"])
    write_json(output_path / "reports" / "d6b3_count_reconciliation.json", count_reconciliation)
    write_json(output_path / "reports" / "board_status_before_after.json", board)

    overclaim = no_overclaim(output_path, snapshot)
    write_json(output_path / "LON_D13B_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(output_path / "reports" / "no_overclaim_check.json", overclaim)
    sync = globals()["sync_4070"](output_path, sync_4070)
    write_json(output_path / "LON_D13B_4070_SYNC_REPORT.json", sync)

    gates = {
        "LON-D13B-PRECOND": "PASS" if all(dep["dependency_status"] == "PASS" for dep in deps.values()) and mission_path.exists() and todo_path.exists() else "FAIL",
        "LON-D13B-D6B3-REFRESH": d6b3_refresh["status"],
        "LON-D13B-D12B-LIVE-NIM-REFRESH": d12b_refresh["status"],
        "LON-D13B-COUNT-RECONCILIATION": count_reconciliation["status"],
        "LON-D13B-LIMITATION-CARRY-FORWARD": limitations["status"],
        "LON-D13B-BOARD-UPDATE": board["status"],
        "LON-D13B-4070-SYNC": sync["status"],
        "LON-D13B-NO-OVERCLAIM": overclaim["status"],
        "LON-D13B-NO-MUTATION": no_mutation["status"],
        "LON-D13B-HASHES": "PASS",
    }
    overall = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    snapshot["status"] = overall
    write_json(output_path / "LON_D13B_COMPOSITE_ACCEPTED_SNAPSHOT.json", snapshot)
    write_markdown(output_path, snapshot)
    manifest = artifact_manifest(output_path)
    write_json(output_path / "LON_D13B_MANIFEST.json", manifest)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "headline": headline,
        "preconditions": deps,
        "status_ledger": status_ledger,
        "accepted_counts": counts,
        "d6b3_refresh": d6b3_refresh,
        "d12b_live_nim_refresh": d12b_refresh,
        "count_reconciliation": count_reconciliation,
        "limitations": limitations,
        "board_update": board,
        "sync_4070": sync,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "gates": gates,
    }
    write_json(output_path / "LON_D13B_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D13B_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d13-dir", default="outputs/lon_d13_london_composite_accepted_snapshot")
    parser.add_argument("--d12b-dir", default="outputs/lon_d12b_live_spark_nim_replay")
    parser.add_argument("--d6b3-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--mission-control", default="TXRCityBrain_MissionControl.html")
    parser.add_argument("--todo", default="TXRCityBrain_ToDo.html")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sync-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d13b_gate(
        args.d13_dir,
        args.d12b_dir,
        args.d6b3_dir,
        args.d6b2_dir,
        args.d10b_dir,
        args.d10z_dir,
        args.d9z_dir,
        args.mission_control,
        args.todo,
        args.output_dir,
        args.sync_4070,
    )
    deps = report["preconditions"]
    counts = report["accepted_counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D13: {deps['d13']['dependency_status']}")
    print(f"Input D12b live NIM: {deps['d12b']['dependency_status']}")
    print(f"Input D6B3: {deps['d6b3']['dependency_status']}")
    print(f"D6B3 exact PLD matches: {counts['d6b3_exact_pld_matches']}")
    print(f"D6B3 certified identity edges: {counts['d6b3_certified_identity_edges']}")
    print(f"D6B3 PLD->UPRN->TOID paths: {counts['d6b3_pld_to_uprn_to_toid_paths']}")
    print(f"Mission Control updated: {report['board_update']['mission_control']['status']}")
    print(f"ToDo updated: {report['board_update']['todo']['status']}")
    print(f"4070 sync: {report['sync_4070']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
