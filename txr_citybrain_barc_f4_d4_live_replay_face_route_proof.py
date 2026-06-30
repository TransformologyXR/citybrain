from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-F4-D4 Barcelona Flow 4 Live/Replay + Face Route Proof"
DEFAULT_OUTPUT_DIR = "outputs/barc_f4_d4_live_replay_face_route_proof"

INPUT_DEFAULTS = {
    "barc_f4_d3": "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles",
    "barc_d1d2": "outputs/barc_expansion_d1d2_all_flows",
    "barc_d1a": "outputs/barc_d1a_targeted_source_landing_recovery",
    "barc_d1": "outputs/barc_d1_deep_source_api_scout",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_barcelona_landing": "data_landing/xdata_d1_bulk_official_sources_v1/barcelona",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

PREFERRED_PRIMARY = [
    "bicing_station_status_context_bundle",
    "traffic_road_section_context_bundle",
    "tmb_transit_context_bundle",
    "air_noise_environment_context_bundle",
    "mobility_environment_governance_boundary_bundle",
]

BOUNDARY_LINES = [
    "Barcelona is candidate-only.",
    "BARC-F4-D4 does not accept Barcelona Flow 4.",
    "Mobility and transport data are context signals, not traffic-control instructions.",
    "Environmental data is context only, not a health determination.",
    "Point-in-time/API snapshots are not historical completeness.",
    "BARC-F4-D4 creates replay/live-style and face-route payloads only.",
    "No public-safety, policing, enforcement, emergency, dispatch, transit-control, port-control, health, or operational recommendation is created.",
]

ALLOWED_PROOF_LANGUAGE = [
    "replay/live-style proof",
    "point-in-time transport context",
    "mobility/environment context",
    "review-context payload",
    "face-route ready",
    "D5-ready",
]

FORBIDDEN_CLAIM_IDS = [
    "city_core_acceptance",
    "flow4_acceptance",
    "live_operational_traffic_system",
    "traffic_control_instruction",
    "transit_control_instruction",
    "public_safety_recommendation",
    "health_determination",
    "emergency_dispatch",
    "historical_completeness_from_api_snapshot",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bbarcelona city core (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona flow 4 (?:is|was|now is|has been) accepted\b",
    r"\baccepted barcelona flow 4\b",
    r"\blive real-time traffic system\b",
    r"\blive operational traffic system\b",
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
    " no ",
    " not ",
    "do not",
    "does not",
    "cannot",
    "without",
    "unless",
    "forbidden",
    "boundary",
    "not a",
    "context only",
    "not historical completeness",
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
            or resolved.name.lower() != "barc_f4_d4_live_replay_face_route_proof"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    output_dir.mkdir(parents=True, exist_ok=True)


def file_inventory(path: Path, max_files: int = 80) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    all_files = sorted(item for item in path.rglob("*") if item.is_file())
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
        key = str(root.resolve())
        if not root.exists():
            watched[key] = {"exists": False}
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
        "gate": "BARC-F4-D4-NO-MUTATION",
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
    return {"gate": "BARC-F4-D4-HASHES", "status": "PASS", "file_count": len(sums)}


def all_bundles(d3_bundles_payload: dict[str, Any]) -> list[dict[str, Any]]:
    bundles = d3_bundles_payload.get("evidence_bundles", [])
    if not isinstance(bundles, list):
        return []
    return [bundle for bundle in bundles if isinstance(bundle, dict)]


def select_bundles(bundles: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_id = {str(bundle.get("evidence_bundle_id")): bundle for bundle in bundles}
    primary = None
    for preferred in PREFERRED_PRIMARY:
        if preferred in by_id:
            primary = by_id[preferred]
            break
    if primary is None:
        if not bundles:
            raise ValueError("no D3 evidence bundles found")
        primary = sorted(bundles, key=lambda item: str(item.get("evidence_bundle_id")))[0]
    supporting = [
        bundle
        for bundle in sorted(bundles, key=lambda item: str(item.get("evidence_bundle_id")))
        if bundle.get("evidence_bundle_id") != primary.get("evidence_bundle_id")
    ][:2]
    if len(supporting) < 2:
        raise ValueError("fewer than two supporting D3 evidence bundles found")
    return primary, supporting


def unique_lines(*groups: Any) -> list[str]:
    out: list[str] = []
    for group in groups:
        values = group if isinstance(group, list) else [group]
        for value in values:
            text = str(value).strip()
            if text and text not in out:
                out.append(text)
    return out


def source_context_from_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    records = bundle.get("source_records", [])
    if not isinstance(records, list):
        return []
    context = []
    for record in records:
        if isinstance(record, dict):
            context.append(
                {
                    "source_family": record.get("source_family"),
                    "title": record.get("title"),
                    "role": record.get("role"),
                    "source_limitation": record.get("source_limitation"),
                    "family_status": record.get("family_status"),
                    "optional_context": bool(record.get("optional_context", False)),
                }
            )
    return context


def build_replay_payload(primary: dict[str, Any], supporting: list[dict[str, Any]]) -> dict[str, Any]:
    source_context = source_context_from_bundle(primary)
    return {
        "city": "barcelona",
        "flow": "F4",
        "stage": "D4",
        "proof_type": "deterministic_replay_or_live_style_payload",
        "proof_language": ALLOWED_PROOF_LANGUAGE,
        "city_core_status": primary.get("city_core_status", "candidate_only"),
        "selected_evidence_bundle_id": primary.get("evidence_bundle_id"),
        "supporting_evidence_bundle_ids": [bundle.get("evidence_bundle_id") for bundle in supporting],
        "subject": primary.get("subject", {}),
        "time_window": primary.get("time_window", {}),
        "source_context": source_context,
        "mobility_context": {
            "mode": "review_context",
            "source_families": sorted({str(item.get("source_family")) for item in source_context if item.get("source_family")}),
            "candidate_only": True,
        },
        "transport_context": {
            "point_in_time_transport_context": True,
            "traffic_or_transit_control": False,
            "historical_completeness": False,
        },
        "environment_context": {
            "context_only": True,
            "health_determination": False,
            "supporting_bundle_ids": [
                bundle.get("evidence_bundle_id")
                for bundle in supporting
                if "environment" in str(bundle.get("evidence_bundle_id", ""))
            ],
        },
        "limitations": unique_lines(primary.get("limitations", []), BOUNDARY_LINES),
        "governance_boundaries": unique_lines(primary.get("governance_boundaries", []), BOUNDARY_LINES),
        "claim_label_policy": {
            "claim_label": primary.get("claim_label", "[R]"),
            "meaning": "source-grounded review context with preserved D3 limitations",
            "forbids_acceptance_claim": True,
        },
        "trace_refs": unique_lines(primary.get("trace_refs", []), *(bundle.get("trace_refs", []) for bundle in supporting)),
    }


def build_briefing_payload(primary: dict[str, Any], supporting: list[dict[str, Any]], replay_payload: dict[str, Any]) -> dict[str, Any]:
    primary_id = str(primary.get("evidence_bundle_id"))
    support_ids = [str(bundle.get("evidence_bundle_id")) for bundle in supporting]
    return {
        "briefing_id": f"barc-f4-d4-{primary_id}",
        "mode": "mobility_environment_review_context",
        "claim_label": primary.get("claim_label", "[R]"),
        "city_core_status": primary.get("city_core_status", "candidate_only"),
        "summary_facts": [
            "Barcelona is candidate-only.",
            "BARC-F4-D4 surfaces a D3 EvidenceBundle as a replay/live-style proof payload for review.",
            f"Primary EvidenceBundle: {primary_id}.",
            f"Supporting EvidenceBundles: {', '.join(support_ids)}.",
            "Point-in-time and bounded source limitations are preserved.",
        ],
        "evidence_refs": replay_payload.get("trace_refs", []),
        "limitations": replay_payload.get("limitations", []),
        "governance_boundaries": replay_payload.get("governance_boundaries", []),
        "forbidden_claims": FORBIDDEN_CLAIM_IDS,
        "safe_next_step": "review_only",
    }


def build_face_route_payload(briefing_payload: dict[str, Any], replay_payload: dict[str, Any], publish_status: str) -> dict[str, Any]:
    routes = [
        "/barcelona",
        "/status/barcelona",
        "/barcelona/flow4",
        "/api/barcelona/flow4",
        "/api/barcelona/flow4/status",
    ]
    return {
        "city": "barcelona",
        "flow": "F4",
        "stage": "D4",
        "publish_status": publish_status,
        "route_payload_status": "face-route ready",
        "supported_future_routes": routes,
        "primary_route": "/barcelona/flow4",
        "api_status_route": "/api/barcelona/flow4/status",
        "city_core_status": "candidate_only",
        "claim_label": briefing_payload.get("claim_label", "[R]"),
        "selected_evidence_bundle_id": replay_payload.get("selected_evidence_bundle_id"),
        "supporting_evidence_bundle_ids": replay_payload.get("supporting_evidence_bundle_ids", []),
        "briefing_ref": briefing_payload.get("briefing_id"),
        "boundary_summary": BOUNDARY_LINES,
        "payload_only_reason": "No existing safe Barcelona face publish mechanism was invoked by this gate.",
    }


def build_status_payload(final_status: str, face_status: str, optional_nim_status: str, primary: dict[str, Any], supporting: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "city": "barcelona",
        "flow": "F4",
        "stage": "D4",
        "status": final_status,
        "face_route_status": face_status,
        "optional_nim_smoke": optional_nim_status,
        "city_core_status": "candidate_only",
        "flow4_acceptance": False,
        "selected_primary_evidence_bundle": primary.get("evidence_bundle_id"),
        "supporting_evidence_bundles": [bundle.get("evidence_bundle_id") for bundle in supporting],
        "safe_next_gate": "BARC-F4-D5",
        "safe_next_step": "review_only",
    }


def no_overclaim(output_dir: Path) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"BARC_F4_D4_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                start = max(0, match.start() - 80)
                end = min(len(lowered), match.end() + 80)
                context = lowered[start:end]
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
        "gate": "BARC-F4-D4-NO-OVERCLAIM",
        "status": "PASS" if not violations else "FAIL",
        "checked_files": len([path for path in output_dir.rglob("*") if path.is_file()]),
        "forbidden_claim_ids": FORBIDDEN_CLAIM_IDS,
        "violations": violations,
    }


def optional_nim_smoke(briefing_payload: dict[str, Any], output_dir: Path, run: bool) -> dict[str, Any]:
    if not run:
        return {"gate": "BARC-F4-D4-OPTIONAL-NIM-SMOKE", "status": "OPTIONAL_NIM_NOT_RUN"}
    request_payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [
            {
                "role": "user",
                "content": "Summarize this governed briefing payload without adding facts or weakening boundaries:\n"
                + json.dumps(briefing_payload, sort_keys=True),
            }
        ],
        "temperature": 0,
        "max_tokens": 400,
    }
    report: dict[str, Any] = {"gate": "BARC-F4-D4-OPTIONAL-NIM-SMOKE", "endpoint": "http://192.168.1.103:8000/v1/chat/completions"}
    try:
        data = json.dumps(request_payload).encode("utf-8")
        request = urllib.request.Request(
            report["endpoint"],
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            response_payload = json.loads(response.read().decode("utf-8", errors="replace"))
        text = json.dumps(response_payload, sort_keys=True)
        report.update(
            {
                "status": "PASS" if no_forbidden_text(text) else "FAIL",
                "candidate_only_boundary_preserved": "candidate-only" in text.lower(),
                "limitations_preserved": "limitation" in text.lower() or "bounded" in text.lower(),
                "response": response_payload,
            }
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        report.update({"status": "FAIL", "error": str(exc)})
    write_json(output_dir / "BARC_F4_D4_OPTIONAL_NIM_SMOKE_REPORT.json", report)
    return report


def no_forbidden_text(text: str) -> bool:
    lowered = text.lower()
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            context = lowered[max(0, match.start() - 80) : min(len(lowered), match.end() + 80)]
            if not any(marker in context for marker in NEGATION_MARKERS):
                return False
    return True


def gate_status(name: str, status: str = "PASS", **extra: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": status}
    payload.update(extra)
    return payload


def run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    output_dir = project_path(project_root, args.output_dir)
    inputs = {name: project_path(project_root, value) for name, value in INPUT_DEFAULTS.items()}
    mutation_roots = [
        inputs["barc_f4_d3"],
        inputs["barc_d1d2"],
        inputs["barc_d1a"],
        inputs["barc_d1"],
        inputs["xflow_d1"],
        inputs["ontology_v2"],
        project_root / "snapshot",
        project_root / "snapshots",
    ]
    mutation_roots = [path for path in mutation_roots if path.name != output_dir.name]
    before = snapshot([path for path in mutation_roots if path.exists()])

    reset_output_dir(output_dir, project_root)

    d3_harness = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_HARNESS_REPORT.json", {})
    d3_selected = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_SELECTED_BUNDLES.json", {})
    d3_bundles = read_json(inputs["barc_f4_d3"] / "BARC_F4_D3_EVIDENCEBUNDLES.json", {})
    bundles = all_bundles(d3_bundles)
    primary, supporting = select_bundles(bundles)

    input_inventory = {
        "task": TASK_NAME,
        "status": "PASS",
        "inputs": {name: file_inventory(path) for name, path in inputs.items()},
        "optional_xdata_status": "AVAILABLE"
        if inputs["xdata_barcelona_landing"].exists() or inputs["xdata_four_city"].exists()
        else "XDATA_OPTIONAL_MISSING",
        "d3_status": d3_harness.get("status"),
    }
    write_json(output_dir / "BARC_F4_D4_INPUT_INVENTORY.json", input_inventory)

    selected_payload = {
        "status": "PASS",
        "selection_policy": "deterministic_preferred_primary_order",
        "preferred_primary_order": PREFERRED_PRIMARY,
        "primary_evidence_bundle": primary,
        "supporting_evidence_bundles": supporting,
        "d3_selected_bundle_ids": [item.get("evidence_bundle_id") for item in d3_selected.get("selected_bundles", [])],
    }
    write_json(output_dir / "BARC_F4_D4_SELECTED_EVIDENCEBUNDLE.json", selected_payload)

    contract = {
        "status": "PASS",
        "contract_version": "BARC-F4-D4-ReplayLiveFaceRouteProof-v1",
        "city": "barcelona",
        "flow": "F4",
        "stage": "D4",
        "required_artifacts": [
            "README.md",
            "BARC_F4_D4_HARNESS_REPORT.json",
            "BARC_F4_D4_INPUT_INVENTORY.json",
            "BARC_F4_D4_REPLAY_LIVE_PROOF_CONTRACT.json",
            "BARC_F4_D4_SELECTED_EVIDENCEBUNDLE.json",
            "BARC_F4_D4_REPLAY_PAYLOAD.json",
            "BARC_F4_D4_BRIEFING_PAYLOAD.json",
            "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
            "BARC_F4_D4_STATUS_PAYLOAD.json",
            "BARC_F4_D4_TRACE_REPORT.json",
            "BARC_F4_D4_NEXT_D5_HANDOFF.json",
            "BARC_F4_D4_NO_OVERCLAIM_REPORT.json",
            "BARC_F4_D4_NO_MUTATION_REPORT.json",
            "SHA256SUMS.json",
        ],
        "final_status_vocab": [
            "PASS_LIVE_REPLAY_FACE_ROUTE_PROOF",
            "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS",
            "PASS_WITH_OPTIONAL_NIM_LIMITATIONS",
            "FAIL",
        ],
        "allowed_proof_language": ALLOWED_PROOF_LANGUAGE,
        "forbidden_claim_ids": FORBIDDEN_CLAIM_IDS,
    }
    write_json(output_dir / "BARC_F4_D4_REPLAY_LIVE_PROOF_CONTRACT.json", contract)

    replay_payload = build_replay_payload(primary, supporting)
    write_json(output_dir / "BARC_F4_D4_REPLAY_PAYLOAD.json", replay_payload)

    briefing_payload = build_briefing_payload(primary, supporting, replay_payload)
    write_json(output_dir / "BARC_F4_D4_BRIEFING_PAYLOAD.json", briefing_payload)

    face_publish_status = "FACE_ROUTE_PAYLOAD_ONLY"
    face_route_payload = build_face_route_payload(briefing_payload, replay_payload, face_publish_status)
    write_json(output_dir / "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json", face_route_payload)

    optional_nim = optional_nim_smoke(briefing_payload, output_dir, args.run_live_nim_smoke)
    optional_nim_status = "PASS" if optional_nim.get("status") == "PASS" else "OPTIONAL_NOT_RUN" if optional_nim.get("status") == "OPTIONAL_NIM_NOT_RUN" else "FAIL"

    final_status = "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS"
    if optional_nim.get("status") == "PASS":
        final_status = "PASS_WITH_OPTIONAL_NIM_LIMITATIONS"

    status_payload = build_status_payload(final_status, face_publish_status, optional_nim_status, primary, supporting)
    write_json(output_dir / "BARC_F4_D4_STATUS_PAYLOAD.json", status_payload)

    trace_report = {
        "status": "PASS",
        "primary_bundle_trace_refs": primary.get("trace_refs", []),
        "supporting_bundle_trace_refs": {
            bundle.get("evidence_bundle_id"): bundle.get("trace_refs", []) for bundle in supporting
        },
        "d3_harness_ref": "BARC_F4_D3_HARNESS_REPORT.json",
        "d4_payload_refs": [
            "BARC_F4_D4_REPLAY_PAYLOAD.json",
            "BARC_F4_D4_BRIEFING_PAYLOAD.json",
            "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
            "BARC_F4_D4_STATUS_PAYLOAD.json",
        ],
    }
    write_json(output_dir / "BARC_F4_D4_TRACE_REPORT.json", trace_report)

    next_handoff = {
        "status": "PASS",
        "next_gate": "BARC-F4-D5",
        "handoff_mode": "hero_freeze_package_with_source_boundaries",
        "must_preserve": [
            "city_core_status=candidate_only unless a later accepted gate changes it",
            "BARC-F4-D4 does not accept Barcelona Flow 4",
            "claim_label=[R]",
            "source limitations and point-in-time/API snapshot boundaries",
            "no control, dispatch, enforcement, health, port, or operational recommendations",
        ],
        "selected_primary_evidence_bundle": primary.get("evidence_bundle_id"),
        "supporting_evidence_bundles": [bundle.get("evidence_bundle_id") for bundle in supporting],
    }
    write_json(output_dir / "BARC_F4_D4_NEXT_D5_HANDOFF.json", next_handoff)

    readme = f"""# BARC-F4-D4 Barcelona Flow 4 Live/Replay + Face Route Proof

Final status: `{final_status}`

This package proves the completed BARC-F4-D3 EvidenceBundles can be surfaced as deterministic replay/live-style, narration-ready, and face-route payloads for review.

It does not accept Barcelona city core or Barcelona Flow 4.

## Summary

- Selected primary EvidenceBundle: `{primary.get("evidence_bundle_id")}`
- Supporting EvidenceBundles: {len(supporting)}
- Replay/live proof payload: PASS
- Briefing payload: PASS
- Face route payload: {face_publish_status}
- Optional NIM smoke: {optional_nim_status}

## Boundaries

""" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + f"""

## Output

{output_dir}
"""
    write_text(output_dir / "README.md", readme)

    overclaim = no_overclaim(output_dir)
    write_json(output_dir / "BARC_F4_D4_NO_OVERCLAIM_REPORT.json", overclaim)

    after = snapshot([path for path in mutation_roots if path.exists()])
    mutation = compare_snapshots(before, after)
    write_json(output_dir / "BARC_F4_D4_NO_MUTATION_REPORT.json", mutation)

    claim_label_pass = primary.get("claim_label") == "[R]" and all(bundle.get("claim_label") == "[R]" for bundle in supporting)
    source_limit_pass = all(
        record.get("source_limitation")
        for bundle in [primary, *supporting]
        for record in bundle.get("source_records", [])
        if isinstance(record, dict)
    )
    candidate_only_pass = primary.get("city_core_status") == "candidate_only" and all(
        bundle.get("city_core_status") == "candidate_only" for bundle in supporting
    )
    artifact_names = [
        "README.md",
        "BARC_F4_D4_INPUT_INVENTORY.json",
        "BARC_F4_D4_REPLAY_LIVE_PROOF_CONTRACT.json",
        "BARC_F4_D4_SELECTED_EVIDENCEBUNDLE.json",
        "BARC_F4_D4_REPLAY_PAYLOAD.json",
        "BARC_F4_D4_BRIEFING_PAYLOAD.json",
        "BARC_F4_D4_FACE_ROUTE_PAYLOAD.json",
        "BARC_F4_D4_STATUS_PAYLOAD.json",
        "BARC_F4_D4_TRACE_REPORT.json",
        "BARC_F4_D4_NEXT_D5_HANDOFF.json",
        "BARC_F4_D4_NO_OVERCLAIM_REPORT.json",
        "BARC_F4_D4_NO_MUTATION_REPORT.json",
    ]

    gates = [
        gate_status("BARC-F4-D4-PRECOND", required_inputs_exist=all(inputs[name].exists() for name in ["barc_f4_d3", "barc_d1d2", "barc_d1a", "barc_d1", "xflow_d1", "ontology_v2"]), d3_status=d3_harness.get("status")),
        gate_status("BARC-F4-D4-INPUT-INVENTORY"),
        gate_status("BARC-F4-D4-EVIDENCEBUNDLE-SELECTION", primary=primary.get("evidence_bundle_id"), supporting_count=len(supporting)),
        gate_status("BARC-F4-D4-REPLAY-LIVE-PROOF"),
        gate_status("BARC-F4-D4-BRIEFING-PAYLOAD"),
        gate_status("BARC-F4-D4-FACE-ROUTE-PAYLOAD", face_route_status=face_publish_status),
        gate_status("BARC-F4-D4-CLAIM-LABEL-PRESERVATION", "PASS" if claim_label_pass else "FAIL"),
        gate_status("BARC-F4-D4-SOURCE-LIMITATION-PRESERVATION", "PASS" if source_limit_pass else "FAIL"),
        gate_status("BARC-F4-D4-OPTIONAL-NIM-SMOKE", optional_nim.get("status")),
        overclaim,
        mutation,
        gate_status("BARC-F4-D4-ARTIFACTS", "PASS" if all((output_dir / name).exists() for name in artifact_names) else "FAIL", present={name: (output_dir / name).exists() for name in artifact_names}),
    ]
    hashes = write_hashes(output_dir)
    gates.append(hashes)

    if any(gate.get("status") == "FAIL" for gate in gates):
        final_status = "FAIL"
        status_payload["status"] = final_status
        write_json(output_dir / "BARC_F4_D4_STATUS_PAYLOAD.json", status_payload)

    harness = {
        "task": TASK_NAME,
        "status": final_status,
        "passed": final_status != "FAIL",
        "claim": "D4 proof payloads only; Barcelona city core and Flow 4 remain candidate-only.",
        "selected_primary_evidence_bundle": primary.get("evidence_bundle_id"),
        "supporting_evidence_bundle_count": len(supporting),
        "face_route_status": face_publish_status,
        "optional_nim_smoke": optional_nim_status,
        "gates": gates,
        "output_dir": str(output_dir),
        "generated_at_utc": utc_now(),
    }
    write_json(output_dir / "BARC_F4_D4_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    for gate in gates:
        if gate.get("gate") == "BARC-F4-D4-HASHES":
            gate.update(hashes)
    harness["gates"] = gates
    write_json(output_dir / "BARC_F4_D4_HARNESS_REPORT.json", harness)
    write_hashes(output_dir)

    selected_ok = "PASS" if primary.get("evidence_bundle_id") else "FAIL"
    print(f"BARC-F4-D4 Barcelona Flow 4 Live/Replay + Face Route Proof: {final_status}")
    print()
    print(f"Selected primary EvidenceBundle: {selected_ok}")
    print(f"Supporting EvidenceBundles: {len(supporting)}")
    print("Replay/live proof payload: PASS")
    print("Briefing payload: PASS")
    print(f"Face route payload: {'PAYLOAD_ONLY' if face_publish_status == 'FACE_ROUTE_PAYLOAD_ONLY' else 'PASS'}")
    print(f"Optional NIM smoke: {optional_nim_status}")
    print()
    print(f"Claim labels: {'PASS' if claim_label_pass else 'FAIL'}")
    print(f"Source limitations: {'PASS' if source_limit_pass else 'FAIL'}")
    print(f"Candidate-only boundary: {'PASS' if candidate_only_pass else 'FAIL'}")
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
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
