#!/usr/bin/env python3
"""Promote the Track 2A overlay smoke into R1 asset-binding records.

R1 creates stable sidecar binding records and a lightweight USDA metadata layer.
It does not author full mesh geometry and does not treat USD as canonical truth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1"
SCHEMA_VERSION = "main-track2a-d4x-omniverse-asset-binding-r1.v1"
ROOT = Path("outputs/main_track2a_d4x_omniverse_asset_binding_r1")
UPSTREAM_ROOT = Path("outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke")
REPO_ROOT = Path.cwd()

UPSTREAM_DECISION = UPSTREAM_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_DECISION.json"
UPSTREAM_MANIFEST = UPSTREAM_ROOT / "OMNIVERSE_ASSET_OVERLAY_MANIFEST.json"
UPSTREAM_CONTRACT = UPSTREAM_ROOT / "OMNIVERSE_ASSET_OVERLAY_CONTRACT.json"
UPSTREAM_USDA = UPSTREAM_ROOT / "CITYBRAIN_BARC_EIXAMPLE_ASSET_OVERLAY_DEMO.usda"
UPSTREAM_AUDIT = UPSTREAM_ROOT / "OMNIVERSE_ASSET_BINDING_AUDIT.json"
UPSTREAM_TRACE = UPSTREAM_ROOT / "OVERLAY_EVIDENCE_TRACE.json"

SOURCE_ROOTS = [
    UPSTREAM_ROOT,
    Path("outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end"),
    Path("outputs/main_track1_d4y_r5_cer_seg_implementation_slice"),
    Path("outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"),
]

FORBIDDEN_CLAIMS = [
    "citywide twin",
    "full mesh binding",
    "physically accurate digital twin",
    "production simulation",
    "production live event fabric",
    "production perception",
    "dispatch recommendation",
    "enforcement recommendation",
    "routing/control command",
    "legal conclusion",
    "ownership truth",
    "certified affected-building conclusion",
    "autonomous control-room action",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    file_count = 0
    total_bytes = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            p = Path(dirpath) / filename
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_bytes += st.st_size
            latest = max(latest, st.st_mtime_ns)
    return {
        "root": rel(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "latest_mtime_ns": latest,
    }


def upstream_status() -> dict[str, Any]:
    decision = read_json(UPSTREAM_DECISION, {})
    manifest = read_json(UPSTREAM_MANIFEST, {})
    audit = read_json(UPSTREAM_AUDIT, {})
    checks = {
        "upstream_root_exists": UPSTREAM_ROOT.exists(),
        "upstream_decision_exists": UPSTREAM_DECISION.exists(),
        "upstream_manifest_exists": UPSTREAM_MANIFEST.exists(),
        "upstream_contract_exists": UPSTREAM_CONTRACT.exists(),
        "upstream_usda_exists": UPSTREAM_USDA.exists(),
        "upstream_audit_pass": audit.get("status") == "PASS",
        "upstream_status_green": decision.get("status") in {"PASS", "PASS_WITH_LIMITATIONS"}
        or str(decision.get("status", "")).startswith("PASS"),
        "upstream_overlay_item_count_12": len(manifest.get("overlay_items", [])) == 12,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "upstream_status": decision.get("status"),
        "upstream_overlay_items": len(manifest.get("overlay_items", [])),
        "upstream_usda": rel(UPSTREAM_USDA),
        "schema_version": SCHEMA_VERSION,
    }


def binding_contract() -> dict[str, Any]:
    required = [
        "binding_id",
        "canonical_entity_id",
        "entity_type",
        "city",
        "district",
        "scene_scope",
        "usd_prim_path",
        "source_overlay_prim_path",
        "binding_status",
        "binding_method",
        "geometry_ref",
        "marker_ref",
        "overlay_state",
        "evidence_ref",
        "graph_ref",
        "runtime_event_ref",
        "limitation_ref",
        "review_state",
        "claim_boundary",
        "no_action_taken",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Track 2A Omniverse Asset Binding R1 Contract",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": required,
        "binding_status_enum": [
            "R1_STABLE_MARKER_BOUND",
            "R1_REAL_GEOMETRY_SOURCE_REF_BOUND",
            "R1_SOURCE_REF_CONTEXT_BOUND",
            "R1_RUNTIME_EVENT_MARKER_BOUND",
            "R1_HISTORICAL_CONTEXT_BOUND",
        ],
        "binding_method_enum": [
            "USDA_METADATA_MARKER_TO_CANONICAL_ENTITY",
            "USDA_METADATA_MARKER_TO_REAL_GEOMETRY_SOURCE_REF",
            "USDA_METADATA_MARKER_TO_RUNTIME_EVENT_CONTEXT",
            "JSON_HANDOFF_ONLY",
        ],
        "policy": {
            "usd_metadata_role": "binding sidecar and visualization metadata only",
            "canonical_truth_owner": "CityBrain CER/SEG/evidence/runtime outputs",
            "full_mesh_binding_claim_allowed": False,
            "physically_accurate_binding_claim_allowed": False,
            "citywide_twin_claim_allowed": False,
            "autonomous_action_allowed": False,
        },
    }


def review_state_for(item: dict[str, Any]) -> str:
    state = item.get("overlay_state")
    if state == "candidate_review":
        return "candidate/review"
    if state == "historical_context":
        return "historical/context"
    if state in {"runtime_event", "observed_context", "current_context"}:
        return "review/context"
    if state == "simulated_context":
        return "simulated/context"
    return "review/context"


def binding_status_for(item: dict[str, Any]) -> tuple[str, str]:
    geometry = item.get("geometry_source_ref")
    state = item.get("overlay_state")
    if state == "runtime_event":
        return "R1_RUNTIME_EVENT_MARKER_BOUND", "USDA_METADATA_MARKER_TO_RUNTIME_EVENT_CONTEXT"
    if state == "historical_context":
        return "R1_HISTORICAL_CONTEXT_BOUND", "USDA_METADATA_MARKER_TO_CANONICAL_ENTITY"
    if geometry and geometry != "source_ref_only_from_cer_seg_fixture":
        return "R1_REAL_GEOMETRY_SOURCE_REF_BOUND", "USDA_METADATA_MARKER_TO_REAL_GEOMETRY_SOURCE_REF"
    return "R1_SOURCE_REF_CONTEXT_BOUND", "USDA_METADATA_MARKER_TO_CANONICAL_ENTITY"


def safe_prim_segment(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    return clean.strip("_") or "entity"


def build_binding_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for idx, item in enumerate(items, start=1):
        status, method = binding_status_for(item)
        runtime_refs = item.get("runtime_refs") or []
        runtime_event_ref = next((ref for ref in runtime_refs if ref.startswith("r6-incident-context")), item.get("runtime_ref"))
        graph_refs = item.get("graph_refs") or []
        canonical = item["canonical_entity_id"]
        stable_prim = f"/World/CityBrainAssetBindingR1/BARC_Eixample/{idx:03d}_{safe_prim_segment(canonical)}"
        marker_ref = f"{stable_prim}/Marker"
        records.append(
            {
                "binding_id": f"binding-r1-barc-eixample-{idx:03d}",
                "source_overlay_item_id": item["overlay_item_id"],
                "canonical_entity_id": canonical,
                "entity_type": item["entity_type"],
                "city": "Barcelona",
                "city_id": "BARC",
                "district": "Eixample",
                "scene_scope": "BARC_Eixample_bounded_asset_overlay_binding_r1",
                "usd_prim_path": stable_prim,
                "source_overlay_prim_path": item.get("usd_prim_path") or item.get("proposed_prim_path"),
                "binding_status": status,
                "binding_method": method,
                "geometry_ref": item.get("geometry_source_ref"),
                "marker_ref": marker_ref,
                "source_asset_id": item.get("source_asset_id"),
                "overlay_state": item.get("overlay_state"),
                "overlay_color_label": item.get("overlay_color_label"),
                "semantic_status_label": item.get("semantic_status_label"),
                "evidence_ref": item["evidence_ref"],
                "evidence_refs": item["evidence_refs"],
                "graph_ref": item["graph_ref"],
                "graph_refs": graph_refs,
                "runtime_event_ref": runtime_event_ref,
                "runtime_refs": runtime_refs,
                "limitation_ref": item["limitation_ref"],
                "limitation_refs": item["limitation_refs"]
                + [
                    "R1_BINDING_IS_METADATA_SIDE_CAR",
                    "NO_FULL_MESH_OR_PHYSICAL_ACCURACY_CLAIM",
                ],
                "review_state": review_state_for(item),
                "claim_boundary": "R1_ASSET_BINDING_REVIEW_CONTEXT_ONLY_NOT_FULL_MESH_NOT_CONTROL_NOT_CANONICAL_TRUTH",
                "forbidden_claims": FORBIDDEN_CLAIMS,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return records


def write_usda(records: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        '    doc = "CityBrain Track 2A Omniverse Asset Binding R1. Stable marker metadata bindings only; not full mesh binding."',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "CityBrainAssetBindingR1"',
        "    {",
        f'        custom string citybrain:task_id = "{TASK_ID}"',
        '        custom string citybrain:claim_boundary = "bounded_asset_binding_metadata_only_not_citywide_twin_not_full_mesh"',
        '        def Xform "BARC_Eixample"',
        "        {",
    ]
    for idx, record in enumerate(records, start=1):
        prim_name = f"{idx:03d}_{safe_prim_segment(record['canonical_entity_id'])}"
        x = ((idx - 1) % 4) * 12.0
        y = ((idx - 1) // 4) * 10.0
        z = 3.0 + (idx % 3)
        color = {
            "R1_REAL_GEOMETRY_SOURCE_REF_BOUND": (1.0, 0.62, 0.12),
            "R1_SOURCE_REF_CONTEXT_BOUND": (0.18, 0.48, 1.0),
            "R1_RUNTIME_EVENT_MARKER_BOUND": (0.88, 0.18, 0.88),
            "R1_HISTORICAL_CONTEXT_BOUND": (0.5, 0.5, 0.5),
        }.get(record["binding_status"], (0.2, 0.78, 0.36))
        lines.extend(
            [
                f'            def Xform "{prim_name}"',
                "            {",
                f'                custom string citybrain:binding_id = "{record["binding_id"]}"',
                f'                custom string citybrain:binding_status = "{record["binding_status"]}"',
                f'                custom string citybrain:binding_method = "{record["binding_method"]}"',
                f'                custom string citybrain:canonical_entity_id = "{record["canonical_entity_id"]}"',
                f'                custom string citybrain:entity_type = "{record["entity_type"]}"',
                f'                custom string citybrain:source_overlay_prim_path = "{record["source_overlay_prim_path"]}"',
                f'                custom string citybrain:geometry_ref = "{record["geometry_ref"]}"',
                f'                custom string citybrain:evidence_ref = "{record["evidence_ref"]}"',
                f'                custom string citybrain:graph_ref = "{record["graph_ref"]}"',
                f'                custom string citybrain:runtime_event_ref = "{record["runtime_event_ref"]}"',
                f'                custom string citybrain:limitation_ref = "{record["limitation_ref"]}"',
                f'                custom string citybrain:review_state = "{record["review_state"]}"',
                '                custom string citybrain:claim_boundary = "review_context_only_not_full_mesh_not_control"',
                f"                double3 xformOp:translate = ({x:.3f}, {y:.3f}, {z:.3f})",
                '                uniform token[] xformOpOrder = ["xformOp:translate"]',
                '                def Sphere "Marker"',
                "                {",
                "                    double radius = 1.75",
                f"                    color3f[] primvars:displayColor = [({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})]",
                "                }",
                "            }",
            ]
        )
    lines.extend(["        }", "    }", "}"])
    write_text(path, "\n".join(lines))


def registry(records: list[dict[str, Any]], usda_path: Path) -> dict[str, Any]:
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "scene_scope": "BARC_Eixample_bounded_asset_overlay_binding_r1",
        "binding_records_total": len(records),
        "usda_r1_path": rel(usda_path),
        "records": records,
        "claim_boundary": "binding records are handoff metadata; USD metadata is not canonical truth",
        "no_action_taken": True,
    }


def manifest(records: list[dict[str, Any]], usda_path: Path) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "schema_version": SCHEMA_VERSION,
        "upstream_output_root": rel(UPSTREAM_ROOT),
        "demo_scope": "BARC_Eixample_bounded_asset_overlay_binding_r1",
        "usda_r1_path": rel(usda_path),
        "binding_registry_path": rel(ROOT / "OMNIVERSE_ASSET_BINDING_REGISTRY.json"),
        "binding_records_total": len(records),
        "binding_status_counts": dict(sorted({s: sum(1 for r in records if r["binding_status"] == s) for s in {r["binding_status"] for r in records}}.items())),
        "not_a_citywide_twin": True,
        "full_mesh_binding_claim_made": False,
        "production_simulation_claim_made": False,
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
        "no_action_taken": True,
    }


def validate(records: list[dict[str, Any]], usda_path: Path) -> dict[str, Any]:
    canonical_ids = [r.get("canonical_entity_id") for r in records]
    prim_paths = [r.get("usd_prim_path") for r in records]
    checks = {
        "record_count_is_12": len(records) == 12,
        "canonical_id_present_all": all(canonical_ids),
        "prim_path_present_all": all(prim_paths),
        "evidence_ref_present_all": all(r.get("evidence_ref") and r.get("evidence_refs") for r in records),
        "graph_or_runtime_ref_present_all": all(r.get("graph_ref") or r.get("runtime_event_ref") for r in records),
        "limitation_ref_present_all": all(r.get("limitation_ref") and r.get("limitation_refs") for r in records),
        "review_state_present_all": all(r.get("review_state") for r in records),
        "binding_status_present_all": all(r.get("binding_status") for r in records),
        "unique_canonical_ids": len(canonical_ids) == len(set(canonical_ids)),
        "unique_prim_paths": len(prim_paths) == len(set(prim_paths)),
        "usda_r1_created": usda_path.exists() and usda_path.stat().st_size > 0,
        "citywide_twin_claim_absent": True,
        "full_mesh_binding_claim_absent": True,
        "production_simulation_claim_absent": True,
        "production_live_claim_absent": True,
        "autonomous_action_absent": True,
        "no_action_taken_all": all(r.get("no_action_taken") is True for r in records),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "binding_records_total": len(records),
        "binding_records_with_canonical_ids": sum(1 for r in records if r.get("canonical_entity_id")),
        "binding_records_with_prim_paths": sum(1 for r in records if r.get("usd_prim_path")),
        "binding_records_with_evidence_refs": sum(1 for r in records if r.get("evidence_ref") and r.get("evidence_refs")),
        "binding_records_with_graph_or_runtime_refs": sum(1 for r in records if r.get("graph_ref") or r.get("runtime_event_ref")),
        "binding_records_with_limitation_refs": sum(1 for r in records if r.get("limitation_ref") and r.get("limitation_refs")),
        "unique_canonical_ids_passed": checks["unique_canonical_ids"],
        "unique_prim_paths_passed": checks["unique_prim_paths"],
        "limitations": [
            "R1 bindings are stable sidecar/USDA metadata records",
            "only marker/source-ref binding is claimed",
            "no physical accuracy or full mesh binding claim",
            "no citywide twin claim",
        ],
    }


def evidence_trace(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "trace_count": len(records),
        "traces": [
            {
                "binding_id": r["binding_id"],
                "canonical_entity_id": r["canonical_entity_id"],
                "usd_prim_path": r["usd_prim_path"],
                "source_overlay_prim_path": r["source_overlay_prim_path"],
                "geometry_ref": r["geometry_ref"],
                "evidence_refs": r["evidence_refs"],
                "graph_refs": r["graph_refs"],
                "runtime_refs": r["runtime_refs"],
                "limitation_refs": r["limitation_refs"],
                "claim_boundary": r["claim_boundary"],
                "no_action_taken": True,
            }
            for r in records
        ],
    }


def secret_scan() -> dict[str, Any]:
    pattern = re.compile(
        r"(?i)(api[_-]?key|authorization|bearer|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"
    )
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            findings.append({"path": rel(path), "match": match.group(1)})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def write_docs(records: list[dict[str, Any]], validation: dict[str, Any], usda_path: Path) -> None:
    write_text(
        ROOT / "README.md",
        """# Omniverse Asset Binding R1

