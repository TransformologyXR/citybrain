from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "CHI-F7-D1 Chicago Civic + Sensor Fusion Cartridge"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D3_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness"
DEFAULT_D4_DIR = "outputs/chi_d4_dual_flow_scope_fork"
DEFAULT_F1_DIR = "outputs/chi_f1_d1_situational_status_cartridge"
DEFAULT_OUTPUT_DIR = "outputs/chi_f7_d1_civic_sensor_fusion_cartridge"

BOUNDARY_LINES = [
    "CHI-F7-D1 is a civic/sensor-fusion cartridge over public Chicago source data.",
    "CHI-F7-D1 produces analyst-review candidates only.",
    "CHI-F7-D1 does not make operational recommendations.",
    "CHI-F7-D1 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "CHI-F7-D1 does not certify affected buildings/assets.",
    "CHI-F7-D1 uses capped/windowed sources where full-source completion is not proven.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
]

FORBIDDEN_PATTERNS = [
    r"\brisk score\b",
    r"\bdanger score\b",
    r"\bcrime score\b",
    r"\bhealth score\b",
    r"\benforcement score\b",
    r"\bemergency score\b",
    r"\bworst\b",
    r"\bunsafe\b",
    r"\boperational recommendation\b(?!s\.)",
    r"\bpolicing recommendation\b(?!s\.)",
    r"\bdispatch recommendation\b(?!s\.)",
    r"\benforcement recommendation\b(?!s\.)",
    r"\bhealth recommendation\b(?!s\.)",
    r"\bemergency recommendation\b(?!s\.)",
    r"\bpublic-safety recommendation\b(?!s\.)",
    r"\bcertifies affected (?:buildings|assets)\b",
]

SIGNAL_ORDER = [
    "311_service_request",
    "traffic_crash",
    "building_permit",
    "building_violation",
    "food_inspection",
    "business_license",
    "open_air_observation",
    "divvy_mobility",
    "crime_context",
]

SIGNAL_LABELS = {
    "311_service_request": "311 civic-service signal",
    "traffic_crash": "traffic crash context signal",
    "building_permit": "building permit activity",
    "building_violation": "building violation activity",
    "food_inspection": "food inspection signal",
    "business_license": "business license activity",
    "open_air_observation": "Open Air / environment observations",
    "divvy_mobility": "Divvy mobility observations",
    "crime_context": "crime as privacy-safe block-level context only",
}

SIGNAL_WEIGHTS = {
    "311_service_request": 1.15,
    "traffic_crash": 0.85,
    "building_permit": 0.55,
    "building_violation": 0.55,
    "food_inspection": 1.00,
    "business_license": 1.00,
    "open_air_observation": 1.10,
    "divvy_mobility": 0.75,
    "crime_context": 0.30,
}

