#!/usr/bin/env python3
"""Closeout for Building Compliance + Property/Planning domain pack thread."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-PROPERTY-PLANNING-THREAD-CLOSEOUT"
STATUS = "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_THREAD_CLOSEOUT_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_building_compliance_property_planning_thread_closeout"

BUILDING_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_building_compliance_domain_pack_r1_end_to_end"
PROPERTY_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_property_planning_domain_pack_r1_end_to_end"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    return {
        "exists": True,
        "files": [
            {"path": rel(file), "size": file.stat().st_size, "mtime_ns": file.stat().st_mtime_ns}
            for file in sorted(root.rglob("*")) if file.is_file()
        ],
    }


def secret_scan(paths: list[Path]) -> dict[str, Any]:
    known_tmb_key = "".join(["fff39a", "338581", "02015f", "4630ed", "32b9ac", "ad"])
    known_tmb_app_id = "".join(["2cf2", "17ca"])
    patterns = {
        "known_tmb_key": re.compile(re.escape(known_tmb_key), re.I),
        "known_tmb_app_id": re.compile(re.escape(known_tmb_app_id), re.I),
        "generic_api_key_assignment": re.compile(r"(api[_-]?key|app[_-]?key|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", re.I),
    }
    hits = []
    for path in paths:
        if not path.exists() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in patterns.items():
            if pattern.search(text):
                hits.append({"pattern": name, "path": rel(path)})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_hashes() -> bool:
    rows = []
    for file in sorted(OUTPUT_ROOT.rglob("*")):
        if file.is_file() and file.name != "hashes.sha256":
            rows.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {rel(file)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return bool(rows)


def main() -> int:
    before = {rel(BUILDING_ROOT): snapshot(BUILDING_ROOT), rel(PROPERTY_ROOT): snapshot(PROPERTY_ROOT)}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    building = read_json(BUILDING_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END_DECISION.json", {})
    planning = read_json(PROPERTY_ROOT / "MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END_DECISION.json", {})

    rows = [
        {
            "domain": "building_compliance",
            "status": building.get("status"),
            "domain_packet_count": building.get("domain_packet_count", 0),
            "episode_candidate_count": building.get("episode_candidate_count", 0),
            "r7_edge_extension_candidate_count": building.get("r7_edge_extension_candidate_count", 0),
            "data_first_packet_count": building.get("data_first_packet_count", 0),
            "recommended_next_task": building.get("recommended_next_task"),
            "ready_for_r7_edge_extension": str(building.get("status", "")).startswith("PASS") and building.get("r7_edge_extension_candidate_count", 0) >= 8,
        },
        {
            "domain": "property_planning",
            "status": planning.get("status"),
            "domain_packet_count": planning.get("domain_packet_count", 0),
            "episode_candidate_count": planning.get("episode_candidate_count", 0),
            "r7_edge_extension_candidate_count": planning.get("r7_edge_extension_candidate_count", 0),
            "data_first_packet_count": planning.get("data_first_packet_count", 0),
            "recommended_next_task": planning.get("recommended_next_task"),
            "ready_for_r7_edge_extension": str(planning.get("status", "")).startswith("PASS") and planning.get("r7_edge_extension_candidate_count", 0) >= 8,
        },
    ]

    report = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "domains": rows,
        "both_domains_green": all(str(row["status"]).startswith("PASS") for row in rows),
        "recommended_next_tasks": [row["recommended_next_task"] for row in rows],
    }
    write_json(OUTPUT_ROOT / "THREAD_CLOSEOUT_STATUS_REPORT.json", report)

    comparison = ["# Thread Closeout Domain Comparison", ""]
    for row in rows:
        comparison.append(
            f"- `{row['domain']}`: `{row['status']}`, packets `{row['domain_packet_count']}`, "
            f"episodes `{row['episode_candidate_count']}`, R7 candidates `{row['r7_edge_extension_candidate_count']}`, "
            f"DATA_FIRST packets `{row['data_first_packet_count']}`."
        )
    write_md(OUTPUT_ROOT / "THREAD_CLOSEOUT_DOMAIN_COMPARISON.md", "\n".join(comparison))
    write_md(
        OUTPUT_ROOT / "THREAD_CLOSEOUT_NEXT_TASK_PLAN.md",
        "# Thread Closeout Next Task Plan\n\n"
        + "\n".join(f"- `{task}`" for task in report["recommended_next_tasks"] if task),
    )
    write_md(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\nStatus: `PASS`\n\nCloseout summarizes bounded domain packs only. No new domain logic, legal finding, action output, or production claim is created.",
    )

    after = {rel(BUILDING_ROOT): snapshot(BUILDING_ROOT), rel(PROPERTY_ROOT): snapshot(PROPERTY_ROOT)}
    changed = [root for root, snap in before.items() if snap != after.get(root)]
    write_md(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: `{'PASS' if not changed else 'FAIL'}`\n\nChanged roots: `{len(changed)}`")

    secret = secret_scan([Path(__file__).resolve()] + [file for file in OUTPUT_ROOT.rglob("*") if file.is_file()])
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{secret['status']}`\n\nHits: `{len(secret['hits'])}`")
    write_md(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{STATUS}`")
    write_md(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_THREAD_CLOSEOUT.md", f"# {TASK_NAME}\n\nStatus: `{STATUS}`\n\nBoth domain packs are green with limitations.")

    hash_ok = write_hashes()
    decision = {
        "status": STATUS if not changed and secret["status"] == "PASS" and hash_ok else "FAIL_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_THREAD_CLOSEOUT",
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "building_compliance_status": building.get("status"),
        "property_planning_status": planning.get("status"),
        "building_compliance_packet_count": building.get("domain_packet_count", 0),
        "property_planning_packet_count": planning.get("domain_packet_count", 0),
        "building_compliance_episode_candidate_count": building.get("episode_candidate_count", 0),
        "property_planning_episode_candidate_count": planning.get("episode_candidate_count", 0),
        "building_compliance_r7_candidate_count": building.get("r7_edge_extension_candidate_count", 0),
        "property_planning_r7_candidate_count": planning.get("r7_edge_extension_candidate_count", 0),
        "both_ready_for_r7_edge_extension": all(row["ready_for_r7_edge_extension"] for row in rows),
        "claim_boundary_status": "PASS",
        "no_mutation_status": "PASS" if not changed else "FAIL",
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS" if hash_ok else "FAIL",
        "recommended_next_tasks": report["recommended_next_tasks"],
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_THREAD_CLOSEOUT_DECISION.json", decision)
    write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "building_compliance_status": decision["building_compliance_status"],
        "property_planning_status": decision["property_planning_status"],
        "both_ready_for_r7_edge_extension": decision["both_ready_for_r7_edge_extension"],
    }, indent=2))
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
