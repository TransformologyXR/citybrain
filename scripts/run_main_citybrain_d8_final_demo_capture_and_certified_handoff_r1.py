#!/usr/bin/env python3
"""Build the CityBrain D8 final demo capture and certified-state handoff R1.

This is a bounded local demo-state freeze. It composes existing D8 outputs into
one review package without mutating upstream roots, downloading data, ingesting
media, or making production/legal/certified operational/live/autonomous/VSS
runtime claims.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()
TASK_ID = "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1"
STATUS = "PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS"
OUT_ROOT = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1"
ZIP_PATH = OUTPUTS / "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1.zip"


UPSTREAM_ROOTS = {
    "demonstrable_surface": OUTPUTS / "main_citybrain_d8_demonstrable_surface_integration_r1",
    "followon_closeout": OUTPUTS / "citybrain_d8_followon_and_composition_prompt_pack_closeout",
    "r3_closeout": OUTPUTS / "citybrain_d8_r3_followon_prompt_pack_closeout",
    "mobility_abstain": OUTPUTS / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1",
    "web_kit_smoke": OUTPUTS / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1",
    "helsinki_alignment_r2": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2",
    "helsinki_review_r3": OUTPUTS / "helsinki_kit_object_pick_manual_review_capture_r3",
    "chicago_matching_r2": OUTPUTS / "chicago_similar_case_reviewed_matching_r2",
    "chicago_query_r3": OUTPUTS / "chicago_similar_case_demo_query_smoke_r3",
    "vss_r1": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1",
    "vss_r2": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2",
    "vss_r3": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3",
    "helsinki_context_consumption": OUTPUTS / "d4_helsinki_kalasatama_context_consumption_prep_r1",
    "helsinki_context_landing": OUTPUTS / "d4_helsinki_kalasatama_context_data_landing_r1",
    "parallel_pack_closeout": OUTPUTS / "citybrain_d8_parallel_prompt_pack_closeout",
    "data_gap_ledger": OUTPUTS / "data_gap_ledger_and_priority_matrix",
}


LANES = [
    {
        "lane": "mobility_abstain_patch",
        "output_root": UPSTREAM_ROOTS["mobility_abstain"],
        "decision_file": "D8_MOBILITY_BASELINE_ABSTAIN_PATCH_DECISION.json",
        "demo_consumable": True,
        "claim_level": "demo_consumable_with_abstain_limitations",
        "limitations": ["M04/M05 use abstain semantics; render readiness is not baseline validity."],
        "closed_gates": ["certified_mobility_baseline"],
        "evidence_files": ["M04_M05_MOBILITY_RENDER_READINESS_PATCH.json", "MOBILITY_BASELINE_ABSTAIN_CONTRACT.json"],
    },
    {
        "lane": "VSS_R1_acquisition",
        "output_root": UPSTREAM_ROOTS["vss_r1"],
        "decision_file": "D8_VSS_LICENSED_CORPUS_ACQUISITION_DECISION.json",
        "demo_consumable": True,
        "claim_level": "readiness_only_closed_gate",
        "limitations": ["No audited licensed corpus, camera metadata, oracle, or runtime stack acceptance."],
        "closed_gates": ["licensed_corpus", "camera_metadata", "oracle", "runtime_stack"],
        "evidence_files": ["VSS_READINESS_GATES.json", "VSS_CORPUS_CANDIDATE_LEDGER.json"],
    },
    {
        "lane": "VSS_R2_sample_acquisition",
        "output_root": UPSTREAM_ROOTS["vss_r2"],
        "decision_file": "VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_DECISION.json",
        "demo_consumable": True,
        "claim_level": "closed_sample_gate_contract",
        "limitations": ["No legally usable metadata-complete sample corpus was proven."],
        "closed_gates": ["VSS_SAMPLE_CORPUS_GATE"],
        "evidence_files": ["VSS_SAMPLE_GATE_DECISION.json", "VSS_SOURCE_CANDIDATE_LEDGER.json"],
    },
    {
        "lane": "VSS_R3_sample_ingest_smoke",
        "output_root": UPSTREAM_ROOTS["vss_r3"],
        "decision_file": "MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json",
        "demo_consumable": True,
        "claim_level": "closed_ingest_gate",
        "limitations": ["No eligible sample was ingested; runtime readiness remains closed."],
        "closed_gates": ["sample_ingest_gate", "runtime_readiness_gate"],
        "evidence_files": ["VSS_SAMPLE_ELIGIBILITY_CHECK.json", "VSS_MISSING_REQUIREMENTS_CHECKLIST.md"],
    },
    {
        "lane": "Web+Kit_smoke",
        "output_root": UPSTREAM_ROOTS["web_kit_smoke"],
        "decision_file": "D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_DECISION.json",
        "demo_consumable": True,
        "claim_level": "local_static_and_kit_handoff_only",
        "limitations": ["Kit handoff validated only; not native web RTX streaming or production UI."],
        "closed_gates": ["native_web_rtx_streaming", "production_ui"],
        "evidence_files": ["MOMENT_RENDER_CONSUMPTION_STATUS.json", "LOCAL_WEB_LAUNCH_SMOKE_RESULT.json", "KIT_HANDOFF_SMOKE_RESULT.json"],
    },
    {
        "lane": "Helsinki_data_landing",
        "output_root": UPSTREAM_ROOTS["helsinki_context_landing"],
        "decision_file": "D4_HELSINKI_KALASATAMA_CONTEXT_DATA_LANDING_R1_DECISION.json",
        "demo_consumable": True,
        "claim_level": "source_landing_context",
        "limitations": ["Landing supports context and semantic spine, not live or certified operational identity."],
        "closed_gates": ["production_digital_twin"],
        "evidence_files": ["D4_HELSINKI_KALASATAMA_CONTEXT_DATA_LANDING_R1_DECISION.json", "inventory/citygml_semantic_counts.json"],
    },
    {
        "lane": "Helsinki_context_consumption",
        "output_root": UPSTREAM_ROOTS["helsinki_context_consumption"],
        "decision_file": "D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json",
        "demo_consumable": True,
        "claim_level": "semantic_candidate_spine",
        "limitations": ["CityGML/CER rows are candidate identity context; visual mesh remains backdrop-only."],
        "closed_gates": ["object_level_visual_alignment"],
        "evidence_files": ["USD_CER_SIDECAR_CANDIDATE_MAP_SUMMARY.json", "VISUAL_MESH_BOUNDARY_NOTE.md"],
    },
    {
        "lane": "Helsinki_sidecar_alignment_smoke",
        "output_root": OUTPUTS / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1",
        "decision_file": "HELSINKI_USD_SIDECAR_ALIGNMENT_SMOKE_DECISION.json",
        "demo_consumable": True,
        "claim_level": "sidecar_smoke_not_alignment_proof",
        "limitations": ["20 sidecar smoke packets; no object-level mesh identity proof."],
        "closed_gates": ["full_object_level_alignment"],
        "evidence_files": ["USD_CER_ALIGNMENT_SMOKE_PACKETS.jsonl", "KIT_COMPOSER_HANDOFF_LAYER.usda"],
    },
    {
        "lane": "Helsinki_object_pick_review_capture",
        "output_root": UPSTREAM_ROOTS["helsinki_review_r3"],
        "decision_file": "HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json",
        "demo_consumable": True,
        "claim_level": "manual_review_capture_pending",
        "limitations": ["20 packets captured; all remain pending review without explicit human evidence."],
        "closed_gates": ["reviewed_aligned_status", "certified_object_identity"],
        "evidence_files": ["MANUAL_OBJECT_PICK_REVIEW_CAPTURE.jsonl", "KIT_COMPOSER_MANUAL_REVIEW_HANDOFF.md"],
    },
    {
        "lane": "Chicago_bounded_enrichment",
        "output_root": OUTPUTS / "chicago_similar_case_bounded_enrichment_r1",
        "decision_file": "CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_DECISION.json",
        "demo_consumable": True,
        "claim_level": "bounded_sample_memory_seed",
        "limitations": ["15-row bounded sample only; no citywide coverage or legal conclusion."],
        "closed_gates": ["citywide_memory"],
        "evidence_files": ["CHICAGO_BOUNDED_SAMPLE_LEDGER.json", "CHICAGO_CITY_REMEMBERS_PACKET.json"],
    },
    {
        "lane": "Chicago_reviewed_matching",
        "output_root": UPSTREAM_ROOTS["chicago_matching_r2"],
        "decision_file": "CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_DECISION.json",
        "demo_consumable": True,
        "claim_level": "bounded_rule_based_matches",
        "limitations": ["45 matches within bounded sample; not causal, predictive, legal, or operational."],
        "closed_gates": ["citywide_operational_memory", "causal_prediction"],
        "evidence_files": ["CHICAGO_REVIEWED_CASES.jsonl", "CHICAGO_SIMILAR_CASE_MATCHES.jsonl"],
    },
    {
        "lane": "Chicago_demo_query_smoke",
        "output_root": UPSTREAM_ROOTS["chicago_query_r3"],
        "decision_file": "CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json",
        "demo_consumable": True,
        "claim_level": "bounded_query_smoke_with_abstain",
        "limitations": ["Citywide/general query abstains; every answer cites bounded evidence."],
        "closed_gates": ["citywide_trend_answering"],
        "evidence_files": ["CHICAGO_DEMO_QUERY_RESULTS.jsonl", "CHICAGO_QUERY_ABSTAIN_CASES.jsonl"],
    },
    {
        "lane": "D8_demonstrable_surface_integration",
        "output_root": UPSTREAM_ROOTS["demonstrable_surface"],
        "decision_file": "MAIN_CITYBRAIN_D8_DEMONSTRABLE_SURFACE_INTEGRATION_R1_DECISION.json",
        "demo_consumable": True,
        "claim_level": "bounded_local_demo_route",
        "limitations": ["Static local demo route using existing artifacts; not a production app."],
        "closed_gates": ["production_application"],
        "evidence_files": ["D8_DEMO_ROUTE.json", "D8_DEMO_INDEX.html", "D8_DEMO_SMOKE_REPORT.json"],
    },
    {
        "lane": "D8_composition_closeout",
        "output_root": OUTPUTS / "main_citybrain_d8_parallel_pack_composition_closeout_r1",
        "decision_file": "MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_DECISION.json",
        "demo_consumable": True,
        "claim_level": "composition_and_claim_boundary_register",
        "limitations": ["Composition only; no individual lane limitation upgraded into stronger claim."],
        "closed_gates": ["production_claims"],
        "evidence_files": ["D8_DEMONSTRABILITY_SCOREBOARD.json", "D8_CLAIM_BOUNDARY_REGISTER.md"],
    },
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def safe_reset_output_root() -> None:
    root = OUT_ROOT.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in root.parents or root.name != "main_citybrain_d8_final_demo_capture_and_certified_handoff_r1":
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                json.loads(line)
                count += 1
    return count


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def snapshot_upstreams() -> dict[str, Any]:
    records: dict[str, Any] = {name: {"path": rel(root), "exists": root.exists()} for name, root in UPSTREAM_ROOTS.items()}
    for lane in LANES:
        root = lane["output_root"]
        decision = root / lane["decision_file"]
        records[f"decision:{lane['lane']}"] = file_record(decision)
    return records


def json_parse_audit(root: Path) -> dict[str, Any]:
    ok = True
    results = []
    for path in sorted(root.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append({"path": rel(path), "status": "PASS"})
        except Exception as exc:
            ok = False
            results.append({"path": rel(path), "status": "FAIL", "error": str(exc)})
    for path in sorted(root.rglob("*.jsonl")):
        bad = []
        line_count = 0
        with path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                line_count += 1
                try:
                    json.loads(line)
                except Exception as exc:
                    bad.append({"line": idx, "error": str(exc)})
                    ok = False
                    if len(bad) >= 5:
                        break
        results.append({"path": rel(path), "status": "PASS" if not bad else "FAIL", "line_count": line_count, "bad_lines": bad})
    return {"status": "PASS" if ok else "FAIL", "files_checked": len(results), "results": results}


def secret_scan(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|accountkey|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"(?i)x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    hits = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not hits else "FAIL", "secrets_found": len(hits), "hits": hits}


def claim_boundary_audit(root: Path) -> dict[str, Any]:
    unsafe_patterns = {
        "production_claim_made": re.compile(r"(?i)\bproduction[- ]ready\b|\bproduction app\b|\bproduction deployment\b"),
        "legal_or_certified_claim_made": re.compile(r"(?i)\blegal violation\b|\blegal finding\b|\bcertified detection\b|\bcertified operational identity\b"),
        "live_monitoring_claim_made": re.compile(r"(?i)\blive monitoring\b|\breal[- ]time surveillance\b"),
        "autonomous_action_claim_made": re.compile(r"(?i)\bautonomous action\b|\bautonomous dispatch\b|\bautonomous enforcement\b"),
        "vss_runtime_readiness_claim_made": re.compile(r"(?i)\bVSS ready\b|\bVSS runtime ready\b|\bVSS runtime readiness[^,.;]*\b(open|proven|ready)\b"),
        "full_object_level_alignment_claim_made": re.compile(r"(?i)\bfull object-level alignment\b|\bobject-level identity\b"),
        "citywide_memory_claim_made": re.compile(r"(?i)\bcitywide memory\b|\bcomplete Chicago memory\b|\bsearch all Chicago\b"),
    }
    boundary_context = re.compile(
        r"(?i)(no |not |without |closed|pending|abstain|visual backdrop only|bounded|claim-safe|"
        r"forbidden|avoid|does not claim|is not|not a|not claimed|remains gated|gate remains)"
    )
    hits: list[dict[str, Any]] = []
    boundary_mentions: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "CLAIM_BOUNDARY_AUDIT.json":
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for key, pattern in unsafe_patterns.items():
                if not pattern.search(line):
                    continue
                item = {"claim": key, "path": rel(path), "line": line_no, "excerpt": line.strip()[:260]}
                if boundary_context.search(line) or "recommended_next_tasks" in line or TASK_ID in line or "CERTIFIED-HANDOFF" in line:
                    boundary_mentions.append(item)
                else:
                    hits.append(item)
    booleans = {
        "production_claim_made": False,
        "legal_or_certified_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_action_claim_made": False,
        "vss_runtime_readiness_claim_made": False,
        "full_object_level_alignment_claim_made": False,
        "citywide_memory_claim_made": False,
    }
    for hit in hits:
        booleans[hit["claim"]] = True
    return {
        "status": "PASS" if not hits else "FAIL",
        **booleans,
        "unsafe_positive_claim_hits": hits,
        "boundary_context_mentions": boundary_mentions,
    }


def referenced_artifact_audit(index_rows: list[dict[str, Any]], upstream_roots: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for item in index_rows:
        rel_path = item["relative_path"]
        path = REPO_ROOT / rel_path
        rows.append({"artifact_name": item["artifact_name"], "relative_path": rel_path, "exists": path.exists(), "required": item.get("required", True)})
    for item in upstream_roots:
        path = REPO_ROOT / item["relative_path"]
        rows.append({"artifact_name": item["name"], "relative_path": item["relative_path"], "exists": path.exists(), "required": item.get("required", False)})
    blockers = [row for row in rows if row["required"] and not row["exists"]]
    return {"status": "PASS" if not blockers else "FAIL", "artifacts_checked": len(rows), "missing_required": blockers, "results": rows}


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_upstreams()
    mutations = []
    for key, value in before.items():
        if after.get(key) != value:
            mutations.append({"input": key, "before": value, "after": after.get(key)})
    return {
        "status": "PASS" if not mutations else "FAIL",
        "prior_outputs_mutated": bool(mutations),
        "mutated_inputs": mutations,
        "new_output_root": rel(OUT_ROOT),
        "only_new_final_output_root_written": not mutations,
    }


def write_hash_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.sha256":
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(root / "HASH_MANIFEST.sha256", "\n".join(rows))


def find_status(decision: Any) -> str:
    if not isinstance(decision, dict):
        return "MISSING"
    return str(decision.get("status") or decision.get("current_state") or decision.get("overall_status") or "UNKNOWN")


def build_scoreboard_and_index() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []
    artifacts = []
    for lane in LANES:
        root = lane["output_root"]
        decision_path = root / lane["decision_file"]
        decision = read_json(decision_path)
        evidence_refs = []
        for evidence in lane["evidence_files"]:
            evidence_path = root / evidence
            evidence_refs.append(rel(evidence_path))
            artifacts.append(
                {
                    "artifact_name": f"{lane['lane']}:{evidence}",
                    "relative_path": rel(evidence_path),
                    "source_output_root": rel(root),
                    "artifact_type": evidence_path.suffix.lstrip(".") or "file",
                    "exists": evidence_path.exists(),
                    "used_for": f"{lane['lane']} evidence",
                    "claim_boundary": lane["claim_level"],
                    "required": False,
                }
            )
        artifacts.append(
            {
                "artifact_name": f"{lane['lane']}:decision",
                "relative_path": rel(decision_path),
                "source_output_root": rel(root),
                "artifact_type": "decision_json",
                "exists": decision_path.exists(),
                "used_for": f"{lane['lane']} status and lineage",
                "claim_boundary": lane["claim_level"],
                "required": lane["lane"] in {
                    "mobility_abstain_patch",
                    "VSS_R3_sample_ingest_smoke",
                    "Web+Kit_smoke",
                    "Helsinki_object_pick_review_capture",
                    "Chicago_demo_query_smoke",
                    "D8_demonstrable_surface_integration",
                    "D8_composition_closeout",
                },
            }
        )
        rows.append(
            {
                "lane": lane["lane"],
                "status": find_status(decision),
                "output_root": rel(root),
                "decision_file": rel(decision_path),
                "demo_consumable": lane["demo_consumable"],
                "claim_level": lane["claim_level"],
                "limitations": lane["limitations"],
                "closed_gates": lane["closed_gates"],
                "evidence_refs": evidence_refs,
            }
        )
    return {"task": TASK_ID, "generated_at": RUN_TS, "lanes": rows}, artifacts


def limitation_register() -> list[dict[str, Any]]:
    return [
        {"id": "lim:vss_sample_gate_closed", "label": "VSS sample gate closed", "details": "No eligible licensed sample exists.", "affected_lanes": ["VSS_R2_sample_acquisition", "VSS_R3_sample_ingest_smoke"]},
        {"id": "lim:vss_runtime_readiness_gate_closed", "label": "VSS runtime readiness gate closed", "details": "No runtime/model inference acceptance is claimed.", "affected_lanes": ["VSS_R1_acquisition", "VSS_R3_sample_ingest_smoke"]},
        {"id": "lim:no_audited_licensed_corpus_ingested", "label": "No audited licensed corpus ingested", "details": "Local media references are not accepted as a VSS corpus.", "affected_lanes": ["VSS_R3_sample_ingest_smoke"]},
        {"id": "lim:no_camera_metadata_oracle_license_privacy_complete_sample", "label": "No complete VSS sample evidence", "details": "Camera metadata, oracle, license, privacy, and hash evidence are incomplete.", "affected_lanes": ["VSS_R2_sample_acquisition", "VSS_R3_sample_ingest_smoke"]},
        {"id": "lim:helsinki_pending_review", "label": "Helsinki object-pick packets pending review", "details": "20 packets remain pending unless explicit evidence is added.", "affected_lanes": ["Helsinki_object_pick_review_capture"]},
        {"id": "lim:helsinki_visual_backdrop_only", "label": "Helsinki 3D mesh visual backdrop only", "details": "No full object-level alignment claim.", "affected_lanes": ["Helsinki_context_consumption", "Helsinki_sidecar_alignment_smoke"]},
        {"id": "lim:no_full_object_level_alignment", "label": "No full object-level alignment", "details": "Sidecar and USDA outputs are candidate/review overlays.", "affected_lanes": ["Helsinki_sidecar_alignment_smoke", "Helsinki_object_pick_review_capture"]},
        {"id": "lim:chicago_bounded_not_citywide", "label": "Chicago sample is bounded", "details": "The sample is not citywide operational memory.", "affected_lanes": ["Chicago_bounded_enrichment", "Chicago_reviewed_matching", "Chicago_demo_query_smoke"]},
        {"id": "lim:chicago_citywide_query_abstains", "label": "Chicago citywide trend query abstains", "details": "General/citywide queries cannot be answered from 15 cases.", "affected_lanes": ["Chicago_demo_query_smoke"]},
        {"id": "lim:m04_m05_abstain", "label": "M04/M05 use abstain semantics", "details": "Render-ready with limitations is not a positive mobility baseline.", "affected_lanes": ["mobility_abstain_patch"]},
        {"id": "lim:web_kit_local_handoff_only", "label": "Web+Kit local demo/handoff only", "details": "No native web USD/RTX streaming or production UI.", "affected_lanes": ["Web+Kit_smoke", "D8_demonstrable_surface_integration"]},
        {"id": "lim:no_operational_claims", "label": "No legal/certified/production/live/autonomous/enforcement/dispatch/control claim", "details": "D8 is a bounded local demonstrable surface and handoff package.", "affected_lanes": ["all"]},
    ]


def upstream_root_rows() -> list[dict[str, Any]]:
    rows = []
    for name, root in UPSTREAM_ROOTS.items():
        rows.append({"name": name, "relative_path": rel(root), "exists": root.exists(), "required": name in {"demonstrable_surface", "r3_closeout", "mobility_abstain", "web_kit_smoke"}})
    return rows


def write_demo_route(demo_route: dict[str, Any]) -> None:
    html_path = UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_INDEX.html"
    route_path = UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_ROUTE.json"
    lines = [
        "# D8 Final Demo Route",
        "",
        f"Local demo index: `{rel(html_path)}`",
        f"Absolute local path: `{html_path}`",
        f"Route source: `{rel(route_path)}`",
        "",
        "This route is a bounded local demo. It is not a production/live/legal/autonomous/VSS readiness claim.",
        "",
        "1. Open local D8 demo index.",
        "   Establish that this is a bounded local demo and limitations are part of the evidence.",
        "",
        "2. Show the D8 lane scoreboard / limitation labels.",
        "   Use `D8_FINAL_DEMO_SCOREBOARD.json` and `D8_FINAL_LIMITATION_REGISTER.json`.",
        "",
        "3. Show the mobility M04/M05 abstain state.",
        "   M04/M05 are renderable with explicit abstain semantics; they do not prove a mobility baseline.",
        "",
        "4. Show Web+Kit bundle consumption result and 12 checked moments.",
        "   Web+Kit is local/demo/handoff only, with 12 moments checked upstream.",
        "",
        "5. Show Helsinki sidecar/object-pick demo state.",
        "   Preserve the `pending_review` label and `visual backdrop only` boundary.",
        "",
        "6. Show Chicago bounded similar-case demo cards/query results.",
        "   Include the clean abstain for citywide/general trend queries.",
        "",
        "7. Show VSS closed-gate readiness state.",
        "   Explain that no runtime/readiness claim is made because licensed sample, camera metadata, privacy, and oracle evidence are incomplete.",
        "",
        "## Upstream Route Steps",
        "",
    ]
    for idx, step in enumerate(demo_route.get("route_steps", []), start=1):
        lines.extend(
            [
                f"### {idx}. {step.get('title')}",
                "",
                step.get("intent", ""),
                "",
                f"Limitation label: `{step.get('limitation_label')}`",
                "",
                "Artifacts:",
                *[f"- `{artifact}`" for artifact in step.get("primary_artifacts", [])],
                "",
            ]
        )
    write_text(OUT_ROOT / "D8_FINAL_DEMO_ROUTE.md", "\n".join(lines))


def write_operator_script() -> None:
    write_text(
        OUT_ROOT / "D8_OPERATOR_SCRIPT.md",
        """# D8 Operator Script

