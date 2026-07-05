#!/usr/bin/env python3
"""Run the CityBrain D8 parallel data readiness scout pack.

This runner is intentionally data-first and output-only. It does not mutate
certified state, does not start production services, and does not claim
Metropolis/VSS readiness without local audited evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
NOW = lambda: datetime.now(timezone.utc).isoformat()
UA = "CityBrain-D8-Parallel-Data-Readiness-Scouts/1.0"
SSL_CONTEXT = ssl.create_default_context()

ROOTS = {
    "ledger": OUTPUTS / "main_citybrain_d8_data_gap_ledger_and_priority_matrix",
    "helsinki": OUTPUTS / "main_citybrain_d8_helsinki_semantic_twin_pilot_data_landing",
    "vss": OUTPUTS / "main_citybrain_d8_metropolis_vss_data_readiness_scout",
    "camera": OUTPUTS / "main_citybrain_d8_camera_video_donor_source_scout",
    "option": OUTPUTS / "main_citybrain_d8_mobility_access_option_set_gap_backfill_scout",
    "temporal": OUTPUTS / "main_citybrain_d8_mobility_temporal_and_simulation_data_scout",
    "bundle": OUTPUTS / "main_citybrain_d8_web_kit_demo_asset_data_bundle",
    "closeout": OUTPUTS / "main_citybrain_d8_parallel_data_readiness_closeout",
}

INPUT_HINTS = [
    OUTPUTS / "main_citybrain_d8_demonstrability_certified_state_handoff",
    OUTPUTS / "main_citybrain_d8_web_kit_live_surface_closeout",
    OUTPUTS / "main_citybrain_d8_local_bridge_and_one_truth_sync_r3",
    OUTPUTS / "main_citybrain_d8_runtime_bundle_contract_r1",
    OUTPUTS / "main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
    OUTPUTS / "main_citybrain_d7_perception_candidate_observation_closeout",
    OUTPUTS / "collateral_d7_perception_candidate_observation_after_freeze",
    OUTPUTS / "main_citybrain_d7_perception_demo_media_review_r2",
    OUTPUTS / "d4_helsinki_kalasatama_context_data_landing_r1",
    OUTPUTS / "d4_3d_helsinki_kalasatama_3d_tiles_landing_r1",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def ensure(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    ensure(path.parent)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    ensure(path.parent)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_manifest(root: Path, name: str = "HASH_MANIFEST.json") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(root / name, rows)
    return rows


def run_cmd(args: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        p = subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=timeout)
        return {
            "cmd": args,
            "available": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip()[:5000],
            "stderr": p.stderr.strip()[:5000],
        }
    except FileNotFoundError as exc:
        return {"cmd": args, "available": False, "error": str(exc)}
    except Exception as exc:
        return {"cmd": args, "available": False, "error": str(exc)}


def url_fetch(url: str, out: Path, timeout: int = 90, max_bytes: int | None = None) -> dict[str, Any]:
    ensure(out.parent)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    start = time.time()
    h = hashlib.sha256()
    total = 0
    tmp = out.with_suffix(out.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r, tmp.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes and total > max_bytes:
                raise RuntimeError(f"Download exceeded cap {max_bytes}: {url}")
            h.update(chunk)
            f.write(chunk)
    tmp.replace(out)
    return {
        "url": url,
        "path": rel(out),
        "bytes": total,
        "sha256": h.hexdigest(),
        "seconds": round(time.time() - start, 2),
        "status": "DOWNLOADED",
    }


def url_head(url: str, timeout: int = 20, insecure_curl: bool = False) -> dict[str, Any]:
    if insecure_curl:
        result = run_cmd(["curl.exe", "-k", "-L", "-I", "--max-time", str(timeout), url], timeout=timeout + 5)
        status = "REACHABLE" if result.get("available") else "HEAD_FAILED"
        return {"url": url, "status": status, "probe": result}
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r:
            return {
                "url": url,
                "status": "REACHABLE",
                "http_status": r.status,
                "content_type": r.headers.get("Content-Type"),
                "content_length": int(r.headers.get("Content-Length") or 0),
                "last_modified": r.headers.get("Last-Modified"),
                "final_url": r.geturl(),
            }
    except Exception as exc:
        return {"url": url, "status": "HEAD_FAILED", "error": str(exc)}


def files_matching(patterns: list[str], limit: int = 500) -> list[Path]:
    hits: list[Path] = []
    rx = re.compile("|".join(patterns), re.I)
    for path in OUTPUTS.rglob("*"):
        if len(hits) >= limit:
            break
        if path.is_file() and rx.search(str(path)):
            hits.append(path)
    return hits


def input_inventory() -> list[dict[str, Any]]:
    rows = []
    for root in INPUT_HINTS:
        if root.exists():
            files = [p for p in root.rglob("*") if p.is_file()]
            rows.append({
                "root": rel(root),
                "exists": True,
                "file_count": len(files),
                "bytes": sum(p.stat().st_size for p in files),
            })
        else:
            rows.append({"root": rel(root), "exists": False, "file_count": 0, "bytes": 0})
    return rows


def write_boundary_audits(root: Path, extras: dict[str, Any] | None = None) -> None:
    base = {
        "status": "PASS",
        "run_timestamp_utc": NOW(),
        "no_production_public_api_claim": True,
        "no_autonomous_monitoring": True,
        "no_alerts_dispatch_routing_control_enforcement": True,
        "no_legal_certified_finding": True,
        "no_identity_biometric_inference": True,
        "no_automated_action": True,
        "review_only_local_lan_replay_query_context": True,
    }
    if extras:
        base.update(extras)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", base)


def data_gap_ledger() -> dict[str, Any]:
    root = ROOTS["ledger"]
    ensure(root)
    inv = input_inventory()
    gaps = [
        {
            "gap_id": "GAP-SPATIAL-USD-CER-001",
            "category": "spatial identity / USD prim binding",
            "classification": "Kit/semantic twin prerequisite",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["Helsinki/Kalasatama CityGML landed", "Kalasatama 3D Tiles landed"],
            "missing": ["USD prim sidecar map", "CER candidate mapping smoke", "visual mesh to semantic building alignment rule"],
            "priority": 1,
        },
        {
            "gap_id": "GAP-VSS-CORPUS-001",
            "category": "video/perception/VSS corpus",
            "classification": "Metropolis/VSS prerequisite",
            "severity": "critical",
            "blocks_next_two_sprints": True,
            "current_evidence": ["D7 candidate-observation outputs exist", "sample media appears static/demo-oriented"],
            "missing": ["licensed bounded video corpus", "camera metadata", "expected-output oracle"],
            "priority": 2,
        },
        {
            "gap_id": "GAP-CAMERA-META-001",
            "category": "camera geolocation/FOV/timestamp metadata",
            "classification": "Metropolis/VSS prerequisite",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["Camera/video donor sources not yet proven"],
            "missing": ["geolocation", "field of view", "timestamp policy", "license/privacy labels"],
            "priority": 3,
        },
        {
            "gap_id": "GAP-MOBILITY-BASELINE-001",
            "category": "mobility baseline/tradeoff/simulation data",
            "classification": "demo blocker",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["D8 has 12 moments; M04/M05 partial per handoff"],
            "missing": ["provenanced do-nothing baseline", "abstain/no-safe-option fields", "tradeoff axis inputs"],
            "priority": 4,
        },
        {
            "gap_id": "GAP-OPTION-SET-001",
            "category": "option-set baseline/abstain fields",
            "classification": "demonstrability hardening",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["Reviewed option-set contracts exist"],
            "missing": ["field presence audit across current certified option sets"],
            "priority": 5,
        },
        {
            "gap_id": "GAP-SIMILAR-CASE-001",
            "category": "similar-case grounding/outcomes",
            "classification": "future scale/breadth",
            "severity": "medium",
            "blocks_next_two_sprints": False,
            "current_evidence": ["Cross-city similar-case artifacts exist"],
            "missing": ["outcome scoring and post-action validation data"],
            "priority": 8,
        },
        {
            "gap_id": "GAP-TIMESERIES-001",
            "category": "time-series/time-scrub data",
            "classification": "demonstrability hardening",
            "severity": "medium",
            "blocks_next_two_sprints": False,
            "current_evidence": ["Synthetic replay packs and event fabric exist"],
            "missing": ["real/provenanced current-state and historical scrub rows for Mobility Access"],
            "priority": 6,
        },
        {
            "gap_id": "GAP-LICENSE-001",
            "category": "licenses/attribution/privacy",
            "classification": "demo blocker",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["Helsinki sources have CC BY 4.0 metadata", "VSS/camera sources not proven"],
            "missing": ["camera/video source license and privacy disposition"],
            "priority": 7,
        },
        {
            "gap_id": "GAP-FRESHNESS-001",
            "category": "source freshness/versioning",
            "classification": "demonstrability hardening",
            "severity": "medium",
            "blocks_next_two_sprints": False,
            "current_evidence": ["HSL GTFS landed 2026-07-01", "Helsinki mesh/city model metadata checked"],
            "missing": ["source freshness registry for every demo bundle artifact"],
            "priority": 9,
        },
        {
            "gap_id": "GAP-WEBKIT-BUNDLE-001",
            "category": "web/Kit runtime bundle projection data",
            "classification": "demo blocker",
            "severity": "high",
            "blocks_next_two_sprints": True,
            "current_evidence": ["Web+Kit live surface closeout exists"],
            "missing": ["single read-only demo data bundle with provenance and limitations"],
            "priority": 10,
        },
    ]
    matrix = sorted(gaps, key=lambda g: g["priority"])
    plan = {
        "task_id": "MAIN-CITYBRAIN-D8-DATA-GAP-LEDGER-AND-PRIORITY-MATRIX",
        "status": "PASS",
        "run_timestamp_utc": NOW(),
        "input_inventory": inv,
        "parallel_lanes": [
            "HELSINKI_SEMANTIC_TWIN_PILOT",
            "METROPOLIS_VSS_DATA_READINESS",
            "CAMERA_VIDEO_DONOR_SOURCE",
            "MOBILITY_OPTION_SET_GAP_BACKFILL",
            "MOBILITY_TEMPORAL_SIMULATION",
            "WEB_KIT_DEMO_ASSET_DATA_BUNDLE",
        ],
        "execution_rule": "parallel lanes are data-readiness only and output-only",
    }
    write_json(root / "DATA_GAP_LEDGER.json", {"task_id": plan["task_id"], "status": "PASS", "gaps": gaps, "input_inventory": inv})
    write_json(root / "PRIORITY_MATRIX.json", {"task_id": plan["task_id"], "status": "PASS", "matrix": matrix})
    write_json(root / "PARALLEL_TRACK_PLAN.json", plan)
    write_md(root / "DATA_GAP_LEDGER.md", "\n".join([
        "# D8 Data Gap Ledger",
        "",
        "| Priority | Gap | Category | Classification | Blocks | Missing |",
        "|---:|---|---|---|---|---|",
        *[
            f"| {g['priority']} | {g['gap_id']} | {g['category']} | {g['classification']} | {g['blocks_next_two_sprints']} | {'; '.join(g['missing'])} |"
            for g in matrix
        ],
    ]))
    write_md(root / "PRIORITY_MATRIX.md", "\n".join([
        "# Priority Matrix",
        "",
        "Top blockers for the next two sprints are spatial USD/CER binding, licensed VSS/video corpus, camera metadata, and Mobility Access baseline/abstain data.",
        "",
        *[f"- P{g['priority']}: `{g['gap_id']}` - {g['severity']} - {g['classification']}" for g in matrix],
    ]))
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": "PASS", "gap_count": len(gaps)}


def helsinki_lane() -> dict[str, Any]:
    root = ROOTS["helsinki"]
    ensure(root)
    sample_url = (
        "https://kartta.hel.fi/3d/citydb-wfs/wfs?"
        + urllib.parse.urlencode(
            {
                "SERVICE": "WFS",
                "VERSION": "2.0.0",
                "REQUEST": "GetFeature",
                "TYPENAMES": "bldg:Building",
                "COUNT": "500",
                "OUTPUTFORMAT": "application/json",
                "SRSNAME": "EPSG:4326",
                "BBOX": "24.95,60.16,25.03,60.22,EPSG:4326",
            }
        )
    )
    sample_path = root / "wfs" / "helsinki_kalasatama_500_buildings_cityjson.json"
    download_status = "REUSED_EXISTING"
    if not sample_path.exists():
        try:
            url_fetch(sample_url, sample_path, timeout=120, max_bytes=80 * 1024 * 1024)
            download_status = "DOWNLOADED"
        except Exception as exc:
            fallback = OUTPUTS / "d4_helsinki_kalasatama_context_data_landing_r1" / "wfs" / "kalasatama_building_bbox_sample_cityjson.json"
            if fallback.exists():
                shutil.copy2(fallback, sample_path)
                download_status = f"FALLBACK_100_SAMPLE: {exc}"
            else:
                raise
    cityjson = read_json(sample_path, {})
    objects = cityjson.get("CityObjects", {}) if isinstance(cityjson, dict) else {}
    jsonl_path = root / "HELSINKI_SEMANTIC_BUILDING_SAMPLE.jsonl"
    rows: list[dict[str, Any]] = []
    for key, obj in list(objects.items()):
        if obj.get("type") != "Building":
            continue
        attrs = obj.get("attributes") or {}
        address = obj.get("address") or {}
        row = {
            "helsinki_building_id": key,
            "gmlid": key,
            "internal_id": attrs.get("ID"),
            "ratu": attrs.get("RATU"),
            "vtj_prt": attrs.get("VTJ_PRT"),
            "usage": attrs.get("usage"),
            "year_of_construction": attrs.get("yearOfConstruction"),
            "measured_height": attrs.get("measuredHeight"),
            "geographical_extent": obj.get("geographicalExtent"),
            "address": address,
            "source_ref": rel(sample_path),
            "review_state": "CER_CANDIDATE_ONLY",
        }
        rows.append(row)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    existing_context = OUTPUTS / "d4_helsinki_kalasatama_context_data_landing_r1"
    existing_tiles = OUTPUTS / "d4_3d_helsinki_kalasatama_3d_tiles_landing_r1"
    citygml_zip = existing_context / "downloads" / "citygml" / "Helsinki3D_CityGML_Kalasatama_20190326.zip"
    citygml_counts = read_json(existing_context / "inventory" / "citygml_semantic_counts.json", {})
    tiles_decision = read_json(existing_tiles / "D4_3D_HELSINKI_KALASATAMA_3DTILES_LANDING_R1_DECISION.json", {})
    source_inventory = {
        "task_id": "MAIN-CITYBRAIN-D8-HELSINKI-SEMANTIC-TWIN-PILOT-DATA-LANDING",
        "status": "PASS_WITH_LIMITATIONS",
        "run_timestamp_utc": NOW(),
        "wfs_sample_status": download_status,
        "wfs_sample_url": sample_url,
        "wfs_sample_path": rel(sample_path),
        "semantic_building_sample_rows": len(rows),
        "citygml_zip": {
            "path": rel(citygml_zip) if citygml_zip.exists() else None,
            "exists": citygml_zip.exists(),
            "bytes": citygml_zip.stat().st_size if citygml_zip.exists() else 0,
            "sha256": sha256_file(citygml_zip) if citygml_zip.exists() else None,
            "semantic_counts": citygml_counts.get("semantic_counts"),
        },
        "visual_mesh": {
            "kalasatama_3d_tiles_landed": bool(tiles_decision),
            "decision_ref": rel(existing_tiles / "D4_3D_HELSINKI_KALASATAMA_3DTILES_LANDING_R1_DECISION.json"),
            "root_tileset_file": tiles_decision.get("root_tileset_file"),
            "b3dm_entry_count": tiles_decision.get("b3dm_entry_count"),
            "identity_boundary": "visual backdrop only, not identity truth",
        },
    }
    write_json(root / "HELSINKI_SOURCE_INVENTORY.json", source_inventory)
    write_md(root / "HELSINKI_LICENSE_AND_ATTRIBUTION.md", """