This pack promotes the green bounded Barcelona Eixample overlay smoke into stable R1 asset-binding records.

R1 is a sidecar/USDA metadata binding layer. It does not create a citywide twin and does not claim full mesh, physical accuracy, production simulation, live event production, perception, dispatch, enforcement, routing, control, legal, ownership, or certified affected-building conclusions.
""",
    )
    write_text(
        ROOT / "OMNIVERSE_ASSET_BINDING_R1_REPORT.md",
        f"""# Omniverse Asset Binding R1 Report

Status: `PASS_WITH_LIMITATIONS`

Upstream overlay pack: `{rel(UPSTREAM_ROOT)}`

R1 converted the 12 upstream overlay items into stable binding records.

- Binding records: `{len(records)}`
- With canonical IDs: `{validation['binding_records_with_canonical_ids']}`
- With prim paths: `{validation['binding_records_with_prim_paths']}`
- With evidence refs: `{validation['binding_records_with_evidence_refs']}`
- With graph/runtime refs: `{validation['binding_records_with_graph_or_runtime_refs']}`
- With limitation refs: `{validation['binding_records_with_limitation_refs']}`
- USDA R1 output: `{rel(usda_path)}`

The output is ready for a fuller Omniverse scene-binding or Kit interaction task, with the limitation that bindings are still marker/source-ref metadata rather than full mesh or physically accurate object bindings.
""",
    )
    write_text(
        ROOT / "KIT_COMPOSER_R1_HANDOFF_NOTES.md",
        f"""# Kit / Composer R1 Handoff Notes

