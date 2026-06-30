#!/usr/bin/env python3
"""CHI-F4X-D5 hero freeze package."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "CHI-F4X-D5 Chicago Flow 4 Hero Freeze Package"
DEFAULT_OUTPUT_DIR = "outputs/chi_f4x_d5_hero_freeze_package"
PASS_STATUSES = {"PASS_HERO_FREEZE_PACKAGE", "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS"}

REQUIRED_ARTIFACTS = [
    "README.md",
    "CHI_F4X_D5_HARNESS_REPORT.json",
    "CHI_F4X_D5_INPUT_INVENTORY.json",
    "CHI_F4X_D5_HERO_SELECTION_POLICY.json",
    "CHI_F4X_D5_HERO_CANDIDATES.json",
    "CHI_F4X_D5_SELECTED_HEROES.json",
    "CHI_F4X_D5_HERO_FREEZE_PACKAGE.json",
    "CHI_F4X_D5_HERO_BRIEFINGS.json",
    "CHI_F4X_D5_FACE_HERO_PAYLOAD.json",
    "CHI_F4X_D5_TRACE_REPORT.json",
    "CHI_F4X_D5_SOURCE_LIMITATION_REPORT.json",
    "CHI_F4X_D5_NEXT_D6_HANDOFF.json",
    "CHI_F4X_D5_NO_OVERCLAIM_REPORT.json",
    "CHI_F4X_D5_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

INPUT_DEFAULTS = {
    "chi_f4x_d3_r1": "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles",
    "chi_f4x_d4": "outputs/chi_f4x_d4_mobility_environment_replay_face_proof",
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "chi_f1f7_d5": "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
    "chi_flowx_d2": "outputs/chi_flowx_d2_parallel_join_hardening",
    "ontology_v2": "contracts/ontology_v2",
    "nightrun_d1_optional": "outputs/nightrun_d1_overnight_current_work_completion",
}

NO_OVERCLAIM_PATTERNS = [
    r"\bchicago flow 4 accepted\b",
    r"\ball chicago mobility/environment sources are full\b",
    r"\bopen air individual is full\b",
    r"\bcook parcels are full\b",
    r"\btraffic tracker is historical completeness\b",
    r"\bcta live status\b",
    r"\blive cta status\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\bhealth determination\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\boperational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "boundary ", "forbidden ")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "chi_f4x_d5_hero_freeze_package":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "CHI_F4X_D5_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 56) : match.end() + 20]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def input_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {}
    for name, rel in INPUT_DEFAULTS.items():
        path = project_path(project_root, rel)
        optional = name.endswith("_optional")
        inputs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "required": not optional,
            "status": "PASS" if path.exists() else ("OPTIONAL_MISSING" if optional else "MISSING_REQUIRED"),
            "signature": input_signature(path),
        }
    return {"status": "PASS", "generated_at": utc_now(), "inputs": inputs}


def load_d4(project_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    d4 = project_path(project_root, "outputs/chi_f4x_d4_mobility_environment_replay_face_proof")
    return (
        read_json(d4 / "CHI_F4X_D4_HARNESS_REPORT.json", {}),
        read_json(d4 / "CHI_F4X_D4_REPLAY_PAYLOAD.json", {}),
        read_json(d4 / "CHI_F4X_D4_FACE_ROUTE_PAYLOAD.json", {}),
    )


def select_limitations(replay: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    limitations = replay.get("source_limitations", [])
    return [item for item in limitations if item.get("source_key") in keys]


def base_hero(hero_id: str, title: str, claim_label: str, summary: str, bundle_ids: list[str], payload_ids: list[str], limitations: list[dict[str, Any]], boundaries: list[str], evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "hero_id": hero_id,
        "hero_title": title,
        "city": "chicago",
        "flow": "F4X",
        "stage": "D5",
        "source_stage": "CHI-F4X-D4",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "source_evidence_bundle_ids": bundle_ids,
        "source_d4_payload_ids": payload_ids,
        "claim_label": claim_label,
        "summary": summary,
        "evidence_refs": evidence_refs,
        "source_limitations": limitations,
        "governance_boundaries": boundaries,
        "forbidden_claims": [
            "NO_CHICAGO_FLOW_4_ACCEPTANCE",
            "NO_LIVE_CTA_STATUS",
            "NO_TRAFFIC_OR_TRANSIT_CONTROL",
            "NO_HEALTH_DETERMINATION",
            "NO_PUBLIC_SAFETY_POLICING_ENFORCEMENT_DISPATCH",
            "NO_OPERATIONAL_COMMAND",
            "NO_CERTIFIED_AFFECTED_ASSET_OR_BUILDING",
        ],
        "next_step": "D6 promotion review only",
    }


def build_heroes(replay: dict[str, Any], face: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload_ids = ["CHI_F4X_D4_REPLAY_PAYLOAD", "CHI_F4X_D4_BRIEFING_PAYLOAD", "CHI_F4X_D4_FACE_ROUTE_PAYLOAD"]
    refs = replay.get("evidencebundle_refs", [])
    boundaries = list(replay.get("governance_boundaries", [])) + ["Chicago Flow 4 is not accepted at D5.", f"D4 face route status is {face.get('status', 'FACE_ROUTE_PAYLOAD_ONLY')}."]
    candidates = [
        base_hero(
            "chi_f4x_d5_hero_1_mobility_context",
            "Chicago Flow 4 Mobility Context",
            "[R]",
            "Mobility/environment review context using traffic tracker, Divvy or micromobility, CTA static schedule context, and Cook parcel/area context only as non-certified area context.",
            [ref for ref in refs if ref in {"traffic_tracker_time_window_context_bundle", "divvy_or_mobility_context_bundle", "cta_static_context_bundle", "mobility_environment_governance_boundary_bundle"}],
            payload_ids,
            select_limitations(replay, ["traffic_tracker_historical_2024_current", "311_service_requests", "divvy_trips", "cta_gtfs_static", "cook_county_parcel_universe_chicago"]),
            boundaries,
            ["CHI-F4X-D4:replay_payload", "CHI-F4X-D3-R1:traffic_tracker_time_window_context_bundle", "CHI-F4X-D3-R1:divvy_or_mobility_context_bundle", "CHI-F4X-D3-R1:cta_static_context_bundle"],
        ),
        base_hero(
            "chi_f4x_d5_hero_2_environment_context",
            "Chicago Flow 4 Environment Context",
            "[R]",
            "Environmental observation review context highlighting Open Air hourly as full where proven and Open Air individual as capped bulk.",
            [ref for ref in refs if ref in {"open_air_environment_context_bundle", "mobility_environment_governance_boundary_bundle"}],
            payload_ids,
            select_limitations(replay, ["open_air_chicago_hour_aggregations", "open_air_chicago_individual_measurements"]),
            boundaries,
            ["CHI-F4X-D4:replay_payload", "CHI-F4X-D3-R1:open_air_environment_context_bundle"],
        ),
        base_hero(
            "chi_f4x_d5_hero_3_governance_boundary",
            "Governance Boundary: Source-Limited / Payload-Only Flow 4",
            "[G]",
            "Governance freeze for a payload-only face route and source-limited D6 promotion-review candidate.",
            refs,
            payload_ids,
            replay.get("source_limitations", []),
            boundaries
            + [
                "Open Air individual is not full.",
                "Cook parcels are not full.",
                "CTA static schedule is not live CTA status.",
                "Environmental data is not a health determination.",
                "Mobility data is not traffic-control or transit-control instruction.",
                "No public-safety, policing, enforcement, dispatch, or certified affected-asset claim.",
            ],
            ["CHI-F4X-D4:face_route_payload", "CHI-F4X-D4:source_limitation_report", "XDATA-D2-R1:source_status_normalization"],
        ),
    ]
    return candidates, candidates


def build_briefings(heroes: list[dict[str, Any]]) -> dict[str, Any]:
    briefings = []
    for hero in heroes:
        briefings.append(
            {
                "hero_id": hero["hero_id"],
                "hero_title": hero["hero_title"],
                "briefing_text": [
                    f"{hero['hero_title']} is a source-limited hero freeze for mobility/environment review context.",
                    "The package is payload-only and remains for operator review.",
                    "Capped bulk, windowed complete, and full where proven labels carry forward.",
                    "This is a D6 promotion-review candidate, not an acceptance decision.",
                ],
                "allowed_language_used": ["mobility/environment review context", "source-limited", "capped bulk", "full where proven", "payload-only face route", "operator review", "D6 promotion-review candidate"],
            }
        )
    return {"status": "PASS", "briefings": briefings}


def run_chi_f4x_d5(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in INPUT_DEFAULTS.items()}
    before = {name: input_signature(path) for name, path in watched.items()}

    d4_harness, replay, face = load_d4(project_root)
    inventory = input_inventory(project_root)
    policy = {
        "status": "PASS",
        "selection_rule": "Select exactly one mobility hero, one environment hero, and one governance boundary hero from CHI-F4X-D4 payload-only proof.",
        "required_count": 3,
        "source_stage": "CHI-F4X-D4",
        "payload_only_required": face.get("status") == "FACE_ROUTE_PAYLOAD_ONLY",
    }
    candidates, selected = build_heroes(replay, face)
    freeze = {
        "status": "PASS",
        "city": "chicago",
        "flow": "F4X",
        "stage": "D5",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "hero_count": len(selected),
        "selected_hero_ids": [hero["hero_id"] for hero in selected],
        "heroes": selected,
        "source_stage": "CHI-F4X-D4",
        "d4_status": d4_harness.get("status"),
        "face_route_status": face.get("status"),
    }
    briefings = build_briefings(selected)
    face_hero = {
        "status": "FACE_HERO_PAYLOAD_ONLY",
        "published": False,
        "reason": "D4 face route status was FACE_ROUTE_PAYLOAD_ONLY; D5 does not publish live hero routes.",
        "future_routes": ["/chicago/flow4/heroes", "/api/chicago/flow4/heroes", "/api/chicago/flow4/heroes/{hero_id}"],
        "hero_ids": [hero["hero_id"] for hero in selected],
        "payload_binding": "CHI_F4X_D5_HERO_FREEZE_PACKAGE.json",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
    }
    trace = {
        "status": "PASS",
        "trace_refs": ["CHI-F4X-D4:CHI_F4X_D4_REPLAY_PAYLOAD.json", "CHI-F4X-D4:CHI_F4X_D4_FACE_ROUTE_PAYLOAD.json"] + [ref for hero in selected for ref in hero["evidence_refs"]],
    }
    source_report = {
        "status": "PASS",
        "source_limitations": replay.get("source_limitations", []),
        "payload_only_boundary": face.get("status") == "FACE_ROUTE_PAYLOAD_ONLY",
        "boundaries": selected[2]["governance_boundaries"],
    }
    next_d6 = {
        "status": "D6_PROMOTION_REVIEW_READY_WITH_SOURCE_LIMITATIONS",
        "recommended_next_gate": "CHI-F4X-D6",
        "decision_scope": "promotion review only",
        "accepted_flow_cartridge": False,
        "hero_freeze_package": "CHI_F4X_D5_HERO_FREEZE_PACKAGE.json",
        "boundaries_to_carry": source_report["boundaries"],
    }

    write_json(out / "CHI_F4X_D5_INPUT_INVENTORY.json", inventory)
    write_json(out / "CHI_F4X_D5_HERO_SELECTION_POLICY.json", policy)
    write_json(out / "CHI_F4X_D5_HERO_CANDIDATES.json", {"status": "PASS", "candidates": candidates})
    write_json(out / "CHI_F4X_D5_SELECTED_HEROES.json", {"status": "PASS", "selected_heroes": selected})
    write_json(out / "CHI_F4X_D5_HERO_FREEZE_PACKAGE.json", freeze)
    write_json(out / "CHI_F4X_D5_HERO_BRIEFINGS.json", briefings)
    write_json(out / "CHI_F4X_D5_FACE_HERO_PAYLOAD.json", face_hero)
    write_json(out / "CHI_F4X_D5_TRACE_REPORT.json", trace)
    write_json(out / "CHI_F4X_D5_SOURCE_LIMITATION_REPORT.json", source_report)
    write_json(out / "CHI_F4X_D5_NEXT_D6_HANDOFF.json", next_d6)

    gates = [
        {"gate": "CHI-F4X-D5-PRECOND", "status": "PASS" if d4_harness.get("status") == "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" else "FAIL"},
        {"gate": "CHI-F4X-D5-INPUT-INVENTORY", "status": "PASS" if all(item["status"] != "MISSING_REQUIRED" for item in inventory["inputs"].values()) else "FAIL"},
        {"gate": "CHI-F4X-D5-HERO-SELECTION-POLICY", "status": policy["status"]},
        {"gate": "CHI-F4X-D5-HERO-CANDIDATES", "status": "PASS" if len(candidates) == 3 else "FAIL", "candidate_count": len(candidates)},
        {"gate": "CHI-F4X-D5-SELECTED-HEROES", "status": "PASS" if len(selected) == 3 else "FAIL", "selected_count": len(selected)},
        {"gate": "CHI-F4X-D5-HERO-FREEZE-PACKAGE", "status": freeze["status"]},
        {"gate": "CHI-F4X-D5-HERO-BRIEFINGS", "status": briefings["status"]},
        {"gate": "CHI-F4X-D5-FACE-HERO-PAYLOAD", "status": "PASS" if face_hero["status"] in {"FACE_HERO_PAYLOAD_ONLY", "FACE_HERO_PUBLISHED"} else "FAIL", "face_hero_status": face_hero["status"]},
        {"gate": "CHI-F4X-D5-SOURCE-LIMITATIONS", "status": source_report["status"]},
        {"gate": "CHI-F4X-D5-BOUNDARY-CARRY-FORWARD", "status": "PASS" if not freeze["accepted_flow_cartridge"] and freeze["review_context_only"] else "FAIL"},
        {"gate": "CHI-F4X-D5-NEXT-D6-HANDOFF", "status": "PASS" if next_d6["status"].startswith("D6_PROMOTION_REVIEW_READY") else "FAIL"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_F4X_D5_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "CHI-F4X-D5-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "CHI_F4X_D5_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "CHI-F4X-D5-NO-MUTATION", "status": mutation["status"]})

    status = "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(out / "README.md", f"# CHI-F4X-D5 Chicago Flow 4 Hero Freeze Package\n\nStatus: `{status}`\n\nHero freeze package only. Source-limited review context. D6 promotion-review candidate, not accepted.\n")
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "hero_candidates": len(candidates),
        "selected_heroes": len(selected),
        "face_hero_status": face_hero["status"],
        "gates": gates,
    }
    write_json(out / "CHI_F4X_D5_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in REQUIRED_ARTIFACTS if p != "SHA256SUMS.json")
    gates.append({"gate": "CHI-F4X-D5-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "CHI_F4X_D5_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# CHI-F4X-D5 Chicago Flow 4 Hero Freeze Package\n\nStatus: `{status}`\n\nHero freeze package only. Source-limited review context. D6 promotion-review candidate, not accepted.\n")
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    gate_map = {gate["gate"]: gate for gate in report["gates"]}
    print(f"CHI-F4X-D5 Chicago Flow 4 Hero Freeze Package: {report['status']}")
    print()
    print(f"Hero candidates: {report['hero_candidates']}")
    print(f"Selected heroes: {report['selected_heroes']}")
    print(f"Hero freeze package: {gate_map.get('CHI-F4X-D5-HERO-FREEZE-PACKAGE', {}).get('status')}")
    print(f"Hero briefings: {gate_map.get('CHI-F4X-D5-HERO-BRIEFINGS', {}).get('status')}")
    print(f"Face hero payload: {gate_map.get('CHI-F4X-D5-FACE-HERO-PAYLOAD', {}).get('face_hero_status')}")
    print()
    print(f"Source limitations: {gate_map.get('CHI-F4X-D5-SOURCE-LIMITATIONS', {}).get('status')}")
    print(f"Payload-only boundary: {gate_map.get('CHI-F4X-D5-BOUNDARY-CARRY-FORWARD', {}).get('status')}")
    print(f"Accepted-flow overclaim blocked: {gate_map.get('CHI-F4X-D5-NO-OVERCLAIM', {}).get('status')}")
    print(f"No-overclaim: {gate_map.get('CHI-F4X-D5-NO-OVERCLAIM', {}).get('status')}")
    print(f"No-mutation: {gate_map.get('CHI-F4X-D5-NO-MUTATION', {}).get('status')}")
    print(f"Hashes: {gate_map.get('CHI-F4X-D5-HASHES', {}).get('status')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F4X-D5 hero freeze package")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_chi_f4x_d5(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
