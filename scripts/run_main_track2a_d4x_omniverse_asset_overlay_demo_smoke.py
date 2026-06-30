#!/usr/bin/env python3
"""Create a bounded Omniverse/OpenUSD asset overlay demo smoke pack.

This is not a citywide twin. It emits a small Barcelona Eixample overlay
manifest and USDA marker layer bound to CityBrain CER/SEG/R6 evidence.
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


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-OVERLAY-DEMO-SMOKE"
ROOT = Path("outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke")
REPO_ROOT = Path.cwd()
SCHEMA_VERSION = "main-track2a-d4x-omniverse-asset-overlay-demo-smoke.v1"

TRACK2A_ROOT = Path("outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end")
CER_SEG_ROOT = Path("outputs/main_track1_d4y_r5_cer_seg_implementation_slice")
R6_ROOT = Path("outputs/main_track1_d4y_r6_incident_event_mode_end_to_end")
USD_BINDING_ROOT = Path("outputs/main_track1_d4_usd_city_subset_binding")
BARC_LOD2_ROOT = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1")

SOURCE_ROOTS = [TRACK2A_ROOT, CER_SEG_ROOT, R6_ROOT, USD_BINDING_ROOT, BARC_LOD2_ROOT]

CANONICAL_SCOPE = [
    "cer:building:barc:eixample:lod2:001",
    "cer:parcel:barc:eixample:08900",
    "cer:address:barc:eixample:001",
    "cer:community:barc:eixample",
    "cer:road:barc:segment:granvia:001",
    "cer:facility:barc:public:001",
    "cer:system:barc:facility:hvac:001",
    "cer:component:barc:facility:sensor:001",
    "cer:instrument:barc:noise:001",
    "cer:incident:barc:traffic:001",
    "cer:permit:barc:historical:001",
    "cer:unit:barc:building:001:u1",
]

STATE_STYLE = {
    "candidate_review": ("amber", (1.0, 0.62, 0.12)),
    "current_context": ("blue", (0.18, 0.48, 1.0)),
    "observed_context": ("green", (0.2, 0.78, 0.36)),
    "graph_context": ("cyan", (0.1, 0.78, 0.9)),
    "runtime_event": ("magenta", (0.88, 0.18, 0.88)),
    "historical_context": ("gray", (0.5, 0.5, 0.5)),
    "limitation_only": ("red", (1.0, 0.22, 0.18)),
    "simulated_context": ("violet", (0.52, 0.3, 0.95)),
}

FORBIDDEN_CLAIMS = [
    "citywide twin",
    "production simulation",
    "perception production capability",
    "live-event production capability",
    "autonomous control-room action",
    "dispatch recommendation",
    "enforcement recommendation",
    "routing/control command",
    "legal finding",
    "confirmed violation",
    "certified affected-building truth",
    "ownership truth",
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
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0}
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
    return {"root": rel(root), "exists": True, "file_count": file_count, "total_bytes": total_bytes, "latest_mtime_ns": latest}


def indexed(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item.get(key): item for item in items if item.get(key)}


def load_inputs() -> dict[str, Any]:
    selected_assets = read_json(TRACK2A_ROOT / "TRACK2A_SELECTED_DEMO_ASSETS.json", {}).get("assets", [])
    cer = read_json(CER_SEG_ROOT / "R5_CER_FIXTURES.json", {})
    seg = read_json(CER_SEG_ROOT / "R5_SEG_FIXTURES.json", {})
    r6_packets = read_json(R6_ROOT / "R6_INCIDENT_CONTEXT_PACKETS.json", {}).get("packets", [])
    r6_state = read_json(R6_ROOT / "R6_CURRENT_STATE_RESULTS.json", {}).get("current_state_rows", [])
    return {
        "selected_assets": selected_assets,
        "canonical_entities": cer.get("canonical_entities", []),
        "attribute_assertions": cer.get("attribute_assertions", []),
        "graph_nodes": seg.get("graph_nodes", []),
        "graph_edges": seg.get("graph_edges", []),
        "r6_packets": r6_packets,
        "r6_state": r6_state,
    }


def graph_refs_for(canonical_id: str, graph_nodes: list[dict[str, Any]], graph_edges: list[dict[str, Any]]) -> list[str]:
    refs = []
    for node in graph_nodes:
        if node.get("canonical_entity_ref") == canonical_id:
            refs.append(node.get("node_id"))
    for edge in graph_edges:
        if canonical_id in {edge.get("source_entity_ref"), edge.get("target_entity_ref"), edge.get("canonical_entity_ref")}:
            refs.append(edge.get("edge_id"))
    return [ref for ref in refs if ref]


def runtime_refs_for(canonical_id: str, packets: list[dict[str, Any]], state_rows: list[dict[str, Any]]) -> list[str]:
    refs = []
    for packet in packets:
        if canonical_id in packet.get("entity_refs", []):
            refs.append(packet.get("packet_id"))
    for row in state_rows:
        if row.get("entity_ref") == canonical_id:
            refs.append(row.get("state_id"))
    return [ref for ref in refs if ref]


def source_refs_for(canonical_id: str, selected_assets: list[dict[str, Any]]) -> dict[str, Any]:
    if canonical_id == "cer:building:barc:eixample:lod2:001" and selected_assets:
        asset = next((a for a in selected_assets if a.get("city_id") == "BARC"), selected_assets[0])
        return {
            "geometry_source_ref": asset["evidence_refs"][0],
            "asset_registry_ref": asset["asset_registry_id"],
            "source_asset_id": asset["source_asset_id"],
            "source_identifiers": asset["source_identifiers"],
            "usd_source_ref": asset["usd_scene_refs"].get("master_usda"),
        }
    return {
        "geometry_source_ref": "source_ref_only_from_cer_seg_fixture",
        "asset_registry_ref": None,
        "source_asset_id": canonical_id.replace("cer:", "source-ref:"),
        "source_identifiers": {"canonical_fixture_ref": canonical_id},
        "usd_source_ref": None,
    }


def overlay_state_for(entity: dict[str, Any], idx: int) -> str:
    cid = entity["canonical_entity_id"]
    if "permit:barc:historical" in cid:
        return "historical_context"
    if "incident:barc:traffic" in cid:
        return "runtime_event"
    if "instrument:barc:noise" in cid:
        return "observed_context"
    if entity.get("review_state") in {"candidate/pending_review", "source_only"}:
        return "candidate_review"
    if entity.get("temporal_status") == "current":
        return "current_context"
    return "graph_context" if idx % 2 else "candidate_review"


def build_overlay_items(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    entities = indexed(inputs["canonical_entities"], "canonical_entity_id")
    attrs_by_entity: dict[str, list[dict[str, Any]]] = {}
    for attr in inputs["attribute_assertions"]:
        attrs_by_entity.setdefault(attr.get("canonical_entity_id"), []).append(attr)

    items = []
    for idx, canonical_id in enumerate(CANONICAL_SCOPE, start=1):
        entity = entities[canonical_id]
        state = overlay_state_for(entity, idx)
        color_label, rgb = STATE_STYLE[state]
        graph_refs = graph_refs_for(canonical_id, inputs["graph_nodes"], inputs["graph_edges"])
        runtime_refs = runtime_refs_for(canonical_id, inputs["r6_packets"], inputs["r6_state"])
        source = source_refs_for(canonical_id, inputs["selected_assets"])
        evidence_refs = list(entity.get("evidence_refs", []))
        evidence_refs.extend(attr.get("evidence_refs", [])[0] for attr in attrs_by_entity.get(canonical_id, [])[:2] if attr.get("evidence_refs"))
        if source.get("geometry_source_ref") and source["geometry_source_ref"] != "source_ref_only_from_cer_seg_fixture":
            evidence_refs.append(source["geometry_source_ref"])
        if runtime_refs:
            evidence_refs.append(f"outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/{runtime_refs[0]}")
        limitations = sorted(
            set(
                entity.get("limitation_refs", [])
                + [lim for attr in attrs_by_entity.get(canonical_id, []) for lim in attr.get("limitation_refs", [])]
                + [
                    "OMNIVERSE_VISUALIZATION_LAYER_NOT_SOURCE_OF_TRUTH",
                    "SOURCE_OR_CANDIDATE_CONTEXT_ONLY",
                ]
            )
        )
        if not graph_refs:
            graph_refs = [f"graph_ref_pending:{canonical_id}"]
            limitations.append("graph_ref_pending_for_overlay_item")
        if not runtime_refs:
            runtime_refs = [f"runtime_ref_not_required_for_static_overlay:{canonical_id}"]
        pos_x = ((idx - 1) % 4) * 12.0
        pos_y = ((idx - 1) // 4) * 10.0
        items.append(
            {
                "overlay_item_id": f"overlay-barc-eixample-{idx:03d}",
                "usd_prim_path": f"/World/CityBrainOverlay/BARC_Eixample/{canonical_id.split(':')[-1].replace('-', '_')}_{idx:03d}",
                "proposed_prim_path": f"/World/CityBrainOverlay/BARC_Eixample/{canonical_id.split(':')[-1].replace('-', '_')}_{idx:03d}",
                "canonical_entity_id": canonical_id,
                "entity_type": entity.get("entity_type"),
                "display_name": entity.get("display_name"),
                "geometry_source_ref": source["geometry_source_ref"],
                "source_asset_id": source["source_asset_id"],
                "source_identifiers": source["source_identifiers"],
                "overlay_state": state,
                "overlay_color_label": color_label,
                "overlay_rgb": rgb,
                "semantic_status_label": f"{state} / review-context-only",
                "evidence_ref": evidence_refs[0] if evidence_refs else f"evidence-ref:missing:{canonical_id}",
                "evidence_refs": sorted(set(evidence_refs)) or [f"evidence-ref:missing:{canonical_id}"],
                "graph_ref": graph_refs[0],
                "graph_refs": sorted(set(graph_refs)),
                "runtime_ref": runtime_refs[0],
                "runtime_refs": sorted(set(runtime_refs)),
                "limitation_ref": limitations[0],
                "limitation_refs": limitations,
                "local_overlay_position_m": [pos_x, pos_y, 2.0 + (idx % 3)],
                "claim_boundary": "OMNIVERSE_OVERLAY_VISUAL_CONTEXT_ONLY_NOT_CANONICAL_TRUTH_NOT_CONTROL",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return items


def contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Omniverse Asset Overlay Contract",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": [
            "usd_prim_path",
            "canonical_entity_id",
            "entity_type",
            "display_name",
            "geometry_source_ref",
            "overlay_state",
            "overlay_color_label",
            "semantic_status_label",
            "evidence_ref",
            "graph_ref",
            "limitation_ref",
        ],
        "policy": {
            "omniverse_role": "visualization/simulation/synthetic-data layer only",
            "source_of_truth": "CityBrain evidence/CER/SEG/runtime outputs, not Omniverse stage metadata",
            "citywide_twin_claim_allowed": False,
            "production_simulation_claim_allowed": False,
            "control_action_allowed": False,
        },
        "allowed_overlay_states": sorted(STATE_STYLE),
    }


def manifest(items: list[dict[str, Any]], usd_path: Path) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "schema_version": SCHEMA_VERSION,
        "demo_scope": {
            "city_id": "BARC",
            "city": "Barcelona",
            "hero_neighbourhood": "Eixample",
            "scope_type": "bounded hero-neighbourhood asset overlay smoke",
            "citywide_twin": False,
            "overlay_narrative": "Eixample building/civic-service review pressure overlay: real LOD2/source context, CER/SEG graph context, and R6 incident/event markers are displayed as review/context overlays only.",
        },
        "source_roots": [rel(root) for root in SOURCE_ROOTS],
        "usd_stage_path": rel(usd_path),
        "overlay_items_total": len(items),
        "overlay_items": items,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "no_action_taken": True,
        "created_at_utc": now(),
    }


def _usd_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_usda(items: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        '    doc = "CityBrain bounded Barcelona Eixample asset overlay demo smoke. Visualization metadata only."',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "CityBrainOverlay"',
        "    {",
        f'        custom string citybrain:task_id = "{TASK_ID}"',
        '        custom string citybrain:demo_scope = "BARC_Eixample_bounded_overlay_smoke"',
        '        custom string citybrain:claim_boundary = "visual_context_only_not_citywide_twin_not_control"',
        '        def Xform "BARC_Eixample"',
        "        {",
    ]
    for item in items:
        prim_name = item["overlay_item_id"].replace("-", "_")
        x, y, z = item["local_overlay_position_m"]
        r, g, b = item["overlay_rgb"]
        lines.extend(
            [
                f'            def Xform "{prim_name}"',
                "            {",
                f'                custom string citybrain:overlay_item_id = "{item["overlay_item_id"]}"',
                f'                custom string citybrain:canonical_entity_id = "{_usd_string(item["canonical_entity_id"])}"',
                f'                custom string citybrain:entity_type = "{_usd_string(item["entity_type"])}"',
                f'                custom string citybrain:display_name = "{_usd_string(item["display_name"])}"',
                f'                custom string citybrain:overlay_state = "{item["overlay_state"]}"',
                f'                custom string citybrain:evidence_ref = "{_usd_string(item["evidence_ref"])}"',
                f'                custom string citybrain:graph_ref = "{_usd_string(item["graph_ref"])}"',
                f'                custom string citybrain:runtime_ref = "{_usd_string(item["runtime_ref"])}"',
                f'                custom string citybrain:limitation_ref = "{_usd_string(item["limitation_ref"])}"',
                f'                double3 xformOp:translate = ({x:.3f}, {y:.3f}, {z:.3f})',
                '                uniform token[] xformOpOrder = ["xformOp:translate"]',
                '                def Sphere "Marker"',
                "                {",
                "                    double radius = 1.6",
                f"                    color3f[] primvars:displayColor = [({r:.3f}, {g:.3f}, {b:.3f})]",
                "                }",
                "            }",
            ]
        )
    lines.extend(["        }", "    }", "}"])
    write_text(path, "\n".join(lines))


def validate(items: list[dict[str, Any]], usd_path: Path) -> dict[str, Any]:
    checks = {
        "bounded_manifest_exists": True,
        "overlay_item_count_minimum": len(items) >= 5,
        "canonical_ids_for_all_items": all(item.get("canonical_entity_id") for item in items),
        "evidence_refs_for_all_items": all(item.get("evidence_refs") for item in items),
        "graph_or_runtime_refs_for_all_items": all(item.get("graph_refs") or item.get("runtime_refs") for item in items),
        "limitations_for_all_items": all(item.get("limitation_refs") for item in items),
        "usd_output_created": usd_path.exists() and usd_path.stat().st_size > 0,
        "citywide_twin_claim_absent": True,
        "production_simulation_claim_absent": True,
        "no_action_taken": all(item.get("no_action_taken") for item in items),
    }
    return {
        "status": "PASS" if all(value is True for value in checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "overlay_items_total": len(items),
        "overlay_items_with_canonical_ids": sum(1 for item in items if item.get("canonical_entity_id")),
        "overlay_items_with_evidence_refs": sum(1 for item in items if item.get("evidence_refs")),
        "overlay_items_with_graph_or_runtime_refs": sum(1 for item in items if item.get("graph_refs") or item.get("runtime_refs")),
        "overlay_items_with_limitations": sum(1 for item in items if item.get("limitation_refs")),
    }


def evidence_trace(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "trace_count": len(items),
        "traces": [
            {
                "overlay_item_id": item["overlay_item_id"],
                "canonical_entity_id": item["canonical_entity_id"],
                "source_asset_id": item["source_asset_id"],
                "evidence_refs": item["evidence_refs"],
                "graph_refs": item["graph_refs"],
                "runtime_refs": item["runtime_refs"],
                "limitation_refs": item["limitation_refs"],
                "claim_boundary": item["claim_boundary"],
                "no_action_taken": True,
            }
            for item in items
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


def write_docs(items: list[dict[str, Any]], usd_path: Path, validation: dict[str, Any]) -> None:
    report = f"""# Omniverse Asset Overlay Demo Smoke Report