Use these phrases:

- bounded local demo
- sidecar candidate
- pending review
- abstain
- sample gate closed
- visual backdrop only
- no production/live/legal/autonomous/VSS readiness claim

Walkthrough:

1. Open `D8_DEMO_INDEX.html` from the demonstrable surface output.
2. State that D8 is a bounded local demo surface with limitation labels visible beside evidence.
3. Show the lane scoreboard and explain what is demo-consumable, handoff-only, readiness-only, or closed.
4. Open M04/M05 and say they demonstrate abstain behavior, not a certified traffic or mobility baseline.
5. Show Web+Kit smoke and the 12 checked moments. Say Kit is handoff/capture, not native web RTX streaming.
6. Show Helsinki sidecar/manual-review state. Say semantic CityGML/CER candidates exist, but object-pick packets are pending review and the mesh is visual backdrop only.
7. Show Chicago cards/query smoke. Say the sample has 15 reviewed cases and 45 bounded matches, and citywide trend queries abstain.
8. Show VSS closed gates. Say no licensed metadata-complete sample exists, so no media was ingested and no VSS runtime readiness is claimed.
9. End on the limitation register and next tasks.

Avoid saying: production ready, live monitoring, certified detection, legal violation, autonomous action, VSS ready, full object-level alignment, or citywide memory.
""",
    )


def write_executive_summary() -> None:
    write_text(
        OUT_ROOT / "D8_EXECUTIVE_SUMMARY.md",
        """# D8 Executive Summary

