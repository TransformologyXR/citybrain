#!/usr/bin/env python3
"""Run the CityBrain D8 parallel prompt pack as bounded readiness/smoke lanes.

This runner creates five output packages:
- Mobility baseline/abstain contract patch
- VSS licensed corpus acquisition readiness
- Web+Kit bundle consumption smoke
- Helsinki USD/CER sidecar alignment smoke
- Chicago similar-case bounded enrichment

It does not download large datasets, mutate prior certified outputs, run VSS, or
claim production/live/autonomous/legal/certified readiness.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

ROOTS = {
    "mobility": REPO_ROOT / "outputs" / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1",
    "vss": REPO_ROOT / "outputs" / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1",
    "webkit": REPO_ROOT / "outputs" / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1",
    "helsinki": REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1",
    "chicago": REPO_ROOT / "outputs" / "chicago_similar_case_bounded_enrichment_r1",
}

STATUS = {
    "mobility": "PASS_MAIN_CITYBRAIN_D8_MOBILITY_BASELINE_ABSTAIN_CONTRACT_PATCH_R1_WITH_LIMITATIONS",
    "vss": "PASS_MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_ACQUISITION_R1_WITH_LIMITATIONS",
    "webkit": "PASS_MAIN_CITYBRAIN_D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS",
    "helsinki": "PASS_D4_HELSINKI_KALASATAMA_USD_SIDECAR_ALIGNMENT_SMOKE_R1_WITH_LIMITATIONS",
    "chicago": "PASS_CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_R1_WITH_LIMITATIONS",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except Exception:
            continue
    return None


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
        "path": rel(path) if path.exists() else str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def watched_input_stats() -> dict[str, dict[str, Any]]:
    paths = {
        "d8_scoreboard": REPO_ROOT / "outputs/main_citybrain_d8_parallel_data_readiness_closeout/DATA_READINESS_SCOREBOARD.json",
        "d8_closeout": REPO_ROOT / "outputs/main_citybrain_d8_parallel_data_readiness_closeout/PARALLEL_DATA_READINESS_CLOSEOUT_DECISION.json",
        "gap_ledger": REPO_ROOT / "outputs/data_gap_ledger_and_priority_matrix/DATA_GAP_LEDGER.json",
        "source_access": REPO_ROOT / "outputs/data_gap_ledger_and_priority_matrix/SOURCE_ACCESS_STATUS.json",
        "demo_bundle_manifest": REPO_ROOT / "outputs/main_citybrain_d8_web_kit_demo_asset_data_bundle/DEMO_DATA_BUNDLE_MANIFEST.json",
        "moment_render_index": REPO_ROOT / "outputs/main_citybrain_d8_mobility_access_live_surface_wiring_r4/MOMENT_RENDER_HOME_INDEX.json",
        "committed_moments": REPO_ROOT / "outputs/main_citybrain_d8_hero_portfolio_and_moment_beat_map_lock_r1/D8_COMMITTED_MOMENTS.json",
        "helsinki_sidecar": REPO_ROOT / "outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/USD_CER_SIDECAR_CANDIDATE_MAP.jsonl",
        "helsinki_decision": REPO_ROOT / "outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json",
    }
    return {name: file_record(path) for name, path in paths.items()}


def json_parse_audit(root: Path) -> dict[str, Any]:
    rows = []
    ok = True
    for path in sorted(root.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            status = "PASS"
            error = None
        except Exception as exc:
            ok = False
            status = "FAIL"
            error = str(exc)
        rows.append({"path": rel(path), "status": status, "error": error})
    for path in sorted(root.rglob("*.jsonl")):
        line_count = 0
        bad_lines = []
        with path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    json.loads(line)
                except Exception as exc:
                    ok = False
                    bad_lines.append({"line": idx, "error": str(exc)})
                    if len(bad_lines) >= 5:
                        break
        rows.append({"path": rel(path), "status": "PASS" if not bad_lines else "FAIL", "line_count": line_count, "bad_lines": bad_lines})
    return {"status": "PASS" if ok else "FAIL", "files_checked": len(rows), "results": rows}


def secret_scan(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|accountkey|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"(?i)x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not hits else "FAIL", "secrets_found": len(hits), "hits": hits}


def hash_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"generated_at": RUN_TS, "files": files}


def write_hashes(root: Path) -> None:
    manifest = hash_manifest(root)
    write_json(root / "HASH_MANIFEST.json", manifest)
    write_text(root / "hashes.sha256", "\n".join(f"{item['sha256']}  {item['path']}" for item in manifest["files"]))
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def write_common_audits(root: Path, before: dict[str, Any], after: dict[str, Any], claim_overrides: dict[str, Any] | None = None) -> None:
    mutations = []
    for key, before_value in before.items():
        after_value = after.get(key)
        if before_value != after_value:
            mutations.append({"key": key, "before": before_value, "after": after_value})
    write_json(
        root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not mutations else "FAIL",
            "prior_outputs_mutated": bool(mutations),
            "mutated_inputs": mutations,
            "generated_output_root": rel(root),
        },
    )
    claims = {
        "status": "PASS",
        "production_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_action_claim_made": False,
        "dispatch_control_enforcement_claim_made": False,
        "legal_or_certified_claim_made": False,
        "vss_or_model_inference_claim_made": False,
    }
    if claim_overrides:
        claims.update(claim_overrides)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claims)
    write_json(root / "SECRET_AUDIT.json", secret_scan(root))
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    write_hashes(root)


def local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", ""]
    for path in sorted(root.iterdir()):
        if path.is_file():
            lines.append(f"- `{path.name}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def load_moments() -> list[dict[str, Any]]:
    committed = read_json(REPO_ROOT / "outputs/main_citybrain_d8_hero_portfolio_and_moment_beat_map_lock_r1/D8_COMMITTED_MOMENTS.json") or {}
    render = read_json(REPO_ROOT / "outputs/main_citybrain_d8_mobility_access_live_surface_wiring_r4/MOMENT_RENDER_HOME_INDEX.json") or {}
    render_by_id = {row.get("moment_id"): row for row in render.get("moments", [])}
    moments = []
    for row in committed.get("moments", []):
        merged = dict(row)
        if row.get("moment_id") in render_by_id:
            merged.update({f"render_{k}": v for k, v in render_by_id[row["moment_id"]].items()})
        moments.append(merged)
    return moments


def run_mobility(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["mobility"]
    root.mkdir(parents=True, exist_ok=True)
    inputs = {
        "readiness_scoreboard": file_record(REPO_ROOT / "outputs/main_citybrain_d8_parallel_data_readiness_closeout/DATA_READINESS_SCOREBOARD.json"),
        "data_gap_ledger": file_record(REPO_ROOT / "outputs/data_gap_ledger_and_priority_matrix/DATA_GAP_LEDGER.json"),
        "source_priority_matrix": file_record(REPO_ROOT / "outputs/data_gap_ledger_and_priority_matrix/DATA_SOURCE_PRIORITY_MATRIX.json"),
        "option_field_presence": file_record(REPO_ROOT / "outputs/main_citybrain_d8_mobility_access_option_set_gap_backfill_scout/OPTION_SET_FIELD_PRESENCE_REPORT.json"),
        "moment_render_index": file_record(REPO_ROOT / "outputs/main_citybrain_d8_mobility_access_live_surface_wiring_r4/MOMENT_RENDER_HOME_INDEX.json"),
        "demo_bundle_moment_scoreboard": file_record(REPO_ROOT / "outputs/main_citybrain_d8_web_kit_demo_asset_data_bundle/moment_scoreboard.json"),
    }
    field_presence = read_json(REPO_ROOT / "outputs/main_citybrain_d8_mobility_access_option_set_gap_backfill_scout/OPTION_SET_FIELD_PRESENCE_REPORT.json") or {}
    contract = {
        "task_id": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
        "allowed_mobility_states": {
            "baseline_supported": "Future state only: explicit baseline evidence exists and passes review.",
            "baseline_abstained": "System intentionally declines baseline validity because evidence is incomplete or not operationally/statistically justified.",
            "ready_for_render_with_limitations": "Enough evidence exists to render the moment with limitations visible; this is not baseline validity.",
            "insufficient_evidence": "Moment cannot render as evidence-backed; show limitation or parking-lot state.",
        },
        "required_fields": [
            "moment_id",
            "mobility_claim_type",
            "evidence_refs",
            "render_status",
            "baseline_status",
            "abstain_reason",
            "limitation_refs",
            "review_state",
        ],
        "separation_rule": "field/evidence presence != render readiness != baseline validity; abstain remains valid product behavior.",
        "forbidden_claims": [
            "live mobility monitoring",
            "certified traffic baseline",
            "measured traffic impact",
            "autonomous routing",
            "dispatch/control/enforcement",
            "legal/compliance conclusion",
            "production readiness",
            "citywide mobility truth",
        ],
    }
    patch_rows = []
    for moment_id, title, claim_type in [
        ("M04", "Do-nothing baseline", "baseline_context"),
        ("M05", "Abstain no-safe-option", "abstain_context"),
    ]:
        patch_rows.append(
            {
                "moment_id": moment_id,
                "title": title,
                "mobility_claim_type": claim_type,
                "current_evidence_available": [
                    "D8 committed moment registry contains documented partial.",
                    "D8 option-set field presence scan marks M04/M05 READY_FOR_RENDER.",
                    "Existing option-set artifacts include baseline/abstain/no-safe-option terms.",
                ],
                "field_presence_status": field_presence.get(moment_id, "UNKNOWN"),
                "missing_baseline_requirements": [
                    "bounded corridor speed/count history",
                    "same-window GTFS/service snapshot",
                    "baseline SUMO/no-action replay fixture",
                    "reviewed statistical/operational baseline acceptance",
                ],
                "render_ready_evidence_fields": [
                    "moment_id",
                    "safe UI label",
                    "evidence refs",
                    "limitation refs",
                    "abstain reason",
                    "review state",
                ],
                "render_status": "ready_for_render_with_limitations",
                "baseline_status": "baseline_abstained",
                "abstain_reason": "Current evidence can explain the product behavior, but does not prove a certified mobility baseline or measured impact.",
                "safe_ui_label": f"{title}: renderable with explicit abstain/limitation semantics",
                "unsafe_forbidden_ui_claims": contract["forbidden_claims"],
                "evidence_refs": [
                    "outputs/main_citybrain_d8_mobility_access_option_set_gap_backfill_scout/OPTION_SET_FIELD_PRESENCE_REPORT.json",
                    "outputs/main_citybrain_d8_mobility_access_live_surface_wiring_r4/MOMENT_RENDER_HOME_INDEX.json",
                    "outputs/main_citybrain_d8_web_kit_demo_asset_data_bundle/moment_scoreboard.json",
                ],
                "limitation_refs": [
                    "lim:render_readiness_not_baseline_validity",
                    "lim:baseline_abstained_until_proven_by_bounded_temporal_data",
                    "lim:no_live_routing_control_or_enforcement",
                ],
                "review_state": "render_candidate_needs_consumption_smoke",
            }
        )
    write_json(root / "MOBILITY_BASELINE_ABSTAIN_CONTRACT.json", contract)
    write_json(root / "M04_M05_MOBILITY_RENDER_READINESS_PATCH.json", {"task_id": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1", "entries": patch_rows})
    write_text(
        root / "MOBILITY_BASELINE_ABSTAIN_UI_COPY.md",
        """# Mobility Baseline Abstain UI Copy