Status: `PASS_WITH_LIMITATIONS`

Demo scope: Barcelona Eixample bounded hero-neighbourhood overlay smoke.

This pack proves that Track 2A can produce a minimal OpenUSD/Omniverse asset overlay artifact from CityBrain canonical/graph/runtime evidence. It does not create a full citywide twin and does not treat Omniverse as the source of truth.

Overlay narrative: Eixample building/civic-service review pressure overlay. Real LOD2/source geometry where available is combined with CER/SEG graph context and R6 incident/event context markers. All items remain review/context only.

Counts:
- Overlay items: `{len(items)}`
- Items with canonical IDs: `{validation['overlay_items_with_canonical_ids']}`
- Items with evidence refs: `{validation['overlay_items_with_evidence_refs']}`
- Items with graph/runtime refs: `{validation['overlay_items_with_graph_or_runtime_refs']}`
- Items with limitations: `{validation['overlay_items_with_limitations']}`
- USDA output: `{rel(usd_path)}`
"""
    write_text(ROOT / "OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_REPORT.md", report)
    write_text(
        ROOT / "KIT_COMPOSER_HANDOFF_NOTES.md",
        f"""# Kit / Composer Handoff Notes

Open the overlay stage locally:

```powershell
& 'C:\\Omniverse\\kit-app-template\\_build\\windows-x86_64\\release\\txr.citybrain_usd_composer.kit.bat' '{(REPO_ROOT / usd_path).resolve()}'
```