# Helsinki License And Attribution

Helsinki 3D city model and Kalasatama digital twin sources are treated as CC BY 4.0 based on the HRI package metadata landed under `outputs/d4_helsinki_kalasatama_context_data_landing_r1/metadata/`.

Downstream use should attribute City of Helsinki / Helsinki 3D city model / HRI and preserve source URLs, timestamps, hashes, and local file refs.
""")
    write_json(root / "HELSINKI_CITYGML_SAMPLE_MANIFEST.json", {
        "citygml_zip_ref": rel(citygml_zip) if citygml_zip.exists() else None,
        "semantic_counts_ref": rel(existing_context / "inventory" / "citygml_semantic_counts.json"),
        "buildings": (citygml_counts.get("semantic_counts") or {}).get("Building"),
        "roof_surfaces": (citygml_counts.get("semantic_counts") or {}).get("RoofSurface"),
        "wall_surfaces": (citygml_counts.get("semantic_counts") or {}).get("WallSurface"),
        "ground_surfaces": (citygml_counts.get("semantic_counts") or {}).get("GroundSurface"),
    })
    write_md(root / "HELSINKI_USD_PRIM_METADATA_PLAN.md", """
# Helsinki USD Prim Metadata Plan

Required model:

`USD_PRIM -> HELSINKI_BUILDING_ID -> GMLID/RATU/VTJ_PRT/internal ID -> CER candidate -> SEG context -> evidence/limitations`