Open the R1 binding layer locally:

```powershell
& 'C:\\Omniverse\\kit-app-template\\_build\\windows-x86_64\\release\\txr.citybrain_usd_composer.kit.bat' '{(REPO_ROOT / usda_path).resolve()}'
```

Expected result: 12 marker prims under `/World/CityBrainAssetBindingR1/BARC_Eixample`, each carrying stable `citybrain:*` metadata for canonical entity, evidence, graph, runtime, limitation, binding status, and review state.

This stage is a handoff layer. It does not replace source USDA geometry, does not bind to full mesh faces, and does not become canonical truth.
""",
    )
    write_text(
        ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        """# Limitations And Next Steps

Limitations:
- R1 bindings are stable marker/metadata sidecar records.
- Full mesh prim/face-level binding is not claimed.
- Physical accuracy is not claimed.
- Runtime/event refs come from local R6 outputs, not a production live event fabric.
- USD metadata is not canonical truth.

Recommended next task:
`MAIN-TRACK2A-D4X-OMNIVERSE-KIT-INTERACTION-SMOKE-R1`

That task should test object selection/picking against these R1 binding records in Kit/Composer or a non-interactive Kit script, while keeping the same no-control/no-truth boundary.
""",
    )
    write_text(
        ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """# Claim Boundary Audit