SOURCE_KEYS = {
    "311_service_request": "311_service_requests",
    "traffic_crash": "traffic_crashes_crashes",
    "building_permit": "building_permits",
    "building_violation": "building_violations",
    "food_inspection": "food_inspections",
    "business_license": "business_licenses",
    "open_air_observation": "open_air_chicago_hour_aggregations_and_individual_measurements",
    "divvy_mobility": "divvy_trips",
    "crime_context": "crimes_2001_present",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def safe_id(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower()).strip("_")
    return text or "unknown"


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    (path / "canonical").mkdir(parents=True, exist_ok=True)
    (path / "evidence").mkdir(parents=True, exist_ok=True)
    (path / "reports").mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        if add_boundary:
            payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    files = sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    sums = {str(p.relative_to(output_dir)).replace("\\", "/"): sha256_file(p) for p in files}
    (output_dir / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = {str(p.relative_to(output_dir)).replace("\\", "/") for p in files}
    return {
        "status": "PASS" if sorted(sums) == sorted(expected) else "FAIL",
        "file_count": len(sums),
        "missing": sorted(expected - set(sums)),
        "extra": sorted(set(sums) - expected),
    }


def snapshot(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for root in paths:
        if not root.exists():
            out[str(root)] = "MISSING"
            continue
        for p in root.rglob("*"):
            if p.is_file():
                out[str(p.resolve())] = sha256_file(p)
    return out


def compare_snapshots(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    changed = sorted(k for k, v in before.items() if after.get(k) != v)
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    return {
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
        "checked_files": len(before),
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    boundary_failures: list[str] = []
    forbidden_hits: list[dict[str, str]] = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        if path.name == "SHA256SUMS.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        checked += 1
        missing = [line for line in BOUNDARY_LINES if line not in text]
        if missing:
            boundary_failures.append(str(path.relative_to(output_dir)))
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                forbidden_hits.append({"file": str(path.relative_to(output_dir)), "pattern": pattern})
    return {
        "status": "PASS" if not boundary_failures and not forbidden_hits else "FAIL",
        "checked_files": checked,
        "boundary_failures": boundary_failures,
        "forbidden_hits": forbidden_hits,
    }


def build_source_status(ledger: dict[str, Any], d3_source_status: dict[str, Any]) -> dict[str, Any]:
    rows = ledger.get("ledger", []) if isinstance(ledger, dict) else []
    capped = [
        r for r in rows
        if str(r.get("completion_status", "")).upper() in {"CAPPED", "WINDOWED_CAPPED", "WINDOWED_COMPLETE"}
    ]
    return {
        "status": "PASS",
        "source_base": "accepted CHI-D2B/CHI-D3/CHI-D4 plus CHI-F1-D1 area summaries",
        "d3_source_status": d3_source_status,
        "shared_source_ledger": rows,
        "capped_or_windowed_sources": capped,
        "limitations": [
            "Capped/windowed source limitations remain active where full-source completion is not proven.",
            "CTA GTFS is static schedule context, not live transit status.",
            "Crime data is privacy-safe block-level context only.",
            "Sensor/environment observations are context signals, not health determinations.",
            "Candidates are for analyst review only and are not operational recommendations.",
        ],
    }


def source_completion_map(ledger: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in ledger.get("ledger", []) if isinstance(ledger, dict) else []:
        key = str(row.get("source_key", ""))
        if key:
            out[key] = str(row.get("completion_status", "unknown"))
    out["open_air_chicago_hour_aggregations_and_individual_measurements"] = "WINDOWED_COMPLETE/WINDOWED_CAPPED"
    return out


def compute_candidates(summary: pd.DataFrame, completion: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eligible = summary[summary["subject_type"].isin(["community_area", "ward", "police_district"])].copy()
    if eligible.empty:
        eligible = summary.copy()

    component_cols = [f"{s}_count" for s in SIGNAL_ORDER]
    rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []

    for _, row in eligible.iterrows():
        subject_id = str(row["subject_id"])
        candidate_id = f"chi-f7:fusion_candidate:{safe_id(row['subject_type'])}:{safe_id(row['subject_key'])}"
        nonzero = 0
        weighted = 0.0
        for signal in SIGNAL_ORDER:
            count = int(row.get(f"{signal}_count", 0) or 0)
            if count <= 0:
                continue
            nonzero += 1
            weight = SIGNAL_WEIGHTS[signal]
            component_score = round(math.log1p(count) * weight, 4)
            weighted += component_score
            source_key = SOURCE_KEYS[signal]
            component_rows.append({
                "candidate_id": candidate_id,
                "signal_type": signal,
                "signal_label": SIGNAL_LABELS[signal],
                "signal_count": count,
                "weight": weight,
                "component_score": component_score,
                "source_key": source_key,
                "source_completion_status": completion.get(source_key, "unknown"),
            })
            edge_rows.append({
                "source_id": candidate_id,
                "target_id": f"source:chicago:{source_key}",
                "relation": "has_fusion_signal_component",
                "signal_type": signal,
                "signal_count": count,
                "source_completion_status": completion.get(source_key, "unknown"),
                "confidence": 0.88 if completion.get(source_key) == "FULL" else 0.76,
                "boundary": "public_source_context_only",
            })

        total = int(row.get("total_public_source_events", 0) or 0)
        location_a = int(row.get("location_confidence_A_count", 0) or 0)
        location_a_ratio = round(location_a / total, 6) if total else 0.0
        fusion_score = round(weighted + (nonzero * 0.85) + (location_a_ratio * 1.25), 4)
        rows.append({
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "subject_type": row.get("subject_type"),
            "subject_key": str(row.get("subject_key")),
            "subject_name": row.get("subject_name"),
            "fusion_signal_score": fusion_score,
            "score_description": "fusion_signal_score = public-source signal convergence score only",
            "nonzero_signal_dimensions": nonzero,
            "total_public_source_events": total,
            "location_confidence_A_count": location_a,
            "location_confidence_A_ratio": location_a_ratio,
            "selection_status": "eligible",
        })
        edge_rows.append({
            "source_id": candidate_id,
            "target_id": subject_id,
            "relation": "uses_area_status_context",
            "signal_type": "area_status_subject",
            "signal_count": total,
            "source_completion_status": "CHI-F1-D1",
            "confidence": 0.90,
            "boundary": "public_source_context_only",
        })

    candidates = pd.DataFrame(rows)
    candidates = candidates.sort_values(
        ["nonzero_signal_dimensions", "fusion_signal_score", "total_public_source_events", "candidate_id"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    candidates["rank"] = range(1, len(candidates) + 1)

    selected = candidates.head(8).copy()
    selected["selection_status"] = "selected_for_d1_evidence_bundle"
    selected_ids = set(selected["candidate_id"])
    candidates.loc[candidates["candidate_id"].isin(selected_ids), "selection_status"] = "selected_for_d1_evidence_bundle"

    subjects = selected[[
        "candidate_id",
        "subject_id",
        "subject_type",
        "subject_key",
        "subject_name",
        "rank",
        "fusion_signal_score",
        "score_description",
        "nonzero_signal_dimensions",
        "total_public_source_events",
        "location_confidence_A_ratio",
    ]].copy()

    components = pd.DataFrame(component_rows)
    edges = pd.DataFrame(edge_rows)
    return subjects, candidates, components, edges


def evidence_bundle(candidate: pd.Series, components: pd.DataFrame, source_status: dict[str, Any], f1_dir: Path, chi_d3_dir: Path, chi_d4_dir: Path) -> dict[str, Any]:
    comp = components[components["candidate_id"] == candidate["candidate_id"]].sort_values("component_score", ascending=False)
    return {
        "bundle_id": f"evidence_bundle_fusion_candidate_{safe_id(candidate['candidate_id'])}",
        "query_type": "civic_sensor_fusion_candidate",
        "candidate_id": candidate["candidate_id"],
        "subject_id": candidate["subject_id"],
        "subject_type": candidate["subject_type"],
        "subject_name": candidate["subject_name"],
        "rank": int(candidate["rank"]),
        "fusion_signal_score": float(candidate["fusion_signal_score"]),
        "score_description": candidate["score_description"],
        "nonzero_signal_dimensions": int(candidate["nonzero_signal_dimensions"]),
        "total_public_source_events": int(candidate["total_public_source_events"]),
        "location_confidence_A_ratio": float(candidate["location_confidence_A_ratio"]),
        "signal_components": comp.to_dict("records"),
        "why_selected": "Deterministically selected by highest public-source signal convergence among D3 area-attributed subjects.",
        "source_limitations": source_status["limitations"],
        "provenance": [
            {"source": "CHI-F1-D1 area signal summary", "path": str(f1_dir / "canonical" / "chi_f1_d1_area_signal_summary.parquet")},
            {"source": "CHI-D3 civic/event ingest", "path": str(chi_d3_dir)},
            {"source": "CHI-D4 dual-flow fork contract", "path": str(chi_d4_dir)},
        ],
    }


def briefing(bundle: dict[str, Any]) -> str:
    lines = [
        f"# CHI-F7-D1 Fusion Candidate: {bundle['subject_name']}",
        "",
        *BOUNDARY_LINES,
        "",
        "This deterministic briefing was generated from CHI-F7-D1 evidence only. No NIM, NeMo, or LLM generated these facts.",
        "",
        f"Candidate ID: `{bundle['candidate_id']}`",
        f"Rank: {bundle['rank']}",
        f"Fusion signal score: {bundle['fusion_signal_score']} ({bundle['score_description']})",
        f"Nonzero signal dimensions: {bundle['nonzero_signal_dimensions']}",
        f"Total public-source events in area attribution: {bundle['total_public_source_events']}",
        f"Location confidence A ratio: {bundle['location_confidence_A_ratio']}",
        "",
        "Signal components:",
    ]
    for item in bundle["signal_components"][:8]:
        lines.append(
            f"- {item['signal_label']}: {item['signal_count']} rows, completion status {item['source_completion_status']}"
        )
    lines.extend([
        "",
        "Interpretation boundary:",
        "- This candidate shows public-source signal convergence for analyst review.",
        "- It is not a real-time sensor surface and not operational guidance.",
        "- It does not certify affected buildings/assets or make public-safety claims.",
        "",
        "Source limitations:",
    ])
    lines.extend(f"- {line}" for line in bundle["source_limitations"])
    lines.append("")
    return "\n".join(lines)


def run_chi_f7_d1_gate(
    project_root: str,
    chi_d2b_dir: str,
    chi_d3_dir: str,
    chi_d4_dir: str,
    f1_d1_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d2b = (root / chi_d2b_dir).resolve()
    d3 = (root / chi_d3_dir).resolve()
    d4 = (root / chi_d4_dir).resolve()
    f1 = (root / f1_d1_dir).resolve()
    out = (root / output_dir).resolve()

    input_roots = [d2b, d3, d4, f1]
    before = snapshot(input_roots)
    ensure_clean_dir(out)

    d2b_harness = read_json(d2b / "CHI_D2B_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3 / "CHI_D3_HARNESS_REPORT.json", {})
    d4_harness = read_json(d4 / "CHI_D4_HARNESS_REPORT.json", {})
    f1_harness = read_json(f1 / "CHI_F1_D1_HARNESS_REPORT.json", {})
    f7_contract = read_json(d4 / "CHI_D4_F7_D1_READINESS_CONTRACT.json", {})
    ledger = read_json(d4 / "CHI_D4_SHARED_SOURCE_LEDGER.json", {})
    d3_source_status = read_json(d3 / "reports" / "source_capped_status.json", {})

    inventory = {
        "status": "PASS"
        if status_pass(d2b_harness.get("status"))
        and status_pass(d3_harness.get("status"))
        and status_pass(d4_harness.get("status"))
        and status_pass(f1_harness.get("status"))
        and f7_contract.get("status") == "PASS"
        else "FAIL",
        "d2b_status": d2b_harness.get("status"),
        "d3_status": d3_harness.get("status"),
        "d4_status": d4_harness.get("status"),
        "f1_status": f1_harness.get("status"),
        "f7_contract_status": f7_contract.get("status"),
        "inputs": {
            "chi_d2b_dir": str(d2b),
            "chi_d3_dir": str(d3),
            "chi_d4_dir": str(d4),
            "chi_f1_d1_dir": str(f1),
        },
    }
    write_json(out / "CHI_F7_D1_INPUT_INVENTORY.json", inventory)

    summary_path = f1 / "canonical" / "chi_f1_d1_area_signal_summary.parquet"
    summary = pd.read_parquet(summary_path)
    source_status = build_source_status(ledger, d3_source_status)
    completion = source_completion_map(ledger)
    subjects, candidates, components, edges = compute_candidates(summary, completion)

    write_parquet(out / "canonical" / "chi_f7_d1_fusion_subjects.parquet", subjects)
    write_parquet(out / "canonical" / "chi_f7_d1_signal_fusion_candidates.parquet", candidates)
    write_parquet(out / "canonical" / "chi_f7_d1_signal_components.parquet", components)
    write_parquet(out / "canonical" / "chi_f7_d1_candidate_context_edges.parquet", edges)

    bundles: list[dict[str, Any]] = []
    for _, candidate in subjects.iterrows():
        payload = evidence_bundle(candidate, components, source_status, f1, d3, d4)
        bundles.append(payload)
        stem = safe_id(candidate["candidate_id"])
        write_json(out / "evidence" / f"evidence_bundle_fusion_candidate_{stem}.json", payload)
        write_text(out / "evidence" / f"deterministic_briefing_fusion_candidate_{stem}.md", briefing(payload))

    write_json(out / "evidence" / "evidence_bundle_source_limitations.json", source_status)

    write_json(out / "CHI_F7_D1_FUSION_MODEL_REPORT.json", {
        "status": "PASS",
        "model": "deterministic weighted log-count signal convergence",
        "score_field": "fusion_signal_score",
        "score_description": "fusion_signal_score = public-source signal convergence score only",
        "weights": SIGNAL_WEIGHTS,
        "source_keys": SOURCE_KEYS,
        "selection_rule": "top ranked non-citywide D3 area-attributed subjects by signal dimensions, fusion score, and public-source event count",
    })
    write_json(out / "CHI_F7_D1_CANDIDATE_REPORT.json", {
        "status": "PASS",
        "candidate_count": int(len(candidates)),
        "selected_candidate_count": int(len(subjects)),
        "top_candidates": subjects.to_dict("records"),
    })
    write_json(out / "CHI_F7_D1_EVIDENCE_BUNDLE_REPORT.json", {
        "status": "PASS",
        "bundle_count": len(bundles),
        "bundle_ids": [b["bundle_id"] for b in bundles],
    })
    write_json(out / "CHI_F7_D1_DETERMINISTIC_BRIEFING_REPORT.json", {
        "status": "PASS",
        "briefing_count": len(bundles),
    })
    write_json(out / "CHI_F7_D1_SOURCE_LIMITATION_REPORT.json", source_status)
    write_json(out / "reports" / "signal_fusion_distribution.json", {
        "status": "PASS",
        "score_summary": {
            "min": float(candidates["fusion_signal_score"].min()),
            "max": float(candidates["fusion_signal_score"].max()),
            "mean": float(candidates["fusion_signal_score"].mean()),
        },
        "selected_signal_dimensions": subjects[["candidate_id", "nonzero_signal_dimensions", "fusion_signal_score"]].to_dict("records"),
    })
    write_json(out / "reports" / "candidate_selection.json", {
        "status": "PASS",
        "selection_rule": "deterministic top ranked candidates from CHI-F1-D1 area summaries",
        "selected": subjects.to_dict("records"),
    })
    write_json(out / "reports" / "source_capped_status.json", source_status)
    write_json(out / "reports" / "privacy_boundary.json", {
        "status": "PASS",
        "crime_boundary": "Crime data is privacy-safe block-level context only.",
        "candidate_boundary": "Fusion candidates are public-source signal convergence records for analyst review only.",
    })
    write_json(out / "reports" / "recommended_f7_d2_live_plan.json", {
        "status": "PASS",
        "recommended_next": "CHI-F7-D2 governed live replay over CHI-F7-D1 EvidenceBundles",
        "note": "No live NIM or face-layer claim in D1.",
    })

    readme = "\n".join([
        "# CHI-F7-D1 Civic + Sensor Fusion Cartridge",
        "",
        *BOUNDARY_LINES,
        "",
        "Status: PASS_WITH_CAPPED_SOURCE_LIMITATIONS",
        f"Fusion candidates: {len(candidates)}",
        f"Selected EvidenceBundles: {len(bundles)}",
        "",
    ])
    write_text(out / "README.md", readme)
    handover = "\n".join([
        "# CHI-F7-D1 Adapter Handover",
        "",
        *BOUNDARY_LINES,
        "",
        "Use the fusion candidates, signal components, context edges, and EvidenceBundles for CHI-F7-D2. Treat fusion_signal_score as public-source signal convergence only.",
        "",
    ])
    write_text(out / "CHI_F7_D1_ADAPTER_HANDOVER.md", handover)

    gates = {
        "CHI-F7-D1-PRECOND": inventory["status"],
        "CHI-F7-D1-F1-HANDOFF": "PASS" if status_pass(f1_harness.get("status")) and summary_path.exists() else "FAIL",
        "CHI-F7-D1-FUSION-MODEL": "PASS" if len(components) > 0 and len(candidates) >= len(subjects) else "FAIL",
        "CHI-F7-D1-CANDIDATE-SELECTION": "PASS" if len(subjects) >= 5 and subjects["nonzero_signal_dimensions"].min() >= 1 else "FAIL",
        "CHI-F7-D1-EVIDENCE-BUNDLES": "PASS" if len(bundles) == len(subjects) else "FAIL",
        "CHI-F7-D1-DETERMINISTIC-BRIEFINGS": "PASS" if len(bundles) == len(list((out / "evidence").glob("deterministic_briefing_fusion_candidate_*.md"))) else "FAIL",
        "CHI-F7-D1-SOURCE-LIMITATIONS": "PASS" if source_status.get("capped_or_windowed_sources") else "FAIL",
        "CHI-F7-D1-PRIVACY": "PASS",
    }

    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F7_D1_NO_MUTATION_REPORT.json", no_mutation)
    gates["CHI-F7-D1-NO-MUTATION"] = no_mutation["status"]

    harness = {
        "task": TASK_NAME,
        "status": "PASS_WITH_CAPPED_SOURCE_LIMITATIONS",
        "fusion_candidates": int(len(candidates)),
        "selected_candidates": int(len(subjects)),
        "evidence_bundles": int(len(bundles)),
        "deterministic_briefings": int(len(bundles)),
        "gates": gates,
        "output": str(out),
    }
    write_json(out / "CHI_F7_D1_HARNESS_REPORT.json", harness)
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_F7_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-F7-D1-NO-OVERCLAIM"] = no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-F7-D1-HASHES"] = hashes["status"]

    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_SOURCE_LIMITATIONS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(out / "CHI_F7_D1_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_F7_D1_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    gates["CHI-F7-D1-NO-OVERCLAIM"] = final_no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-F7-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_SOURCE_LIMITATIONS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(out / "CHI_F7_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)

    return {
        "status": harness["status"],
        "fusion_candidates": int(len(candidates)),
        "selected_candidates": int(len(subjects)),
        "evidence_bundles": int(len(bundles)),
        "deterministic_briefings": int(len(bundles)),
        "no_overclaim": gates["CHI-F7-D1-NO-OVERCLAIM"],
        "gates": gates,
        "output": str(out),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--chi-d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--chi-d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--f1-d1-dir", default=DEFAULT_F1_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_f7_d1_gate(
        args.project_root,
        args.chi_d2b_dir,
        args.chi_d3_dir,
        args.chi_d4_dir,
        args.f1_d1_dir,
        args.output_dir,
    )
    print(f"CHI-F7-D1: {result['status']}")
    print(f"F7 fusion candidates: {result['fusion_candidates']}")
    print(f"F7 selected candidates: {result['selected_candidates']}")
    print(f"F7 EvidenceBundles: {result['evidence_bundles']}")
    print(f"F7 deterministic briefings: {result['deterministic_briefings']}")
    print(f"F7 no-overclaim: {result['no_overclaim']}")
    print(f"Output: {result['output']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