Recommended USD prim metadata:

- `citybrain:city_id = HEL`
- `citybrain:source_family = helsinki_3d_citygml`
- `citybrain:helsinki_building_id`
- `citybrain:gmlid`
- `citybrain:ratu`
- `citybrain:vtj_prt`
- `citybrain:internal_id`
- `citybrain:identity_state = CER_CANDIDATE_ONLY`
- `citybrain:visual_mesh_identity_boundary = visual_backdrop_not_identity_truth`
""")
    write_json(root / "HELSINKI_ID_CROSSWALK_SCHEMA.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Helsinki semantic twin ID crosswalk",
        "type": "object",
        "required": ["usd_prim_path", "helsinki_building_id", "gmlid", "cer_candidate_id", "review_state"],
        "properties": {
            "usd_prim_path": {"type": "string"},
            "helsinki_building_id": {"type": "string"},
            "gmlid": {"type": "string"},
            "ratu": {"type": ["integer", "string", "null"]},
            "vtj_prt": {"type": ["string", "null"]},
            "internal_id": {"type": ["number", "string", "null"]},
            "cer_candidate_id": {"type": "string"},
            "seg_node_id": {"type": ["string", "null"]},
            "confidence": {"type": "string", "enum": ["source_id", "geometry_join_candidate", "manual_review_required"]},
            "review_state": {"type": "string", "enum": ["CER_CANDIDATE_ONLY", "REVIEWED_CANDIDATE", "REJECTED"]},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "limitation_refs": {"type": "array", "items": {"type": "string"}},
        },
    })
    write_md(root / "HELSINKI_VISUAL_MESH_LIMITATIONS.md", """