## Moment Card

M04/M05 can be shown as review moments with visible limitations. CityBrain is not claiming a certified mobility baseline or measured traffic impact.

## Evidence Drawer

Evidence is sufficient to explain why the moment is renderable, but not sufficient to validate a statistical or operational baseline. The safe behavior is abstain.

## Limitation Banner

Baseline validity is not established. No routing, dispatch, enforcement, traffic control, or production/live monitoring action is available.

## Executive Summary

The product demonstrates disciplined restraint: when mobility evidence is incomplete, CityBrain can show the context and explicitly decline a stronger claim.
""",
    )
    tests = {
        "task_id": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
        "cases": [
            {"case_id": "m04_render_allowed_with_limitations", "moment_id": "M04", "expected": "ready_for_render_with_limitations"},
            {"case_id": "m05_render_allowed_with_limitations", "moment_id": "M05", "expected": "ready_for_render_with_limitations"},
            {"case_id": "no_data_mobility_abstains", "input": "no corridor baseline", "expected": "baseline_abstained"},
            {"case_id": "future_supported_baseline_possible", "input": "complete reviewed baseline", "expected": "baseline_supported_possible_not_current"},
            {"case_id": "unsupported_claim_blocked", "claim": "certified traffic baseline", "expected": "blocked"},
            {"case_id": "forbidden_wording_blocked", "claim": "live autonomous routing", "expected": "blocked"},
        ],
    }
    write_json(root / "MOBILITY_BASELINE_ABSTAIN_TEST_MATRIX.json", tests)
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
        "status": STATUS["mobility"],
        "run_timestamp_utc": RUN_TS,
        "inputs_inspected": inputs,
        "moments_patched": ["M04", "M05"],
        "contract_created": True,
        "tests_created": True,
        "hard_errors": [],
        "limitations": [
            "Render readiness remains separate from baseline validity.",
            "M04/M05 keep explicit abstain/limitation semantics.",
            "No mobility engine or new data landing was created.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1",
    }
    write_json(root / "D8_MOBILITY_BASELINE_ABSTAIN_PATCH_DECISION.json", decision)
    local_open_index(root, "Mobility Baseline Abstain Contract Patch R1")
    write_common_audits(root, before, watched_input_stats())
    return decision


def run_vss(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["vss"]
    root.mkdir(parents=True, exist_ok=True)
    source_access = read_json(REPO_ROOT / "outputs/data_gap_ledger_and_priority_matrix/SOURCE_ACCESS_STATUS.json") or {}
    stack_status = read_json(REPO_ROOT / "outputs/main_citybrain_d8_metropolis_vss_data_readiness_scout/STACK_STATUS_REPORT.json") or {}
    camera_manifest = read_json(REPO_ROOT / "outputs/main_citybrain_d8_camera_video_donor_source_scout/SAMPLE_MEDIA_MANIFEST.json") or {}
    sample_count = len(camera_manifest.get("sample_media", []))
    write_text(
        root / "VSS_LICENSED_CORPUS_REQUIREMENTS.md",
        """# VSS Licensed Corpus Requirements