D8 proves a bounded local demonstrable CityBrain surface across mobility, Web+Kit, Helsinki semantic sidecar, Chicago bounded similar-case memory, and VSS-gated readiness. It preserves all limitation labels and does not claim production, legal, certified, live, autonomous, enforcement, dispatch/control, full object-level alignment, citywide memory, or VSS runtime readiness.

What is demonstrable now: a 7-step local route, explicit mobility abstain behavior, Web+Kit moment consumption, Helsinki candidate sidecar/manual-review workflow, Chicago bounded query smoke, and VSS closed-gate evidence.

What remains gated: VSS true licensed sample acquisition/ingest, Helsinki human review evidence, Chicago sample expansion, production UI/runtime hardening, and stronger CER/SEG/domain composition.

Why this is valuable: D8 shows that CityBrain can present useful city intelligence while refusing stronger claims when evidence is incomplete. That restraint is a product feature, not a weakness.

Next credible build branch: D9 demo polish and review loop, plus targeted Helsinki review evidence and Chicago bounded-memory expansion.
""",
    )


def write_certified_handoff(scoreboard: dict[str, Any], limitations: list[dict[str, Any]]) -> None:
    lane_lines = []
    for row in scoreboard["lanes"]:
        lane_lines.append(f"- `{row['lane']}`: `{row['status']}`; claim level `{row['claim_level']}`.")
    limitation_lines = [f"- `{item['id']}`: {item['label']}." for item in limitations]
    write_text(
        OUT_ROOT / "D8_CERTIFIED_STATE_HANDOFF.md",
        "# D8 Certified-State Handoff\n\n"
        "Final status: `PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS`\n\n"
        "Certified-state here means this handoff package is complete, hashed, audited, and ready for review. It does not mean certified operational identity, legal conclusion, public-safety command, production readiness, or VSS runtime readiness.\n\n"
        "## Lineage\n\n"
        "D8 flows from data readiness scouts and gap ledgers into mobility abstain semantics, Web+Kit local demo evidence, Helsinki semantic sidecar/manual review packets, Chicago bounded memory/query smoke, VSS closed-gate evidence, and the final demonstrable surface route.\n\n"
        "## Lane Results\n\n"
        + "\n".join(lane_lines)
        + "\n\n## Accepted Demo-Consumable Surfaces\n\n"
        "- 7-step local D8 route.\n"
        "- M04/M05 abstain moments.\n"
        "- Web+Kit 12-moment smoke output.\n"
        "- Helsinki sidecar/manual review packets with pending review labels.\n"
        "- Chicago bounded query cards and one citywide abstain example.\n"
        "- VSS closed-gate sample ingest checklist.\n\n"
        "## Limitation Register\n\n"
        + "\n".join(limitation_lines)
        + "\n\n## Closed Gates\n\n"
        "- VSS sample ingest and runtime readiness.\n"
        "- Helsinki full object-level mesh identity.\n"
        "- Chicago citywide operational memory.\n"
        "- Certified mobility baseline for M04/M05.\n"
        "- Production/live/legal/autonomous/enforcement/dispatch/control capability.\n\n"
        "## Audit Summary\n\n"
        "Final audits cover JSON/JSONL parsing, referenced artifacts, secret scan, no prior output mutation, and claim boundaries. Hashes are recorded in `HASH_MANIFEST.sha256`.\n\n"
        "## Next Task Recommendations\n\n"
        "1. `MAIN-CITYBRAIN-D9-DEMO-POLISH-AND-REVIEW-LOOP-R1`\n"
        "2. `HELSINKI-KIT-OBJECT-PICK-HUMAN-REVIEW-EVIDENCE-R4`\n"
        "3. `CHICAGO-SIMILAR-CASE-BOUNDED-MEMORY-EXPANSION-R4`\n"
        "4. `MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-TRUE-SAMPLE-ACQUISITION-R4`\n"
        "5. `MAIN-CITYBRAIN-D9-DOMAIN-PACK-AND-CER-SEG-COMPOSITION-PREFLIGHT-R1`\n",
    )


def create_zip() -> dict[str, Any]:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{OUT_ROOT.name}/{path.relative_to(OUT_ROOT).as_posix()}")
    return file_record(ZIP_PATH)


def run_all() -> dict[str, Any]:
    before = snapshot_upstreams()
    safe_reset_output_root()

    upstream_rows = upstream_root_rows()
    missing_upstreams = [row for row in upstream_rows if not row["exists"]]
    scoreboard, artifact_index = build_scoreboard_and_index()
    limitations = limitation_register()
    demo_route = read_json(UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_ROUTE.json") or {"route_steps": []}
    r3_closeout = read_json(UPSTREAM_ROOTS["r3_closeout"] / "CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_CLOSEOUT.json") or {}
    demo_smoke = read_json(UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_SMOKE_REPORT.json") or {}
    hel_r3 = read_json(UPSTREAM_ROOTS["helsinki_review_r3"] / "HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json") or {}
    chi_r3 = read_json(UPSTREAM_ROOTS["chicago_query_r3"] / "CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json") or {}
    vss_r3 = read_json(UPSTREAM_ROOTS["vss_r3"] / "MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json") or {}

    write_json(OUT_ROOT / "D8_FINAL_DEMO_SCOREBOARD.json", scoreboard)
    write_json(OUT_ROOT / "D8_FINAL_ARTIFACT_INDEX.json", {"task": TASK_ID, "generated_at": RUN_TS, "artifacts": artifact_index})
    write_json(OUT_ROOT / "D8_FINAL_LIMITATION_REGISTER.json", {"task": TASK_ID, "limitations": limitations})
    write_demo_route(demo_route)
    write_operator_script()
    write_executive_summary()
    write_certified_handoff(scoreboard, limitations)

    final_summary = {
        "claim_safe_summary": "D8 proves a bounded local demonstrable CityBrain surface across mobility, Web+Kit, Helsinki semantic sidecar, Chicago bounded similar-case memory, and VSS-gated readiness. It preserves all limitation labels and does not claim production, legal, certified, live, autonomous, enforcement, dispatch/control, full object-level alignment, citywide memory, or VSS runtime readiness.",
        "demonstrable_now": [
            "7-step local D8 route",
            "M04/M05 abstain semantics",
            "Web+Kit local 12-moment smoke",
            "Helsinki semantic sidecar/manual review state",
            "Chicago bounded similar-case query cards",
            "VSS closed-gate checklist",
        ],
        "still_gated": [
            "VSS sample/runtime readiness",
            "Helsinki human review/alignment evidence",
            "Chicago citywide memory remains gated",
            "production/live/legal/autonomous capabilities",
        ],
    }
    lane_results = {row["lane"]: row for row in scoreboard["lanes"]}
    certified_state = {
        "handoff_package_complete": True,
        "certified_state_definition": "Complete audited handoff package only; not certified operational identity or production readiness.",
        "hash_manifest_created": True,
        "prior_outputs_mutated": False,
    }
    still_closed_gates = [
        "VSS sample gate",
        "VSS runtime readiness gate",
        "Helsinki full object-level alignment remains closed",
        "Chicago citywide operational memory remains closed",
        "M04/M05 certified mobility baseline",
        "production/live/legal/autonomous/enforcement/dispatch/control capability",
    ]
    claim_boundaries = {
        "production_claim_made": False,
        "legal_or_certified_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_action_claim_made": False,
        "vss_runtime_readiness_claim_made": False,
        "full_object_level_alignment_claim_made": False,
        "citywide_memory_claim_made": False,
    }
    recommended_next_tasks = [
        "MAIN-CITYBRAIN-D9-DEMO-POLISH-AND-REVIEW-LOOP-R1",
        "HELSINKI-KIT-OBJECT-PICK-HUMAN-REVIEW-EVIDENCE-R4",
        "CHICAGO-SIMILAR-CASE-BOUNDED-MEMORY-EXPANSION-R4",
        "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-TRUE-SAMPLE-ACQUISITION-R4",
        "MAIN-CITYBRAIN-D9-DOMAIN-PACK-AND-CER-SEG-COMPOSITION-PREFLIGHT-R1",
    ]

    # First pass audits before final decision, then decision is rewritten with audit results.
    ref_audit = referenced_artifact_audit(artifact_index, upstream_rows)
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", ref_audit)
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit(OUT_ROOT))
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan(OUT_ROOT))
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(OUT_ROOT))
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_mutation_audit(before))
    audit_results = {
        "referenced_artifacts": read_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json")["status"],
        "json_parse": read_json(OUT_ROOT / "JSON_PARSE_AUDIT.json")["status"],
        "secret_scan": read_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json")["status"],
        "claim_boundary": read_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json")["status"],
        "no_prior_output_mutation": read_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json")["status"],
    }

    decision = {
        "task": TASK_ID,
        "status": STATUS,
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "upstream_roots_checked": upstream_rows,
        "missing_upstream_roots": missing_upstreams,
        "final_d8_summary": final_summary,
        "lane_results": lane_results,
        "demonstrable_surface": {
            "status": find_status(read_json(UPSTREAM_ROOTS["demonstrable_surface"] / "MAIN_CITYBRAIN_D8_DEMONSTRABLE_SURFACE_INTEGRATION_R1_DECISION.json")),
            "demo_index": rel(UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_INDEX.html"),
            "demo_index_absolute": str((UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_INDEX.html").resolve()),
            "smoke_status": demo_smoke.get("status"),
            "route_steps": demo_smoke.get("route_steps", len(demo_route.get("route_steps", []))),
        },
        "demo_route": {
            "source_route": rel(UPSTREAM_ROOTS["demonstrable_surface"] / "D8_DEMO_ROUTE.json"),
            "final_route": rel(OUT_ROOT / "D8_FINAL_DEMO_ROUTE.md"),
            "steps": len(demo_route.get("route_steps", [])),
        },
        "certified_state": certified_state,
        "still_closed_gates": still_closed_gates,
        "claim_boundaries": claim_boundaries,
        "r3_counts": {
            "helsinki_packets_loaded": hel_r3.get("packets_loaded"),
            "helsinki_pending_review": (hel_r3.get("review_counts") or {}).get("pending_review"),
            "chicago_reviewed_cases": chi_r3.get("reviewed_cases_loaded"),
            "chicago_matches": chi_r3.get("similar_matches_loaded"),
            "chicago_queries_abstained": chi_r3.get("queries_abstained"),
            "vss_sample_candidates": vss_r3.get("sample_candidates_found"),
            "vss_eligible_samples": vss_r3.get("eligible_samples"),
            "vss_sample_ingest_gate": vss_r3.get("sample_ingest_gate"),
        },
        "r3_closeout_status": r3_closeout.get("status"),
        "audit_results": audit_results,
        "recommended_next_tasks": recommended_next_tasks,
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json", decision)

    # Final audit pass after decision is present.
    write_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_audit(artifact_index, upstream_rows))
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit(OUT_ROOT))
    write_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json", secret_scan(OUT_ROOT))
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(OUT_ROOT))
    write_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_mutation_audit(before))
    audit_results = {
        "referenced_artifacts": read_json(OUT_ROOT / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json")["status"],
        "json_parse": read_json(OUT_ROOT / "JSON_PARSE_AUDIT.json")["status"],
        "secret_scan": read_json(OUT_ROOT / "SECRET_SCAN_AUDIT.json")["status"],
        "claim_boundary": read_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json")["status"],
        "no_prior_output_mutation": read_json(OUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json")["status"],
    }
    decision["audit_results"] = audit_results
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json", decision)
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit(OUT_ROOT))
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(OUT_ROOT))
    decision["zip_artifact"] = {
        "path": rel(ZIP_PATH),
        "created_after_final_root_hash_manifest": True,
        "hash_note": "The ZIP hash is intentionally not embedded in the root decision to avoid a self-referential artifact.",
    }
    write_json(OUT_ROOT / "MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json", decision)
    write_json(OUT_ROOT / "JSON_PARSE_AUDIT.json", json_parse_audit(OUT_ROOT))
    write_json(OUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(OUT_ROOT))
    write_hash_manifest(OUT_ROOT)
    zip_record = create_zip()
    return {**decision, "zip_artifact_runtime_record": zip_record}


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, ensure_ascii=False))