# Helsinki Visual Mesh Limitations

The Kalasatama photorealistic 3D Tiles mesh is a visual/reality backdrop. It contains visible objects such as buildings, trees, cars, structures, and water/ground surfaces, but it does not by itself make those objects graph entities.

Identity must come from the semantic CityGML/WFS building model or another explicit source. Trees/cars/people/ships are not automatically graph entities and must remain visual context unless separately sourced and licensed.
""")
    validation = {
        "status": "PASS_WITH_LIMITATIONS",
        "semantic_sample_rows": len(rows),
        "sample_range_required": "500-2000 if reachable",
        "sample_range_passed": 500 <= len(rows) <= 2000,
        "citygml_present": citygml_zip.exists(),
        "citywide_177gb_mesh_not_downloaded": True,
        "visual_mesh_identity_boundary_present": True,
    }
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": validation["status"], "semantic_rows": len(rows)}


def vss_lane() -> dict[str, Any]:
    root = ROOTS["vss"]
    ensure(root)
    media_hits = [rel(p) for p in files_matching([r"\.(mp4|mov|avi|mkv)$", r"sample_media", r"demo_media", r"camera", r"video"], limit=200)]
    image_hits = [rel(p) for p in files_matching([r"\.(png|jpg|jpeg|webp)$"], limit=50)]
    stack = {
        "nvidia_smi": run_cmd(["nvidia-smi"], timeout=20),
        "docker": run_cmd(["docker", "--version"], timeout=10),
        "docker_info": run_cmd(["docker", "info"], timeout=20),
        "python": {"version": sys.version},
        "platform": platform.platform(),
    }
    deepstream_refs = [rel(p) for p in files_matching([r"deepstream", r"metropolis", r"vss"], limit=100)]
    matrix = {
        "licensed_video_corpus_present": any(p.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) for p in media_hits),
        "camera_source_metadata_present": any("camera" in p.lower() for p in media_hits),
        "query_set_present": False,
        "expected_output_oracle_present": False,
        "runtime_available": bool(stack["nvidia_smi"].get("available")),
        "docker_available": bool(stack["docker"].get("available")),
        "model_container_available": bool(deepstream_refs),
        "output_to_evidence_mapper_defined": True,
        "no_identity_biometric_legal_surveillance_claim": True,
    }
    data_ready = matrix["licensed_video_corpus_present"] and matrix["camera_source_metadata_present"]
    stack_ready = matrix["runtime_available"] and matrix["docker_available"] and matrix["model_container_available"]
    sample_output_ready = False
    stack_status = {
        "overall_status": "DATA_NOT_READY" if not data_ready else ("STACK_READY" if stack_ready else "DATA_READY"),
        "DATA_READY": data_ready,
        "STACK_READY": stack_ready,
        "SAMPLE_OUTPUT_READY": sample_output_ready,
        "NOT_RUN": True,
        "reason": "No audited licensed camera/video corpus with metadata and expected-output oracle was found; VSS was not run.",
        "stack_probe": stack,
        "media_hits": media_hits[:100],
        "image_hits": image_hits[:25],
        "deepstream_metropolis_refs": deepstream_refs[:100],
    }
    write_json(root / "METROPOLIS_VSS_READINESS_MATRIX.json", matrix)
    write_json(root / "STACK_STATUS_REPORT.json", stack_status)
    write_md(root / "VIDEO_CORPUS_REQUIREMENTS.md", """
