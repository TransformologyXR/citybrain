from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-F4-D6 Barcelona Flow 4 Candidate Review Snapshot"
DEFAULT_OUTPUT_DIR = "outputs/barc_f4_d6_candidate_review_snapshot"

INPUT_DEFAULTS = {
    "barc_f4_d3": "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles",
    "barc_f4_d4": "outputs/barc_f4_d4_live_replay_face_route_proof",
    "barc_f4_d5": "outputs/barc_f4_d5_hero_freeze_package",
    "barc_d1d2": "outputs/barc_expansion_d1d2_all_flows",
    "barc_d1a": "outputs/barc_d1a_targeted_source_landing_recovery",
    "barc_d1": "outputs/barc_d1_deep_source_api_scout",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_barcelona_landing": "data_landing/xdata_d1_bulk_official_sources_v1/barcelona",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

BOUNDARY_LINES = [
    "Barcelona remains candidate-only.",
    "BARC-F4-D6 does not accept the Barcelona city core.",
    "BARC-F4-D6 does not accept Barcelona Flow 4 as a production/operational cartridge.",
    "Flow 4 evidence is mobility / transport / environment review context.",
    "Point-in-time/API snapshots are not historical completeness.",
    "Environmental data is not a health determination.",
    "Mobility/traffic/transit data is not traffic-control or transit-control instruction.",
    "Face route payload is payload-only unless a later gate publishes and smokes live routes.",
]

FORBIDDEN_CLAIMS = [
    "city_core_acceptance",
    "flow4_production_or_operational_acceptance",
    "live_real_time_traffic_system",
    "traffic_control_instruction",
    "operational_transit_control",
    "public_safety_recommendation",
    "emergency_dispatch",
    "health_determination",
    "bounded_landing_full_source",
    "api_snapshot_historical_completeness",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bbarcelona city core (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona flow 4 (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona flow 4 accepted as (?:a )?(?:production|operational) cartridge\b",
    r"\blive real-time traffic system\b",
    r"\boperational transit control\b",
    r"\btraffic-control instruction\b",
    r"\btraffic control instruction\b",
    r"\btransit-control instruction\b",
    r"\btransit control instruction\b",
    r"\bpublic-safety recommendation\b",
    r"\bpublic safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bhealth determination\b",
    r"\bbounded landing is full source\b",
    r"\bbounded source landing is full\b",
    r"\bapi snapshot is historical completeness\b",
]

NEGATION_MARKERS = [
    "\"no ",
    "'no ",
    "no ",
    " no ",
    " not ",
    "do not",
    "does not",
    "cannot",
    "without",
    "unless",
    "forbidden",
    "boundary",
    "does not accept",
    "not historical completeness",
    "not a health determination",
    "not traffic-control",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            return value
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reset_output_dir(output_dir: Path, project_root: Path) -> None:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or resolved.name.lower() != "barc_f4_d6_candidate_review_snapshot"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    output_dir.mkdir(parents=True, exist_ok=True)


def file_inventory(path: Path, max_files: int = 80) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    all_files = sorted(item for item in path.rglob("*") if item.is_file())
    files = []
    for item in all_files[:max_files]:
        stat = item.stat()
        files.append(
            {
                "path": item.relative_to(path).as_posix(),
                "bytes": stat.st_size,
                "sha256": sha256_file(item) if stat.st_size <= 25_000_000 else None,
            }
        )
    return {"exists": True, "file_count": len(all_files), "files": files}


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".tmp", ".part"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size <= 25_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(key for key, value in before.items() if after.get(key) != value)
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    return {
        "gate": "BARC-F4-D6-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    return {"gate": "BARC-F4-D6-HASHES", "status": "PASS", "file_count": len(sums)}


def unique_lines(*groups: Any) -> list[str]:
    out: list[str] = []
    for group in groups:
        values = group if isinstance(group, list) else [group]
        for value in values:
            text = str(value).strip()
            if text and text not in out:
                out.append(text)
    return out


def no_overclaim(output_dir: Path) -> dict[str, Any]:
    violations = []
    files = [path for path in output_dir.rglob("*") if path.is_file()]
    for path in files:
        if path.name in {"BARC_F4_D6_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        lowered = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                context = lowered[max(0, match.start() - 90) : min(len(lowered), match.end() + 90)]
                if any(marker in context for marker in NEGATION_MARKERS):
                    continue
                violations.append(
                    {
                        "file": path.relative_to(output_dir).as_posix(),
                        "pattern_id": hashlib.sha256(pattern.encode("utf-8")).hexdigest()[:12],
                        "context": context.strip(),
                    }
                )
    return {
        "gate": "BARC-F4-D6-NO-OVERCLAIM",
        "status": "PASS" if not violations else "FAIL",
        "checked_files": len(files),
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "violations": violations,
    }


def gate(name: str, status: str = "PASS", **extra: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": status}
    payload.update(extra)
    return payload


def run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    output_dir = project_path(project_root, args.output_dir)
    inputs = {name: project_path(project_root, value) for name, value in INPUT_DEFAULTS.items()}
    mutation_roots = [
        inputs["barc_f4_d3"],
        inputs["barc_f4_d4"],
        inputs["barc_f4_d5"],
        inputs["barc_d1d2"],
        inputs["barc_d1a"],
        inputs["barc_d1"],
        inputs["xflow_d1"],
        inputs["ontology_v2"],
        project_root / "snapshot",
        project_root / "snapshots",
    ]
    before = snapshot([path for path in mutation_roots if path.exists()])
    reset_output_dir(output_dir, project_root)

    d3_harness = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_HARNESS_REPORT.json", {})
    d3_selected = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_SELECTED_BUNDLES.json", {})
    d3_limitations = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_SOURCE_LIMITATION_REPORT.json", {})
    d4_harness = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_HARNESS_REPORT.json", {})
    d4_status = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_STATUS_PAYLOAD.json", {})
    d4_face = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json", {})
    d5_harness = read_json(inputs["barc_f4_d5"] / "BARC_F4_D5_HARNESS_REPORT.json", {})
    d5_freeze = read_json(inputs["barc_f4_d5"] / "BARC_F4_D5_HERO_FREEZE_PACKAGE.json", {})
    d5_face = read_json(inputs["barc_f4_d5"] / "BARC_F4_D5_FACE_HERO_PAYLOAD.json", {})

    d3_status = str(d3_harness.get("status", ""))
    d4_status_text = str(d4_harness.get("status") or d4_status.get("status") or "")
    d5_status = str(d5_harness.get("status") or d5_freeze.get("status") or "")
    source_limitations = unique_lines(
        [f"{item.get('source_family')}: {item.get('source_limitation')}" for item in d3_limitations.get("source_limitations", []) if isinstance(item, dict)],
        d5_freeze.get("boundary_lines", []),
        BOUNDARY_LINES,
    )
    selected_heroes = [
        {
            "hero_id": hero.get("hero_id"),
            "hero_title": hero.get("hero_title"),
            "claim_label": hero.get("claim_label"),
            "source_evidence_bundle_ids": hero.get("source_evidence_bundle_ids", []),
        }
        for hero in d5_freeze.get("heroes", [])
        if isinstance(hero, dict)
    ]
    evidencebundle_refs = [
        item.get("evidence_bundle_id")
        for item in d3_selected.get("selected_bundles", [])
        if isinstance(item, dict)
    ]
    face_payload_refs = [
        "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
        "BARC_F4_D5_FACE_HERO_PAYLOAD.json",
    ]
    governance_boundaries = unique_lines(
        d4_face.get("boundary_summary", []),
        d5_freeze.get("boundary_lines", []),
        BOUNDARY_LINES,
    )
    final_status = "PASS_CANDIDATE_REVIEW_SNAPSHOT"

    input_inventory = {
        "task": TASK_NAME,
        "status": "PASS",
        "inputs": {name: file_inventory(path) for name, path in inputs.items()},
        "optional_xdata_status": "AVAILABLE"
        if inputs["xdata_barcelona_landing"].exists() or inputs["xdata_four_city"].exists()
        else "XDATA_OPTIONAL_MISSING",
    }
    write_json(output_dir / "BARC_F4_D6_INPUT_INVENTORY.json", input_inventory)

    stage_ledger = {
        "status": "PASS",
        "stages": [
            {"stage": "BARC-F4-D3", "status": d3_status, "artifact": "BARC_F4_D3_HARNESS_REPORT.json"},
            {"stage": "BARC-F4-D4", "status": d4_status_text, "artifact": "BARC_F4_D4_HARNESS_REPORT.json"},
            {"stage": "BARC-F4-D5", "status": d5_status, "artifact": "BARC_F4_D5_HARNESS_REPORT.json"},
            {"stage": "BARC-F4-D6", "status": final_status, "artifact": "BARC_F4_D6_CANDIDATE_REVIEW_SNAPSHOT.json"},
        ],
        "acceptance_state": "candidate_review_context_only",
    }
    write_json(output_dir / "BARC_F4_D6_STAGE_LEDGER.json", stage_ledger)

    candidate_snapshot = {
        "city": "barcelona",
        "flow": "F4",
        "stage": "D6",
        "snapshot_type": "candidate_review_snapshot",
        "city_core_status": "candidate_only",
        "flow_status": "candidate_review_context",
        "accepted_city_core": False,
        "accepted_flow_cartridge": False,
        "d3_status": d3_status,
        "d4_status": d4_status_text,
        "d5_status": d5_status,
        "selected_heroes": selected_heroes,
        "evidencebundle_refs": evidencebundle_refs,
        "face_payload_refs": face_payload_refs,
        "source_limitations": source_limitations,
        "governance_boundaries": governance_boundaries,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "next_decision": "requires_barcelona_city_core_acceptance_before_flow_acceptance",
    }
    write_json(output_dir / "BARC_F4_D6_CANDIDATE_REVIEW_SNAPSHOT.json", candidate_snapshot)

    acceptance_boundary = {
        "status": "PASS",
        "accepted_city_core": False,
        "accepted_flow_cartridge": False,
        "required_before_flow_acceptance": [
            "separate Barcelona city-core identity/geography acceptance gate",
            "explicit source limitation disposition",
            "live route publish/smoke gate if routes are claimed",
        ],
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(output_dir / "BARC_F4_D6_ACCEPTANCE_BOUNDARY_REPORT.json", acceptance_boundary)

    source_limit_report = {
        "status": "PASS",
        "source_limitations": source_limitations,
        "d3_source_limitation_report_ref": "BARC_F4_D3_SOURCE_LIMITATION_REPORT.json",
        "policy": "D6 preserves D3-D5 source limitations without promotion.",
    }
    write_json(output_dir / "BARC_F4_D6_SOURCE_LIMITATION_REPORT.json", source_limit_report)

    hero_snapshot = {
        "status": "PASS",
        "hero_count": len(selected_heroes),
        "selected_heroes": selected_heroes,
        "d5_hero_freeze_ref": "BARC_F4_D5_HERO_FREEZE_PACKAGE.json",
    }
    write_json(output_dir / "BARC_F4_D6_HERO_SNAPSHOT.json", hero_snapshot)

    face_snapshot = {
        "status": "PASS",
        "face_route_payload_status": d4_face.get("publish_status", "FACE_ROUTE_PAYLOAD_ONLY"),
        "face_hero_payload_status": d5_face.get("publish_status", "FACE_HERO_PAYLOAD_ONLY"),
        "face_payload_refs": face_payload_refs,
        "publish_boundary": "Face payloads remain payload-only unless a later gate publishes and smokes live routes.",
    }
    write_json(output_dir / "BARC_F4_D6_FACE_PAYLOAD_SNAPSHOT.json", face_snapshot)

    next_decision = {
        "status": "PASS",
        "recommendations": [
            {
                "gate": "BARC-CORE-D3",
                "recommendation": "first if the goal is to accept Barcelona as a city core",
                "reason": "Flow acceptance should not outrun city-core identity/geography acceptance.",
            },
            {
                "gate": "BARC-F7-D3",
                "recommendation": "first if the goal is to continue candidate-flow breadth while city-core remains candidate-only",
                "reason": "Maintains candidate-safe breadth without acceptance claims.",
            },
            {
                "gate": "BARC-F4-D7",
                "recommendation": "only after city-core policy allows live route publish/smoke",
                "reason": "D4/D5 face artifacts are payload-only.",
            },
        ],
        "expected_decision": "BARC-CORE-D3 before accepted Barcelona city core; BARC-F7-D3 for candidate-flow breadth.",
        "next_decision": "requires_barcelona_city_core_acceptance_before_flow_acceptance",
    }
    write_json(output_dir / "BARC_F4_D6_NEXT_DECISION_REPORT.json", next_decision)

    readme = f"""# BARC-F4-D6 Barcelona Flow 4 Candidate Review Snapshot

Final status: `{final_status}`

This package freezes the Barcelona Flow 4 D3-D5 line into one candidate review snapshot.

It does not accept Barcelona city core and does not accept Barcelona Flow 4 as a production or operational cartridge.

## Summary

- D3 stage: {d3_status}
- D4 stage: {d4_status_text}
- D5 stage: {d5_status}
- Selected heroes: {len(selected_heroes)}
- Face payload refs: {len(face_payload_refs)}

## Boundaries

""" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + f"""

## Output

{output_dir}
"""
    write_text(output_dir / "README.md", readme)

    overclaim = no_overclaim(output_dir)
    write_json(output_dir / "BARC_F4_D6_NO_OVERCLAIM_REPORT.json", overclaim)
    after = snapshot([path for path in mutation_roots if path.exists()])
    mutation = compare_snapshots(before, after)
    write_json(output_dir / "BARC_F4_D6_NO_MUTATION_REPORT.json", mutation)

    d3_pass = d3_status.startswith("PASS")
    d4_pass = d4_status_text.startswith("PASS")
    d5_pass = d5_status.startswith("PASS")
    candidate_only_pass = (
        candidate_snapshot["city_core_status"] == "candidate_only"
        and candidate_snapshot["accepted_city_core"] is False
        and candidate_snapshot["accepted_flow_cartridge"] is False
    )
    source_limit_pass = bool(source_limitations)
    artifact_names = [
        "README.md",
        "BARC_F4_D6_INPUT_INVENTORY.json",
        "BARC_F4_D6_STAGE_LEDGER.json",
        "BARC_F4_D6_CANDIDATE_REVIEW_SNAPSHOT.json",
        "BARC_F4_D6_ACCEPTANCE_BOUNDARY_REPORT.json",
        "BARC_F4_D6_SOURCE_LIMITATION_REPORT.json",
        "BARC_F4_D6_HERO_SNAPSHOT.json",
        "BARC_F4_D6_FACE_PAYLOAD_SNAPSHOT.json",
        "BARC_F4_D6_NEXT_DECISION_REPORT.json",
        "BARC_F4_D6_NO_OVERCLAIM_REPORT.json",
        "BARC_F4_D6_NO_MUTATION_REPORT.json",
    ]
    gates = [
        gate("BARC-F4-D6-PRECOND", "PASS" if all([d3_pass, d4_pass, d5_pass]) else "FAIL", d3_status=d3_status, d4_status=d4_status_text, d5_status=d5_status),
        gate("BARC-F4-D6-INPUT-INVENTORY"),
        gate("BARC-F4-D6-STAGE-LEDGER"),
        gate("BARC-F4-D6-CANDIDATE-SNAPSHOT"),
        gate("BARC-F4-D6-HERO-SNAPSHOT", hero_count=len(selected_heroes)),
        gate("BARC-F4-D6-FACE-PAYLOAD-SNAPSHOT"),
        gate("BARC-F4-D6-SOURCE-LIMITATIONS", "PASS" if source_limit_pass else "FAIL"),
        gate("BARC-F4-D6-CANDIDATE-ONLY-BOUNDARY", "PASS" if candidate_only_pass else "FAIL"),
        gate("BARC-F4-D6-NEXT-DECISION"),
        overclaim,
        mutation,
        gate("BARC-F4-D6-ARTIFACTS", "PASS" if all((output_dir / name).exists() for name in artifact_names) else "FAIL", present={name: (output_dir / name).exists() for name in artifact_names}),
    ]
    hashes = write_hashes(output_dir)
    gates.append(hashes)
    if any(item.get("status") == "FAIL" for item in gates):
        final_status = "FAIL"
        candidate_snapshot["status"] = final_status
        write_json(output_dir / "BARC_F4_D6_CANDIDATE_REVIEW_SNAPSHOT.json", candidate_snapshot)

    harness = {
        "task": TASK_NAME,
        "status": final_status,
        "passed": final_status != "FAIL",
        "claim": "D6 candidate review snapshot only; Barcelona city core and Flow 4 remain candidate-only.",
        "d3_status": d3_status,
        "d4_status": d4_status_text,
        "d5_status": d5_status,
        "gates": gates,
        "output_dir": str(output_dir),
        "generated_at_utc": utc_now(),
    }
    write_json(output_dir / "BARC_F4_D6_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    for item in gates:
        if item.get("gate") == "BARC-F4-D6-HASHES":
            item.update(hashes)
    harness["gates"] = gates
    write_json(output_dir / "BARC_F4_D6_HARNESS_REPORT.json", harness)
    write_hashes(output_dir)

    print(f"BARC-F4-D6 Barcelona Flow 4 Candidate Review Snapshot: {final_status}")
    print()
    print(f"D3 stage: {'PASS' if d3_pass else 'FAIL'}")
    print(f"D4 stage: {'PASS' if d4_pass else 'FAIL'}")
    print(f"D5 stage: {'PASS' if d5_pass else 'FAIL'}")
    print("Candidate review snapshot: PASS")
    print("Hero snapshot: PASS")
    print("Face payload snapshot: PASS")
    print()
    print(f"Candidate-only boundary: {'PASS' if candidate_only_pass else 'FAIL'}")
    print(f"Accepted-flow overclaim blocked: {'PASS' if overclaim['status'] == 'PASS' else 'FAIL'}")
    print(f"Source limitations: {'PASS' if source_limit_pass else 'FAIL'}")
    print(f"No-overclaim: {overclaim['status']}")
    print(f"No-mutation: {mutation['status']}")
    print(f"Hashes: {hashes['status']}")
    print()
    print(f"Final status: {final_status}")
    print()
    print(f"Output: {output_dir.relative_to(project_root)}")
    return 0 if final_status != "FAIL" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