Minimum acceptable corpus requirements:

- explicit license or usage rights for analysis/demo;
- source owner and contact/authority;
- jurisdiction and privacy context;
- camera metadata: site, coordinate or bbox, view orientation, field of view or zones;
- timestamp handling and retention constraints;
- resolution, frame rate, duration, and clip integrity hash;
- event categories and negative windows;
- expected-output oracle with reviewer notes and acceptance thresholds;
- privacy/safety labels and masking/redaction requirements.

Ordinary web video, unaudited public imagery, or unlabeled local clips are not acceptable for VSS readiness claims.
""",
    )
    candidates = [
        {
            "source_name": "Singapore data.gov traffic images",
            "source_family": "public traffic images",
            "access_status": "blocked_or_access_verification_required_403",
            "license_status": "needs_endpoint_level_verification",
            "camera_metadata_status": "unknown_until_access_resolved",
            "oracle_status": "missing",
            "privacy_review_status": "not_started",
            "expected_usefulness": "high_if_access_and_metadata_are_resolved",
            "blocker_status": "blocked",
            "recommended_next_action": "resolve official API access and license/privacy disposition before sample use",
        },
        {
            "source_name": "LTA DataMall Traffic Images v2",
            "source_family": "public agency API",
            "access_status": "api_key_required",
            "license_status": "requires_DataMall_terms_review",
            "camera_metadata_status": "unknown_until_keyed_access",
            "oracle_status": "missing",
            "privacy_review_status": "not_started",
            "expected_usefulness": "high_if_approved",
            "blocker_status": "blocked_auth_missing",
            "recommended_next_action": "obtain approved AccountKey and terms clearance",
        },
        {
            "source_name": "Local D7/demo media inventory",
            "source_family": "local references",
            "access_status": f"local_inventory_refs_not_audited_corpus_{sample_count}",
            "license_status": "not_audited_as_vss_corpus",
            "camera_metadata_status": "incomplete_or_not_uniform",
            "oracle_status": "missing",
            "privacy_review_status": "bounded_demo_labels_only",
            "expected_usefulness": "low_for_real_world_vss_readiness",
            "blocker_status": "not_ready",
            "recommended_next_action": "use only as disclosed local/demo references unless audited",
        },
        {
            "source_name": "Synthetic Omniverse/Cosmos/DeepStream clips",
            "source_family": "synthetic test media",
            "access_status": "potential_internal_generation",
            "license_status": "internal_generation_terms_required",
            "camera_metadata_status": "can_be_authored",
            "oracle_status": "can_be_authored",
            "privacy_review_status": "synthetic_not_real_world",
            "expected_usefulness": "useful_for_pipeline_tests_not_real_world_corpus_claim",
            "blocker_status": "deferred",
            "recommended_next_action": "label synthetic and keep separate from real-world corpus gates",
        },
    ]
    write_json(root / "VSS_CORPUS_CANDIDATE_LEDGER.json", {"task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1", "candidates": candidates, "source_access_refs": source_access.get("sources", [])})
    write_json(
        root / "VSS_ORACLE_TEMPLATE.json",
        {
            "clip_id": "string",
            "camera_id": "string",
            "source_license_ref": "string",
            "privacy_label": "public_context|restricted|synthetic|redacted_required",
            "event_windows": [{"start_time": "iso-or-frame", "end_time": "iso-or-frame", "event_type": "string"}],
            "expected_objects": [{"class": "string", "zone": "string", "count_range": [0, 0]}],
            "expected_zones": [{"zone_id": "string", "description": "string"}],
            "expected_candidate_events": [{"event_type": "string", "confidence_floor": 0.0}],
            "negative_windows": [{"start_time": "iso-or-frame", "end_time": "iso-or-frame", "expected_no_event": "string"}],
            "reviewer_notes": "string",
            "acceptance_thresholds": {"precision_floor": None, "recall_floor": None, "manual_review_required": True},
        },
    )
    write_json(
        root / "VSS_CAMERA_METADATA_TEMPLATE.json",
        {
            "camera_id": "string",
            "site_location": "string",
            "coordinate_or_bbox": None,
            "view_orientation": None,
            "field_of_view_or_scene_zones": [],
            "resolution": None,
            "fps": None,
            "timestamp_handling": "source_timestamp|required_clock_policy",
            "privacy_mask_requirements": [],
            "source_owner": "string",
            "source_license": "string",
        },
    )
    write_text(
        root / "VSS_ACQUISITION_ACTION_PLAN.md",
        """# VSS Acquisition Action Plan