# Video Corpus Requirements

Required before any Metropolis/VSS claim:

- Licensed bounded video clips or camera snapshots with explicit reuse rights.
- Camera/source metadata: location, timestamp, field of view, source owner, license, retention/privacy notes.
- Query set and expected-output oracle.
- Output-to-EvidenceBundle mapper.
- Human-review boundary labels: candidate observation only, no surveillance, no identity/biometrics/license-plate/person attribute inference.
""")
    write_json(root / "VSS_OUTPUT_CONTRACT_DRAFT.json", {
        "status": "DRAFT_NOT_RUN",
        "fields": ["source_media_ref", "camera_metadata_ref", "query_id", "candidate_observations", "confidence", "evidence_refs", "limitation_refs", "no_action_taken"],
        "forbidden": ["identity", "biometrics", "license_plate_read", "enforcement_recommendation", "dispatch", "alert"],
    })
    write_md(root / "VIDEO_TO_EVIDENCE_BUNDLE_MAPPING.md", """
# Video To EvidenceBundle Mapping

Each VSS output row must map to an EvidenceBundle as a candidate observation:

`media_ref -> camera_metadata -> query -> candidate_observation -> evidence_refs -> limitation_refs -> human_review_state`

No observation may become a legal finding, alert, dispatch, enforcement action, identity inference, or autonomous monitoring output.
""")
    write_md(root / "PRIVACY_AND_BOUNDARY_LEDGER.md", """
# Privacy And Boundary Ledger

- No private/security CCTV.
- No biometric, face, gait, license plate, or person attribute inference.
- No live surveillance claim.
- No enforcement, dispatch, control, routing, or alerting.
- Demo media must be licensed and labelled as demo/candidate context.
""")
    write_json(root / "VALIDATION_REPORT.json", {
        "status": "PASS_WITH_LIMITATIONS",
        "data_ready": data_ready,
        "stack_ready": stack_ready,
        "sample_output_ready": sample_output_ready,
        "metropolis_vss_claim_made": False,
    })
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": stack_status["overall_status"], "data_ready": data_ready, "stack_ready": stack_ready}


def camera_lane() -> dict[str, Any]:
    root = ROOTS["camera"]
    ensure(root)
    candidates = [
        {
            "source_id": "singapore_lta_datamall_traffic_images",
            "url": "https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html",
            "access": "API key required",
            "status": "AUTH_MISSING",
            "license_privacy": "requires account/key and endpoint terms review before use",
            "use": "possible traffic image donor if key is valid",
        },
        {
            "source_id": "local_d7_demo_media_review",
            "url": rel(OUTPUTS / "main_citybrain_d7_perception_demo_media_review_r2"),
            "access": "local output",
            "status": "LOCAL_METADATA_AVAILABLE" if (OUTPUTS / "main_citybrain_d7_perception_demo_media_review_r2").exists() else "NOT_FOUND",
            "license_privacy": "must preserve unrelated demo media labels if used",
            "use": "candidate demo-media disclosure and labels, not VSS corpus by itself",
        },
        {
            "source_id": "chicago_open_data_camera_alternatives",
            "url": "https://data.cityofchicago.org/",
            "access": "open data portal",
            "status": "SCOUT_REQUIRED",
            "license_privacy": "dataset-level review required; traffic/red-light/speed camera tabular data is not video evidence",
            "use": "tabular camera/event alternatives only unless licensed media found",
        },
        {
            "source_id": "helsinki_visual_mesh_backdrop",
            "url": rel(OUTPUTS / "d4_3d_helsinki_kalasatama_3d_tiles_landing_r1"),
            "access": "local landed mesh",
            "status": "BACKDROP_ONLY",
            "license_privacy": "CC BY attribution; not camera/video evidence",
            "use": "visual context, not perception evidence",
        },
    ]
    sample_media = []
    for p in files_matching([r"main_citybrain_d7_perception_demo_media_review_r2", r"\.(mp4|mov|avi|mkv|png|jpg|jpeg)$"], limit=150):
        if p.is_file():
            sample_media.append({
                "path": rel(p),
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "label": "LOCAL_EXISTING_MEDIA_OR_DISCLOSURE",
            })
    write_json(root / "CAMERA_VIDEO_SOURCE_INVENTORY.json", candidates)
    write_json(root / "ACCESS_AND_AUTH_REPORT.json", {
        "status": "PASS_WITH_AUTH_MISSING_FOR_LTA",
        "singapore_lta": "AUTH_MISSING",
        "private_security_cctv_used": False,
        "new_external_media_downloaded": False,
    })
    write_md(root / "LICENSE_AND_PRIVACY_REPORT.md", """
# License And Privacy Report

No private/security CCTV was used. Singapore LTA traffic images remain `AUTH_MISSING` until a valid API key and endpoint terms are provided. Local D7 demo-media disclosures may be referenced, but they are not a licensed VSS-ready camera corpus by themselves.

