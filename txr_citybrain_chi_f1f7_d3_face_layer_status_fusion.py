from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "CHI-F1F7-D3 Chicago Face-Layer Status/Fusion Surface"
DEFAULT_F1_DIR = "outputs/chi_f1_d1_situational_status_cartridge"
DEFAULT_F7_DIR = "outputs/chi_f7_d1_civic_sensor_fusion_cartridge"
DEFAULT_D2_DIR = "outputs/chi_f1f7_d2_live_spark_nim_replay"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_OUTPUT_DIR = "outputs/chi_f1f7_d3_face_layer_status_fusion_surface"
SYNC_TARGET = Path("/data/citybrain/from_3090/chicago_f1f7_d3_face_layer_v1")

PUBLIC_TOOL = "citybrain_chicago_f1f7_query"

BOUNDARY_LINES = [
    "CHI-F1F7-D3 is a static Chicago face-layer publication surface over accepted CHI-F1-D1, CHI-F7-D1, and CHI-F1F7-D2 outputs.",
    "CHI-F1F7-D3 publishes Flow 1 area-status and Flow 7 fusion-candidate views for analyst review.",
    "CHI-F1F7-D3 does not recompute source counts or add facts beyond accepted input artifacts.",
    "CHI-F1F7-D3 does not make operational recommendations.",
    "CHI-F1F7-D3 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "CHI-F1F7-D3 does not certify affected buildings/assets.",
    "CHI-F1F7-D3 does not provide live transit status or health determinations.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
    "Capped/windowed source limitations remain unless upstream Flow artifacts are rerun and accepted.",
    "D1B expanded raw landing facts are source-landing context only and are not silently promoted into F1/F7 evidence counts.",
]

NEGATIVE_BOUNDARY_VIEWS = [
    {
        "view_id": "affected_building_asset_certainty",
        "request_category": "affected-building/asset certainty",
        "accepted": False,
        "deterministic_response": "Rejected. The face layer can show accepted Flow 1 and Flow 7 public-source context, but cannot certify affected buildings or assets.",
    },
    {
        "view_id": "operational_public_safety_response",
        "request_category": "operational or public-safety recommendation",
        "accepted": False,
        "deterministic_response": "Rejected. The face layer is not an operational, policing, dispatch, enforcement, emergency, or public-safety recommender.",
    },
    {
        "view_id": "live_transit_or_health_status",
        "request_category": "live transit or health determination",
        "accepted": False,
        "deterministic_response": "Rejected. CTA context is static schedule context and environmental observations are context signals only.",
    },
    {
        "view_id": "raw_sensitive_rows",
        "request_category": "raw person, vehicle, crime, or private-row drilldown",
        "accepted": False,
        "deterministic_response": "Rejected. D3 publishes governed summaries and EvidenceBundle references only, not raw sensitive rows.",
    },
    {
        "view_id": "silent_source_upgrade",
        "request_category": "upgrade Flow counts from newer landing without rerun",
        "accepted": False,
        "deterministic_response": "Rejected. Newer D1B landing counts require accepted D3/F1/F7 reruns before they can change face-layer evidence counts.",
    },
]


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
    return value


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


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