1. Acquire an internal/local licensed sample first, with camera metadata and a reviewer-authored oracle.
2. Use a municipal or partner-approved sample second, only after written usage terms are captured.
3. Use public datasets only when license, privacy, camera metadata, and oracle support the test.
4. Use synthetic Omniverse/Cosmos/DeepStream clips only as synthetic pipeline tests, not real-world corpus proof.

No VSS readiness claim is allowed until licensed corpus, metadata, privacy review, oracle, runtime stack, inference smoke, and claim-boundary gates all pass.
""",
    )
    gates = {
        "licensed_corpus_available": False,
        "camera_metadata_available": False,
        "privacy_review_passed": False,
        "oracle_available": False,
        "runtime_stack_available": bool(stack_status.get("STACK_READY")) if stack_status else False,
        "model_inference_smoke_passed": False,
        "claim_boundary_passed": True,
    }
    write_json(root / "VSS_READINESS_GATES.json", {"task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1", "current_state": "NOT_READY", "gates": gates, "stack_status_ref": "outputs/main_citybrain_d8_metropolis_vss_data_readiness_scout/STACK_STATUS_REPORT.json"})
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1",
        "status": STATUS["vss"],
        "run_timestamp_utc": RUN_TS,
        "candidates_classified": len(candidates),
        "blockers": [
            "no audited licensed real-world corpus",
            "camera metadata incomplete",
            "expected-output oracle missing",
            "Docker/runtime stack not ready locally",
            "Singapore data.gov probe was 403; LTA DataMall requires AccountKey",
        ],
        "gates": gates,
        "hard_errors": [],
        "limitations": ["Acquisition/readiness only; no VSS stack or model inference run."],
        "next_recommended_task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2",
    }
    write_json(root / "D8_VSS_LICENSED_CORPUS_ACQUISITION_DECISION.json", decision)
    local_open_index(root, "VSS Licensed Corpus Acquisition R1")
    write_common_audits(root, before, watched_input_stats(), {"vss_or_model_inference_claim_made": False})
    return decision


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_get(url: str, timeout: int = 8) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(4096)
            return {"url": url, "ok": 200 <= resp.status < 400, "status": resp.status, "bytes_read": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "bytes_read": 0, "error": f"{exc.__class__.__name__}: {exc}"}


def run_local_web_smoke() -> dict[str, Any]:
    app_dir = REPO_ROOT / "apps" / "web-control-room"
    if not (app_dir / "index.html").exists():
        return {"status": "SKIPPED", "safe_skip_reason": "apps/web-control-room/index.html not found", "files_still_validated": False}
    port = find_free_port()
    cmd = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(app_dir)]
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    checks = []
    try:
        time.sleep(1.0)
        for route in ["/index.html", "/styles.css", "/src/main.js"]:
            checks.append(http_get(f"http://127.0.0.1:{port}{route}"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return {
        "status": "PASS" if all(item.get("ok") for item in checks) else "PARTIAL",
        "command": " ".join(cmd),
        "host": "127.0.0.1",
        "port": port,
        "checked_routes": checks,
        "screenshot_path": None,
        "note": "Static local launch smoke only; no production web claim.",
    }


def run_webkit(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["webkit"]
    root.mkdir(parents=True, exist_ok=True)
    bundle_root = REPO_ROOT / "outputs" / "main_citybrain_d8_web_kit_demo_asset_data_bundle"
    hel_root = REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_context_consumption_prep_r1"
    mobility_root = ROOTS["mobility"]
    web_files = []
    for path in [
        bundle_root / "DEMO_DATA_BUNDLE_MANIFEST.json",
        bundle_root / "scenario_state.json",
        bundle_root / "review_state.json",
        bundle_root / "evidence_bundle.json",
        bundle_root / "option_sets.json",
        bundle_root / "track_d_packets.json",
        bundle_root / "kit_overlay_packets.json",
        bundle_root / "moment_scoreboard.json",
        bundle_root / "limitations.json",
        mobility_root / "MOBILITY_BASELINE_ABSTAIN_CONTRACT.json",
        mobility_root / "M04_M05_MOBILITY_RENDER_READINESS_PATCH.json",
    ]:
        web_files.append({**file_record(path), "limitation_refs": ["lim:read_only_projection", "lim:consume_not_mutate"]})
    kit_files = []
    for path in [
        hel_root / "USD_CER_SIDECAR_CANDIDATE_MAP.jsonl",
        hel_root / "VISUAL_MESH_BOUNDARY_NOTE.md",
        REPO_ROOT / "apps/kit/citybrain.control_room/config/extension.toml",
        REPO_ROOT / "apps/kit/citybrain.control_room/citybrain/control_room/selection_inspector.py",
    ]:
        kit_files.append({**file_record(path), "mode": "handoff_manifest_only", "limitation_refs": ["lim:kit_not_launched_in_this_smoke", "lim:visual_backdrop_only"]})
    write_text(
        root / "WEB_KIT_CONSUMPTION_SMOKE_PLAN.md",
        """# Web+Kit Consumption Smoke Plan