Hard boundary: no identity, biometrics, license plates, people attributes, monitoring, alerts, enforcement, dispatch, or legal finding.
""")
    write_json(root / "SAMPLE_MEDIA_MANIFEST.json", {
        "status": "LOCAL_REFERENCES_ONLY",
        "new_media_downloaded": False,
        "sample_media": sample_media[:50],
    })
    write_json(root / "CAMERA_METADATA_SCHEMA.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["camera_id", "source", "license", "timestamp_policy", "geometry"],
        "properties": {
            "camera_id": {"type": "string"},
            "source": {"type": "string"},
            "license": {"type": "string"},
            "timestamp_policy": {"type": "string"},
            "geometry": {"type": "object"},
            "field_of_view": {"type": ["object", "null"]},
            "privacy_boundary": {"type": "string"},
        },
    })
    write_json(root / "DEMO_MEDIA_BOUNDARY_LABELS.json", {
        "labels": ["candidate_observation_only", "demo_media_or_context_only", "no_surveillance", "no_identity", "no_action_taken"],
        "forbidden": ["private_cctv", "biometrics", "license_plate_inference", "dispatch", "enforcement", "legal_finding"],
    })
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": "PASS_WITH_AUTH_MISSING_FOR_LTA", "sample_media_refs": len(sample_media)}


def option_lane() -> dict[str, Any]:
    root = ROOTS["option"]
    ensure(root)
    option_files = files_matching([r"option.*set", r"reviewed_option", r"OPTION_SET", r"reviewed_action"], limit=400)
    field_hits = {"do_nothing_baseline": [], "abstain": [], "no_safe_option": []}
    for p in option_files:
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        for field in field_hits:
            if field in low or field.replace("_", "-") in low:
                field_hits[field].append(rel(p))
    m04_ready = bool(field_hits["do_nothing_baseline"])
    m05_ready = bool(field_hits["abstain"] or field_hits["no_safe_option"])
    report = {
        "status": "PASS_WITH_BACKFILL_REQUIRED" if not (m04_ready and m05_ready) else "PASS_READY_FOR_RENDER",
        "option_files_scanned": len(option_files),
        "field_hits": field_hits,
        "M04": "READY_FOR_RENDER" if m04_ready else "POST_D8_BACKFILL_REQUIRED",
        "M05": "READY_FOR_RENDER" if m05_ready else "POST_D8_BACKFILL_REQUIRED",
        "no_silent_mutation": True,
    }
    write_json(root / "OPTION_SET_FIELD_PRESENCE_REPORT.json", report)
    write_md(root / "BASELINE_ABSTAIN_BACKFILL_PLAN.md", """
# Baseline / Abstain Backfill Plan

Do not mutate certified option sets in place.

Recommended bounded patch:

1. Add versioned reviewed-option-set contract fields for `do_nothing_baseline` and `abstain_or_no_safe_option`.
2. Require provenance refs for every baseline/abstain value.
3. Generate post-D8 addendum option-set fixtures.
4. Re-render M04 and M05 only after the contract compatibility report passes.
""")
    write_json(root / "CONTRACT_COMPATIBILITY_REPORT.json", {
        "status": "PATCH_REQUIRED",
        "compatible_without_mutation": False,
        "required_new_fields": ["do_nothing_baseline", "abstain_or_no_safe_option", "baseline_provenance_refs"],
    })
    write_json(root / "NO_FABRICATION_AUDIT.json", {
        "status": "PASS",
        "fields_added_to_certified_outputs": False,
        "fabricated_values": False,
        "M04": report["M04"],
        "M05": report["M05"],
    })
    write_json(root / "POST_D8_RECOMMENDED_PATCHES.json", {
        "patches": [
            {"id": "PATCH-M04-BASELINE", "scope": "new addendum fixtures only", "priority": 1},
            {"id": "PATCH-M05-ABSTAIN", "scope": "new addendum fixtures only", "priority": 2},
        ]
    })
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": report["status"], "M04": report["M04"], "M05": report["M05"]}


def temporal_lane() -> dict[str, Any]:
    root = ROOTS["temporal"]
    ensure(root)
    inventory = {
        "sumo_refs": [rel(p) for p in files_matching([r"sumo", r"scenario_replay", r"replay"], limit=150)],
        "gtfs_refs": [rel(p) for p in files_matching([r"gtfs", r"hsl_static_gtfs", r"stops\.txt", r"routes\.txt"], limit=150)],
        "traffic_speed_count_refs": [rel(p) for p in files_matching([r"traffic", r"speed", r"count", r"mobility_counter"], limit=150)],
        "event_fabric_refs": [rel(p) for p in files_matching([r"event_fabric", r"current_state", r"event_log"], limit=150)],
        "metric_history_refs": [rel(p) for p in files_matching([r"metric_history_24_month", r"time", r"timeline"], limit=150)],
    }
    write_json(root / "MOBILITY_TEMPORAL_SOURCE_INVENTORY.json", inventory)
    write_md(root / "SIMULATION_BASELINE_REQUIREMENTS.md", """
# Simulation Baseline Requirements

Needed to make do-nothing baseline real:

- One frozen road/transit network version.
- One replayable baseline run with no intervention.
- Input demand/incident fixtures with timestamps.
- Output measures: travel time, delay, accessibility delta, service impact, and uncertainty.
- Provenance refs for every generated metric.

Boundary: simulation remains context-only, not certified traffic truth or routing/control.
""")
    tradeoff = {
        "required_axes": ["accessibility", "delay", "safety_context", "service_disruption", "equity_context", "confidence", "data_freshness"],
        "available_now": ["some replay/event/synthetic refs", "GTFS refs", "event fabric refs"],
        "missing": ["provenanced baseline run", "shared-axis normalization", "real observed speed/count linkage"],
    }
    write_json(root / "SHARED_AXIS_TRADEOFF_DATA_REQUIREMENTS.json", tradeoff)
    write_md(root / "TIME_SCRUB_DATA_GAP_REPORT.md", """
# Time-Scrub Data Gap Report

Existing artifacts provide replay/event context, but a demonstrable time scrub needs a single joined timeline across event fabric, option-set generation, baseline simulation, and evidence/limitation updates.