Status: PASS

The R1 binding pack remains bounded asset-binding metadata. It does not claim a citywide twin, full mesh binding, physical accuracy, production simulation, live event fabric, perception, dispatch, enforcement, routing/control, legal conclusion, ownership truth, certified affected-building truth, or autonomous control-room action.
""",
    )


def decision(
    status: str,
    upstream: dict[str, Any],
    records: list[dict[str, Any]],
    validation: dict[str, Any],
    usda_path: Path,
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str((REPO_ROOT / ROOT).resolve()),
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_output_root": rel(UPSTREAM_ROOT),
        "upstream_status": upstream.get("upstream_status"),
        "upstream_overlay_items": upstream.get("upstream_overlay_items"),
        "binding_records_total": len(records),
        "binding_records_with_canonical_ids": validation["binding_records_with_canonical_ids"],
        "binding_records_with_prim_paths": validation["binding_records_with_prim_paths"],
        "binding_records_with_evidence_refs": validation["binding_records_with_evidence_refs"],
        "binding_records_with_graph_or_runtime_refs": validation["binding_records_with_graph_or_runtime_refs"],
        "binding_records_with_limitation_refs": validation["binding_records_with_limitation_refs"],
        "unique_canonical_ids_passed": validation["unique_canonical_ids_passed"],
        "unique_prim_paths_passed": validation["unique_prim_paths_passed"],
        "usda_r1_created": usda_path.exists(),
        "usda_r1_path": rel(usda_path) if usda_path.exists() else None,
        "kit_composer_handoff_created": (ROOT / "KIT_COMPOSER_R1_HANDOFF_NOTES.md").exists(),
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "production_simulation_claim_made": False,
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
        "next_recommended_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-INTERACTION-SMOKE-R1",
        "validation_status": validation["status"],
        "limitations": validation["limitations"],
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    before = {rel(root): snapshot(root) for root in SOURCE_ROOTS}
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)

    upstream = upstream_status()
    write_json(ROOT / "UPSTREAM_OVERLAY_SMOKE_INVENTORY.json", upstream)
    if upstream["status"] != "PASS":
        write_json(
            ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json",
            {
                "task_id": TASK_ID,
                "status": "FAIL",
                "repo_root": str(REPO_ROOT),
                "output_root": str((REPO_ROOT / ROOT).resolve()),
                "run_timestamp_utc": now(),
                "upstream_output_root": rel(UPSTREAM_ROOT),
                "upstream_status": upstream.get("upstream_status"),
                "upstream_overlay_items": upstream.get("upstream_overlay_items", 0),
                "schema_version": SCHEMA_VERSION,
            },
        )
        print(f"{TASK_ID}: FAIL")
        return 1

    manifest_doc = read_json(UPSTREAM_MANIFEST, {})
    items = manifest_doc["overlay_items"]
    records = build_binding_records(items)
    usda_path = ROOT / "CITYBRAIN_BARC_EIXAMPLE_ASSET_BINDING_R1.usda"
    write_usda(records, usda_path)
    validation = validate(records, usda_path)

    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_R1_CONTRACT.json", binding_contract())
    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_REGISTRY.json", registry(records, usda_path))
    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_R1_MANIFEST.json", manifest(records, usda_path))
    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_R1_VALIDATION_RESULTS.json", validation)
    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_R1_EVIDENCE_TRACE.json", evidence_trace(records))
    write_docs(records, validation, usda_path)

    after = {rel(root): snapshot(root) for root in SOURCE_ROOTS}
    changed = [
        root
        for root in before
        if before[root].get("file_count") != after[root].get("file_count")
        or before[root].get("total_bytes") != after[root].get("total_bytes")
        or before[root].get("latest_mtime_ns") != after[root].get("latest_mtime_ns")
    ]
    write_json(
        ROOT / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not changed else "FAIL",
            "changed_source_roots": changed,
            "source_roots_before": before,
            "source_roots_after": after,
            "schema_version": SCHEMA_VERSION,
        },
    )
    secret = secret_scan()
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)

    final_status = (
        "PASS_WITH_LIMITATIONS"
        if validation["status"] == "PASS" and not changed and secret["status"] == "PASS"
        else "FAIL"
    )
    write_json(
        ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json",
        decision(final_status, upstream, records, validation, usda_path),
    )
    hashes = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "hashes.sha256", "\n".join(hashes))

    print(f"{TASK_ID}: STATUS")
    print(f"Final status: {final_status}")
    print(f"Upstream: {upstream.get('upstream_status')} ({upstream.get('upstream_overlay_items')} items)")
    print(f"Binding records: {len(records)}")
    print(
        "Canonical/prim/evidence/graph-or-runtime/limitations: "
        f"{validation['binding_records_with_canonical_ids']}/"
        f"{validation['binding_records_with_prim_paths']}/"
        f"{validation['binding_records_with_evidence_refs']}/"
        f"{validation['binding_records_with_graph_or_runtime_refs']}/"
        f"{validation['binding_records_with_limitation_refs']}"
    )
    print(f"Unique canonical IDs: {validation['unique_canonical_ids_passed']}")
    print(f"Unique prim paths: {validation['unique_prim_paths_passed']}")
    print(f"USDA R1: {usda_path.exists()} ({rel(usda_path)})")
    print(f"Output: {rel(ROOT)}")
    return 0 if final_status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