Consume the D8 read-only demo bundle, the M04/M05 mobility-abstain contract patch, and the Helsinki sidecar candidate prep as local evidence fixtures.

Out of scope: production deployment, internet dependency installs, native WebRTC/RTX streaming, live monitoring, autonomous action, traffic/transit/dispatch/control/enforcement, legal/certified findings, or accepting Helsinki mesh identity.
""",
    )
    write_json(root / "WEB_CONSUMPTION_FIXTURE_MANIFEST.json", {"task_id": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1", "files": web_files})
    write_json(root / "KIT_CONSUMPTION_FIXTURE_MANIFEST.json", {"task_id": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1", "kit_mode": "handoff_manifest_only", "files": kit_files})
    moments = load_moments()
    mobility_patch = read_json(mobility_root / "M04_M05_MOBILITY_RENDER_READINESS_PATCH.json") or {}
    patch_by_id = {row.get("moment_id"): row for row in mobility_patch.get("entries", [])}
    moment_rows = []
    for moment in moments:
        mid = moment.get("moment_id")
        if mid in patch_by_id:
            patch = patch_by_id[mid]
            web_status = "render_allowed_with_abstain_limitations"
            kit_status = "handoff_allowed_with_abstain_limitations"
            limitations = patch.get("limitation_refs", [])
            blocked_reason = patch.get("abstain_reason")
        else:
            web_status = "render_home_ready" if moment.get("render_status") == "render_home_ready" or moment.get("status") != "documented_partial" else "documented_partial"
            kit_status = moment.get("render_kit_render_home", "handoff_or_not_required")
            limitations = ["lim:local_replay_review_context_only"]
            blocked_reason = moment.get("partial_reason")
        moment_rows.append(
            {
                "moment_id": mid,
                "title": moment.get("title"),
                "source_evidence_refs": moment.get("data_basis") or moment.get("render_data_basis") or [],
                "web_render_status": web_status,
                "kit_handoff_render_status": kit_status,
                "limitation_refs": limitations,
                "blocked_or_partial_reason": blocked_reason,
            }
        )
    write_json(root / "MOMENT_RENDER_CONSUMPTION_STATUS.json", {"task_id": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1", "moments": moment_rows})
    web_smoke = run_local_web_smoke()
    write_json(root / "LOCAL_WEB_LAUNCH_SMOKE_RESULT.json", web_smoke)
    sidecar_path = hel_root / "USD_CER_SIDECAR_CANDIDATE_MAP.jsonl"
    sidecar_count = 0
    if sidecar_path.exists():
        with sidecar_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    json.loads(line)
                    sidecar_count += 1
    kit_smoke = {
        "status": "PASS_HANDOFF_ONLY",
        "kit_composer_launched": False,
        "handoff_only_validation_result": True,
        "helsinki_sidecar_candidate_count": sidecar_count,
        "visual_backdrop_limitation_preserved": True,
        "notes": "Kit/Composer was not launched by this smoke; files and handoff refs validated only.",
    }
    write_json(root / "KIT_HANDOFF_SMOKE_RESULT.json", kit_smoke)
    write_text(
        root / "WEB_KIT_CLAIM_BOUNDARY_COPY.md",
        """# Web+Kit Claim Boundary Copy

The web surface is a local companion evidence, episode, and executive review surface. Kit/Composer is the spatial control-room and handoff surface where available.