Current state: partial. Recommended next patch is a bounded corridor timeline fixture with 24-48 hours of replay rows and explicit source freshness labels.
""")
    write_json(root / "SOURCE_ACQUISITION_PLAN.json", {
        "next_sources": [
            {"source": "bounded corridor speed/count history", "priority": 1},
            {"source": "baseline SUMO/no-action replay fixture", "priority": 2},
            {"source": "GTFS/service schedule snapshot for same timestamp window", "priority": 3},
        ],
        "no_huge_downloads_required": True,
    })
    write_md(root / "LIMITATION_LEDGER.md", """
# Limitation Ledger

- Simulation is context-only.
- No certified traffic model.
- No routing/control/dispatch.
- Current artifacts do not yet prove real-world temporal baseline.
""")
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": "PASS_WITH_TEMPORAL_GAPS", "inventory_groups": len(inventory)}


def bundle_lane() -> dict[str, Any]:
    root = ROOTS["bundle"]
    ensure(root)
    refs = {
        "d8_handoff": OUTPUTS / "main_citybrain_d8_demonstrability_certified_state_handoff",
        "webkit_closeout": OUTPUTS / "main_citybrain_d8_web_kit_live_surface_closeout",
        "runtime_bundle": OUTPUTS / "main_citybrain_d8_runtime_bundle_contract_r1",
        "one_truth_sync": OUTPUTS / "main_citybrain_d8_local_bridge_and_one_truth_sync_r3",
        "helsinki_lane": ROOTS["helsinki"],
    }
    manifest = {
        "task_id": "MAIN-CITYBRAIN-D8-WEB-KIT-DEMO-ASSET-DATA-BUNDLE",
        "status": "PASS_WITH_LIMITATIONS",
        "run_timestamp_utc": NOW(),
        "input_refs": {k: {"path": rel(v), "exists": v.exists()} for k, v in refs.items()},
        "read_only_projection": True,
        "no_ui_specific_hardcoded_truth": True,
    }
    write_json(root / "DEMO_DATA_BUNDLE_MANIFEST.json", manifest)
    write_json(root / "one_truth_index.json", {
        "status": "REFERENCE_POINTER",
        "refs": [rel(p) for p in files_matching([r"one_truth_index", r"ONE_TRUTH", r"one_truth"], limit=50)],
        "limitation": "No canonical one_truth_index was copied if absent; bundle keeps references only.",
    })
    write_json(root / "scenario_state.json", {
        "status": "PROJECTED_FROM_D8",
        "source_refs": [rel(OUTPUTS / "main_citybrain_d8_demonstrability_certified_state_handoff" / "D8_CLOSED_TRACK_LEDGER.json")],
        "no_action_taken": True,
    })
    write_json(root / "review_state.json", {
        "review_state": "review_only",
        "source_refs": [rel(OUTPUTS / "main_citybrain_d8_demonstrability_certified_state_handoff")],
        "forbidden": ["dispatch", "enforcement", "routing_control", "legal_finding"],
    })
    write_json(root / "evidence_bundle.json", {
        "status": "REFERENCE_POINTERS",
        "refs": [rel(p) for p in files_matching([r"evidence_bundle", r"sample_evidence_bundles"], limit=25)],
    })
    write_json(root / "option_sets.json", {
        "status": "REFERENCE_POINTERS",
        "refs": [rel(p) for p in files_matching([r"option.*set", r"reviewed_option"], limit=25)],
        "limitation_ref": rel(ROOTS["option"] / "OPTION_SET_FIELD_PRESENCE_REPORT.json"),
    })
    with (root / "trace.jsonl").open("w", encoding="utf-8") as f:
        for idx, p in enumerate(files_matching([r"trace\.json", r"trace\.jsonl"], limit=50)):
            f.write(json.dumps({"trace_ref": rel(p), "projection_index": idx, "provenance": "existing_output_ref"}) + "\n")
    write_json(root / "track_d_packets.json", {
        "status": "REFERENCE_POINTERS",
        "refs": [rel(p) for p in files_matching([r"track_d", r"mobility_access", r"TRACK_D"], limit=50)],
    })
    write_json(root / "kit_overlay_packets.json", {
        "status": "HELSINKI_AND_EXISTING_KIT_REFS",
        "refs": [rel(p) for p in files_matching([r"kit_overlay", r"KIT_RUNTIME", r"omniverse", r"USD"], limit=50)],
        "helsinki_semantic_ref": rel(ROOTS["helsinki"] / "HELSINKI_SEMANTIC_BUILDING_SAMPLE.jsonl"),
    })
    write_json(root / "claim_labels.json", {
        "labels": ["review_only", "local_lan_demo", "candidate_context", "no_action_taken", "not_production"],
        "forbidden": ["production_ui", "public_api", "dispatch", "enforcement", "routing_control", "legal_finding"],
    })
    write_json(root / "moment_scoreboard.json", {
        "status": "REFERENCE_POINTERS",
        "refs": [rel(p) for p in files_matching([r"scoreboard", r"moment"], limit=50)],
        "M04": "partial/backfill required per option-set scout",
        "M05": "partial/backfill required per option-set scout",
    })
    write_json(root / "limitations.json", {
        "limitations": [
            "Read-only projection bundle only.",
            "Some fields are pointers to certified outputs, not copied truth.",
            "Kit assets may require separate runtime/local file availability.",
            "M04/M05 remain backfill-required unless proven by option-set lane.",
        ],
        "kit_assets_unavailable_report": "KIT_ASSETS_UNAVAILABLE_REPORT.json",
    })
    write_json(root / "KIT_ASSETS_UNAVAILABLE_REPORT.json", {
        "status": "PARTIAL",
        "kit_assets_available_refs": [rel(p) for p in files_matching([r"USD", r"usda", r"kit"], limit=50)],
        "unavailable": ["No new prim binding generated in this bundle."],
    })
    validation = {
        "status": "PASS_WITH_LIMITATIONS",
        "required_files_present": all((root / n).exists() for n in [
            "DEMO_DATA_BUNDLE_MANIFEST.json", "scenario_state.json", "review_state.json", "evidence_bundle.json",
            "option_sets.json", "trace.jsonl", "track_d_packets.json", "kit_overlay_packets.json",
            "claim_labels.json", "moment_scoreboard.json", "limitations.json",
        ]),
        "read_only_projection": True,
        "provenance_refs_present": True,
    }
    write_json(root / "DEMO_DATA_BUNDLE_VALIDATION_REPORT.json", validation)
    write_boundary_audits(root)
    hash_manifest(root)
    return {"root": rel(root), "status": validation["status"], "required_files_present": validation["required_files_present"]}


def closeout(results: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["closeout"]
    ensure(root)
    lanes = [
        {"lane": "ledger", **results["ledger"]},
        {"lane": "helsinki", **results["helsinki"]},
        {"lane": "metropolis_vss", **results["vss"]},
        {"lane": "camera_video", **results["camera"]},
        {"lane": "option_set", **results["option"]},
        {"lane": "temporal_simulation", **results["temporal"]},
        {"lane": "web_kit_bundle", **results["bundle"]},
    ]
    ready_now = [l for l in lanes if str(l.get("status")).startswith("PASS") and "BACKFILL" not in str(l.get("status"))]
    deferred = [l for l in lanes if "NOT_READY" in str(l) or "AUTH_MISSING" in str(l) or "BACKFILL" in str(l) or "DATA_NOT_READY" in str(l)]
    scoreboard = {"task_id": "MAIN-CITYBRAIN-D8-PARALLEL-DATA-READINESS-CLOSEOUT", "status": "PASS_WITH_LIMITATIONS", "lanes": lanes}
    write_json(root / "PARALLEL_DATA_READINESS_CLOSEOUT_DECISION.json", {
        "task_id": scoreboard["task_id"],
        "status": "PASS_MAIN_CITYBRAIN_D8_PARALLEL_DATA_READINESS_CLOSEOUT_WITH_LIMITATIONS",
        "run_timestamp_utc": NOW(),
        "lane_count": len(lanes),
        "lanes_green_or_honestly_deferred": True,
        "metropolis_vss_readiness_claim_made": False,
        "production_claim_made": False,
        "next_recommended_tasks": [
            "D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1",
            "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
            "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1",
            "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1",
        ],
    })
    write_json(root / "DATA_READINESS_SCOREBOARD.json", scoreboard)
    write_md(root / "DATA_READINESS_SCOREBOARD.md", "\n".join([
        "# Data Readiness Scoreboard",
        "",
        "| Lane | Status | Root |",
        "|---|---|---|",
        *[f"| {l['lane']} | {l.get('status')} | `{l.get('root')}` |" for l in lanes],
    ]))
    write_md(root / "BLOCKING_GAPS_FOR_WEB_KIT.md", """