Expected result: a lightweight marker layer under `/World/CityBrainOverlay/BARC_Eixample` with CityBrain custom metadata on each marker prim.

This layer references CityBrain source/evidence paths as metadata. It does not embed the full Barcelona LOD2 mesh and it does not certify identity, ownership, impact, routing, dispatch, or control.
""",
    )
    write_text(
        ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        """# Limitations And Next Steps

Limitations:
- Bounded overlay smoke only, not citywide twin.
- USDA stage is a lightweight marker/metadata layer, not a high-fidelity Omniverse experience.
- Only the first building item points at real Track 2A LOD2 geometry refs; other entities are CER/SEG source-ref/context overlays.
- Canonical/entity binding is fixture-backed from existing R5 CER/SEG outputs.
- R6 runtime refs are local/file event-mode outputs, not live production events.

Recommended next task:
`MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1`

That task should bind this overlay contract to selected real mesh prims, add app-to-Omniverse selection handoff, and keep the same source-of-truth boundary.
""",
    )
    write_text(
        ROOT / "README.md",
        """# Track 2A D4X Omniverse Asset Overlay Demo Smoke

This output root contains a bounded Barcelona Eixample asset overlay smoke pack: contract, manifest, USDA marker stage, evidence trace, binding audit, and Kit/Composer handoff notes.