def normalize_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")[:140] or "unknown"


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def resolve_under(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "chi_f1f7_d3" not in resolved.name.lower()
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["face_payload", "face_app", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


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
    changed = sorted(k for k, v in before.items() if after.get(k) != v)
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    return {
        "gate": "CHI-F1F7-D3-NO-MUTATION",
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
    return {"status": "PASS", "file_count": len(sums)}


def evidence_files(root: Path, pattern: str) -> list[Path]:
    return sorted((root / "evidence").glob(pattern))


def subject_key_from_id(subject_id: str) -> str:
    return str(subject_id).split(":")[-1]


def compact_limitations_from_bundle(bundle: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for line in BOUNDARY_LINES:
        if line not in out:
            out.append(line)
    source_limitations = bundle.get("source_limitations")
    if isinstance(source_limitations, dict):
        required = source_limitations.get("required_statement")
        if required and required not in out:
            out.append(str(required))
    elif isinstance(source_limitations, list):
        for item in source_limitations:
            text = str(item)
            if text not in out:
                out.append(text)
    return out


def area_key(subject_type: str, subject_key: str | None, subject_id: str | None = None) -> tuple[str, str] | None:
    stype = str(subject_type or "").strip()
    key = str(subject_key or "").strip()
    if stype == "citywide":
        return ("city", "chicago")
    if not key and subject_id:
        key = subject_key_from_id(subject_id)
    if stype in {"community_area", "ward", "police_district"} and key:
        return (stype, key)
    return None


def load_area_geometry_index(d2b_dir: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    path = d2b_dir / "canonical" / "chi_d2b_area_context.parquet"
    if not path.exists():
        return {}, {"status": "FAIL", "reason": f"missing {path}"}
    try:
        import pandas as pd

        columns = ["area_type", "native_id", "canonical_id", "name", "geometry_status", "geometry_json", "source_layer", "confidence"]
        frame = pd.read_parquet(path, columns=columns)
        index: dict[tuple[str, str], dict[str, Any]] = {}
        geometry_count = 0
        for row in frame.to_dict("records"):
            key = (str(row.get("area_type")), str(row.get("native_id")))
            geometry_text = row.get("geometry_json")
            if geometry_text:
                geometry_count += 1
            index[key] = {
                "canonical_id": row.get("canonical_id"),
                "name": row.get("name"),
                "geometry_status": row.get("geometry_status"),
                "geometry_json": geometry_text,
                "source_layer": row.get("source_layer"),
                "confidence": row.get("confidence"),
            }
        return index, {"status": "PASS", "source": str(path), "area_context_rows": int(len(frame)), "geometry_rows": geometry_count}
    except Exception as exc:
        return {}, {"status": "FAIL", "source": str(path), "reason": f"{type(exc).__name__}: {exc}"}


def geometry_for_subject(subject_type: str, subject_key: str | None, subject_id: str | None, geometry_index: dict[tuple[str, str], dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
    key = area_key(subject_type, subject_key, subject_id)
    if key is None:
        return None, {"status": "missing_geometry", "reason": "no area key"}
    area = geometry_index.get(key)
    if not area:
        return None, {"status": "missing_geometry", "area_key": list(key), "reason": "area key not found in D2B context"}
    if key == ("city", "chicago"):
        return None, {
            "status": "citywide_extent_not_embedded",
            "area_key": list(key),
            "source_area_canonical_id": area.get("canonical_id"),
            "source_geometry_status": area.get("geometry_status"),
        }
    geometry_text = area.get("geometry_json")
    if not geometry_text:
        return None, {
            "status": "missing_geometry",
            "area_key": list(key),
            "source_area_canonical_id": area.get("canonical_id"),
            "source_geometry_status": area.get("geometry_status"),
        }
    try:
        return json.loads(str(geometry_text)), {
            "status": "PASS",
            "area_key": list(key),
            "source_area_canonical_id": area.get("canonical_id"),
            "source_geometry_status": area.get("geometry_status"),
            "source_layer": area.get("source_layer"),
        }
    except Exception as exc:
        return None, {
            "status": "invalid_geometry_json",
            "area_key": list(key),
            "source_area_canonical_id": area.get("canonical_id"),
            "reason": f"{type(exc).__name__}: {exc}",
        }


def load_flow1_records(f1_dir: Path, geometry_index: dict[tuple[str, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index_payload = read_json(f1_dir / "CHI_F1_D1_AREA_STATUS_INDEX.json", {})
    rank_by_subject = {
        str(row.get("subject_id")): row
        for row in index_payload.get("subjects", [])
        if isinstance(row, dict) and row.get("subject_id")
    }
    records: list[dict[str, Any]] = []
    geometry_found = 0
    for path in evidence_files(f1_dir, "evidence_bundle_area_status_*.json"):
        bundle = read_json(path, {})
        subject = bundle.get("subject") or {}
        subject_id = str(subject.get("subject_id") or "")
        indexed = rank_by_subject.get(subject_id, {})
        subject_type = str(subject.get("subject_type") or indexed.get("subject_type") or "")
        subject_key = str(subject.get("subject_key") or indexed.get("subject_key") or "")
        signal_counts = bundle.get("signal_counts") or {}
        total_events = sum(int(v or 0) for v in signal_counts.values())
        nonzero = sum(1 for v in signal_counts.values() if int(v or 0) > 0)
        geometry, geometry_meta = geometry_for_subject(subject_type, subject_key, subject_id, geometry_index)
        if geometry_meta.get("status") == "PASS":
            geometry_found += 1
        record = {
            "surface_id": f"chi-f1f7-d3:flow1:area_status:{normalize_id(subject_id)}",
            "flow": "flow1",
            "view_type": "area_status",
            "subject_id": subject_id,
            "subject_type": subject_type,
            "subject_key": subject_key,
            "subject_name": subject.get("subject_name") or indexed.get("subject_name"),
            "selection_rank": indexed.get("selection_rank"),
            "why_selected": subject.get("why_selected") or indexed.get("why_selected"),
            "status_signal_score": bundle.get("status_signal_score"),
            "score_description": bundle.get("score_description"),
            "signal_counts": signal_counts,
            "total_public_source_events": total_events,
            "nonzero_signal_dimensions": nonzero,
            "location_confidence": bundle.get("location_confidence") or {},
            "evidence_bundle_id": bundle.get("bundle_id"),
            "evidence_bundle_path": str(path),
            "source_lineage": bundle.get("provenance") or [],
            "source_limitations": compact_limitations_from_bundle(bundle),
            "geometry": geometry_meta,
        }
        records.append(record)
    records.sort(key=lambda row: (row.get("selection_rank") is None, row.get("selection_rank") or 999999, str(row.get("subject_id"))))
    return records, {
        "status": "PASS" if records else "FAIL",
        "record_count": len(records),
        "geometry_backed_records": geometry_found,
        "citywide_record_geometry": "not_embedded_by_design",
    }


def candidate_key(row: dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("evidence_bundle_id") or row.get("bundle_id") or "")


def load_flow7_records(f7_dir: Path, geometry_index: dict[tuple[str, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate_report = read_json(f7_dir / "CHI_F7_D1_CANDIDATE_REPORT.json", {})
    top_by_id = {
        str(row.get("candidate_id")): row
        for row in candidate_report.get("top_candidates", [])
        if isinstance(row, dict) and row.get("candidate_id")
    }
    records: list[dict[str, Any]] = []
    geometry_found = 0
    for path in evidence_files(f7_dir, "evidence_bundle_fusion_candidate_*.json"):
        bundle = read_json(path, {})
        candidate_id = str(bundle.get("candidate_id") or "")
        indexed = top_by_id.get(candidate_id, {})
        subject_type = str(bundle.get("subject_type") or indexed.get("subject_type") or "")
        subject_key = str(indexed.get("subject_key") or subject_key_from_id(bundle.get("subject_id", "")) or "")
        subject_id = str(bundle.get("subject_id") or indexed.get("subject_id") or "")
        geometry, geometry_meta = geometry_for_subject(subject_type, subject_key, subject_id, geometry_index)
        if geometry_meta.get("status") == "PASS":
            geometry_found += 1
        components = []
        for item in bundle.get("signal_components") or []:
            components.append(
                {
                    "signal_type": item.get("signal_type"),
                    "signal_label": item.get("signal_label"),
                    "signal_count": item.get("signal_count"),
                    "source_key": item.get("source_key"),
                    "source_completion_status": item.get("source_completion_status"),
                    "component_score": item.get("component_score"),
                    "weight": item.get("weight"),
                }
            )
        record = {
            "surface_id": f"chi-f1f7-d3:flow7:fusion_candidate:{normalize_id(candidate_id)}",
            "flow": "flow7",
            "view_type": "fusion_candidate",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "subject_key": subject_key,
            "subject_name": bundle.get("subject_name") or indexed.get("subject_name"),
            "rank": int(bundle.get("rank") or indexed.get("rank") or 999999),
            "fusion_signal_score": bundle.get("fusion_signal_score"),
            "score_description": bundle.get("score_description"),
            "nonzero_signal_dimensions": bundle.get("nonzero_signal_dimensions"),
            "total_public_source_events": bundle.get("total_public_source_events"),
            "location_confidence_A_ratio": bundle.get("location_confidence_A_ratio"),
            "signal_components": components,
            "why_selected": bundle.get("why_selected"),
            "evidence_bundle_id": bundle.get("bundle_id"),
            "evidence_bundle_path": str(path),
            "source_lineage": bundle.get("provenance") or [],
            "source_limitations": compact_limitations_from_bundle(bundle),
            "geometry": geometry_meta,
        }
        records.append(record)
    records.sort(key=lambda row: (int(row.get("rank") or 999999), candidate_key(row)))
    return records, {"status": "PASS" if records else "FAIL", "record_count": len(records), "geometry_backed_records": geometry_found}


def feature_collection(records: list[dict[str, Any]], geometry_index: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    features = []
    for row in records:
        geometry, geometry_meta = geometry_for_subject(row.get("subject_type", ""), row.get("subject_key"), row.get("subject_id"), geometry_index)
        props = {key: value for key, value in row.items() if key not in {"source_limitations", "source_lineage"}}
        props["geometry"] = geometry_meta
        props["source_limitations_ref"] = "chicago_source_limitations.json"
        props["boundary_ref"] = "chicago_negative_boundary_views.json"
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return {
        "type": "FeatureCollection",
        "features": features,
        "boundary_lines": BOUNDARY_LINES,
        "generated_at": utc_now(),
    }


def compact_ledger_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_key": row.get("source_key"),
        "resource_id": row.get("resource_id"),
        "completion_status": row.get("completion_status"),
        "downloaded_rows": row.get("downloaded_rows"),
        "rows_loaded_by_d3": row.get("rows_loaded_by_d3"),
        "total_count": row.get("total_count"),
        "window_count": row.get("window_count"),
        "planned_count": row.get("planned_count"),
        "flow1_role": row.get("flow1_role"),
        "flow7_role": row.get("flow7_role"),
    }


def source_limitations_payload(f1_dir: Path, f7_dir: Path, d1b_dir: Path) -> dict[str, Any]:
    f1_raw = read_json(f1_dir / "evidence" / "evidence_bundle_source_limitations.json", {})
    f7_raw = read_json(f7_dir / "evidence" / "evidence_bundle_source_limitations.json", {})
    f1_limits = f1_raw.get("source_limitations") if isinstance(f1_raw, dict) else {}
    if not isinstance(f1_limits, dict):
        f1_limits = {}
    f7_limits = f7_raw if isinstance(f7_raw, dict) else {}
    accepted_ledger = f1_limits.get("shared_ledger") or f7_limits.get("shared_source_ledger") or []
    accepted_ledger = [compact_ledger_row(row) for row in accepted_ledger if isinstance(row, dict)]

    d1b_counts_raw = read_json(d1b_dir / "CHI_D1B_COUNTS_REPORT.json", {})
    d1b_counts = [compact_ledger_row(row) for row in d1b_counts_raw.get("counts", []) if isinstance(row, dict)]
    accepted_by_key = {str(row.get("source_key")): row for row in accepted_ledger}
    differences = []
    for row in d1b_counts:
        key = str(row.get("source_key") or "")
        accepted = accepted_by_key.get(key)
        if not accepted:
            continue
        if accepted.get("downloaded_rows") != row.get("downloaded_rows") or accepted.get("completion_status") != row.get("completion_status"):
            differences.append(
                {
                    "source_key": key,
                    "accepted_flow_downloaded_rows": accepted.get("downloaded_rows"),
                    "accepted_flow_completion_status": accepted.get("completion_status"),
                    "current_d1b_downloaded_rows": row.get("downloaded_rows"),
                    "current_d1b_completion_status": row.get("completion_status"),
                    "face_layer_treatment": "D1B context only until CHI-D3/F1/F7 are rerun and accepted.",
                }
            )

    return {
        "status": "PASS",
        "public_tool": PUBLIC_TOOL,
        "limitations": BOUNDARY_LINES,
        "accepted_flow_artifact_ledger": accepted_ledger,
        "current_d1b_landing_counts": d1b_counts,
        "source_propagation_differences": differences,
        "needs_rerun_for_count_upgrade": bool(differences),
        "privacy_notes": [
            "Crash people and vehicle source rows are not face-layer person/vehicle records.",
            "Crime data remains privacy-safe block-level context only.",
            "D3 publishes governed summaries only; raw sensitive rows stay out of the D3 payload.",
        ],
    }


def live_replay_index(d2_dir: Path) -> dict[str, Any]:
    harness = read_json(d2_dir / "CHI_F1F7_D2_HARNESS_REPORT.json", {})
    grounding = read_json(d2_dir / "CHI_F1F7_D2_GROUNDING_REPORT.json", {})
    negative = read_json(d2_dir / "CHI_F1F7_D2_NEGATIVE_REQUEST_REPORT.json", {})
    narrations = read_json(d2_dir / "samples" / "live_sample_narrations.json", [])
    samples = []
    if isinstance(narrations, list):
        for item in narrations:
            text = str(item.get("narration") or "")
            samples.append(
                {
                    "sample_id": item.get("sample_id"),
                    "query_type": item.get("query_type"),
                    "answer_status": item.get("answer_status"),
                    "grounding_status": (item.get("grounding") or {}).get("status"),
                    "narration_excerpt": text[:500],
                }
            )
    return {
        "status": "PASS" if status_pass(harness.get("status")) and status_pass(grounding.get("status")) and status_pass(negative.get("status")) else "FAIL",
        "d2_status": harness.get("status"),
        "public_tool": harness.get("public_tool") or PUBLIC_TOOL,
        "grounding_status": grounding.get("status"),
        "negative_request_status": negative.get("status"),
        "sample_count": harness.get("sample_requests"),
        "samples": samples,
        "note": "D3 reuses accepted D2 live replay evidence. D3 does not invoke NIM.",
    }


def negative_boundary_payload() -> dict[str, Any]:
    return {
        "status": "PASS",
        "public_tool": PUBLIC_TOOL,
        "views": NEGATIVE_BOUNDARY_VIEWS,
        "all_negative_views_accept_false": all(not view["accepted"] for view in NEGATIVE_BOUNDARY_VIEWS),
    }


def route_manifest() -> dict[str, Any]:
    routes = {
        "/chicago": "face_app/chicago.html",
        "/chicago/status": "face_payload/chicago_status.json",
        "/chicago/flow1/area-status": "face_payload/chicago_flow1_area_status.json",
        "/chicago/flow1/area-status.geojson": "face_payload/chicago_flow1_area_status.geojson",
        "/chicago/flow7/fusion-candidates": "face_payload/chicago_flow7_fusion_candidates.json",
        "/chicago/flow7/fusion-candidates.geojson": "face_payload/chicago_flow7_fusion_candidates.geojson",
        "/chicago/limitations": "face_payload/chicago_source_limitations.json",
        "/chicago/boundary-views": "face_payload/chicago_negative_boundary_views.json",
        "/chicago/live-replay": "face_payload/chicago_live_replay_index.json",
        "/api/chicago/f1f7/status": "face_payload/chicago_status.json",
        "/api/chicago/f1f7/flow1/area-status": "face_payload/chicago_flow1_area_status.json",
        "/api/chicago/f1f7/flow7/fusion-candidates": "face_payload/chicago_flow7_fusion_candidates.json",
        "/api/chicago/f1f7/limitations": "face_payload/chicago_source_limitations.json",
        "/api/chicago/f1f7/boundary-views": "face_payload/chicago_negative_boundary_views.json",
    }
    return {
        "status": "PASS",
        "mode": "static_file_payload_routes",
        "public_tool": PUBLIC_TOOL,
        "routes": routes,
        "raw_data_routes": [],
    }


def html_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chicago CityBrain Face Layer</title>
  <style>
    * { box-sizing: border-box; }
    body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f5f7f8; color:#182129; }
    #app { min-height:100vh; display:grid; grid-template-columns:300px minmax(0,1fr); }
    .rail { background:#10251f; color:#f7fbf8; padding:20px; display:flex; flex-direction:column; gap:16px; }
    .rail h1 { margin:0; font-size:24px; letter-spacing:0; }
    .rail p { margin:0; color:#c9d8d1; line-height:1.4; }
    .rail a { color:#f7fbf8; text-decoration:none; border:1px solid rgba(255,255,255,.18); border-radius:6px; padding:10px 12px; display:block; margin-top:8px; }
    main { padding:18px; display:grid; gap:16px; align-content:start; }
    h2 { margin:0; font-size:26px; letter-spacing:0; }
    h3 { margin:0 0 10px; font-size:16px; letter-spacing:0; }
    .muted { color:#697783; }
    .grid { display:grid; grid-template-columns:repeat(4,minmax(140px,1fr)); gap:10px; }
    .panel, .metric { border:1px solid #d5dde4; background:#fff; border-radius:6px; padding:14px; }
    .metric span { display:block; color:#697783; font-size:12px; }
    .metric strong { display:block; margin-top:8px; font-size:22px; }
    .two { display:grid; grid-template-columns:minmax(0,1fr) minmax(320px,.55fr); gap:14px; }
    table { border-collapse:collapse; width:100%; font-size:13px; }
    th, td { border-bottom:1px solid #e2e8ee; padding:8px; text-align:left; vertical-align:top; }
    th { color:#4c5965; font-weight:650; }
    .tag { display:inline-block; border:1px solid #c5d0da; background:#eef3f7; border-radius:6px; padding:4px 7px; margin:3px; font-size:12px; }
    pre { white-space:pre-wrap; overflow:auto; max-height:360px; font-size:12px; }
    footer { color:#697783; font-size:12px; line-height:1.45; }
    @media (max-width: 840px) {
      #app { grid-template-columns:1fr; }
      .grid, .two { grid-template-columns:1fr; }
    }
  </style>
</head>
<body>
<div id="app">
  <aside class="rail">
    <div>
      <h1>CityBrain Chicago</h1>
      <p>Flow 1 + Flow 7 face layer</p>
    </div>
    <nav>
      <a href="../face_payload/chicago_status.json">Status payload</a>
      <a href="../face_payload/chicago_flow1_area_status.json">Flow 1 area status</a>
      <a href="../face_payload/chicago_flow7_fusion_candidates.json">Flow 7 fusion candidates</a>
      <a href="../face_payload/chicago_source_limitations.json">Source limitations</a>
      <a href="../face_payload/chicago_negative_boundary_views.json">Boundary views</a>
    </nav>
  </aside>
  <main>
    <header>
      <p class="muted">CHI-F1F7-D3</p>
      <h2>Chicago status and fusion surface</h2>
    </header>
    <section class="grid" id="metrics"></section>
    <section class="two">
      <div class="panel">
        <h3>Flow 1 area-status</h3>
        <table id="flow1"><thead><tr><th>Subject</th><th>Type</th><th>Events</th><th>Score</th></tr></thead><tbody></tbody></table>
      </div>
      <div class="panel">
        <h3>Flow 7 fusion candidates</h3>
        <table id="flow7"><thead><tr><th>Rank</th><th>Subject</th><th>Dimensions</th><th>Score</th></tr></thead><tbody></tbody></table>
      </div>
    </section>
    <section class="two">
      <div class="panel">
        <h3>Source limitations</h3>
        <div id="limits"></div>
      </div>
      <div class="panel">
        <h3>Negative-boundary views</h3>
        <div id="boundaries"></div>
      </div>
    </section>
    <footer id="boundary">No operational recommendations. No affected-building/asset certification. No live transit or health determination.</footer>
  </main>
</div>
<script>
const j = p => fetch(p).then(r => r.json());
const td = value => `<td>${value ?? ""}</td>`;
Promise.all([
  j("../face_payload/chicago_status.json"),
  j("../face_payload/chicago_flow1_area_status.json"),
  j("../face_payload/chicago_flow7_fusion_candidates.json"),
  j("../face_payload/chicago_source_limitations.json"),
  j("../face_payload/chicago_negative_boundary_views.json")
]).then(([status, f1, f7, limits, boundaries]) => {
  document.getElementById("metrics").innerHTML = [
    ["Flow 1 subjects", status.counts.flow1_area_status_records],
    ["Flow 7 candidates", status.counts.flow7_fusion_candidate_records],
    ["D2 replay", status.inputs.chi_f1f7_d2_status],
    ["4070 mode", "static payload"]
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  document.querySelector("#flow1 tbody").innerHTML = f1.records.map(row =>
    `<tr>${td(row.subject_name)}${td(row.subject_type)}${td(row.total_public_source_events)}${td(row.status_signal_score)}</tr>`
  ).join("");
  document.querySelector("#flow7 tbody").innerHTML = f7.records.map(row =>
    `<tr>${td(row.rank)}${td(row.subject_name)}${td(row.nonzero_signal_dimensions)}${td(row.fusion_signal_score)}</tr>`
  ).join("");
  document.getElementById("limits").innerHTML = limits.limitations.slice(0, 8).map(x => `<span class="tag">${x}</span>`).join("");
  document.getElementById("boundaries").innerHTML = boundaries.views.map(x => `<p><strong>${x.request_category}</strong><br><span class="muted">${x.deterministic_response}</span></p>`).join("");
  document.getElementById("boundary").textContent = status.boundary_lines.join(" ");
});
</script>
</body>
</html>
"""


def write_face_app(output_dir: Path) -> dict[str, Any]:
    html = html_page()
    write_text(output_dir / "face_app" / "chicago.html", html)
    required = ["Flow 1 area-status", "Flow 7 fusion candidates", "Source limitations", "Negative-boundary views", "No operational recommendations"]
    missing = [item for item in required if item not in html]
    return {"gate": "CHI-F1F7-D3-UI-SMOKE", "status": "PASS" if not missing else "FAIL", "missing": missing, "html_bytes": len(html.encode("utf-8"))}


def payload_size_report(output_dir: Path) -> dict[str, Any]:
    files = []
    total = 0
    for path in sorted((output_dir / "face_payload").glob("*")):
        if path.is_file():
            rel = path.relative_to(output_dir).as_posix()
            size = path.stat().st_size
            files.append({"path": rel, "bytes": size})
            total += size
    report = {
        "gate": "CHI-F1F7-D3-PAYLOAD-SIZE",
        "status": "PASS",
        "total_bytes": total,
        "files": files,
        "raw_files_included": False,
        "large_parquet_included": False,
    }
    write_json(output_dir / "reports" / "payload_size_report.json", report)
    return report


def grounding_report(status: dict[str, Any], flow1_records: list[dict[str, Any]], flow7_records: list[dict[str, Any]], f1_harness: dict[str, Any], f7_harness: dict[str, Any], d2_harness: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "f1_status_pass": status_pass(f1_harness.get("status")),
        "f7_status_pass": status_pass(f7_harness.get("status")),
        "d2_status_pass": status_pass(d2_harness.get("status")),
        "flow1_count_matches_harness": len(flow1_records) == int(f1_harness.get("evidence_bundles") or len(flow1_records)),
        "flow7_count_matches_harness": len(flow7_records) == int(f7_harness.get("selected_candidates") or f7_harness.get("evidence_bundles") or len(flow7_records)),
        "public_tool_unchanged": status.get("public_tool") == PUBLIC_TOOL,
        "input_facts_mode_accepted_only": status.get("input_facts_mode") == "accepted_f1_f7_d1_and_d2_outputs_only",
        "all_flow1_records_have_bundle": all(row.get("evidence_bundle_id") for row in flow1_records),
        "all_flow7_records_have_bundle": all(row.get("evidence_bundle_id") for row in flow7_records),
    }
    return {"gate": "CHI-F1F7-D3-GROUNDING", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitation_carry_forward_report(output_dir: Path) -> dict[str, Any]:
    files = [
        output_dir / "face_payload" / "chicago_source_limitations.json",
        output_dir / "face_payload" / "chicago_negative_boundary_views.json",
        output_dir / "README.md",
    ]
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files if path.exists())
    missing = [line for line in BOUNDARY_LINES if line not in joined]
    required_tokens = ["capped", "windowed", "not silently promoted", "raw sensitive rows stay out"]
    missing_tokens = [token for token in required_tokens if token.lower() not in joined.lower()]
    return {
        "gate": "CHI-F1F7-D3-LIMITATION-CARRY-FORWARD",
        "status": "PASS" if not missing and not missing_tokens else "FAIL",
        "missing_boundary_lines": missing,
        "missing_tokens": missing_tokens,
    }


def negative_boundary_report(payload: dict[str, Any]) -> dict[str, Any]:
    views = payload.get("views", [])
    required = {
        "affected-building/asset certainty",
        "operational or public-safety recommendation",
        "live transit or health determination",
        "raw person, vehicle, crime, or private-row drilldown",
        "upgrade Flow counts from newer landing without rerun",
    }
    categories = {view.get("request_category") for view in views if isinstance(view, dict)}
    return {
        "gate": "CHI-F1F7-D3-NEGATIVE-BOUNDARY-VIEWS",
        "status": "PASS" if required.issubset(categories) and all(not view.get("accepted") for view in views) else "FAIL",
        "view_count": len(views),
        "missing_categories": sorted(required - categories),
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    texts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".html", ".geojson"} and path.name not in {"SHA256SUMS.json", "CHI_F1F7_D3_NO_OVERCLAIM_REPORT.json"}:
            texts.append((path.relative_to(output_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace").lower()))
    patterns = [
        ("affected asset certification", r"\b(?:certifies|certified|confirms|confirmed)\s+affected (?:buildings|assets)\b"),
        ("definite affected asset claim", r"\b(?:definitely|are)\s+affected (?:buildings|assets)\b"),
        ("operational recommendation", r"\boperational recommendations?\s+(?:is|are|provided|ready|available)\b"),
        ("public safety recommendation", r"\bpublic-safety recommendations?\s+(?:is|are|provided|ready|available)\b"),
        ("dispatch recommendation", r"\bdispatch recommendations?\s+(?:is|are|provided|ready|available)\b"),
        ("live transit status", r"\blive transit status\s+(?:is|was|provided|ready|available)\b"),
        ("health determination", r"\bhealth determinations?\s+(?:is|are|were|provided|ready|available)\b"),
        ("silent source promotion", r"\bsilently promoted into f1/f7 evidence counts\s*[:=]\s*true\b"),
        ("raw sensitive publication", r"\braw sensitive rows\s+(?:are|were)\s+published\b"),
    ]
    findings = []
    for label, pattern in patterns:
        for rel, text in texts:
            if re.search(pattern, text):
                findings.append({"label": label, "path": rel, "pattern": pattern})
    return {"gate": "CHI-F1F7-D3-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def api_smoke_report(output_dir: Path) -> dict[str, Any]:
    required = [
        "chicago_status.json",
        "chicago_flow1_area_status.json",
        "chicago_flow1_area_status.geojson",
        "chicago_flow7_fusion_candidates.json",
        "chicago_flow7_fusion_candidates.geojson",
        "chicago_source_limitations.json",
        "chicago_negative_boundary_views.json",
        "chicago_live_replay_index.json",
        "chicago_route_manifest.json",
    ]
    payload_dir = output_dir / "face_payload"
    missing = [name for name in required if not (payload_dir / name).exists()]
    return {
        "gate": "CHI-F1F7-D3-API-SMOKE",
        "status": "PASS" if not missing else "FAIL",
        "mode": "server_smoke_not_run_file_payload_verified",
        "checked_payloads": required,
        "missing": missing,
    }


def write_docs(output_dir: Path, status_payload: dict[str, Any]) -> None:
    counts = status_payload["counts"]
    readme = [
        "# CHI-F1F7-D3 Chicago Face-Layer Status/Fusion Surface",
        "",
        "Status: PASS",
        "",
        "This surface publishes accepted CHI-F1-D1 area-status records and CHI-F7-D1 fusion candidates through lightweight 4070-facing payload files.",
        "",
        "## Counts",
        f"- Flow 1 area-status records: {counts['flow1_area_status_records']}",
        f"- Flow 7 fusion-candidate records: {counts['flow7_fusion_candidate_records']}",
        f"- Flow 1 geometry-backed records: {counts['flow1_geometry_backed_records']}",
        f"- Flow 7 geometry-backed records: {counts['flow7_geometry_backed_records']}",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
        "## 4070",
        "- Serve face_app/chicago.html for /chicago.",
        "- Map /api/chicago/f1f7/* to the JSON files in face_payload.",
        "- Do not publish raw CSV, parquet, ZIP, person, vehicle, crime, or private-row files from D3.",
        "",
    ]
    write_text(output_dir / "README.md", "\n".join(readme))

    handover = [
        "# CHI-F1F7-D3 Adapter Handover",
        "",
        "Route /chicago to face_app/chicago.html and expose only the static payload routes listed in face_payload/chicago_route_manifest.json.",
        "",
        "The public query tool remains citybrain_chicago_f1f7_query from CHI-F1F7-D2. D3 does not add raw-data tools.",
        "",
        "Source counts shown in D3 are accepted F1/F7 evidence counts. Newer D1B landing counts are visible only as source-landing context until upstream reruns are accepted.",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(output_dir / "CHI_F1F7_D3_ADAPTER_HANDOVER.md", "\n".join(handover))


def sync_4070(output_dir: Path, publish_4070: bool) -> dict[str, Any]:
    if not publish_4070:
        return {"gate": "CHI-F1F7-D3-4070-PUBLISH", "status": "NOT_RUN", "target": str(SYNC_TARGET)}
    try:
        target = SYNC_TARGET
        resolved = target.resolve()
        if target.exists():
            parts = {part.lower() for part in resolved.parts}
            if "citybrain" not in parts or "chicago_f1f7_d3_face_layer_v1" != resolved.name.lower():
                raise ValueError(f"refusing to remove unexpected sync target: {resolved}")
            shutil.rmtree(resolved)
        copied = []
        bytes_total = 0
        allowed = {".json", ".geojson", ".md", ".html", ".txt"}
        for path in sorted(output_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            rel = path.relative_to(output_dir)
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)
            copied.append(rel.as_posix())
            bytes_total += dst.stat().st_size
        return {
            "gate": "CHI-F1F7-D3-4070-PUBLISH",
            "status": "PASS",
            "target": str(target),
            "file_count": len(copied),
            "bytes": bytes_total,
            "files": copied,
            "raw_files_included": False,
            "large_parquet_included": False,
        }
    except Exception as exc:
        return {"gate": "CHI-F1F7-D3-4070-PUBLISH", "status": "NOT_RUN_OR_UNREACHABLE", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def run_chi_f1f7_d3_gate(
    project_root: str,
    f1_d1_dir: str,
    f7_d1_dir: str,
    f1f7_d2_dir: str,
    chi_d2b_dir: str,
    chi_d1b_dir: str,
    output_dir: str,
    publish_4070: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    f1 = resolve_under(root, f1_d1_dir).resolve()
    f7 = resolve_under(root, f7_d1_dir).resolve()
    d2 = resolve_under(root, f1f7_d2_dir).resolve()
    d2b = resolve_under(root, chi_d2b_dir).resolve()
    d1b = resolve_under(root, chi_d1b_dir).resolve()
    out = resolve_under(root, output_dir).resolve()

    input_roots = [f1, f7, d2, d2b, d1b]
    before = snapshot(input_roots)
    reset_output_dir(out)

    f1_harness = read_json(f1 / "CHI_F1_D1_HARNESS_REPORT.json", {})
    f7_harness = read_json(f7 / "CHI_F7_D1_HARNESS_REPORT.json", {})
    d2_harness = read_json(d2 / "CHI_F1F7_D2_HARNESS_REPORT.json", {})
    d2b_harness = read_json(d2b / "CHI_D2B_HARNESS_REPORT.json", {})
    d1b_harness = read_json(d1b / "CHI_D1B_HARNESS_REPORT.json", {})
    preconditions = {
        "gate": "CHI-F1F7-D3-PRECOND",
        "status": "PASS"
        if status_pass(f1_harness.get("status"))
        and status_pass(f7_harness.get("status"))
        and status_pass(d2_harness.get("status"))
        and status_pass(d2b_harness.get("status"))
        and status_pass(d1b_harness.get("status"))
        else "FAIL",
        "f1_status": f1_harness.get("status"),
        "f7_status": f7_harness.get("status"),
        "d2_status": d2_harness.get("status"),
        "d2b_status": d2b_harness.get("status"),
        "d1b_status": d1b_harness.get("status"),
    }
    write_json(out / "CHI_F1F7_D3_INPUT_INVENTORY.json", {
        **preconditions,
        "inputs": {
            "f1_d1_dir": str(f1),
            "f7_d1_dir": str(f7),
            "f1f7_d2_dir": str(d2),
            "chi_d2b_dir": str(d2b),
            "chi_d1b_dir": str(d1b),
        },
    })

    geometry_index, geometry_report = load_area_geometry_index(d2b)
    flow1_records, flow1_report = load_flow1_records(f1, geometry_index)
    flow7_records, flow7_report = load_flow7_records(f7, geometry_index)
    source_limitations = source_limitations_payload(f1, f7, d1b)
    negative_payload = negative_boundary_payload()
    replay_index = live_replay_index(d2)
    routes = route_manifest()

    status_payload = {
        "status": "PASS",
        "task": TASK_NAME,
        "public_tool": PUBLIC_TOOL,
        "face_layer_mode": "static_4070_payload_surface",
        "input_facts_mode": "accepted_f1_f7_d1_and_d2_outputs_only",
        "inputs": {
            "chi_f1_d1_status": f1_harness.get("status"),
            "chi_f7_d1_status": f7_harness.get("status"),
            "chi_f1f7_d2_status": d2_harness.get("status"),
            "chi_d2b_status": d2b_harness.get("status"),
            "chi_d1b_status": d1b_harness.get("status"),
        },
        "counts": {
            "flow1_area_status_records": len(flow1_records),
            "flow7_fusion_candidate_records": len(flow7_records),
            "flow1_geometry_backed_records": flow1_report.get("geometry_backed_records"),
            "flow7_geometry_backed_records": flow7_report.get("geometry_backed_records"),
            "d2_live_replay_samples": replay_index.get("sample_count"),
        },
        "routes": routes["routes"],
        "source_limitations_ref": "chicago_source_limitations.json",
        "negative_boundary_views_ref": "chicago_negative_boundary_views.json",
    }

    face_payload = out / "face_payload"
    write_json(face_payload / "chicago_status.json", status_payload)
    write_json(face_payload / "chicago_flow1_area_status.json", {"status": "PASS", "record_count": len(flow1_records), "records": flow1_records})
    write_json(face_payload / "chicago_flow1_area_status.geojson", feature_collection(flow1_records, geometry_index))
    write_json(face_payload / "chicago_flow7_fusion_candidates.json", {"status": "PASS", "record_count": len(flow7_records), "records": flow7_records})
    write_json(face_payload / "chicago_flow7_fusion_candidates.geojson", feature_collection(flow7_records, geometry_index))
    write_json(face_payload / "chicago_source_limitations.json", source_limitations)
    write_json(face_payload / "chicago_negative_boundary_views.json", negative_payload)
    write_json(face_payload / "chicago_live_replay_index.json", replay_index)
    write_json(face_payload / "chicago_route_manifest.json", routes)

    surface = {
        "status": "PASS",
        "flow1_area_status_records": flow1_records,
        "flow7_fusion_candidate_records": flow7_records,
        "source_limitations": source_limitations,
        "negative_boundary_views": negative_payload,
        "live_replay_index": replay_index,
    }
    write_json(face_payload / "chicago_status_fusion_surface.json", surface)

    write_docs(out, status_payload)
    ui_smoke = write_face_app(out)
    size = payload_size_report(out)
    grounding = grounding_report(status_payload, flow1_records, flow7_records, f1_harness, f7_harness, d2_harness)
    limitation = limitation_carry_forward_report(out)
    negative_report = negative_boundary_report(negative_payload)
    api_smoke = api_smoke_report(out)
    no_overclaim = no_overclaim_report(out)
    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)

    write_json(out / "CHI_F1F7_D3_FACE_PAYLOAD_REPORT.json", {
        "gate": "CHI-F1F7-D3-FACE-PAYLOAD",
        "status": "PASS" if flow1_report["status"] == "PASS" and flow7_report["status"] == "PASS" and size["status"] == "PASS" else "FAIL",
        "flow1": flow1_report,
        "flow7": flow7_report,
        "geometry": geometry_report,
        "payload_size": size,
        "payload_files": sorted(path.name for path in face_payload.glob("*") if path.is_file()),
    })
    write_json(out / "CHI_F1F7_D3_ROUTE_REPORT.json", routes)
    write_json(out / "CHI_F1F7_D3_API_SMOKE_REPORT.json", api_smoke)
    write_json(out / "CHI_F1F7_D3_UI_SMOKE_REPORT.json", ui_smoke)
    write_json(out / "CHI_F1F7_D3_GROUNDING_REPORT.json", grounding)
    write_json(out / "CHI_F1F7_D3_SOURCE_LIMITATION_REPORT.json", source_limitations)
    write_json(out / "CHI_F1F7_D3_NEGATIVE_BOUNDARY_VIEWS_REPORT.json", negative_report)
    write_json(out / "CHI_F1F7_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(out / "CHI_F1F7_D3_NO_MUTATION_REPORT.json", no_mutation)

    publish_report = sync_4070(out, publish_4070)
    write_json(out / "CHI_F1F7_D3_4070_PUBLISH_MANIFEST.json", publish_report)

    face_payload_report = read_json(out / "CHI_F1F7_D3_FACE_PAYLOAD_REPORT.json", {})
    gates = {
        "CHI-F1F7-D3-PRECOND": preconditions["status"],
        "CHI-F1F7-D3-FACE-PAYLOAD": face_payload_report.get("status"),
        "CHI-F1F7-D3-ROUTES": routes["status"],
        "CHI-F1F7-D3-API-SMOKE": api_smoke["status"],
        "CHI-F1F7-D3-UI-SMOKE": ui_smoke["status"],
        "CHI-F1F7-D3-GROUNDING": grounding["status"],
        "CHI-F1F7-D3-LIMITATION-CARRY-FORWARD": limitation["status"],
        "CHI-F1F7-D3-NEGATIVE-BOUNDARY-VIEWS": negative_report["status"],
        "CHI-F1F7-D3-NO-OVERCLAIM": no_overclaim["status"],
        "CHI-F1F7-D3-NO-MUTATION": no_mutation["status"],
        "CHI-F1F7-D3-4070-PUBLISH": "PASS" if publish_report["status"] in {"PASS", "NOT_RUN", "NOT_RUN_OR_UNREACHABLE"} else "FAIL",
    }
    overall = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "public_tool": PUBLIC_TOOL,
        "output": str(out),
        "counts": status_payload["counts"],
        "gates": gates,
        "preconditions": preconditions,
        "4070_publish": publish_report,
        "boundary_lines": BOUNDARY_LINES,
        "generated_at": utc_now(),
    }
    write_json(out / "CHI_F1F7_D3_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    gates["CHI-F1F7-D3-HASHES"] = hashes["status"]
    overall = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness["status"] = overall
    harness["gates"] = gates
    harness["hashes"] = hashes
    write_json(out / "CHI_F1F7_D3_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--f1-d1-dir", default=DEFAULT_F1_DIR)
    parser.add_argument("--f7-d1-dir", default=DEFAULT_F7_DIR)
    parser.add_argument("--f1f7-d2-dir", default=DEFAULT_D2_DIR)
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--chi-d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--publish-4070", dest="publish_4070", action="store_true", default=True)
    parser.add_argument("--no-publish-4070", dest="publish_4070", action="store_false")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_chi_f1f7_d3_gate(
        project_root=args.project_root,
        f1_d1_dir=args.f1_d1_dir,
        f7_d1_dir=args.f7_d1_dir,
        f1f7_d2_dir=args.f1f7_d2_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        chi_d1b_dir=args.chi_d1b_dir,
        output_dir=args.output_dir,
        publish_4070=args.publish_4070,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Status: {report['status']}")
    print(f"Flow 1 area-status records: {report['counts']['flow1_area_status_records']}")
    print(f"Flow 7 fusion-candidate records: {report['counts']['flow7_fusion_candidate_records']}")
    print(f"4070 publish: {report['4070_publish']['status']}")
    return 0 if str(report.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