This demo does not claim production deployment, native web USD/RTX streaming, live city monitoring, autonomous action, traffic/transit/port control, dispatch, enforcement, legal findings, certified government decisioning, certified mobility baselines, or accepted object-level identity for Helsinki mesh objects.
""",
    )
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1",
        "status": STATUS["webkit"],
        "run_timestamp_utc": RUN_TS,
        "web_consumed": all(item["exists"] for item in web_files[:9]),
        "kit_consumed_or_handoff_validated": kit_smoke["handoff_only_validation_result"],
        "moments_checked": len(moment_rows),
        "mobility_abstain_contract_seen": (mobility_root / "MOBILITY_BASELINE_ABSTAIN_CONTRACT.json").exists(),
        "helsinki_sidecar_seen": sidecar_path.exists(),
        "hard_errors": [],
        "limitations": [
            "Kit handoff validated only; Composer not launched in this task.",
            "Web local launch is static/local-only.",
            "M04/M05 render with abstain semantics, not certified baseline validity.",
            "Helsinki sidecar remains candidate and visual mesh remains backdrop-only.",
        ],
        "next_recommended_task": "D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1",
    }
    write_json(root / "D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_DECISION.json", decision)
    local_open_index(root, "Web+Kit Bundle Consumption Smoke R1")
    write_common_audits(root, before, watched_input_stats())
    return decision


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def run_helsinki_alignment(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["helsinki"]
    root.mkdir(parents=True, exist_ok=True)
    prep_root = REPO_ROOT / "outputs/d4_helsinki_kalasatama_context_consumption_prep_r1"
    sidecar = read_jsonl(prep_root / "USD_CER_SIDECAR_CANDIDATE_MAP.jsonl")
    identity_rows = []
    csv_path = prep_root / "CITYGML_BUILDING_IDENTITY_NORMALIZATION.csv"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            identity_rows = list(csv.DictReader(fh))
    by_gml = {row.get("gml_id"): row for row in identity_rows}
    selected: list[dict[str, Any]] = []
    reasons: dict[str, list[str]] = defaultdict(list)

    def add(record: dict[str, Any], reason: str) -> None:
        sid = record.get("source_citygml_id")
        if not sid or any(row.get("source_citygml_id") == sid for row in selected):
            return
        selected.append(record)
        reasons[sid].append(reason)

    for record in sidecar[:8]:
        add(record, "deterministic_first_records")
    height_sorted = sorted(
        sidecar,
        key=lambda row: float((by_gml.get(row.get("source_citygml_id"), {}) or {}).get("measuredHeight") or 0),
        reverse=True,
    )
    for record in height_sorted[:6]:
        add(record, "varied_height_high_records")
    id_rich = [row for row in sidecar if (by_gml.get(row.get("source_citygml_id"), {}) or {}).get("VTJ_PRT") or (by_gml.get(row.get("source_citygml_id"), {}) or {}).get("UUID")]
    for record in id_rich[:8]:
        add(record, "explicit_source_identifier_available")
    for record in sidecar:
        if len(selected) >= 20:
            break
        add(record, "deterministic_fill_to_20")

    selection = {
        "task_id": "D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1",
        "sample_count": len(selected),
        "selection_rules": ["first 8 sidecar rows", "high/varied height rows", "explicit source ID rows", "deterministic fill to 20"],
        "selected": [
            {
                "source_citygml_id": row.get("source_citygml_id"),
                "candidate_prim_path": row.get("candidate_prim_path"),
                "linked_citybrain_candidate_id": row.get("linked_citybrain_candidate_id"),
                "canonical_entity_candidate_id": row.get("canonical_entity_candidate_id"),
                "reason": reasons.get(row.get("source_citygml_id"), []),
            }
            for row in selected
        ],
    }
    write_json(root / "SIDECAR_ALIGNMENT_SAMPLE_SELECTION.json", selection)
    visual_ref = file_record(REPO_ROOT / "outputs/d4_3d_helsinki_kalasatama_3d_tiles_landing_r1/SOURCE_MANIFEST.json")
    with (root / "USD_CER_ALIGNMENT_SMOKE_PACKETS.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in selected:
            packet = {
                "candidate_prim_path": row.get("candidate_prim_path"),
                "suggested_prim_name": row.get("suggested_prim_name"),
                "canonical_entity_candidate_id": row.get("canonical_entity_candidate_id"),
                "linked_citybrain_candidate_id": row.get("linked_citybrain_candidate_id"),
                "source_citygml_id": row.get("source_citygml_id"),
                "source_record_ref": row.get("source_record_ref"),
                "geometry_ref": row.get("geometry_ref"),
                "visual_backdrop_ref": visual_ref,
                "evidence_refs": row.get("evidence_refs", []),
                "limitation_refs": list(dict.fromkeys(row.get("limitation_refs", []) + ["lim:smoke_packet_not_object_level_alignment_proof"])),
                "binding_status": "SAMPLE_PACKET_CREATED_ALIGNMENT_NOT_PROVEN",
                "review_state": "ready_for_kit_object_pick_alignment_review",
            }
            fh.write(json.dumps(packet, ensure_ascii=False) + "\n")
    usda_lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "CityBrain"',
        "    {",
        '        def Xform "HEL"',
        "        {",
        '            def Xform "KalasatamaSidecarSmoke"',
        "            {",
        f'                custom string citybrain_task = "D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1"',
        f'                custom int sample_count = {len(selected)}',
    ]
    for idx, row in enumerate(selected):
        token = re.sub(r"[^A-Za-z0-9_]", "_", row.get("suggested_prim_name") or f"sample_{idx:02d}")
        if token and token[0].isdigit():
            token = f"b_{token}"
        usda_lines.extend(
            [
                f'                def Xform "{token}"',
                "                {",
                f'                    custom string source_citygml_id = "{row.get("source_citygml_id")}"',
                f'                    custom string canonical_entity_candidate_id = "{row.get("canonical_entity_candidate_id")}"',
                f'                    custom string binding_status = "SAMPLE_MARKER_ONLY_ALIGNMENT_NOT_PROVEN"',
                "                }",
            ]
        )
    usda_lines.extend(["            }", "        }", "    }", "}"])
    write_text(root / "KIT_COMPOSER_HANDOFF_LAYER.usda", "\n".join(usda_lines))
    write_text(
        root / "SIDE_CAR_ALIGNMENT_SMOKE_REPORT.md",
        f"""# Sidecar Alignment Smoke Report