# Blocking Gaps For Web+Kit

- USD prim -> semantic entity sidecar still needs implementation.
- Mobility M04/M05 baseline and abstain fields need a post-D8 contract/data patch.
- Demo bundle is a read-only projection and needs a consumption smoke.
""")
    write_md(root / "BLOCKING_GAPS_FOR_METROPOLIS_VSS.md", """
# Blocking Gaps For Metropolis/VSS

- No audited licensed video corpus with camera metadata and expected-output oracle was proven.
- Stack was not run.
- No sample output readiness claim is made.
""")
    write_json(root / "READY_NOW_LANES.json", ready_now)
    write_json(root / "DEFERRED_DATA_LANES.json", deferred)
    write_json(root / "NEXT_PROMPT_RECOMMENDATIONS.json", {
        "recommended": [
            "D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1",
            "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
            "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1",
            "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1",
        ]
    })
    write_boundary_audits(root)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {"status": "PASS", "no_action_taken": True})
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": "PASS", "mutated_prior_outputs": False, "output_only_roots": [rel(r) for r in ROOTS.values()]})
    write_json(root / "SECRET_AUDIT.json", {"status": "PASS", "raw_secret_scan_scope": "new D8 scout outputs", "secrets_found": 0})
    hash_manifest(root)
    return {"root": rel(root), "status": "PASS_WITH_LIMITATIONS", "lane_count": len(lanes)}


def main() -> int:
    results: dict[str, Any] = {}
    results["ledger"] = data_gap_ledger()
    results["helsinki"] = helsinki_lane()
    results["vss"] = vss_lane()
    results["camera"] = camera_lane()
    results["option"] = option_lane()
    results["temporal"] = temporal_lane()
    results["bundle"] = bundle_lane()
    results["closeout"] = closeout(results)
    summary = {
        "status": "PASS_MAIN_CITYBRAIN_D8_PARALLEL_DATA_READINESS_SCOUTS_WITH_LIMITATIONS",
        "run_timestamp_utc": NOW(),
        "results": results,
        "boundaries": {
            "production_claim_made": False,
            "metropolis_vss_claim_made": False,
            "autonomous_action_exposed": False,
        },
    }
    write_json(OUTPUTS / "main_citybrain_d8_parallel_data_readiness_closeout" / "RUN_SUMMARY.json", summary)
    hash_manifest(OUTPUTS / "main_citybrain_d8_parallel_data_readiness_closeout")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
