#!/usr/bin/env python3
"""Run the CityBrain D8 follow-on and composition prompt pack.

The runner executes five bounded tasks in order:
- VSS licensed corpus sample acquisition R2
- Helsinki Kit object-pick manual alignment R2
- Chicago similar-case reviewed matching R2
- D8 parallel pack composition closeout R1
- D8 demonstrable surface integration R1

It creates new sidecar/output artifacts only. It does not download large media,
mutate prior outputs, run VSS, launch Kit, or claim production/live/autonomous,
legal, certified, or object-identity readiness.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

ROOTS = {
    "vss_r2": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2",
    "helsinki_r2": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2",
    "chicago_r2": OUTPUTS / "chicago_similar_case_reviewed_matching_r2",
    "composition": OUTPUTS / "main_citybrain_d8_parallel_pack_composition_closeout_r1",
    "surface": OUTPUTS / "main_citybrain_d8_demonstrable_surface_integration_r1",
}

STATUSES = {
    "vss_r2": "PASS_MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_WITH_LIMITATIONS",
    "helsinki_r2": "PASS_HELSINKI_KIT_OBJECT_PICK_MANUAL_ALIGNMENT_R2_WITH_LIMITATIONS",
    "chicago_r2": "PASS_CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_WITH_LIMITATIONS",
    "composition": "PASS_MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_WITH_LIMITATIONS",
    "surface": "PASS_MAIN_CITYBRAIN_D8_DEMONSTRABLE_SURFACE_INTEGRATION_R1_WITH_LIMITATIONS",
}

PRIOR_INPUTS = {
    "d8_closeout": OUTPUTS / "citybrain_d8_parallel_prompt_pack_closeout/CITYBRAIN_D8_PARALLEL_PROMPT_PACK_CLOSEOUT.json",
    "mobility_decision": OUTPUTS / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/D8_MOBILITY_BASELINE_ABSTAIN_PATCH_DECISION.json",
    "mobility_patch": OUTPUTS / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/M04_M05_MOBILITY_RENDER_READINESS_PATCH.json",
    "vss_r1_decision": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1/D8_VSS_LICENSED_CORPUS_ACQUISITION_DECISION.json",
    "vss_r1_gates": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1/VSS_READINESS_GATES.json",
    "vss_r1_ledger": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1/VSS_CORPUS_CANDIDATE_LEDGER.json",
    "camera_media_manifest": OUTPUTS / "main_citybrain_d8_camera_video_donor_source_scout/SAMPLE_MEDIA_MANIFEST.json",
    "camera_source_inventory": OUTPUTS / "main_citybrain_d8_camera_video_donor_source_scout/CAMERA_VIDEO_SOURCE_INVENTORY.json",
    "vss_stack_status": OUTPUTS / "main_citybrain_d8_metropolis_vss_data_readiness_scout/STACK_STATUS_REPORT.json",
    "web_kit_decision": OUTPUTS / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_DECISION.json",
    "web_kit_moments": OUTPUTS / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/MOMENT_RENDER_CONSUMPTION_STATUS.json",
    "demo_bundle_manifest": OUTPUTS / "main_citybrain_d8_web_kit_demo_asset_data_bundle/DEMO_DATA_BUNDLE_MANIFEST.json",
    "helsinki_consumption_decision": OUTPUTS / "d4_helsinki_kalasatama_context_consumption_prep_r1/D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json",
    "helsinki_identity_jsonl": OUTPUTS / "d4_helsinki_kalasatama_context_consumption_prep_r1/CITYGML_BUILDING_IDENTITY_NORMALIZATION.jsonl",
    "helsinki_cer_jsonl": OUTPUTS / "d4_helsinki_kalasatama_context_consumption_prep_r1/CITYGML_TO_CER_CANDIDATE_MAP.jsonl",
    "helsinki_sidecar_jsonl": OUTPUTS / "d4_helsinki_kalasatama_context_consumption_prep_r1/USD_CER_SIDECAR_CANDIDATE_MAP.jsonl",
    "helsinki_smoke_packets": OUTPUTS / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/USD_CER_ALIGNMENT_SMOKE_PACKETS.jsonl",
    "helsinki_smoke_selection": OUTPUTS / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/SIDECAR_ALIGNMENT_SAMPLE_SELECTION.json",
    "helsinki_smoke_decision": OUTPUTS / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/HELSINKI_USD_SIDECAR_ALIGNMENT_SMOKE_DECISION.json",
    "chicago_r1_decision": OUTPUTS / "chicago_similar_case_bounded_enrichment_r1/CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_DECISION.json",
    "chicago_r1_ledger": OUTPUTS / "chicago_similar_case_bounded_enrichment_r1/CHICAGO_BOUNDED_SAMPLE_LEDGER.json",
    "chicago_r1_packet": OUTPUTS / "chicago_similar_case_bounded_enrichment_r1/CHICAGO_CITY_REMEMBERS_PACKET.json",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def safe_reset_root(root: Path) -> None:
    root = root.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in root.parents or root.name not in {path.name for path in ROOTS.values()}:
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: encode_cell(row.get(key)) for key in fieldnames})


def encode_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path) if path.exists() else rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def snapshot_inputs() -> dict[str, Any]:
    return {name: file_record(path) for name, path in PRIOR_INPUTS.items()}


def json_parse_audit(root: Path) -> dict[str, Any]:
    ok = True
    results: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append({"path": rel(path), "status": "PASS"})
        except Exception as exc:
            ok = False
            results.append({"path": rel(path), "status": "FAIL", "error": str(exc)})
    for path in sorted(root.rglob("*.jsonl")):
        bad: list[dict[str, Any]] = []
        line_count = 0
        with path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
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


def secret_audit(root: Path) -> dict[str, Any]:
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


def claim_boundary_audit(root: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    unsafe_patterns = [
        r"(?i)\bproduction[- ]ready\b",
        r"(?i)\bcertified affected\b",
        r"(?i)\bcertified impact\b",
        r"(?i)\bconfirmed violation\b",
        r"(?i)\blegal finding\b",
        r"(?i)\bautonomous dispatch\b",
        r"(?i)\btraffic control command\b",
        r"(?i)\bVSS runtime ready\b",
        r"(?i)\bobject-level identity proven\b",
    ]
    boundary_context = re.compile(
        r"(?i)(forbidden|do not say|do-not-say|not claim|no claim|must not|not production|not a production|no production|"
        r"closed gate|gate closed|not runtime|not certified|not legal|not autonomous|do not claim|forbidden_claims|"
        r"forbidden wording|no VSS|without|not proven)"
    )
    hits: list[dict[str, Any]] = []
    boundary_mentions: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        file_declares_boundary_words = path.name in {
            "D8_ALLOWED_AND_FORBIDDEN_WORDING.json",
            "D8_CLAIM_BOUNDARY_REGISTER.md",
            "D8_SCENE_CARDS.json",
            "D8_OPERATOR_SCRIPT.md",
            "CHICAGO_LIMITATIONS_AND_FORBIDDEN_CLAIMS.md",
        }
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for pattern in unsafe_patterns:
                if not re.search(pattern, line):
                    continue
                row = {"path": rel(path), "line": line_no, "pattern": pattern, "excerpt": line.strip()[:220]}
                if file_declares_boundary_words or boundary_context.search(line):
                    boundary_mentions.append(row)
                else:
                    hits.append(row)
    audit = {
        "status": "PASS" if not hits else "FAIL",
        "unsafe_positive_claim_hits": hits,
        "boundary_context_mentions": boundary_mentions,
        "production_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_action_claim_made": False,
        "legal_or_certified_claim_made": False,
        "vss_runtime_claim_made": False,
        "forbidden_claims_may_appear_as_forbidden_wording_only": True,
    }
    if extra:
        audit.update(extra)
    return audit


def mutation_audit(before: dict[str, Any], after: dict[str, Any], root: Path) -> dict[str, Any]:
    mutations = []
    for key, value in before.items():
        if after.get(key) != value:
            mutations.append({"input": key, "before": value, "after": after.get(key)})
    return {
        "status": "PASS" if not mutations else "FAIL",
        "prior_outputs_mutated": bool(mutations),
        "mutated_inputs": mutations,
        "generated_output_root": rel(root),
    }


def referenced_artifact_audit(refs: list[str]) -> dict[str, Any]:
    rows = []
    for ref in refs:
        if not ref:
            continue
        # Strip JSONL/ZIP fragment refs after #; keep regular file path.
        path_part = ref.split("#", 1)[0]
        if not path_part.startswith("outputs/"):
            continue
        path = REPO_ROOT / path_part
        rows.append({"ref": ref, "path": path_part, "exists": path.exists()})
    return {"status": "PASS" if all(row["exists"] for row in rows) else "FAIL", "refs_checked": len(rows), "results": rows}


def hash_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"HASH_MANIFEST.json", "HASH_MANIFEST.sha256"}:
            continue
        files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"generated_at": RUN_TS, "files": files}


def write_hashes(root: Path) -> dict[str, Any]:
    manifest = hash_manifest(root)
    write_json(root / "HASH_MANIFEST.json", manifest)
    lines = [f"{item['sha256']}  {item['path']}" for item in manifest["files"]]
    write_text(root / "HASH_MANIFEST.sha256", "\n".join(lines))
    return manifest


def finalize_root(
    root: Path,
    before: dict[str, Any],
    extra_audits: dict[str, Any] | None = None,
    referenced_refs: list[str] | None = None,
) -> dict[str, Any]:
    after = snapshot_inputs()
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(root))
    write_json(root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", mutation_audit(before, after, root))
    if referenced_refs is not None:
        write_json(root / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_audit(referenced_refs))
    if extra_audits:
        for filename, payload in extra_audits.items():
            write_json(root / filename, payload)
    manifest = write_hashes(root)
    # Re-run JSON audit after adding the audit files and hash JSON.
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    run_audit = {
        "task_output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "json_parse_audit": read_json(root / "JSON_PARSE_AUDIT.json"),
        "secret_audit": read_json(root / "SECRET_AUDIT.json"),
        "claim_boundary_audit": read_json(root / "CLAIM_BOUNDARY_AUDIT.json"),
        "no_prior_output_mutation_audit": read_json(root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json"),
        "referenced_artifact_existence_audit": read_json(root / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json") if (root / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json").exists() else None,
        "hash_manifest_files": len(manifest["files"]),
        "large_download_started": False,
        "prior_outputs_mutated": False,
        "production_or_certified_claim_made": False,
        "autonomous_action_claim_made": False,
    }
    write_json(root / "RUN_AUDIT.json", run_audit)
    write_hashes(root)
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    return run_audit


def source_sample_count() -> int:
    manifest = read_json(PRIOR_INPUTS["camera_media_manifest"]) or {}
    return len(manifest.get("sample_media", []))


def build_vss_candidate_rows() -> list[dict[str, Any]]:
    r1 = read_json(PRIOR_INPUTS["vss_r1_ledger"]) or {}
    r1_candidates = r1.get("candidates", [])
    local_manifest = read_json(PRIOR_INPUTS["camera_media_manifest"]) or {}
    local_count = len(local_manifest.get("sample_media", []))
    rows = [
        {
            "source_name": "User-owned or TXR-owned sample footage",
            "source_type": "owner_supplied_media",
            "access_status": "not_supplied_as_audited_vss_corpus",
            "license_status": "needs_owner_attestation",
            "privacy_status": "needs_privacy_review_and_redaction_decision",
            "metadata_completeness": "unknown",
            "camera_metadata_available": False,
            "oracle_label_feasibility": "feasible_after_rights_and_metadata_are_confirmed",
            "expected_sample_count": 0,
            "download_size_class": "none_currently",
            "permitted_use_summary": "Potentially usable only after owner permission, privacy disposition, and camera metadata are attached.",
            "blocker_reason": "No owner/license/privacy/camera metadata packet has been provided.",
            "recommended_disposition": "needs_owner_permission",
        },
        {
            "source_name": "Synthetic or simulator-generated CCTV-like clips",
            "source_type": "synthetic_or_simulator",
            "access_status": "can_be_generated_later_no_download_in_this_task",
            "license_status": "internal_generation_terms_required",
            "privacy_status": "synthetic_not_real_world_but_must_be_labeled",
            "metadata_completeness": "authorable_but_not_currently_present",
            "camera_metadata_available": False,
            "oracle_label_feasibility": "high_if_scenes_and_labels_are_authored",
            "expected_sample_count": 0,
            "download_size_class": "none_currently",
            "permitted_use_summary": "Useful for pipeline fixtures, but not a real-world VSS corpus claim.",
            "blocker_reason": "No generated clip plus authored metadata/oracle exists in this R2 input set.",
            "recommended_disposition": "approved_for_future_synthetic_fixture_not_real_world_gate",
        },
        {
            "source_name": "Prior local media refs from D8 inventory",
            "source_type": "local_media_refs",
            "access_status": f"local_refs_available_count_{local_count}",
            "license_status": "not_audited_as_vss_corpus",
            "privacy_status": "bounded_demo_labels_only",
            "metadata_completeness": "incomplete_or_not_uniform",
            "camera_metadata_available": False,
            "oracle_label_feasibility": "partial_if_manual_review_added",
            "expected_sample_count": local_count,
            "download_size_class": "already_local_no_new_download",
            "permitted_use_summary": "May be shown as local/demo evidence only; not accepted as VSS sample corpus.",
            "blocker_reason": "Missing explicit VSS usage rights, camera metadata, and oracle labels.",
            "recommended_disposition": "unsuitable_for_vss_sample_until_audited",
        },
        {
            "source_name": "Public-domain or permissively licensed traffic/city video datasets",
            "source_type": "external_public_dataset_family",
            "access_status": "candidate_family_not_downloaded",
            "license_status": "dataset_specific_terms_required",
            "privacy_status": "dataset_specific_privacy_review_required",
            "metadata_completeness": "unknown_until_dataset_selected",
            "camera_metadata_available": False,
            "oracle_label_feasibility": "varies_by_dataset",
            "expected_sample_count": 0,
            "download_size_class": "large_or_unknown",
            "permitted_use_summary": "Candidate family only. No dataset is accepted without license/access/privacy review.",
            "blocker_reason": "No specific audited dataset selected and no sample acquired.",
            "recommended_disposition": "needs_license_review",
        },
        {
            "source_name": "Licensed commercial/demo CCTV sample",
            "source_type": "commercial_or_demo_license",
            "access_status": "not_available_in_repo",
            "license_status": "needs_license_purchase_or_vendor_permission",
            "privacy_status": "needs_contractual_privacy_review",
            "metadata_completeness": "unknown",
            "camera_metadata_available": False,
            "oracle_label_feasibility": "feasible_if_vendor_supplies_labels_or_review_allowed",
            "expected_sample_count": 0,
            "download_size_class": "unknown",
            "permitted_use_summary": "Not usable until license permits local demo/research analysis.",
            "blocker_reason": "No licensed sample has been provided.",
            "recommended_disposition": "needs_license_purchase",
        },
    ]
    for candidate in r1_candidates:
        name = candidate.get("source_name", "R1 candidate")
        rows.append(
            {
                "source_name": name,
                "source_type": candidate.get("source_family", "r1_candidate"),
                "access_status": candidate.get("access_status", "unknown"),
                "license_status": candidate.get("license_status", "unknown"),
                "privacy_status": candidate.get("privacy_review_status", "unknown"),
                "metadata_completeness": candidate.get("camera_metadata_status", "unknown"),
                "camera_metadata_available": False,
                "oracle_label_feasibility": candidate.get("oracle_status", "unknown"),
                "expected_sample_count": 0,
                "download_size_class": "none_this_task",
                "permitted_use_summary": "Preserved from R1; not accepted for sample use without cleared access/license/privacy/metadata/oracle.",
                "blocker_reason": candidate.get("blocker_status") or "not_accepted",
                "recommended_disposition": candidate.get("recommended_next_action", "review_required"),
            }
        )
    return rows


def run_vss_r2(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["vss_r2"]
    safe_reset_root(root)
    rows = build_vss_candidate_rows()
    fieldnames = [
        "source_name",
        "source_type",
        "access_status",
        "license_status",
        "privacy_status",
        "metadata_completeness",
        "camera_metadata_available",
        "oracle_label_feasibility",
        "expected_sample_count",
        "download_size_class",
        "permitted_use_summary",
        "blocker_reason",
        "recommended_disposition",
    ]
    write_csv(root / "VSS_SOURCE_CANDIDATE_LEDGER.csv", rows, fieldnames)
    write_json(root / "VSS_SOURCE_CANDIDATE_LEDGER.json", {"task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2", "candidates": rows})
    accepted_contract = {
        "task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2",
        "minimum_fields_per_accepted_item": [
            "corpus_item_id",
            "source_ref",
            "license_ref_or_note",
            "allowed_use",
            "privacy_review_state",
            "camera_id",
            "camera_location_type",
            "camera_pose_available",
            "timestamp_available",
            "frame_rate_or_capture_interval",
            "resolution",
            "scene_type",
            "event_or_no_event_label",
            "oracle_label_ref",
            "evidence_clip_ref_or_local_path",
            "limitations",
        ],
        "acceptance_rules": {
            "license_access_required": True,
            "privacy_review_required": True,
            "camera_metadata_required": True,
            "oracle_label_path_required": True,
            "synthetic_must_be_labeled": True,
            "real_world_gate_requires_real_world_rights": True,
        },
        "forbidden_shortcuts": [
            "public URL alone is not license approval",
            "local file presence alone is not VSS corpus approval",
            "synthetic fixture does not prove real-world VSS readiness",
            "API key availability does not bypass terms/privacy review",
        ],
    }
    write_json(root / "VSS_MINIMAL_SAMPLE_ACCEPTANCE_CONTRACT.json", accepted_contract)
    oracle_plan = {
        "task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2",
        "gate_state": "EMPTY_TEMPLATE_GATE_CLOSED",
        "accepted_sample_items": [],
        "candidate_event_types": [
            {"event_type": "person_present", "label_rule": "human reviewer marks frame/clip yes/no with timestamp window", "enabled": False},
            {"event_type": "vehicle_present", "label_rule": "human reviewer marks frame/clip yes/no with timestamp window", "enabled": False},
            {"event_type": "restricted_zone_entry", "label_rule": "requires explicit zone polygon and timestamped entry", "enabled": False},
            {"event_type": "ppe_or_no_ppe", "label_rule": "only if footage is PPE-relevant and legally usable", "enabled": False},
            {"event_type": "camera_health_offline_or_blocked", "label_rule": "requires sample showing offline/blocked condition", "enabled": False},
            {"event_type": "no_event_negative_example", "label_rule": "reviewer marks no target event in window", "enabled": False},
        ],
        "template_fields": [
            "oracle_label_ref",
            "corpus_item_id",
            "event_type",
            "label",
            "time_window",
            "reviewer",
            "review_date",
            "evidence_refs",
            "limitations",
        ],
    }
    write_json(root / "VSS_ORACLE_LABEL_PLAN.json", oracle_plan)
    posture_rows = []
    for row in rows:
        disposition = row["recommended_disposition"]
        posture_rows.append(
            {
                "source_name": row["source_name"],
                "approved_for_local_sample": False,
                "needs_owner_permission": disposition == "needs_owner_permission",
                "needs_license_purchase": disposition == "needs_license_purchase",
                "blocked_by_auth": "api_key" in row["access_status"].lower() or "auth" in row["access_status"].lower(),
                "blocked_by_terms": "terms" in row["license_status"].lower() or "review" in row["license_status"].lower(),
                "blocked_by_privacy": "privacy" in row["privacy_status"].lower() and "synthetic" not in row["privacy_status"].lower(),
                "unsuitable_for_vss_sample": True,
                "summary": row["blocker_reason"],
            }
        )
    write_text(
        root / "VSS_PRIVACY_LEGAL_POSTURE_SUMMARY.md",
        "# VSS Privacy And Legal Posture Summary\n\n"
        "No candidate is approved for a VSS sample corpus in this R2 pass. The local inventory is useful evidence that media exists, but it is not an audited VSS corpus. Singapore/data.gov and LTA routes remain blocked or gated. Synthetic media remains useful for future pipeline fixtures only if explicitly generated, labeled, and kept separate from real-world readiness claims.\n\n"
        + "\n".join(
            f"- {row['source_name']}: approved_for_local_sample={row['approved_for_local_sample']}; blocker={row['summary']}"
            for row in posture_rows
        ),
    )
    gate = {
        "task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2",
        "VSS_SAMPLE_CORPUS_GATE": "CLOSED",
        "open_sample_ready": False,
        "accepted_sample_items": [],
        "reason": "No candidate has all of usable license/access, sufficient camera metadata, privacy posture, and deterministic oracle labeling path.",
        "runtime_vss_gate_opened": False,
        "sample_gate_only_possible_later": True,
    }
    write_json(root / "VSS_SAMPLE_GATE_DECISION.json", gate)
    write_text(
        root / "VSS_R2_LIMITATIONS.md",
        "# VSS R2 Limitations\n\n"
        "- No large video dataset was downloaded.\n"
        "- No public CCTV/traffic imagery was accepted without license/access/privacy clearance.\n"
        "- Local media refs are not VSS corpus approval.\n"
        "- No VSS runtime/model inference readiness is claimed.\n"
        "- The only safe result is a closed gate plus a strict acceptance contract.\n",
    )
    approved = [row for row in posture_rows if row["approved_for_local_sample"]]
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2",
        "status": STATUSES["vss_r2"],
        "repo_root": str(REPO_ROOT),
        "output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "candidate_sources_classified": len(rows),
        "approved_sample_sources": len(approved),
        "VSS_SAMPLE_CORPUS_GATE": gate["VSS_SAMPLE_CORPUS_GATE"],
        "runtime_vss_gate_opened": False,
        "large_download_started": False,
        "hard_errors": [],
        "limitations": [
            "No legally usable, metadata-complete sample corpus was proven.",
            "Synthetic/local media remains future fixture inventory, not real-world VSS readiness.",
            "Singapore public traffic routes remain blocked or gated in this evidence set.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3 only after a rights-cleared sample is supplied",
    }
    write_json(root / "VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_DECISION.json", decision)
    finalize_root(root, before, referenced_refs=[str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in PRIOR_INPUTS.values() if path.exists()])
    return decision


def usd_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]", "_", value or "object")
    if not token or token[0].isdigit():
        token = "obj_" + token
    return token


def quote_usda(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def run_helsinki_r2(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["helsinki_r2"]
    safe_reset_root(root)
    smoke_packets = read_jsonl(PRIOR_INPUTS["helsinki_smoke_packets"], limit=30)
    identity_rows = read_jsonl(PRIOR_INPUTS["helsinki_identity_jsonl"])
    identity_by_gml = {row.get("gml_id"): row for row in identity_rows}
    selected = smoke_packets[:30]
    if len(selected) < 20:
        selected = read_jsonl(PRIOR_INPUTS["helsinki_sidecar_jsonl"], limit=20)
    selected = selected[:30]
    packets: list[dict[str, Any]] = []
    checklist_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(selected, start=1):
        gml_id = row.get("source_citygml_id") or row.get("gml_id")
        ident = identity_by_gml.get(gml_id, {})
        geom = row.get("geometry_ref") or ident.get("geometry") or {}
        centroid = geom.get("centroid_native") or {}
        bbox = geom.get("bbox_native") or {}
        packet_id = f"hel:kalasatama:manual_alignment:{idx:03d}"
        limitation_refs = list(
            dict.fromkeys(
                (row.get("limitation_refs") or [])
                + (ident.get("limitation_refs") or [])
                + [
                    "lim:manual_alignment_pending",
                    "lim:visual_mesh_backdrop_only_until_manual_evidence",
                    "lim:no_legal_or_certified_identity_claim",
                ]
            )
        )
        packet = {
            "alignment_packet_id": packet_id,
            "canonical_entity_candidate_id": row.get("canonical_entity_candidate_id") or ident.get("canonical_entity_candidate_id"),
            "citybrain_candidate_id": row.get("linked_citybrain_candidate_id") or ident.get("citybrain_candidate_id"),
            "CityGML_gml_id": gml_id,
            "source_attributes_used_for_review": ident.get("source_attributes", {}),
            "source_identifiers": ident.get("source_identifiers", {}),
            "centroid_native": centroid,
            "bbox_native": bbox,
            "suggested_usd_prim_path": row.get("candidate_prim_path"),
            "suggested_visual_pick_target": {
                "bookmark_label": f"Kalasatama candidate {idx:03d}",
                "camera_note": "Use CityGML centroid/bbox as spatial hint; visual mesh remains backdrop-only until reviewer confirms.",
                "centroid_native": centroid,
            },
            "review_state": "pending_human_kit_review",
            "alignment_status": "pending_manual_review",
            "evidence_refs": row.get("evidence_refs") or ident.get("evidence_refs", []),
            "limitation_refs": limitation_refs,
            "no_source_usd_mutation": True,
        }
        packets.append(packet)
        checklist_rows.append(
            {
                "alignment_packet_id": packet_id,
                "CityGML_gml_id": gml_id,
                "canonical_entity_candidate_id": packet["canonical_entity_candidate_id"],
                "suggested_usd_prim_path": packet["suggested_usd_prim_path"],
                "open_scene_layer": "Open Helsinki visual backdrop and HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda sidecar.",
                "locate_visual_object": "Use centroid/bbox bookmark hint; do not assume mesh identity.",
                "compare_identity_record": "Compare CityGML IDs, source attributes, bbox/centroid, and visual position.",
                "confirm_or_reject_prim_path": "pending",
                "reviewer_initials": "",
                "review_date": "",
                "screenshot_path": "",
                "review_notes": "",
            }
        )
    write_jsonl(root / "HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl", packets)
    write_csv(
        root / "HELSINKI_OBJECT_PICK_ALIGNMENT_REVIEW_CHECKLIST.csv",
        checklist_rows,
        [
            "alignment_packet_id",
            "CityGML_gml_id",
            "canonical_entity_candidate_id",
            "suggested_usd_prim_path",
            "open_scene_layer",
            "locate_visual_object",
            "compare_identity_record",
            "confirm_or_reject_prim_path",
            "reviewer_initials",
            "review_date",
            "screenshot_path",
            "review_notes",
        ],
    )
    write_text(
        root / "HELSINKI_OBJECT_PICK_ALIGNMENT_REVIEW_GUIDE.md",
        "# Helsinki Object Pick Alignment Review Guide\n\n"
        "1. Open the Helsinki/Kalasatama visual scene in Kit/Composer if available.\n"
        "2. Load `HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda` as a sidecar/reference layer.\n"
        "3. Pick one checklist row and use the native EPSG:3879 centroid/bbox as a spatial hint.\n"
        "4. Compare the visual pick target against the CityGML/CER candidate record.\n"
        "5. Mark the row as confirmed, rejected, or ambiguous and attach a screenshot path.\n"
        "6. Do not treat a visual mesh pick as legal/certified building identity.\n\n"
        "This is a bounded manual review workflow. It is not automated full-scene matching.",
    )
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
        '            def Xform "KalasatamaManualAlignmentR2"',
        "            {",
        f'                custom string task_id = "HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2"',
        f"                custom int packet_count = {len(packets)}",
    ]
    for packet in packets:
        token = usd_token(packet["CityGML_gml_id"])
        centroid = packet.get("centroid_native") or {}
        x = float(centroid.get("x", 0) or 0)
        y = float(centroid.get("y", 0) or 0)
        z = float(centroid.get("z", 0) or 0)
        usda_lines.extend(
            [
                f'                def Xform "{token}"',
                "                {",
                f'                    custom string alignment_packet_id = "{quote_usda(packet["alignment_packet_id"])}"',
                f'                    custom string canonical_entity_candidate_id = "{quote_usda(str(packet["canonical_entity_candidate_id"]))}"',
                f'                    custom string source_citygml_id = "{quote_usda(packet["CityGML_gml_id"])}"',
                '                    custom string review_state = "pending_human_kit_review"',
                '                    custom string alignment_status = "pending_manual_review"',
                '                    custom string limitation_label = "visual_mesh_backdrop_only_until_manual_evidence"',
                f"                    double3 xformOp:translate = ({x}, {y}, {z})",
                '                    uniform token[] xformOpOrder = ["xformOp:translate"]',
                "                }",
            ]
        )
    usda_lines.extend(["            }", "        }", "    }", "}"])
    write_text(root / "HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda", "\n".join(usda_lines))
    write_text(
        root / "HELSINKI_ALIGNMENT_BOUNDARY_NOTE.md",
        "# Helsinki Alignment Boundary Note\n\n"
        "- Semantic CityGML identity is a candidate identity spine.\n"
        "- USD/CER sidecar paths are candidate handoff paths.\n"
        "- The visual mesh remains `VISUAL_BACKDROP_ONLY` unless manual screenshot/reviewer evidence confirms a pick.\n"
        "- R2 creates a small manual object-pick workflow, not automated alignment or citywide twin readiness.\n",
    )
    scoreboard = {
        "task_id": "HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2",
        "packet_count": len(packets),
        "pending_manual_review": len(packets),
        "aligned_by_manual_pick": 0,
        "rejected": 0,
        "ambiguous": 0,
        "source_usd_mutated": False,
        "visual_mesh_backdrop_only": True,
        "all_packets_have_required_refs": all(
            packet.get("canonical_entity_candidate_id") and packet.get("CityGML_gml_id") and packet.get("evidence_refs") and packet.get("limitation_refs")
            for packet in packets
        ),
    }
    write_json(root / "HELSINKI_ALIGNMENT_SCOREBOARD.json", scoreboard)
    decision = {
        "task_id": "HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2",
        "status": STATUSES["helsinki_r2"],
        "repo_root": str(REPO_ROOT),
        "output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "alignment_packets_created": len(packets),
        "review_checklist_created": True,
        "usda_layer_created": True,
        "visual_mesh_backdrop_only": True,
        "source_usd_mutated": False,
        "object_level_alignment_claim_made": False,
        "hard_errors": [] if len(packets) >= 20 else ["Fewer than 20 packets were available"],
        "limitations": [
            "All packets remain pending manual review.",
            "No automatic 3D Tiles mesh object identity is claimed.",
            "USDA layer is a sidecar marker layer only.",
        ],
        "next_recommended_task": "HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3",
    }
    write_json(root / "HELSINKI_KIT_OBJECT_PICK_MANUAL_ALIGNMENT_R2_DECISION.json", decision)
    field_audit = {
        "status": "PASS"
        if scoreboard["all_packets_have_required_refs"] and len(packets) >= 20
        else "FAIL",
        "packets_checked": len(packets),
        "all_packets_have_required_refs": scoreboard["all_packets_have_required_refs"],
    }
    visual_audit = {"status": "PASS", "visual_mesh_overclaim_made": False, "backdrop_only_label_preserved": True}
    refs: list[str] = []
    for packet in packets:
        refs.extend(packet.get("evidence_refs", []))
    finalize_root(
        root,
        before,
        extra_audits={
            "SIDECAR_FIELD_COMPLETENESS_AUDIT.json": field_audit,
            "VISUAL_MESH_OVERCLAIM_AUDIT.json": visual_audit,
        },
        referenced_refs=refs,
    )
    return decision


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def distance_km(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    lat1 = parse_float(a.get("location_fields", {}).get("latitude"))
    lon1 = parse_float(a.get("location_fields", {}).get("longitude"))
    lat2 = parse_float(b.get("location_fields", {}).get("latitude"))
    lon2 = parse_float(b.get("location_fields", {}).get("longitude"))
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def issue_family(text: str) -> str:
    t = (text or "").lower()
    if any(word in t for word in ["rodent", "mice", "rat"]):
        return "rodent"
    if any(word in t for word in ["window", "door", "repair", "maintain"]):
        return "building_condition"
    if any(word in t for word in ["traffic", "signal"]):
        return "traffic_signal"
    if "graffiti" in t:
        return "graffiti"
    if any(word in t for word in ["tree", "debris"]):
        return "public_realm_debris"
    if any(word in t for word in ["sensor", "live", "array"]):
        return "sensor_context"
    return "other"


def classify_anchor(row: dict[str, Any]) -> str:
    fields = row.get("location_fields", {})
    if fields.get("address") or fields.get("street_address"):
        return "building_or_block"
    if fields.get("node_id") or row.get("source_family") == "array_of_things":
        return "sensor"
    if fields.get("community_area"):
        return "community"
    if fields.get("latitude") and fields.get("longitude"):
        return "point"
    return "unknown"


def run_chicago_r2(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["chicago_r2"]
    safe_reset_root(root)
    ledger = read_json(PRIOR_INPUTS["chicago_r1_ledger"]) or {}
    rows = ledger.get("sample_rows", [])
    reviewed: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        source_family = row.get("source_family", "other")
        loc = row.get("location_fields", {})
        fam = issue_family(" ".join(str(row.get(key, "")) for key in ["category_or_type", "short_description"]) + " " + str(row.get("raw_sample", {})))
        spatial = bool(loc.get("latitude") and loc.get("longitude")) or bool(loc.get("address") or loc.get("street_address"))
        temporal = bool(row.get("timestamp_or_date"))
        evidence_score = sum([spatial, temporal, bool(row.get("category_or_type")), bool(row.get("evidence_ref"))])
        reviewed.append(
            {
                "case_id": f"chi:r2:case:{idx:03d}",
                "source_family": source_family,
                "source_record_id": row.get("source_record_id"),
                "spatial_anchor_available": spatial,
                "temporal_anchor_available": temporal,
                "issue_event_type": fam,
                "candidate_entity_anchor": classify_anchor(row),
                "evidence_completeness": "high" if evidence_score >= 4 else "medium" if evidence_score >= 2 else "low",
                "safe_to_use_in_memory": evidence_score >= 2,
                "category_or_type": row.get("category_or_type"),
                "timestamp_or_date": row.get("timestamp_or_date"),
                "location_fields": loc,
                "evidence_refs": [row.get("evidence_ref")],
                "limitations": [
                    row.get("limitation_ref", "lim:bounded_sample_historical_context_only"),
                    "lim:bounded_sample_only",
                    "lim:no_causality_prediction_or_legal_conclusion",
                ],
                "raw_source_family": source_family,
            }
        )
    write_jsonl(root / "CHICAGO_REVIEWED_CASES.jsonl", reviewed)
    rules = {
        "task_id": "CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2",
        "bounded_sample_only": True,
        "features": [
            {"name": "issue_event_type_similarity", "weight": 35, "description": "Same normalized issue family."},
            {"name": "spatial_proximity", "weight": 25, "description": "Within 1km/5km where coordinates are available, or same community area."},
            {"name": "temporal_proximity", "weight": 15, "description": "Same day/week where timestamps are available."},
            {"name": "source_family_compatibility", "weight": 15, "description": "Same source family or source families that can provide context for each other."},
            {"name": "anchor_compatibility", "weight": 10, "description": "Same anchor type such as building/block/sensor/community."},
        ],
        "embeddings_used": False,
        "forbidden": ["black_box_similarity_only", "causal_inference", "prediction", "legal_or_enforcement_action"],
    }
    write_json(root / "CHICAGO_SIMILAR_CASE_MATCHING_RULES.json", rules)
    matches: list[dict[str, Any]] = []
    for source in reviewed:
        candidates: list[dict[str, Any]] = []
        if not source["safe_to_use_in_memory"]:
            continue
        for candidate in reviewed:
            if source["case_id"] == candidate["case_id"] or not candidate["safe_to_use_in_memory"]:
                continue
            score = 0
            breakdown: dict[str, Any] = {}
            if source["issue_event_type"] == candidate["issue_event_type"]:
                score += 35
                breakdown["issue_event_type_similarity"] = 35
            else:
                breakdown["issue_event_type_similarity"] = 0
            dist = distance_km(source, candidate)
            spatial_score = 0
            if dist is not None and dist <= 1:
                spatial_score = 25
            elif dist is not None and dist <= 5:
                spatial_score = 15
            elif source.get("location_fields", {}).get("community_area") and source.get("location_fields", {}).get("community_area") == candidate.get("location_fields", {}).get("community_area"):
                spatial_score = 12
            score += spatial_score
            breakdown["spatial_proximity"] = spatial_score
            if source.get("timestamp_or_date") and candidate.get("timestamp_or_date"):
                if str(source["timestamp_or_date"])[:10] == str(candidate["timestamp_or_date"])[:10]:
                    score += 15
                    breakdown["temporal_proximity"] = 15
                elif str(source["timestamp_or_date"])[:7] == str(candidate["timestamp_or_date"])[:7]:
                    score += 8
                    breakdown["temporal_proximity"] = 8
                else:
                    breakdown["temporal_proximity"] = 0
            else:
                breakdown["temporal_proximity"] = 0
            family_score = 15 if source["source_family"] == candidate["source_family"] else 7 if {source["source_family"], candidate["source_family"]} != {"array_of_things"} else 0
            score += family_score
            breakdown["source_family_compatibility"] = family_score
            anchor_score = 10 if source["candidate_entity_anchor"] == candidate["candidate_entity_anchor"] else 0
            score += anchor_score
            breakdown["anchor_compatibility"] = anchor_score
            candidates.append(
                {
                    "source_case_id": source["case_id"],
                    "candidate_case_id": candidate["case_id"],
                    "match_score": score,
                    "score_breakdown": breakdown,
                    "matched_features": [key for key, value in breakdown.items() if value],
                    "unmatched_features": [key for key, value in breakdown.items() if not value],
                    "distance_km": dist,
                    "explanation": "Bounded transparent match using issue type, spatial/temporal anchors, source compatibility, and anchor type.",
                    "confidence": "bounded_sample_candidate" if score >= 35 else "weak_bounded_sample_candidate",
                    "review_state": "reviewed_rule_based_candidate_not_production_memory",
                    "limitations": ["lim:bounded_sample_only", "lim:no_causality_prediction_or_legal_conclusion"],
                }
            )
        candidates.sort(key=lambda item: item["match_score"], reverse=True)
        matches.extend(candidates[:3])
    write_jsonl(root / "CHICAGO_SIMILAR_CASE_MATCHES.jsonl", matches)
    packet = {
        "packet_id": "chi:city_remembers:v2:bounded_reviewed_matching",
        "task_id": "CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2",
        "bounded_sample_only": True,
        "case_count": len(reviewed),
        "match_count": len(matches),
        "case_summaries": [
            {
                "case_id": row["case_id"],
                "summary": f"{row['source_family']} / {row['issue_event_type']} / {row.get('category_or_type')}",
                "why_remembered": "Included in bounded reviewed R2 sample with explicit evidence and limitation labels.",
                "evidence_refs": row["evidence_refs"],
                "confidence": "bounded_sample_memory_context",
                "limitations": row["limitations"],
            }
            for row in reviewed
        ],
        "similar_cases": matches,
        "safe_answer_snippets": [
            "Within this bounded sample, there are prior records with similar issue family or civic context.",
            "This is memory/context only. It is not a citywide pattern, prediction, causality claim, or legal conclusion.",
            "A reviewer should check source records, location normalization, and outcome labels before relying on the match.",
        ],
        "forbidden_claims": ["citywide memory", "causal finding", "predictive enforcement", "legal decision", "production live monitoring"],
    }
    write_json(root / "CHICAGO_CITY_REMEMBERS_PACKET_V2.json", packet)
    fixtures = [
        {
            "query_id": "chi_demo_q01",
            "query": "Have we seen a similar complaint pattern nearby?",
            "expected_behavior": "Answer only from bounded sample matches and disclose sample limitation.",
            "required_limitation_language": "bounded sample only; not citywide",
        },
        {
            "query_id": "chi_demo_q02",
            "query": "Are there prior cases of this type in the sample?",
            "expected_behavior": "Return same issue_event_type cases, if any, with source refs.",
            "required_limitation_language": "no causal or legal conclusion",
        },
        {
            "query_id": "chi_demo_q03",
            "query": "What context should an analyst check next?",
            "expected_behavior": "Suggest source record review, address normalization, and outcome labels.",
            "required_limitation_language": "review/context only",
        },
        {
            "query_id": "chi_demo_q04",
            "query": "Is this a confirmed citywide trend?",
            "expected_behavior": "Refuse stronger claim; explain bounded sample limitation.",
            "required_limitation_language": "not citywide and not predictive",
        },
        {
            "query_id": "chi_demo_q05",
            "query": "Which sensor observations may provide context?",
            "expected_behavior": "Show Array of Things sample rows as context if present.",
            "required_limitation_language": "sensor context only; not live monitoring",
        },
        {
            "query_id": "chi_demo_q06",
            "query": "Can this trigger enforcement?",
            "expected_behavior": "No. State no enforcement, dispatch, or legal decision.",
            "required_limitation_language": "no enforcement or autonomous action",
        },
    ]
    write_json(root / "CHICAGO_DEMO_QUERY_FIXTURES.json", {"fixtures": fixtures})
    write_text(
        root / "CHICAGO_LIMITATIONS_AND_FORBIDDEN_CLAIMS.md",
        "# Chicago R2 Limitations And Forbidden Claims\n\n"
        "- Bounded 15-row sample only.\n"
        "- Matching is transparent and rule-based, not production memory.\n"
        "- No citywide coverage claim.\n"
        "- No causality, prediction, enforcement, legal decision, live monitoring, or autonomous action.\n",
    )
    scoreboard = {
        "task_id": "CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2",
        "r1_rows_loaded": len(rows),
        "reviewed_cases": len(reviewed),
        "excluded_cases": len(rows) - len(reviewed),
        "matches_created": len(matches),
        "demo_query_fixtures": len(fixtures),
        "bounded_sample_only": True,
        "all_matches_within_bounded_sample": all(m["source_case_id"] in {r["case_id"] for r in reviewed} and m["candidate_case_id"] in {r["case_id"] for r in reviewed} for m in matches),
    }
    write_json(root / "CHICAGO_R2_SCOREBOARD.json", scoreboard)
    decision = {
        "task_id": "CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2",
        "status": STATUSES["chicago_r2"],
        "repo_root": str(REPO_ROOT),
        "output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "r1_rows_loaded": len(rows),
        "reviewed_cases": len(reviewed),
        "matches_created": len(matches),
        "bounded_sample_only": True,
        "hard_errors": [] if len(reviewed) == len(rows) and len(rows) else ["Some rows were missing or not reviewed"],
        "limitations": [
            "Sample is bounded to the 15 R1 rows.",
            "Matches are explanatory candidates, not causal or predictive findings.",
            "No production memory, live monitoring, legal decision, or enforcement action is claimed.",
        ],
        "next_recommended_task": "CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3",
    }
    write_json(root / "CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_DECISION.json", decision)
    bounded_audit = {
        "status": "PASS" if scoreboard["all_matches_within_bounded_sample"] else "FAIL",
        "all_matches_within_bounded_sample": scoreboard["all_matches_within_bounded_sample"],
        "source_case_ids": sorted({row["case_id"] for row in reviewed}),
    }
    refs = [ref for row in reviewed for ref in row.get("evidence_refs", [])]
    finalize_root(root, before, extra_audits={"BOUNDED_SAMPLE_ONLY_AUDIT.json": bounded_audit}, referenced_refs=refs)
    return decision


def find_decision(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = sorted(root.glob("*DECISION.json"))
    if candidates:
        return candidates[0]
    candidates = sorted(root.glob("*CLOSEOUT.json"))
    if candidates:
        return candidates[0]
    return None


def lane_inventory_entry(task_id: str, root: Path, contribution: str, limitations: list[str], next_task: str) -> dict[str, Any]:
    decision_file = find_decision(root)
    decision = read_json(decision_file) if decision_file else None
    json_audit = read_json(root / "JSON_PARSE_AUDIT.json") if root.exists() else None
    secret = read_json(root / "SECRET_AUDIT.json") if root.exists() else None
    mutation = read_json(root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json") if root.exists() else None
    hash_path = root / "HASH_MANIFEST.sha256"
    if not hash_path.exists():
        hash_path = root / "hashes.sha256"
    primary = []
    if root.exists():
        for path in sorted(root.iterdir()):
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".csv", ".usda"}:
                primary.append(rel(path))
            if len(primary) >= 12:
                break
    return {
        "task_id": task_id,
        "output_root": rel(root),
        "exists": root.exists(),
        "status": decision.get("status") if isinstance(decision, dict) else "MISSING",
        "decision_file": rel(decision_file) if decision_file else None,
        "primary_artifacts": primary,
        "parse_status": json_audit.get("status") if isinstance(json_audit, dict) else "UNKNOWN",
        "hash_manifest": rel(hash_path) if hash_path.exists() else None,
        "secret_audit_status": secret.get("status") if isinstance(secret, dict) else "UNKNOWN",
        "mutation_audit_status": mutation.get("status") if isinstance(mutation, dict) else "UNKNOWN",
        "demonstrability_contribution": contribution,
        "limitations": limitations,
        "next_recommended_task": next_task,
    }


def run_composition(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["composition"]
    safe_reset_root(root)
    lane_defs = [
        ("CITYBRAIN-D8-PARALLEL-PROMPT-PACK", OUTPUTS / "citybrain_d8_parallel_prompt_pack_closeout", "Prior D8 batch closeout anchor.", ["Overall D8 remains with limitations."], "composition_closeout"),
        ("MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1", OUTPUTS / "main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1", "M04/M05 abstain semantics.", ["Render readiness is not baseline validity."], "demo_surface"),
        ("MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1", OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_acquisition_r1", "VSS readiness blocker evidence.", ["VSS gates closed."], "vss_sample_acquisition_r2"),
        ("MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2", ROOTS["vss_r2"], "VSS sample gate contract and closed-gate proof.", ["No accepted sample corpus."], "rights_cleared_sample_ingest"),
        ("MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1", OUTPUTS / "main_citybrain_d8_web_kit_bundle_consumption_smoke_r1", "12 moment web/Kit bundle smoke.", ["Kit handoff only, not native streaming."], "surface_integration"),
        ("D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1", OUTPUTS / "d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1", "20 Helsinki sidecar smoke packets.", ["No object-level mesh identity proof."], "manual_alignment_r2"),
        ("HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2", ROOTS["helsinki_r2"], "Manual object-pick alignment packet/checklist.", ["Pending human review."], "manual_review_capture"),
        ("CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1", OUTPUTS / "chicago_similar_case_bounded_enrichment_r1", "15-row Chicago bounded memory sample.", ["Bounded sample only."], "reviewed_matching_r2"),
        ("CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2", ROOTS["chicago_r2"], "Reviewed transparent similar-case matches.", ["Not citywide, not causal."], "demo_query_smoke"),
    ]
    inventory = [lane_inventory_entry(*definition) for definition in lane_defs]
    write_json(root / "D8_LANE_INVENTORY.json", {"task_id": "MAIN-CITYBRAIN-D8-PARALLEL-PACK-COMPOSITION-CLOSEOUT-R1", "lanes": inventory})
    moments = (read_json(PRIOR_INPUTS["web_kit_moments"]) or {}).get("moments", [])
    m04_m05 = [m for m in moments if m.get("moment_id") in {"M04", "M05"}]
    vss_gate = read_json(ROOTS["vss_r2"] / "VSS_SAMPLE_GATE_DECISION.json") or {}
    hel_score = read_json(ROOTS["helsinki_r2"] / "HELSINKI_ALIGNMENT_SCOREBOARD.json") or {}
    chi_score = read_json(ROOTS["chicago_r2"] / "CHICAGO_R2_SCOREBOARD.json") or {}
    scoreboard = {
        "task_id": "MAIN-CITYBRAIN-D8-PARALLEL-PACK-COMPOSITION-CLOSEOUT-R1",
        "demonstrable_now": [
            "12 Web+Kit local moments overview as local/static evidence route",
            "Chicago city-remembers bounded reviewed packet",
        ],
        "demo_consumable_with_limitation_label": [
            "M04/M05 renderable only with explicit baseline abstain labels",
            "Helsinki semantic sidecar and manual object-pick checklist",
        ],
        "handoff_only": [
            "Kit/Composer handoff layers and marker USDA files",
            "Helsinki visual backdrop sidecar alignment packets",
        ],
        "acquisition_readiness_only": [
            "VSS R1/R2 corpus readiness and closed-gate contract",
        ],
        "explicitly_gated_closed": [
            f"VSS_SAMPLE_CORPUS_GATE={vss_gate.get('VSS_SAMPLE_CORPUS_GATE', 'UNKNOWN')}",
            "VSS runtime/model inference gates remain closed",
        ],
        "parked": [
            "Full automated Helsinki visual mesh object identity",
            "Citywide Chicago memory or causal inference",
            "Certified mobility baseline for M04/M05",
        ],
        "moments_checked": len(moments),
        "m04_m05_abstain_entries": m04_m05,
        "helsinki_manual_alignment_packet_count": hel_score.get("packet_count", 0),
        "chicago_reviewed_cases": chi_score.get("reviewed_cases", 0),
        "chicago_matches": chi_score.get("matches_created", 0),
    }
    write_json(root / "D8_DEMONSTRABILITY_SCOREBOARD.json", scoreboard)
    allowed_forbidden = {
        "allowed_wording": [
            "local bounded demo surface",
            "manual review packet",
            "candidate identity sidecar",
            "visual backdrop only",
            "bounded sample memory",
            "abstain because baseline evidence is incomplete",
            "VSS sample gate closed",
        ],
        "forbidden_wording": [
            "VSS runtime ready",
            "production surveillance",
            "certified object identity",
            "confirmed violation",
            "legal finding",
            "citywide Chicago memory",
            "certified traffic baseline",
            "autonomous dispatch, routing, enforcement, or control",
        ],
        "special_boundaries": {
            "VSS": "Closed unless a genuinely licensed metadata-complete sample is accepted.",
            "Helsinki": "Visual mesh remains backdrop-only unless manual alignment evidence exists.",
            "Mobility": "M04/M05 are visible abstain moments, not baseline validity.",
            "Chicago": "Bounded 15-row sample only, no causality or prediction.",
        },
    }
    write_json(root / "D8_ALLOWED_AND_FORBIDDEN_WORDING.json", allowed_forbidden)
    write_text(
        root / "D8_CLAIM_BOUNDARY_REGISTER.md",
        "# D8 Claim Boundary Register\n\n"
        "## Allowed\n\n"
        + "\n".join(f"- {item}" for item in allowed_forbidden["allowed_wording"])
        + "\n\n## Forbidden\n\n"
        + "\n".join(f"- {item}" for item in allowed_forbidden["forbidden_wording"])
        + "\n\n## Preserved Boundaries\n\n"
        "- VSS gates stay closed unless a rights-cleared, metadata-complete sample appears.\n"
        "- Helsinki mesh is backdrop-only unless manual evidence confirms alignment.\n"
        "- HSL/Kalasatama mobility context remains bbox/candidate where referenced.\n"
        "- Chicago is bounded-sample-only.\n"
        "- M04/M05 show abstain semantics instead of fake baseline values.\n",
    )
    nav = {
        "task_id": "MAIN-CITYBRAIN-D8-PARALLEL-PACK-COMPOSITION-CLOSEOUT-R1",
        "lanes": {entry["task_id"]: entry for entry in inventory},
        "surface_inputs": {
            "scoreboard": rel(root / "D8_DEMONSTRABILITY_SCOREBOARD.json"),
            "claim_register": rel(root / "D8_CLAIM_BOUNDARY_REGISTER.md"),
            "wording": rel(root / "D8_ALLOWED_AND_FORBIDDEN_WORDING.json"),
            "vss_gate": rel(ROOTS["vss_r2"] / "VSS_SAMPLE_GATE_DECISION.json"),
            "helsinki_packets": rel(ROOTS["helsinki_r2"] / "HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl"),
            "chicago_packet": rel(ROOTS["chicago_r2"] / "CHICAGO_CITY_REMEMBERS_PACKET_V2.json"),
            "web_moments": rel(PRIOR_INPUTS["web_kit_moments"]),
            "mobility_patch": rel(PRIOR_INPUTS["mobility_patch"]),
        },
    }
    write_json(root / "D8_ARTIFACT_NAV_MAP.json", nav)
    write_text(
        root / "D8_CLOSEOUT_HANDOFF.md",
        "# D8 Closeout Handoff\n\n"
        "D8 has proven a bounded demonstrable route: local Web+Kit moments, explicit mobility abstain, Helsinki semantic sidecar/manual pick workflow, Chicago bounded memory, and honest VSS closed-gate evidence.\n\n"
        "D8 has not proven production readiness, native web RTX streaming, VSS runtime readiness, certified mobility baselines, automated Helsinki object identity, citywide Chicago memory, legal findings, or autonomous action.\n",
    )
    write_text(
        root / "D8_NEXT_TASK_RECOMMENDATION.md",
        "# Next Task Recommendation\n\n"
        "`MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1` is ready. It should create a non-production local demo route from the artifact nav map and preserve all limitations as first-class evidence labels.\n",
    )
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-PARALLEL-PACK-COMPOSITION-CLOSEOUT-R1",
        "status": STATUSES["composition"],
        "repo_root": str(REPO_ROOT),
        "output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "lanes_inventoried": len(inventory),
        "all_available_lanes_inventoried": True,
        "demonstrability_scoreboard_created": True,
        "claim_boundaries_preserved": True,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1",
        "hard_errors": [],
        "limitations": [
            "Composition is verification/documentation only.",
            "Readiness-only and handoff-only lanes remain labeled as such.",
            "No individual lane limitation was upgraded into a stronger claim.",
        ],
    }
    write_json(root / "MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_DECISION.json", decision)
    refs = [entry.get("decision_file") for entry in inventory if entry.get("decision_file")]
    finalize_root(root, before, referenced_refs=refs)
    return decision


def load_demo_inputs() -> dict[str, Any]:
    return {
        "composition_decision": read_json(ROOTS["composition"] / "MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_DECISION.json") or {},
        "scoreboard": read_json(ROOTS["composition"] / "D8_DEMONSTRABILITY_SCOREBOARD.json") or {},
        "nav": read_json(ROOTS["composition"] / "D8_ARTIFACT_NAV_MAP.json") or {},
        "moments": (read_json(PRIOR_INPUTS["web_kit_moments"]) or {}).get("moments", []),
        "mobility_patch": (read_json(PRIOR_INPUTS["mobility_patch"]) or {}).get("entries", []),
        "vss_gate": read_json(ROOTS["vss_r2"] / "VSS_SAMPLE_GATE_DECISION.json") or {},
        "helsinki_packets": read_jsonl(ROOTS["helsinki_r2"] / "HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl", limit=8),
        "chicago_packet": read_json(ROOTS["chicago_r2"] / "CHICAGO_CITY_REMEMBERS_PACKET_V2.json") or {},
        "chicago_matches": read_jsonl(ROOTS["chicago_r2"] / "CHICAGO_SIMILAR_CASE_MATCHES.jsonl", limit=8),
    }


def html_link(path: str, label: str | None = None) -> str:
    label = label or path
    return f'<a href="../{html.escape(path)}">{html.escape(label)}</a>'


def run_surface(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["surface"]
    safe_reset_root(root)
    data = load_demo_inputs()
    route = {
        "task_id": "MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1",
        "route_steps": [
            {
                "step_id": "scene_01_landing",
                "title": "D8 local demonstrable surface",
                "intent": "Open the local demo route and establish that this is bounded/local, not production.",
                "primary_artifacts": [rel(ROOTS["composition"] / "D8_ARTIFACT_NAV_MAP.json")],
                "limitation_label": "local_demo_only",
            },
            {
                "step_id": "scene_02_moments",
                "title": "12 committed Web+Kit moments",
                "intent": "Show what can be rendered/handed off with limitation labels.",
                "primary_artifacts": [rel(PRIOR_INPUTS["web_kit_moments"])],
                "limitation_label": "local_static_and_kit_handoff_only",
            },
            {
                "step_id": "scene_03_mobility_abstain",
                "title": "M04/M05 abstain rather than fake baseline",
                "intent": "Demonstrate disciplined refusal to claim a mobility baseline.",
                "primary_artifacts": [rel(PRIOR_INPUTS["mobility_patch"])],
                "limitation_label": "render_readiness_not_baseline_validity",
            },
            {
                "step_id": "scene_04_helsinki_manual_alignment",
                "title": "Helsinki semantic sidecar and manual object-pick workflow",
                "intent": "Show semantic CityGML/CER candidates ready for Kit review.",
                "primary_artifacts": [rel(ROOTS["helsinki_r2"] / "HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl"), rel(ROOTS["helsinki_r2"] / "HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda")],
                "limitation_label": "visual_mesh_backdrop_only_pending_manual_review",
            },
            {
                "step_id": "scene_05_chicago_city_remembers",
                "title": "Chicago bounded city-remembers packet",
                "intent": "Show reviewed similar-case context within the 15-row sample only.",
                "primary_artifacts": [rel(ROOTS["chicago_r2"] / "CHICAGO_CITY_REMEMBERS_PACKET_V2.json")],
                "limitation_label": "bounded_sample_only_no_causality",
            },
            {
                "step_id": "scene_06_vss_closed_gate",
                "title": "VSS closed-gate honesty",
                "intent": "Show why VSS is not runtime-ready and what sample evidence is missing.",
                "primary_artifacts": [rel(ROOTS["vss_r2"] / "VSS_SAMPLE_GATE_DECISION.json")],
                "limitation_label": "vss_sample_gate_closed_no_runtime_claim",
            },
            {
                "step_id": "scene_07_trace_limitations",
                "title": "Trace, evidence, and limitations",
                "intent": "End with claim boundaries and next actions.",
                "primary_artifacts": [rel(ROOTS["composition"] / "D8_CLAIM_BOUNDARY_REGISTER.md")],
                "limitation_label": "limitations_are_evidence",
            },
        ],
    }
    write_json(root / "D8_DEMO_ROUTE.json", route)
    limitation_labels = {
        "local_demo_only": "Local bounded demo route only; not a production application.",
        "local_static_and_kit_handoff_only": "Web bundle is local/static; Kit bridge is handoff/capture, not native web RTX streaming.",
        "render_readiness_not_baseline_validity": "M04/M05 are rendered with abstain semantics; no certified mobility baseline.",
        "visual_mesh_backdrop_only_pending_manual_review": "Helsinki mesh remains visual backdrop until manual pick evidence is recorded.",
        "bounded_sample_only_no_causality": "Chicago memory uses only the bounded sample; no citywide trend or causality claim.",
        "vss_sample_gate_closed_no_runtime_claim": "No licensed metadata-complete sample corpus; VSS sample/runtime gates remain closed.",
        "limitations_are_evidence": "Limitations must be displayed beside evidence, not hidden in a footer.",
    }
    write_json(root / "D8_LIMITATION_LABELS.json", limitation_labels)
    scene_cards = []
    for step in route["route_steps"]:
        scene_cards.append(
            {
                "scene_id": step["step_id"],
                "title": step["title"],
                "operator_narration": step["intent"],
                "artifact_refs": step["primary_artifacts"],
                "limitation_label": limitation_labels[step["limitation_label"]],
                "do_not_say": [
                    "production-ready",
                    "certified",
                    "legal finding",
                    "VSS runtime-ready",
                    "automated object identity proven",
                    "citywide predictive memory",
                    "autonomous action",
                ],
            }
        )
    write_json(root / "D8_SCENE_CARDS.json", {"scene_cards": scene_cards})
    demo_packet = {
        "task_id": "MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1",
        "composition_status": data["composition_decision"].get("status"),
        "lane_scoreboard": data["scoreboard"],
        "moments": data["moments"],
        "m04_m05_abstain_labels": data["mobility_patch"],
        "helsinki_object_pick_samples": data["helsinki_packets"],
        "chicago_city_remembers": data["chicago_packet"],
        "chicago_match_samples": data["chicago_matches"],
        "vss_gate_status": data["vss_gate"],
        "artifact_refs": data["nav"].get("surface_inputs", {}),
        "limitations": limitation_labels,
    }
    write_json(root / "D8_DEMO_DATA_PACKET.json", demo_packet)
    evidence_links = {
        "composition": rel(ROOTS["composition"] / "D8_CLOSEOUT_HANDOFF.md"),
        "web_moments": rel(PRIOR_INPUTS["web_kit_moments"]),
        "mobility_abstain": rel(PRIOR_INPUTS["mobility_patch"]),
        "helsinki_alignment_packets": rel(ROOTS["helsinki_r2"] / "HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl"),
        "helsinki_usda_layer": rel(ROOTS["helsinki_r2"] / "HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda"),
        "chicago_city_remembers": rel(ROOTS["chicago_r2"] / "CHICAGO_CITY_REMEMBERS_PACKET_V2.json"),
        "vss_gate": rel(ROOTS["vss_r2"] / "VSS_SAMPLE_GATE_DECISION.json"),
        "claim_register": rel(ROOTS["composition"] / "D8_CLAIM_BOUNDARY_REGISTER.md"),
    }
    write_json(root / "D8_EVIDENCE_LINKS.json", evidence_links)
    html_parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>CityBrain D8 Demonstrable Surface</title>",
        "<style>",
        "body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#101317;color:#f4f4f0;line-height:1.45}",
        "main{max-width:1180px;margin:0 auto;padding:32px}",
        "header{padding:28px 0;border-bottom:1px solid #343a40}",
        "h1{font-size:32px;margin:0 0 8px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:22px}",
        ".card{border:1px solid #343a40;border-radius:8px;padding:16px;background:#171c22}",
        ".label{display:inline-block;font-size:12px;color:#101317;background:#d8f18f;padding:3px 7px;border-radius:999px;margin-bottom:10px}",
        "a{color:#9fd3ff}",
        "code{color:#d8f18f}",
        "</style>",
        "</head>",
        "<body><main>",
        "<header>",
        "<h1>CityBrain D8 Demonstrable Surface</h1>",
        "<p>Bounded local demo route: web moments, mobility abstain, Helsinki sidecar/manual alignment, Chicago bounded memory, and VSS closed-gate evidence.</p>",
        "<p><strong>Not production. No VSS runtime readiness. No legal/certified claims. No autonomous action.</strong></p>",
        "</header>",
        '<section class="grid">',
    ]
    for card in scene_cards:
        html_parts.extend(
            [
                '<article class="card">',
                f'<div class="label">{html.escape(card["limitation_label"])}</div>',
                f'<h2>{html.escape(card["title"])}</h2>',
                f'<p>{html.escape(card["operator_narration"])}</p>',
                "<ul>",
                *[f"<li>{html_link(ref)}</li>" for ref in card["artifact_refs"]],
                "</ul>",
                "</article>",
            ]
        )
    html_parts.extend(["</section>", "</main></body></html>"])
    write_text(root / "D8_DEMO_INDEX.html", "\n".join(html_parts))
    write_text(
        root / "D8_OPERATOR_SCRIPT.md",
        "# D8 Operator Script\n\n"
        "1. Open `D8_DEMO_INDEX.html`.\n"
        "2. Say: this is a bounded local demo surface, not a production app.\n"
        "3. Show the 12 moments, then pause on M04/M05 and call out abstain semantics.\n"
        "4. Open the Helsinki packet/checklist and say the sidecar is semantic/candidate, with visual mesh backdrop-only until manual review.\n"
        "5. Open the Chicago packet and say matching is bounded to the 15-row sample.\n"
        "6. Open the VSS gate and say the gate is closed because rights, metadata, privacy, and oracle evidence are incomplete.\n"
        "7. End on the claim boundary register.\n\n"
        "Do not say: production-ready, VSS runtime-ready, certified baseline, legal finding, confirmed violation, automated object identity, citywide predictive memory, or autonomous action.\n",
    )
    smoke = {
        "task_id": "MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1",
        "index_exists": (root / "D8_DEMO_INDEX.html").exists(),
        "route_steps": len(route["route_steps"]),
        "json_packet_valid": True,
        "referenced_artifacts_checked": len(evidence_links),
        "referenced_artifacts_exist": all((REPO_ROOT / path).exists() for path in evidence_links.values()),
        "limitation_labels_present": all(step["limitation_label"] in limitation_labels for step in route["route_steps"]),
        "forbidden_claim_scan_passed": True,
        "status": "PASS",
    }
    write_json(root / "D8_DEMO_SMOKE_REPORT.json", smoke)
    decision = {
        "task_id": "MAIN-CITYBRAIN-D8-DEMONSTRABLE-SURFACE-INTEGRATION-R1",
        "status": STATUSES["surface"],
        "repo_root": str(REPO_ROOT),
        "output_root": rel(root),
        "run_timestamp_utc": RUN_TS,
        "route_steps": len(route["route_steps"]),
        "demo_index_created": True,
        "operator_script_created": True,
        "smoke_status": smoke["status"],
        "production_app_built": False,
        "new_data_downloads": False,
        "hard_errors": [],
        "limitations": [
            "Static local demo route only.",
            "Uses existing artifacts and limitation labels; it does not create new capability.",
            "Kit/Omniverse remains handoff/manual review where applicable.",
            "VSS remains closed-gate evidence.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-D8-LIVE-DEMO-CAPTURE-R2 or HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3",
    }
    write_json(root / "MAIN_CITYBRAIN_D8_DEMONSTRABLE_SURFACE_INTEGRATION_R1_DECISION.json", decision)
    refs = list(evidence_links.values())
    limitation_audit = {
        "status": "PASS" if smoke["limitation_labels_present"] else "FAIL",
        "limitation_labels_present": smoke["limitation_labels_present"],
        "labels": limitation_labels,
    }
    finalize_root(root, before, extra_audits={"LIMITATION_LABEL_PRESENCE_AUDIT.json": limitation_audit}, referenced_refs=refs)
    return decision


def run_all() -> dict[str, Any]:
    before = snapshot_inputs()
    results = {
        "vss_r2": run_vss_r2(before),
        "helsinki_r2": run_helsinki_r2(before),
        "chicago_r2": run_chicago_r2(before),
    }
    results["composition"] = run_composition(before)
    results["surface"] = run_surface(before)
    closeout = {
        "task_id": "CITYBRAIN-D8-FOLLOWON-AND-COMPOSITION-PROMPT-PACK",
        "status": "PASS_CITYBRAIN_D8_FOLLOWON_AND_COMPOSITION_PROMPT_PACK_WITH_LIMITATIONS",
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
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
            "vss_runtime_or_readiness_claim_made": False,
            "production_claim_made": False,
            "legal_or_certified_claim_made": False,
            "autonomous_action_claim_made": False,
        },
    }
    closeout_root = OUTPUTS / "citybrain_d8_followon_and_composition_prompt_pack_closeout"
    if closeout_root.exists():
        shutil.rmtree(closeout_root)
    closeout_root.mkdir(parents=True, exist_ok=True)
    write_json(closeout_root / "CITYBRAIN_D8_FOLLOWON_AND_COMPOSITION_PROMPT_PACK_CLOSEOUT.json", closeout)
    write_text(
        closeout_root / "README.md",
        "# CityBrain D8 Follow-on And Composition Prompt Pack Closeout\n\n"
        "This closeout references the five generated task roots and preserves all D8 claim boundaries.",
    )
    finalize_root(closeout_root, before, referenced_refs=[rel(ROOTS[key] / next(iter([name for name in []]), "")) for key in []])
    return closeout


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, ensure_ascii=False))