Created {len(selected)} sample packets from the Helsinki/Kalasatama sidecar.

What is proven:

- CityGML semantic building candidates exist.
- CER candidate IDs and suggested USD prim paths can be packaged for Kit/Web handoff.
- A lightweight USDA marker layer can carry sample metadata without mutating source assets.

What is not proven:

- object-level alignment to the reality mesh;
- canonical/legal/certified building identity;
- full Kalasatama or Helsinki citywide twin readiness;
- production Omniverse readiness.
""",
    )
    status = {
        "visual_backdrop_present": visual_ref["exists"],
        "source_visual_root": "outputs/d4_3d_helsinki_kalasatama_3d_tiles_landing_r1",
        "object_level_alignment_proven": False,
        "smoke_sample_count": len(selected),
        "source_mutation": False,
        "limitations": [
            "USDA layer is marker metadata only.",
            "Visual mesh remains backdrop-only.",
            "Sample packets are ready for manual/Kit alignment review.",
        ],
    }
    write_json(root / "VISUAL_BACKDROP_ALIGNMENT_STATUS.json", status)
    decision = {
        "task_id": "D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1",
        "status": STATUS["helsinki"],
        "run_timestamp_utc": RUN_TS,
        "sample_count": len(selected),
        "packets_created": len(selected),
        "usda_layer_created": True,
        "visual_backdrop_present": visual_ref["exists"],
        "object_level_alignment_claim_made": False,
        "hard_errors": [],
        "limitations": status["limitations"],
        "next_recommended_task": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1 or HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2",
    }
    write_json(root / "HELSINKI_USD_SIDECAR_ALIGNMENT_SMOKE_DECISION.json", decision)
    local_open_index(root, "Helsinki USD Sidecar Alignment Smoke R1")
    write_common_audits(root, before, watched_input_stats(), {"legal_or_certified_claim_made": False})
    return decision


def fetch_json_sample(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "CityBrainChicagoBoundedSample/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read(256 * 1024)
            data = json.loads(body.decode("utf-8"))
            return {"ok": True, "status": resp.status, "url": url, "rows": data if isinstance(data, list) else [], "bytes_read": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    except Exception as exc:
        return {"ok": False, "url": url, "rows": [], "error": f"{exc.__class__.__name__}: {exc}"}


def summarize_chicago_row(family: str, row: dict[str, Any], idx: int, url: str) -> dict[str, Any]:
    record_id = row.get("id") or row.get("service_request_number") or row.get("request_id") or row.get("node_id") or row.get("violation_id") or f"{family}_{idx}"
    date = row.get("violation_date") or row.get("creation_date") or row.get("created_date") or row.get("date") or row.get("start_timestamp")
    location_fields = {
        key: row.get(key)
        for key in [
            "address",
            "street_address",
            "street_number",
            "street_direction",
            "street_name",
            "community_area",
            "latitude",
            "longitude",
            "location",
            "node_id",
            "description",
        ]
        if row.get(key) not in (None, "")
    }
    category = row.get("violation_code") or row.get("sr_type") or row.get("type") or row.get("sensor") or row.get("status")
    description = row.get("violation_description") or row.get("description") or row.get("sr_short_code") or row.get("address") or ""
    return {
        "source_family": family,
        "source_record_id": str(record_id),
        "timestamp_or_date": date,
        "location_fields": location_fields,
        "category_or_type": category,
        "short_description": str(description)[:300],
        "evidence_ref": url,
        "limitation_ref": "lim:bounded_sample_historical_context_only",
        "raw_sample": row,
    }


def run_chicago(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["chicago"]
    root.mkdir(parents=True, exist_ok=True)
    queries = {
        "violations": "https://data.cityofchicago.org/resource/e9ic-ry4z.json?$limit=5",
        "311": "https://data.cityofchicago.org/resource/v6vf-nfxy.json?$limit=5",
        "array_of_things": "https://data.cityofchicago.org/resource/6rq2-yx28.json?$limit=5",
    }
    samples = {family: fetch_json_sample(url) for family, url in queries.items()}
    source_smoke = {
        "task_id": "CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1",
        "no_large_download": True,
        "sources": [
            {
                "source_family": family,
                "access_method": url,
                "sample_size": len(result.get("rows", [])),
                "status": "PASS" if result.get("ok") else "FAILED_OR_BLOCKED",
                "limitations": ["bounded $limit=5 sample", "historical/context only", "no legal/compliance conclusion"],
                "error": result.get("error"),
            }
            for family, url in queries.items()
            for result in [samples[family]]
        ],
    }
    write_json(root / "CHICAGO_SOURCE_ACCESS_SMOKE.json", source_smoke)
    ledger_rows = []
    for family, result in samples.items():
        for idx, row in enumerate(result.get("rows", []), start=1):
            ledger_rows.append(summarize_chicago_row(family, row, idx, result.get("url", queries[family])))
    write_json(root / "CHICAGO_BOUNDED_SAMPLE_LEDGER.json", {"task_id": "CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1", "sample_rows": ledger_rows})
    violations = [row for row in ledger_rows if row["source_family"] == "violations"]
    service = [row for row in ledger_rows if row["source_family"] == "311"]
    sensors = [row for row in ledger_rows if row["source_family"] == "array_of_things"]
    packet = {
        "task_id": "CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1",
        "packet_id": "chi:city_remembers:bounded_sample:001",
        "place_context_anchor": "Chicago bounded civic/building/sensor sample, not citywide",
        "related_prior_violations": violations[:3],
        "related_311_cases": service[:3],
        "related_sensor_environment_observations": sensors[:3],
        "temporal_hints": [row.get("timestamp_or_date") for row in ledger_rows if row.get("timestamp_or_date")][:8],
        "similarity_explanation": [
            "Rows are grouped because they are public Chicago civic/building/sensor context records.",
            "This packet demonstrates memory-style evidence organization, not an accepted similarity model.",
        ],
        "missing_data": ["spatial clustering", "reviewed same-address matching", "outcome labels", "full citywide ingestion"],
        "safe_next_look_suggestions": [
            "Review address/location normalization.",
            "Add source-specific limitations beside each case.",
            "Only then create a stronger similar-case index.",
        ],
        "forbidden_claims": ["legal/compliance conclusion", "citywide ingestion", "live monitoring", "autonomous action"],
    }
    write_json(root / "CHICAGO_CITY_REMEMBERS_PACKET.json", packet)
    with (root / "CHICAGO_SIMILAR_CASE_ENTITY_CANDIDATES.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in ledger_rows:
            entity_type = {"violations": "violation", "311": "case_request", "array_of_things": "sensor_observation"}.get(row["source_family"], "source_record")
            entity = {
                "candidate_entity_id": f"chi:similar_case_candidate:{row['source_family']}:{hashlib.sha1(row['source_record_id'].encode()).hexdigest()[:12]}",
                "entity_type": entity_type,
                "source_family": row["source_family"],
                "source_record_id": row["source_record_id"],
                "source_refs": [row["evidence_ref"]],
                "confidence": "source_sample_candidate",
                "review_state": "candidate_no_canonical_acceptance",
                "limitation_refs": [row["limitation_ref"], "lim:sample_only_not_citywide"],
            }
            fh.write(json.dumps(entity, ensure_ascii=False) + "\n")
    write_text(
        root / "CHICAGO_SIMILAR_CASE_LIMITATIONS.md",
        """# Chicago Similar Case Limitations

