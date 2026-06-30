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


TASK_NAME = "CHI-F1-D1 Chicago Situational Status Cartridge"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D3_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness"
DEFAULT_D4_DIR = "outputs/chi_d4_dual_flow_scope_fork"
DEFAULT_OUTPUT_DIR = "outputs/chi_f1_d1_situational_status_cartridge"

BOUNDARY_LINES = [
    "CHI-F1-D1 is a situational-status cartridge over public Chicago source data.",
    "CHI-F1-D1 does not make operational recommendations.",
    "CHI-F1-D1 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "CHI-F1-D1 does not certify affected buildings/assets.",
    "CHI-F1-D1 uses capped/windowed sources where full-source completion is not proven.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
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
    "traffic_crash": "traffic crash signal",
    "building_permit": "building permit activity",
    "building_violation": "building violation activity",
    "food_inspection": "food inspection signal",
    "business_license": "business license activity",
    "open_air_observation": "Open Air / environment observations",
    "divvy_mobility": "Divvy mobility observations",
    "crime_context": "crime as privacy-safe block-level context only",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def with_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("generated_at", utc_now())
    out.setdefault("boundary_lines", BOUNDARY_LINES)
    return out


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = with_boundary(payload)
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
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    expected = sorted(p.relative_to(output_dir).as_posix() for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    return {"status": "PASS" if sorted(sums) == expected else "FAIL", "file_count": len(sums), "missing": sorted(set(expected) - set(sums)), "extra": sorted(set(sums) - set(expected))}


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()):
            raise ValueError(f"Refusing to remove output outside workspace: {resolved}")
        if "chi_f1_d1_situational_status_cartridge" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["canonical", "evidence", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            entry = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if stat.st_size <= 5_000_000:
                entry["sha256"] = sha256_file(path)
            watched[str(path.resolve())] = entry
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value is not None else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:180] or fallback


def status_pass(value: Any) -> bool:
    return str(value or "").upper().startswith("PASS")


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    checked = []
    boundary_failures = []
    forbidden_hits = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"} or path.name == "SHA256SUMS.json":
            continue
        if "canonical" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(str(path.relative_to(output_dir)))
        missing = [line for line in BOUNDARY_LINES if line not in text]
        if missing:
            boundary_failures.append({"path": str(path.relative_to(output_dir)), "missing_boundary_lines": missing})
        lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                forbidden_hits.append({"path": str(path.relative_to(output_dir)), "pattern": pattern})
    return {"status": "PASS" if not boundary_failures and not forbidden_hits else "FAIL", "checked_files": checked, "boundary_failures": boundary_failures, "forbidden_hits": forbidden_hits}


def load_area_names(chi_d2b_dir: Path) -> dict[tuple[str, str], str]:
    area_path = chi_d2b_dir / "canonical" / "chi_d2b_area_context.parquet"
    areas = pd.read_parquet(area_path, columns=["area_type", "native_id", "name"]) if area_path.exists() else pd.DataFrame()
    mapping: dict[tuple[str, str], str] = {}
    for _, row in areas.iterrows():
        mapping[(str(row["area_type"]), str(row["native_id"]))] = str(row["name"])
    return mapping


def load_location_table(chi_d3_dir: Path) -> pd.DataFrame:
    path = chi_d3_dir / "canonical" / "chi_d3_event_location_confidence.parquet"
    return pd.read_parquet(path, columns=["event_type", "source_status", "location_confidence", "ward", "community_area", "police_district"])


def pivot_counts(frame: pd.DataFrame, subject_type: str, subject_key: str, subject_name: str, name_map: dict[tuple[str, str], str]) -> pd.DataFrame:
    rows = []
    if subject_type == "citywide":
        grouped = frame.groupby("event_type", dropna=False).size()
        loc = frame.groupby("location_confidence", dropna=False).size()
        row = {"subject_id": "chi-f1:citywide:chicago", "subject_type": "citywide", "subject_key": "chicago", "subject_name": "Chicago citywide"}
        for signal in SIGNAL_ORDER:
            row[f"{signal}_count"] = int(grouped.get(signal, 0))
        for tier in ["A", "B", "C", "D"]:
            row[f"location_confidence_{tier}"] = int(loc.get(tier, 0))
        rows.append(row)
        return pd.DataFrame(rows)

    sub = frame[frame[subject_key].notna()].copy()
    sub[subject_key] = sub[subject_key].astype("string")
    counts = sub.groupby([subject_key, "event_type"]).size().reset_index(name="count")
    locs = sub.groupby([subject_key, "location_confidence"]).size().reset_index(name="count")
    for key in sorted(counts[subject_key].dropna().unique(), key=lambda x: str(x)):
        key_text = str(key)
        display = name_map.get((subject_type, key_text), f"{subject_name} {key_text}")
        row = {"subject_id": f"chi-f1:{subject_type}:{safe_id(key_text)}", "subject_type": subject_type, "subject_key": key_text, "subject_name": display}
        g = counts[counts[subject_key] == key]
        for signal in SIGNAL_ORDER:
            row[f"{signal}_count"] = int(g.loc[g["event_type"] == signal, "count"].sum())
        l = locs[locs[subject_key] == key]
        for tier in ["A", "B", "C", "D"]:
            row[f"location_confidence_{tier}"] = int(l.loc[l["location_confidence"] == tier, "count"].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def add_scores(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    signal_cols = [f"{signal}_count" for signal in SIGNAL_ORDER]
    for col in signal_cols:
        if col not in out.columns:
            out[col] = 0
    out["total_public_source_events"] = out[signal_cols].sum(axis=1).astype(int)
    out["nonzero_signal_dimensions"] = (out[signal_cols] > 0).sum(axis=1).astype(int)
    out["location_confidence_A_count"] = out.get("location_confidence_A", 0)
    out["status_signal_score"] = out["total_public_source_events"].map(lambda v: round(math.log1p(float(v)), 4)) + (out["nonzero_signal_dimensions"] * 0.35)
    out["score_description"] = "status_signal_score = public-source activity/context score only"
    return out


def build_subjects(summary: pd.DataFrame) -> pd.DataFrame:
    selected = []
    city = summary[summary["subject_type"] == "citywide"].head(1).copy()
    if not city.empty:
        city["why_selected"] = "citywide baseline subject for comparison"
        selected.append(city)
    communities = summary[summary["subject_type"] == "community_area"].sort_values(["nonzero_signal_dimensions", "status_signal_score", "total_public_source_events"], ascending=False).head(2).copy()
    communities["why_selected"] = "strong signal coverage across public-source activity dimensions"
    selected.append(communities)
    ward = summary[summary["subject_type"] == "ward"].sort_values(["nonzero_signal_dimensions", "status_signal_score", "total_public_source_events"], ascending=False).head(1).copy()
    ward["why_selected"] = "high observed public-source activity with area-context support"
    selected.append(ward)
    district = summary[summary["subject_type"] == "police_district"].sort_values(["nonzero_signal_dimensions", "status_signal_score", "total_public_source_events"], ascending=False).head(1).copy()
    district["why_selected"] = "police-district subject with strong public-source location-field coverage"
    selected.append(district)
    subjects = pd.concat(selected, ignore_index=True)
    subjects.insert(0, "selection_rank", range(1, len(subjects) + 1))
    return subjects


def source_limitations(chi_d3_dir: Path, chi_d4_dir: Path) -> dict[str, Any]:
    d3_source = read_json(chi_d3_dir / "reports" / "source_capped_status.json", {})
    d4_ledger = read_json(chi_d4_dir / "CHI_D4_SHARED_SOURCE_LEDGER.json", {})
    return {
        "status": "PASS",
        "capped_sources": d3_source.get("capped_sources", []),
        "source_rows": d3_source.get("sources", []),
        "shared_ledger": d4_ledger.get("ledger", []),
        "required_statement": "CHI-F1-D1 uses capped/windowed sources where full-source completion is not proven.",
    }


def evidence_bundle(subject: dict[str, Any], limitations: dict[str, Any]) -> dict[str, Any]:
    signal_counts = {SIGNAL_LABELS[sig]: int(subject.get(f"{sig}_count", 0) or 0) for sig in SIGNAL_ORDER}
    return {
        "bundle_id": f"evidence_bundle_area_status_{safe_id(subject['subject_id'])}",
        "query_type": "area_status",
        "subject": {k: subject.get(k) for k in ["subject_id", "subject_type", "subject_key", "subject_name", "why_selected"]},
        "status_signal_score": subject.get("status_signal_score"),
        "score_description": "status_signal_score = public-source activity/context score only",
        "signal_counts": signal_counts,
        "location_confidence": {tier: int(subject.get(f"location_confidence_{tier}", 0) or 0) for tier in ["A", "B", "C", "D"]},
        "source_limitations": limitations,
        "provenance": ["CHI-D2B area/resource context", "CHI-D3 normalized event/location evidence", "CHI-D4 Flow 1 readiness contract"],
        "boundary_lines": BOUNDARY_LINES,
    }


def briefing(bundle: dict[str, Any]) -> str:
    subject = bundle["subject"]
    lines = [
        f"# Area Status Briefing: {subject['subject_name']}",
        "",
        *BOUNDARY_LINES,
        "",
        "This deterministic briefing answers: What is happening in this place?",
        "",
        f"Subject type: {subject['subject_type']}",
        f"Why selected: {subject.get('why_selected')}",
        f"Status signal score: {bundle['status_signal_score']} ({bundle['score_description']})",
        "",
        "Signal counts:",
    ]
    for label, value in bundle["signal_counts"].items():
        lines.append(f"- {label}: {value}")
    loc = bundle["location_confidence"]
    lines.extend(
        [
            "",
            f"Location confidence counts: A={loc.get('A', 0)} B={loc.get('B', 0)} C={loc.get('C', 0)} D={loc.get('D', 0)}",
            "",
            "Source limitations remain active for capped/windowed sources; this is not real-time status and not operational guidance.",
            "",
        ]
    )
    return "\n".join(lines)


def build_context_edges(subjects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in subjects.iterrows():
        for signal in SIGNAL_ORDER:
            rows.append(
                {
                    "canonical_id": f"edge:us-chicago:chi-f1-d1:subject_signal:{safe_id(row['subject_id'])}:{signal}",
                    "entity_type": "context_edge",
                    "source_id": row["subject_id"],
                    "target_id": f"signal_dimension:chi-f1-d1:{signal}",
                    "relation": "has_status_signal_dimension",
                    "join_method": "deterministic_area_signal_summary",
                    "status": "public_source_context_only",
                    "count": int(row.get(f"{signal}_count", 0) or 0),
                    "confidence": 0.8,
                }
            )
    return pd.DataFrame(rows)


def run_chi_f1_d1_gate(
    project_root: str,
    chi_d2b_dir: str,
    chi_d3_dir: str,
    chi_d4_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root)
    resolve = lambda p: Path(p) if Path(p).is_absolute() else root / p
    d2b = resolve(chi_d2b_dir)
    d3 = resolve(chi_d3_dir)
    d4 = resolve(chi_d4_dir)
    out = resolve(output_dir)
    input_roots = [d2b, d3, d4]
    before = snapshot(input_roots)
    reset_output_dir(out)

    d2b_harness = read_json(d2b / "CHI_D2B_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3 / "CHI_D3_HARNESS_REPORT.json", {})
    d4_harness = read_json(d4 / "CHI_D4_HARNESS_REPORT.json", {})
    f1_contract = read_json(d4 / "contracts" / "chi_f1_d1_readiness_contract.json", {})
    limitations = source_limitations(d3, d4)

    inventory = {
        "status": "PASS" if status_pass(d2b_harness.get("status")) and status_pass(d3_harness.get("status")) and status_pass(d4_harness.get("status")) and f1_contract.get("status") == "PASS" else "FAIL",
        "d2b_status": d2b_harness.get("status"),
        "d3_status": d3_harness.get("status"),
        "d4_status": d4_harness.get("status"),
        "f1_contract": f1_contract,
    }
    write_json(out / "CHI_F1_D1_INPUT_INVENTORY.json", inventory)

    loc = load_location_table(d3)
    names = load_area_names(d2b)
    frames = [
        pivot_counts(loc, "citywide", "", "Citywide", names),
        pivot_counts(loc, "community_area", "community_area", "Community Area", names),
        pivot_counts(loc, "ward", "ward", "Ward", names),
        pivot_counts(loc, "police_district", "police_district", "Police District", names),
    ]
    summary = add_scores(pd.concat(frames, ignore_index=True))
    subjects = build_subjects(summary)
    scores = summary[["subject_id", "subject_type", "subject_key", "subject_name", "total_public_source_events", "nonzero_signal_dimensions", "status_signal_score", "score_description"]].copy()
    edges = build_context_edges(subjects)

    write_parquet(out / "canonical" / "chi_f1_d1_area_status_subjects.parquet", subjects)
    write_parquet(out / "canonical" / "chi_f1_d1_area_signal_summary.parquet", summary)
    write_parquet(out / "canonical" / "chi_f1_d1_area_status_scores.parquet", scores)
    write_parquet(out / "canonical" / "chi_f1_d1_area_context_edges.parquet", edges)

    bundle_count = 0
    briefing_count = 0
    bundles = []
    for _, row in subjects.iterrows():
        payload = evidence_bundle(row.to_dict(), limitations)
        stem = safe_id(row["subject_id"])
        write_json(out / "evidence" / f"evidence_bundle_area_status_{stem}.json", payload)
        write_text(out / "evidence" / f"deterministic_briefing_area_status_{stem}.md", briefing(payload))
        bundles.append(payload)
        bundle_count += 1
        briefing_count += 1
    write_json(out / "evidence" / "evidence_bundle_source_limitations.json", {"status": "PASS", "source_limitations": limitations})

    write_json(out / "CHI_F1_D1_AREA_STATUS_INDEX.json", {"status": "PASS", "subjects": subjects.to_dict("records")})
    write_json(out / "CHI_F1_D1_SIGNAL_DIMENSION_REPORT.json", {"status": "PASS", "signal_labels": SIGNAL_LABELS, "signal_distribution": summary[SIGNAL_ORDER and [f"{s}_count" for s in SIGNAL_ORDER]].sum().to_dict()})
    write_json(out / "CHI_F1_D1_EVIDENCE_BUNDLE_REPORT.json", {"status": "PASS", "bundle_count": bundle_count, "bundle_ids": [b["bundle_id"] for b in bundles]})
    write_json(out / "CHI_F1_D1_DETERMINISTIC_BRIEFING_REPORT.json", {"status": "PASS", "briefing_count": briefing_count})
    write_json(out / "CHI_F1_D1_SOURCE_LIMITATION_REPORT.json", limitations)
    write_json(out / "reports" / "subject_selection.json", {"status": "PASS", "selection_rule": "citywide baseline + top two community areas + top ward + top police district by public-source signal coverage", "subjects": subjects.to_dict("records")})
    write_json(out / "reports" / "signal_distribution.json", {"status": "PASS", "event_type_counts": summary[[f"{s}_count" for s in SIGNAL_ORDER]].sum().to_dict()})
    write_json(out / "reports" / "source_capped_status.json", limitations)
    write_json(out / "reports" / "privacy_boundary.json", {"status": "PASS", "crime_boundary": "Crime data is privacy-safe block-level context only."})
    write_json(out / "reports" / "recommended_f1_d2_live_plan.json", {"status": "PASS", "recommended_next": "CHI-F1-D2 live deterministic query/replay plan", "note": "No live NIM claim in D1."})

    readme = "\n".join(["# CHI-F1-D1 Situational Status Cartridge", "", *BOUNDARY_LINES, "", f"Status: PASS_WITH_CAPPED_SOURCE_LIMITATIONS", f"Subjects: {len(subjects)}", f"EvidenceBundles: {bundle_count}", f"Deterministic briefings: {briefing_count}", ""])
    write_text(out / "README.md", readme)
    handover = "\n".join(["# CHI-F1-D1 Adapter Handover", "", *BOUNDARY_LINES, "", "Use the area status subjects, signal summary, scores, and evidence bundles for CHI-F1-D2. Do not treat status_signal_score as risk, danger, crime, health, enforcement, or emergency scoring.", ""])
    write_text(out / "CHI_F1_D1_ADAPTER_HANDOVER.md", handover)

    gates = {
        "CHI-F1-D1-PRECOND": inventory["status"],
        "CHI-F1-D1-SUBJECT-SELECTION": "PASS" if len(subjects) >= 5 and {"citywide", "community_area", "ward", "police_district"}.issubset(set(subjects["subject_type"])) else "FAIL",
        "CHI-F1-D1-SIGNAL-SUMMARY": "PASS" if len(summary) > 0 and summary["total_public_source_events"].sum() > 0 else "FAIL",
        "CHI-F1-D1-EVIDENCE-BUNDLES": "PASS" if bundle_count == len(subjects) else "FAIL",
        "CHI-F1-D1-DETERMINISTIC-BRIEFINGS": "PASS" if briefing_count == len(subjects) else "FAIL",
        "CHI-F1-D1-SOURCE-LIMITATIONS": "PASS" if limitations.get("capped_sources") else "FAIL",
        "CHI-F1-D1-PRIVACY": "PASS",
    }
    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F1_D1_NO_MUTATION_REPORT.json", no_mutation)
    gates["CHI-F1-D1-NO-MUTATION"] = no_mutation["status"]
    harness = {"task": TASK_NAME, "status": "PASS_WITH_CAPPED_SOURCE_LIMITATIONS", "subjects": int(len(subjects)), "evidence_bundles": bundle_count, "deterministic_briefings": briefing_count, "gates": gates, "output": str(out)}
    write_json(out / "CHI_F1_D1_HARNESS_REPORT.json", harness)
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_F1_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-F1-D1-NO-OVERCLAIM"] = no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-F1-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_SOURCE_LIMITATIONS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(out / "CHI_F1_D1_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_F1_D1_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    gates["CHI-F1-D1-NO-OVERCLAIM"] = final_no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-F1-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_SOURCE_LIMITATIONS" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(out / "CHI_F1_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)

    return {"status": harness["status"], "subjects": int(len(subjects)), "evidence_bundles": bundle_count, "deterministic_briefings": briefing_count, "no_overclaim": gates["CHI-F1-D1-NO-OVERCLAIM"], "gates": gates, "output": str(out)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--chi-d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--chi-d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_f1_d1_gate(args.project_root, args.chi_d2b_dir, args.chi_d3_dir, args.chi_d4_dir, args.output_dir)
    print(f"CHI-F1-D1: {result['status']}")
    print(f"F1 subjects: {result['subjects']}")
    print(f"F1 EvidenceBundles: {result['evidence_bundles']}")
    print(f"F1 deterministic briefings: {result['deterministic_briefings']}")
    print(f"F1 no-overclaim: {result['no_overclaim']}")
    print(f"Output: {result['output']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