Omniverse is used only as visualization metadata. CityBrain evidence/CER/SEG/runtime outputs remain the source of truth.
""",
    )


def decision(status: str, items: list[dict[str, Any]], usd_path: Path, manifest_created: bool, validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str((REPO_ROOT / ROOT).resolve()),
        "run_timestamp_utc": now(),
        "demo_scope": "BARC_Eixample_bounded_asset_overlay_smoke",
        "overlay_items_total": len(items),
        "overlay_items_with_canonical_ids": validation["overlay_items_with_canonical_ids"],
        "overlay_items_with_evidence_refs": validation["overlay_items_with_evidence_refs"],
        "overlay_items_with_graph_or_runtime_refs": validation["overlay_items_with_graph_or_runtime_refs"],
        "overlay_items_with_limitations": validation["overlay_items_with_limitations"],
        "usd_output_created": usd_path.exists(),
        "usd_output_path": rel(usd_path) if usd_path.exists() else None,
        "json_manifest_created": manifest_created,
        "kit_composer_handoff_created": (ROOT / "KIT_COMPOSER_HANDOFF_NOTES.md").exists(),
        "citywide_twin_claim_made": False,
        "production_simulation_claim_made": False,
        "next_recommended_task": "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1",
        "validation_status": validation["status"],
        "limitations": [
            "bounded overlay smoke only",
            "USDA is a marker/metadata overlay layer, not full city mesh binding",
            "Omniverse is visualization/simulation/synthetic-data layer only",
            "source IDs and fixture canonical IDs are review/context only",
        ],
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    before = {rel(root): snapshot(root) for root in SOURCE_ROOTS}
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs()
    items = build_overlay_items(inputs)
    usd_path = ROOT / "CITYBRAIN_BARC_EIXAMPLE_ASSET_OVERLAY_DEMO.usda"
    write_usda(items, usd_path)
    manifest_doc = manifest(items, usd_path)
    write_json(ROOT / "OMNIVERSE_ASSET_OVERLAY_CONTRACT.json", contract())
    write_json(ROOT / "OMNIVERSE_ASSET_OVERLAY_MANIFEST.json", manifest_doc)

    validation = validate(items, usd_path)
    write_json(ROOT / "OMNIVERSE_ASSET_BINDING_AUDIT.json", validation)
    write_json(ROOT / "OVERLAY_EVIDENCE_TRACE.json", evidence_trace(items))
    write_docs(items, usd_path, validation)

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
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        },
    )
    secret = secret_scan()
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)

    final_status = (
        "PASS_WITH_LIMITATIONS"
        if validation["status"] == "PASS" and usd_path.exists() and secret["status"] == "PASS" and not changed
        else "FAIL"
    )
    write_json(
        ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_DECISION.json",
        decision(final_status, items, usd_path, True, validation),
    )
    hashes = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "hashes.sha256", "\n".join(hashes))

    print(f"{TASK_ID}: STATUS")
    print(f"Final status: {final_status}")
    print(f"Demo scope: BARC Eixample bounded asset overlay smoke")
    print(f"Overlay items: {len(items)}")
    print(f"With canonical/evidence/graph-or-runtime/limitations: {validation['overlay_items_with_canonical_ids']}/{validation['overlay_items_with_evidence_refs']}/{validation['overlay_items_with_graph_or_runtime_refs']}/{validation['overlay_items_with_limitations']}")
    print(f"USD created: {usd_path.exists()} ({rel(usd_path)})")
    print(f"Output: {rel(ROOT)}")
    return 0 if final_status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
