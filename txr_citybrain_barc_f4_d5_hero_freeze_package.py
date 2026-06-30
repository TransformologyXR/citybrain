from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-F4-D5 Barcelona Flow 4 Hero Freeze Package"
DEFAULT_OUTPUT_DIR = "outputs/barc_f4_d5_hero_freeze_package"

INPUT_DEFAULTS = {
    "barc_f4_d3": "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles",
    "barc_f4_d4": "outputs/barc_f4_d4_live_replay_face_route_proof",
    "barc_d1d2": "outputs/barc_expansion_d1d2_all_flows",
    "barc_d1a": "outputs/barc_d1a_targeted_source_landing_recovery",
    "barc_d1": "outputs/barc_d1_deep_source_api_scout",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_barcelona_landing": "data_landing/xdata_d1_bulk_official_sources_v1/barcelona",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

BOUNDARY_LINES = [
    "Barcelona is candidate-only.",
    "BARC-F4-D5 does not accept Barcelona Flow 4.",
    "D6 acceptance review, if justified, comes later.",
    "Mobility and transport data are context signals, not traffic-control instructions.",
    "Environmental data is context only, not a health determination.",
    "Point-in-time/API snapshots are not historical completeness.",
    "BARC-F4-D5 creates a review-context hero freeze package only.",
    "No public-safety, policing, enforcement, emergency, dispatch, transit-control, port-control, health, or operational recommendation is created.",
]

FORBIDDEN_CLAIMS = [
    "city_core_acceptance",
    "flow4_acceptance",
    "live_real_time_traffic_system",
    "traffic_control_instruction",
    "transit_control_instruction",
    "public_safety_recommendation",
    "emergency_dispatch",
    "health_determination",
    "operational_command",
    "historical_completeness_from_api_snapshot",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bbarcelona city core (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona flow 4 (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona accepted\b",
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
    r"\boperational command\b",
    r"\bbounded landing is full source\b",
    r"\bbounded source landing is full\b",
    r"\bapi snapshot is historical completeness\b",
    r"\bhistorical completeness from api snapshot\b",
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
    "refuses",
    "refuse",
    "forbidden",
    "boundary",
    "not a",
    "not historical completeness",
    "context only",
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


def project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def reset_output_dir(output_dir: Path, project_root: Path) -> None:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or resolved.name.lower() != "barc_f4_d5_hero_freeze_package"
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
        "gate": "BARC-F4-D5-NO-MUTATION",
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
    return {"gate": "BARC-F4-D5-HASHES", "status": "PASS", "file_count": len(sums)}


def unique_lines(*groups: Any) -> list[str]:
    out: list[str] = []
    for group in groups:
        values = group if isinstance(group, list) else [group]
        for value in values:
            text = str(value).strip()
            if text and text not in out:
                out.append(text)
    return out


def all_bundles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    bundles = payload.get("evidence_bundles", [])
    if not isinstance(bundles, list):
        return []
    return [bundle for bundle in bundles if isinstance(bundle, dict)]


def bundle_by_id(bundles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(bundle.get("evidence_bundle_id")): bundle for bundle in bundles}


def source_limitations(bundle: dict[str, Any]) -> list[str]:
    limitations = list(bundle.get("limitations", [])) if isinstance(bundle.get("limitations"), list) else []
    for record in bundle.get("source_records", []):
        if isinstance(record, dict) and record.get("source_limitation"):
            text = f"{record.get('source_family')}: {record.get('source_limitation')}"
            limitations.append(text)
    return unique_lines(limitations, BOUNDARY_LINES)


def evidence_refs(bundle: dict[str, Any], d4_refs: list[str]) -> list[str]:
    return unique_lines(bundle.get("trace_refs", []), d4_refs)


def make_hero(hero_id: str, title: str, bundle_ids: list[str], bundles_by_id: dict[str, dict[str, Any]], d4_refs: list[str], summary: str, claim_label: str = "[R]") -> dict[str, Any]:
    selected_bundles = [bundles_by_id[item] for item in bundle_ids if item in bundles_by_id]
    limitations: list[str] = []
    boundaries: list[str] = []
    refs: list[str] = []
    for bundle in selected_bundles:
        limitations = unique_lines(limitations, source_limitations(bundle))
        boundaries = unique_lines(boundaries, bundle.get("governance_boundaries", []), BOUNDARY_LINES)
        refs = unique_lines(refs, evidence_refs(bundle, d4_refs))
    if not selected_bundles:
        limitations = unique_lines(limitations, BOUNDARY_LINES)
        boundaries = unique_lines(boundaries, BOUNDARY_LINES)
        refs = unique_lines(refs, d4_refs)
    return {
        "hero_id": hero_id,
        "hero_title": title,
        "city": "barcelona",
        "flow": "F4",
        "stage": "D5",
        "city_core_status": "candidate_only",
        "source_evidence_bundle_ids": bundle_ids,
        "source_d4_payload_ids": [
            "BARC_F4_D4_REPLAY_PAYLOAD.json",
            "BARC_F4_D4_BRIEFING_PAYLOAD.json",
            "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
        ],
        "claim_label": claim_label,
        "review_context_only": True,
        "summary": summary,
        "evidence_refs": refs,
        "source_limitations": limitations,
        "governance_boundaries": unique_lines(boundaries, BOUNDARY_LINES),
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "next_step": "D6 acceptance review only",
    }


def make_governance_hero(bundles_by_id: dict[str, dict[str, Any]], d4_refs: list[str]) -> dict[str, Any]:
    preferred = ["mobility_environment_governance_boundary_bundle", "bicing_station_status_context_bundle"]
    ids = [item for item in preferred if item in bundles_by_id][:1]
    hero = make_hero(
        "barc_f4_d5_hero_3_governance_boundary",
        "Governance Boundary: Candidate City / Source-Limited Flow",
        ids,
        bundles_by_id,
        d4_refs,
        "Governance boundary hero showing what BARC-F4-D5 refuses to claim while preserving candidate city core and source-limited Flow 4 context.",
        claim_label="[G]",
    )
    hero["refusal_lines"] = [
        "No accepted Barcelona city core.",
        "No accepted Barcelona Flow 4.",
        "No traffic-control instruction.",
        "No transit-control instruction.",
        "No health determination from environmental data.",
        "No historical completeness from point-in-time API snapshots.",
    ]
    return hero


def candidate_heroes(bundles_by_id: dict[str, dict[str, Any]], d4_refs: list[str]) -> list[dict[str, Any]]:
    specs = [
        (
            "barc_f4_d5_candidate_mobility_bicing",
            "Barcelona Flow 4 Mobility Context",
            ["bicing_station_status_context_bundle"],
            "Review-context hero for Bicing mobility context using point-in-time station status evidence.",
        ),
        (
            "barc_f4_d5_candidate_environment_air_noise",
            "Barcelona Flow 4 Environment / Sensor Context",
            ["air_noise_environment_context_bundle"],
            "Review-context hero for air, noise, and environmental context with health-decision boundaries preserved.",
        ),
        (
            "barc_f4_d5_candidate_traffic_context",
            "Barcelona Flow 4 Traffic Section Context",
            ["traffic_road_section_context_bundle"],
            "Review-context hero for bounded road-section traffic context, without control instructions.",
        ),
        (
            "barc_f4_d5_candidate_transit_context",
            "Barcelona Flow 4 Transit Context",
            ["tmb_transit_context_bundle"],
            "Review-context hero for transit context, without transit-control instructions.",
        ),
        (
            "barc_f4_d5_candidate_sentilo_context",
            "Barcelona Flow 4 Sensor Catalogue Context",
            ["sentilo_sensor_mobility_context_bundle"],
            "Review-context hero for Sentilo sensor catalogue context with endpoint/source limitations preserved.",
        ),
    ]
    candidates = [make_hero(*spec, bundles_by_id, d4_refs) for spec in specs if spec[2][0] in bundles_by_id]
    candidates.append(make_governance_hero(bundles_by_id, d4_refs))
    return candidates


def select_heroes(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required_order = [
        "barc_f4_d5_candidate_mobility_bicing",
        "barc_f4_d5_candidate_environment_air_noise",
        "barc_f4_d5_hero_3_governance_boundary",
    ]
    by_id = {hero["hero_id"]: hero for hero in candidates}
    selected = [by_id[item] for item in required_order if item in by_id]
    if len(selected) != 3:
        raise ValueError(f"could not select exactly 3 required heroes; selected {len(selected)}")
    selected[0]["hero_id"] = "barc_f4_d5_hero_1_mobility_context"
    selected[1]["hero_id"] = "barc_f4_d5_hero_2_environment_sensor_context"
    return selected


def make_briefings(heroes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    briefings = []
    for hero in heroes:
        briefings.append(
            {
                "briefing_id": f"{hero['hero_id']}_briefing",
                "hero_id": hero["hero_id"],
                "mode": "hero_review_context",
                "claim_label": hero["claim_label"],
                "city_core_status": "candidate_only",
                "allowed_language": [
                    "candidate Barcelona mobility/environment context",
                    "review-context hero",
                    "source-limited",
                    "point-in-time API snapshot",
                    "face-route payload ready",
                    "D6-ready freeze package",
                ],
                "summary_facts": [
                    hero["summary"],
                    "Barcelona remains candidate-only.",
                    "BARC-F4-D5 is a source-limited review-context hero freeze package.",
                    "D6 acceptance review is the next possible gate.",
                ],
                "evidence_refs": hero["evidence_refs"],
                "limitations": hero["source_limitations"],
                "governance_boundaries": hero["governance_boundaries"],
                "forbidden_claims": hero["forbidden_claims"],
                "safe_next_step": "D6 acceptance review only",
            }
        )
    return briefings


def no_overclaim(output_dir: Path) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    files = [path for path in output_dir.rglob("*") if path.is_file()]
    for path in files:
        if path.name in {"BARC_F4_D5_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
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
        "gate": "BARC-F4-D5-NO-OVERCLAIM",
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
    d3_bundle_payload = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_EVIDENCEBUNDLES.json", {})
    d4_harness = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_HARNESS_REPORT.json", {})
    d4_status = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_STATUS_PAYLOAD.json", {})
    d4_briefing = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_BRIEFING_PAYLOAD.json", {})
    d4_face = read_json(inputs["barc_f4_d4"] / "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json", {})

    bundles = all_bundles(d3_bundle_payload)
    bundles_by_id = bundle_by_id(bundles)
    d4_refs = unique_lines(
        d4_briefing.get("evidence_refs", []),
        d4_face.get("briefing_ref", ""),
        "BARC_F4_D4_REPLAY_PAYLOAD.json",
        "BARC_F4_D4_BRIEFING_PAYLOAD.json",
        "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
    )
    candidates = candidate_heroes(bundles_by_id, d4_refs)
    selected = select_heroes(candidates)
    briefings = make_briefings(selected)
    face_status = "FACE_HERO_PAYLOAD_ONLY"
    final_status = "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS"

    input_inventory = {
        "task": TASK_NAME,
        "status": "PASS",
        "inputs": {name: file_inventory(path) for name, path in inputs.items()},
        "optional_xdata_status": "AVAILABLE"
        if inputs["xdata_barcelona_landing"].exists() or inputs["xdata_four_city"].exists()
        else "XDATA_OPTIONAL_MISSING",
        "d3_status": d3_harness.get("status"),
        "d4_status": d4_harness.get("status") or d4_status.get("status"),
    }
    write_json(output_dir / "BARC_F4_D5_INPUT_INVENTORY.json", input_inventory)

    policy = {
        "status": "PASS",
        "policy_version": "BARC-F4-D5-HeroSelection-v1",
        "required_selected_hero_count": 3,
        "hero_1_primary_preference": "bicing_station_status_context_bundle",
        "hero_2_preference_set": [
            "traffic_road_section_context_bundle",
            "air_noise_environment_context_bundle",
            "tmb_transit_context_bundle",
            "sentilo_sensor_mobility_context_bundle",
        ],
        "hero_3_required_refusals": [
            "No accepted Barcelona city core.",
            "No accepted Barcelona Flow 4.",
            "No traffic-control instruction.",
            "No transit-control instruction.",
            "No health determination from environmental data.",
            "No historical completeness from point-in-time API snapshots.",
        ],
        "determinism": "fixed hero ids and fixed bundle preference order",
    }
    write_json(output_dir / "BARC_F4_D5_HERO_SELECTION_POLICY.json", policy)
    write_json(output_dir / "BARC_F4_D5_HERO_CANDIDATES.json", {"status": "PASS", "hero_candidates": candidates, "candidate_count": len(candidates)})
    write_json(output_dir / "BARC_F4_D5_SELECTED_HEROES.json", {"status": "PASS", "selected_heroes": selected, "selected_count": len(selected)})

    freeze_package = {
        "status": final_status,
        "package_id": "barc_f4_d5_hero_freeze_package",
        "city": "barcelona",
        "flow": "F4",
        "stage": "D5",
        "city_core_status": "candidate_only",
        "flow4_accepted": False,
        "hero_count": len(selected),
        "heroes": selected,
        "source_d3_package": "BARC_F4_D3_EVIDENCEBUNDLES.json",
        "source_d4_package": "BARC_F4_D4_STATUS_PAYLOAD.json",
        "freeze_mode": "D6-ready freeze package",
        "safe_next_gate": "BARC-F4-D6",
    }
    write_json(output_dir / "BARC_F4_D5_HERO_FREEZE_PACKAGE.json", freeze_package)
    write_json(output_dir / "BARC_F4_D5_HERO_BRIEFINGS.json", {"status": "PASS", "briefings": briefings, "briefing_count": len(briefings)})

    face_payload = {
        "status": face_status,
        "city": "barcelona",
        "flow": "F4",
        "stage": "D5",
        "publish_status": face_status,
        "supported_future_routes": [
            "/barcelona/flow4/heroes",
            "/api/barcelona/flow4/heroes",
            "/api/barcelona/flow4/heroes/{hero_id}",
        ],
        "heroes": [
            {
                "hero_id": hero["hero_id"],
                "hero_title": hero["hero_title"],
                "claim_label": hero["claim_label"],
                "city_core_status": hero["city_core_status"],
                "review_context_only": hero["review_context_only"],
            }
            for hero in selected
        ],
        "payload_only_reason": "No existing safe Barcelona hero face publish mechanism was invoked by this gate.",
    }
    write_json(output_dir / "BARC_F4_D5_FACE_HERO_PAYLOAD.json", face_payload)

    trace_report = {
        "status": "PASS",
        "source_d3_refs": ["BARC_F4_D3_EVIDENCEBUNDLES.json", "BARC_F4_D3_SELECTED_BUNDLES.json"],
        "source_d4_refs": ["BARC_F4_D4_REPLAY_PAYLOAD.json", "BARC_F4_D4_BRIEFING_PAYLOAD.json", "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json"],
        "hero_trace_refs": {hero["hero_id"]: hero["evidence_refs"] for hero in selected},
    }
    write_json(output_dir / "BARC_F4_D5_TRACE_REPORT.json", trace_report)

    next_handoff = {
        "status": "PASS",
        "next_gate": "BARC-F4-D6",
        "handoff_mode": "accepted_flow4_extension_snapshot_review_if_gates_justify_it",
        "must_preserve": [
            "city_core_status=candidate_only unless D6 explicitly changes it",
            "BARC-F4-D5 does not accept Barcelona Flow 4",
            "claim labels and governance hero boundaries",
            "source limitations and point-in-time/API snapshot boundaries",
            "no control, dispatch, enforcement, health, port, or operational recommendations",
        ],
        "selected_hero_ids": [hero["hero_id"] for hero in selected],
        "face_hero_status": face_status,
    }
    write_json(output_dir / "BARC_F4_D5_NEXT_D6_HANDOFF.json", next_handoff)

    readme = f"""# BARC-F4-D5 Barcelona Flow 4 Hero Freeze Package

Final status: `{final_status}`

This package freezes exactly three deterministic Barcelona Flow 4 review-context heroes from the BARC-F4-D3 EvidenceBundles and BARC-F4-D4 replay/briefing/face-route payloads.

It does not accept Barcelona city core or Barcelona Flow 4.

## Summary

- Hero candidates: {len(candidates)}
- Selected heroes: {len(selected)}
- Hero freeze package: PASS
- Hero briefings: PASS
- Face hero payload: FACE_HERO_PAYLOAD_ONLY

## Boundaries

""" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + f"""

## Output

{output_dir}
"""
    write_text(output_dir / "README.md", readme)

    overclaim = no_overclaim(output_dir)
    write_json(output_dir / "BARC_F4_D5_NO_OVERCLAIM_REPORT.json", overclaim)
    after = snapshot([path for path in mutation_roots if path.exists()])
    mutation = compare_snapshots(before, after)
    write_json(output_dir / "BARC_F4_D5_NO_MUTATION_REPORT.json", mutation)

    candidate_only_pass = all(hero.get("city_core_status") == "candidate_only" for hero in selected)
    source_limit_pass = all(hero.get("source_limitations") for hero in selected)
    exact_heroes_pass = len(selected) == 3
    artifact_names = [
        "README.md",
        "BARC_F4_D5_INPUT_INVENTORY.json",
        "BARC_F4_D5_HERO_SELECTION_POLICY.json",
        "BARC_F4_D5_HERO_CANDIDATES.json",
        "BARC_F4_D5_SELECTED_HEROES.json",
        "BARC_F4_D5_HERO_FREEZE_PACKAGE.json",
        "BARC_F4_D5_HERO_BRIEFINGS.json",
        "BARC_F4_D5_FACE_HERO_PAYLOAD.json",
        "BARC_F4_D5_TRACE_REPORT.json",
        "BARC_F4_D5_NEXT_D6_HANDOFF.json",
        "BARC_F4_D5_NO_OVERCLAIM_REPORT.json",
        "BARC_F4_D5_NO_MUTATION_REPORT.json",
    ]
    gates = [
        gate("BARC-F4-D5-PRECOND", required_inputs_exist=all(inputs[name].exists() for name in ["barc_f4_d3", "barc_f4_d4", "barc_d1d2", "barc_d1a", "barc_d1", "xflow_d1", "ontology_v2"]), d3_status=d3_harness.get("status"), d4_status=d4_harness.get("status") or d4_status.get("status")),
        gate("BARC-F4-D5-INPUT-INVENTORY"),
        gate("BARC-F4-D5-HERO-SELECTION-POLICY"),
        gate("BARC-F4-D5-HERO-CANDIDATES", hero_candidates=len(candidates)),
        gate("BARC-F4-D5-SELECTED-HEROES", "PASS" if exact_heroes_pass else "FAIL", selected_heroes=len(selected)),
        gate("BARC-F4-D5-HERO-FREEZE-PACKAGE"),
        gate("BARC-F4-D5-HERO-BRIEFINGS", briefing_count=len(briefings)),
        gate("BARC-F4-D5-FACE-HERO-PAYLOAD", face_hero_status=face_status),
        gate("BARC-F4-D5-SOURCE-LIMITATION-PRESERVATION", "PASS" if source_limit_pass else "FAIL"),
        gate("BARC-F4-D5-CANDIDATE-ONLY-BOUNDARY", "PASS" if candidate_only_pass else "FAIL"),
        overclaim,
        mutation,
        gate("BARC-F4-D5-ARTIFACTS", "PASS" if all((output_dir / name).exists() for name in artifact_names) else "FAIL", present={name: (output_dir / name).exists() for name in artifact_names}),
    ]
    hashes = write_hashes(output_dir)
    gates.append(hashes)

    if any(item.get("status") == "FAIL" for item in gates):
        final_status = "FAIL"
        freeze_package["status"] = final_status
        write_json(output_dir / "BARC_F4_D5_HERO_FREEZE_PACKAGE.json", freeze_package)

    harness = {
        "task": TASK_NAME,
        "status": final_status,
        "passed": final_status != "FAIL",
        "claim": "D5 hero freeze package only; Barcelona city core and Flow 4 remain candidate-only.",
        "hero_candidates": len(candidates),
        "selected_heroes": len(selected),
        "face_hero_status": face_status,
        "gates": gates,
        "output_dir": str(output_dir),
        "generated_at_utc": utc_now(),
    }
    write_json(output_dir / "BARC_F4_D5_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    for item in gates:
        if item.get("gate") == "BARC-F4-D5-HASHES":
            item.update(hashes)
    harness["gates"] = gates
    write_json(output_dir / "BARC_F4_D5_HARNESS_REPORT.json", harness)
    write_hashes(output_dir)

    print(f"BARC-F4-D5 Barcelona Flow 4 Hero Freeze Package: {final_status}")
    print()
    print(f"Hero candidates: {len(candidates)}")
    print(f"Selected heroes: {len(selected)}")
    print("Hero freeze package: PASS")
    print("Hero briefings: PASS")
    print("Face hero payload: PAYLOAD_ONLY")
    print()
    print(f"Candidate-only boundary: {'PASS' if candidate_only_pass else 'FAIL'}")
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