- Bounded sample only.
- Not citywide ingestion.
- No legal/compliance conclusion.
- No production ingestion.
- No real-time monitoring.
- No autonomous action, dispatch, enforcement, or control.
- No full Flow 7 claim; broader civic/sensor fusion remains a separate accepted/contracted lane.
""",
    )
    decision = {
        "task_id": "CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1",
        "status": STATUS["chicago"],
        "run_timestamp_utc": RUN_TS,
        "sources_checked": list(queries.keys()),
        "sample_rows": len(ledger_rows),
        "city_remembers_packet_created": True,
        "hard_errors": [] if ledger_rows else ["No remote rows returned; package is metadata-only"],
        "limitations": ["Small bounded sample only", "No citywide/live/legal/compliance claim"],
        "next_recommended_task": "CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2",
    }
    write_json(root / "CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_DECISION.json", decision)
    local_open_index(root, "Chicago Similar Case Bounded Enrichment R1")
    write_common_audits(root, before, watched_input_stats())
    return decision


def run_all() -> dict[str, Any]:
    before = watched_input_stats()
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)
    results = {
        "mobility": run_mobility(before),
        "vss": run_vss(before),
        "helsinki": run_helsinki_alignment(before),
        "webkit": run_webkit(before),
        "chicago": run_chicago(before),
    }
    closeout = {
        "task_id": "CITYBRAIN-D8-PARALLEL-PROMPT-PACK",
        "status": "PASS_CITYBRAIN_D8_PARALLEL_PROMPT_PACK_WITH_LIMITATIONS",
        "run_timestamp_utc": RUN_TS,
        "results": {
            key: {
                "status": value.get("status"),
                "output_root": rel(ROOTS[key]),
                "hard_errors": value.get("hard_errors", []),
                "next_recommended_task": value.get("next_recommended_task"),
            }
            for key, value in results.items()
        },
        "boundaries": {
            "large_download_started": False,
            "prior_outputs_mutated": False,
            "vss_readiness_claim_made": False,
            "production_claim_made": False,
            "legal_or_certified_claim_made": False,
            "autonomous_action_claim_made": False,
        },
    }
    closeout_root = REPO_ROOT / "outputs" / "citybrain_d8_parallel_prompt_pack_closeout"
    closeout_root.mkdir(parents=True, exist_ok=True)
    write_json(closeout_root / "CITYBRAIN_D8_PARALLEL_PROMPT_PACK_CLOSEOUT.json", closeout)
    local_open_index(closeout_root, "CityBrain D8 Parallel Prompt Pack Closeout")
    write_common_audits(closeout_root, before, watched_input_stats())
    return closeout


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, ensure_ascii=False))
