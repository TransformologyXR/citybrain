#!/usr/bin/env python3
"""Emit a provenance and gate-label repair overlay for the story arc review."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORY_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1"
DEFAULT_REVIEW_INPUT_ROOT = ROOT / "inputs" / "ai_diagnostic_story_review"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-STORY-ARC-REVIEW-PROVENANCE-GATE-REPAIR-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-story-arc-review-provenance-gate-repair-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_R1_WITH_LIMITATIONS"
WAIT_DECISION = "WAIT_FOR_SECOND_INDEPENDENT_AI_ARTIFACT_REVIEW"

REQUIRED_FILES = [
    "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json",
    "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json",
    "AI_DIAGNOSTIC_REVIEW_PROVENANCE_CONTRACT.json",
    "CONCORDANCE_IMPORT_GUARD_R2.json",
    "CLAUDE_REVIEW_OF_REVIEW_CLASSIFICATION.json",
    "FOUNDER_DIAGNOSTIC_READINESS_AFTER_REPAIR.json",
    "CODEX_CLOSEOUT.md",
    "HASH_MANIFEST.sha256",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def source_hashes(story_root: Path) -> dict[str, str]:
    names = [
        "CROSS_DOMAIN_STORY_ARC_DECISION.json",
        "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json",
        "CROSS_FAMILY_CAUSAL_LINK_LEDGER.json",
        "STORY_ARC_REVIEW_PACKET_360.json",
    ]
    return {name: sha256_file(story_root / name) for name in names if (story_root / name).exists()}


def find_primary_shared_entity(entity_report: dict[str, Any]) -> dict[str, Any]:
    rows = entity_report.get("shared_canonical_entities_with_3plus_families") or entity_report.get("shared_canonical_entities") or []
    rows = sorted(rows, key=lambda row: (-int(row.get("family_count", 0)), row.get("canonical_entity_ref", "")))
    if rows:
        row = rows[0]
        return {
            "ref": row.get("canonical_entity_ref"),
            "family_ids": row.get("family_ids", []),
            "family_span": int(row.get("family_count") or len(row.get("family_ids", []))),
        }
    return {"ref": None, "family_ids": [], "family_span": 0}


def classify_claude_reviews(review_root: Path) -> dict[str, Any]:
    candidates = []
    if review_root.exists():
        for path in sorted(review_root.iterdir()):
            name = path.name.lower()
            if "claude" not in name:
                continue
            if "prompt" in name:
                continue
            if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            payload = read_json(path, {}) if path.suffix.lower() == ".json" else {}
            independent = payload.get("independent_artifact_review")
            review_of_review = payload.get("review_of_review")
            artifact_available = payload.get("artifact_availability_confirmed")

            if independent is None:
                independent = "independent_artifact_review=true" in lower and "review_of_review=true" not in lower
            if review_of_review is None:
                review_of_review = "review_of_review=true" in lower or "review of review" in lower
            if artifact_available is None:
                artifact_available = "artifact availability is confirmed" in lower or "actual story-arc artifacts" in lower

            actual_artifact_pointer = (
                "main-citybrain-cross-domain-story-arc-eval-expansion-r1" in lower
                or "outputs\\main-citybrain-cross-domain-story-arc-eval-expansion-r1" in lower
                or "outputs/main-citybrain-cross-domain-story-arc-eval-expansion-r1" in lower
            )
            absent_signal = (
                "artifacts were absent" in lower
                or "actual artifacts absent" in lower
                or "artifact zip unavailable" in lower
                or "received the ai diagnostic review pack" in lower
            )
            counts = bool(independent is True and review_of_review is False and artifact_available and actual_artifact_pointer and not absent_signal)
            if absent_signal or review_of_review is True or independent is False:
                classification = "review_of_review_not_independent"
                counts = False
            elif counts:
                classification = "independent_artifact_review"
            else:
                classification = "not_countable_as_independent_artifact_review"
                counts = False
            candidates.append(
                {
                    "path": rel(path),
                    "classification": classification,
                    "independent_artifact_review": bool(counts),
                    "review_of_review": bool(review_of_review),
                    "artifact_availability_confirmed": bool(artifact_available),
                    "counts_as_second_independent_ai_review": counts,
                }
            )
    return {
        "artifact_id": "CLAUDE_REVIEW_OF_REVIEW_CLASSIFICATION",
        "review_input_root": rel(review_root),
        "claude_review_file_count": len(candidates),
        "classifications": candidates,
        "true_second_independent_ai_artifact_review_count": sum(
            1 for row in candidates if row["counts_as_second_independent_ai_review"]
        ),
        "status": "NO_CLAUDE_REVIEW_FOUND"
        if not candidates
        else (
            "TRUE_SECOND_INDEPENDENT_AI_ARTIFACT_REVIEW_FOUND"
            if any(row["counts_as_second_independent_ai_review"] for row in candidates)
            else "ONLY_REVIEW_OF_REVIEW_OR_UNCOUNTABLE_CLAUDE_REVIEW_FOUND"
        ),
    }


def build(story_root: Path, review_root: Path, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    before_hashes = source_hashes(story_root)
    decision = read_json(story_root / "CROSS_DOMAIN_STORY_ARC_DECISION.json")
    entity_report = read_json(story_root / "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json")
    primary = find_primary_shared_entity(entity_report)
    shared_count = int(entity_report.get("shared_canonical_entity_count", 0))
    asset_edge = next(
        (
            edge
            for edge in entity_report.get("cross_family_resolution_edges", [])
            if "city_asset_infrastructure_issue" in edge.get("family_ids", [])
            and "mobility_access_interruption_v0" in edge.get("family_ids", [])
        ),
        {},
    )
    asset_link_type = "corridor_context_not_same_entity"
    if asset_edge.get("supports_gate") is True:
        asset_link_type = "same_entity_gate_supporting_edge"

    overlay = {
        "artifact_id": "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY",
        "source_story_arc_id": decision.get("story_arc_id"),
        "source_decision_status": decision.get("status"),
        "deprecated_field": "shared_canonical_entity_3plus_gate_met",
        "deprecated_field_value": decision.get("shared_canonical_entity_3plus_gate_met"),
        "replacement_fields": {
            "shared_canonical_entity_family_span_gate_met": primary["family_span"] >= 3,
            "shared_canonical_entity_family_span_minimum": 3,
            "shared_canonical_entity_family_span": primary["family_span"],
            "shared_canonical_entity_count": shared_count,
            "shared_canonical_entity_refs": [primary["ref"]] if primary["ref"] else [],
            "families_spanned_by_primary_shared_entity": primary["family_ids"],
            "asset_infrastructure_link_type": asset_link_type,
        },
        "overclaim_guard": "Do not read this as three shared entities. It means one shared canonical entity spans three families.",
        "source_refs": [
            rel(story_root / "CROSS_DOMAIN_STORY_ARC_DECISION.json"),
            rel(story_root / "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json"),
        ],
    }

    contract = {
        "artifact_id": "AI_DIAGNOSTIC_REVIEW_PROVENANCE_CONTRACT",
        "independent_review_required_fields": {
            "independent_artifact_review": True,
            "review_of_review": False,
            "artifact_zip_name_or_artifact_root_points_to_actual_story_arc_artifacts": True,
            "artifact_availability_confirmed": True,
            "reviewer_did_not_rely_only_on_chatgpt_summary_or_review_pack": True,
        },
        "not_independent_if": [
            "review_of_review=true",
            "independent_artifact_review=false",
            "actual artifacts absent",
            "review only pressure-tests another review",
            "reviewer used AI diagnostic review pack instead of story-arc artifact pack",
        ],
        "actual_story_arc_artifact_root": rel(story_root),
        "actual_story_arc_required_files": [
            "CROSS_DOMAIN_STORY_ARC_DECISION.json",
            "CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json",
            "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json",
            "STORY_ARC_REVIEW_PACKET_360.json",
            "STORY_ARC_EVAL_EXPANSION_CASES.jsonl",
        ],
    }
    claude = classify_claude_reviews(review_root)
    true_second_count = claude["true_second_independent_ai_artifact_review_count"]
    chatgpt_present = (review_root / "chatgpt_story_review_r1.json").exists()
    concordance_decision = WAIT_DECISION if true_second_count == 0 else "READY_FOR_AI_DIAGNOSTIC_REVIEW_CONCORDANCE_IMPORT"
    guard = {
        "artifact_id": "CONCORDANCE_IMPORT_GUARD_R2",
        "status": "PASS",
        "chatgpt_ai_diagnostic_review_present": chatgpt_present,
        "true_second_independent_ai_artifact_review_count": true_second_count,
        "review_of_review_counts_as_second_review": False,
        "concordance_import_allowed": true_second_count > 0,
        "decision": concordance_decision,
        "reason": "A second independent artifact review is still required before concordance."
        if true_second_count == 0
        else "At least one second independent artifact review is present.",
    }
    founder = {
        "artifact_id": "FOUNDER_DIAGNOSTIC_READINESS_AFTER_REPAIR",
        "status": "WAIT_FOR_SECOND_INDEPENDENT_AI_ARTIFACT_REVIEW",
        "founder_diagnostic_review_allowed": False,
        "founder_product_review_allowed": False,
        "product_review_ready": False,
        "client_ready": False,
        "reason": "Do not advance from review-of-review concordance; import a true second independent artifact review first.",
    }
    after_hashes = source_hashes(story_root)
    repair_decision = {
        "artifact_id": "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION",
        "status": STATUS_PASS,
        "decision": concordance_decision,
        "source_story_arc_id": decision.get("story_arc_id"),
        "source_artifacts_rewritten": before_hashes != after_hashes,
        "source_artifact_hashes_before": before_hashes,
        "source_artifact_hashes_after": after_hashes,
        "shared_canonical_entity_count": shared_count,
        "shared_canonical_entity_family_span": primary["family_span"],
        "shared_canonical_entity_ref": primary["ref"],
        "asset_infrastructure_link_type": asset_link_type,
        "deprecated_field": "shared_canonical_entity_3plus_gate_met",
        "replacement_field": "shared_canonical_entity_family_span_gate_met",
        "true_second_independent_ai_artifact_review_count": true_second_count,
        "product_review_ready": False,
        "client_ready": False,
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "forecast_packet_created": False,
        "source_truth_mutated": False,
        "forbidden_capabilities_created": [],
    }

    write_json(out / "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json", repair_decision)
    write_json(out / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json", overlay)
    write_json(out / "AI_DIAGNOSTIC_REVIEW_PROVENANCE_CONTRACT.json", contract)
    write_json(out / "CONCORDANCE_IMPORT_GUARD_R2.json", guard)
    write_json(out / "CLAUDE_REVIEW_OF_REVIEW_CLASSIFICATION.json", claude)
    write_json(out / "FOUNDER_DIAGNOSTIC_READINESS_AFTER_REPAIR.json", founder)
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Story Arc Review Provenance + Gate Label Repair R1

Status: `{STATUS_PASS}`

- Corrected semantics: one shared canonical entity, `{primary["ref"]}`, spans {primary["family_span"]} families.
- Shared canonical entity count remains `{shared_count}`.
- Asset/infrastructure link type is `{asset_link_type}`.
- Concordance decision is `{concordance_decision}`.

Boundaries: overlay/supersession only; original story artifacts were not rewritten. No founder session result, operator fuel, training rows, ForecastPacket, source-truth mutation, official action/control/enforcement, product/client-ready claim, or founder product review.
""",
    )
    hash_manifest(out)
    copy_publication(out)
    return repair_decision


def hash_manifest(out: Path) -> None:
    rows = []
    for path in sorted(out.iterdir(), key=lambda item: item.name):
        if path.name == "HASH_MANIFEST.sha256" or not path.is_file():
            continue
        rows.append(f"{sha256_file(path)}  {path.name}")
    write_text(out / "HASH_MANIFEST.sha256", "\n".join(rows))


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing manifest: {rel(path)}"]
    errors = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split("  ", 1)
        candidate = path.parent / name
        if not candidate.exists():
            errors.append(f"manifest target missing: {name}")
        elif sha256_file(candidate) != expected:
            errors.append(f"manifest mismatch: {name}")
    return errors


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            shutil.copy2(path, PUBLICATION_ROOT / path.name)


def validate(out: Path) -> list[str]:
    errors = []
    for path in required_paths(out):
        if not path.exists():
            errors.append(f"missing required artifact: {path.name}")
            continue
        if path.suffix == ".json":
            try:
                read_json(path)
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors.append(f"json parse failed: {path.name}: {exc}")
    if errors:
        return errors
    decision = read_json(out / "STORY_ARC_REVIEW_PROVENANCE_GATE_REPAIR_DECISION.json")
    overlay = read_json(out / "CROSS_DOMAIN_SHARED_ENTITY_SEMANTICS_OVERLAY.json")
    contract = read_json(out / "AI_DIAGNOSTIC_REVIEW_PROVENANCE_CONTRACT.json")
    guard = read_json(out / "CONCORDANCE_IMPORT_GUARD_R2.json")
    founder = read_json(out / "FOUNDER_DIAGNOSTIC_READINESS_AFTER_REPAIR.json")
    claude = read_json(out / "CLAUDE_REVIEW_OF_REVIEW_CLASSIFICATION.json")
    fields = overlay.get("replacement_fields", {})
    if decision.get("status") != STATUS_PASS:
        errors.append("unexpected decision status")
    if decision.get("source_artifacts_rewritten") is not False:
        errors.append("source artifacts were rewritten")
    if overlay.get("deprecated_field") != "shared_canonical_entity_3plus_gate_met":
        errors.append("missing deprecated field marker")
    if fields.get("shared_canonical_entity_family_span_gate_met") is not True:
        errors.append("family span gate not true")
    if fields.get("shared_canonical_entity_family_span") != 3:
        errors.append("family span is not 3")
    if fields.get("shared_canonical_entity_count") != 1:
        errors.append("shared canonical entity count is not 1")
    if fields.get("shared_canonical_entity_refs") != ["cer:building:alpha"]:
        errors.append("shared entity ref mismatch")
    if fields.get("asset_infrastructure_link_type") != "corridor_context_not_same_entity":
        errors.append("asset link type mismatch")
    if contract.get("independent_review_required_fields", {}).get("review_of_review") is not False:
        errors.append("contract does not reject review_of_review")
    if guard.get("review_of_review_counts_as_second_review") is not False:
        errors.append("concordance guard counts review-of-review")
    if guard.get("decision") != WAIT_DECISION:
        errors.append("guard did not wait for second independent review")
    if founder.get("founder_product_review_allowed") or founder.get("product_review_ready") or founder.get("client_ready"):
        errors.append("founder/product/client review incorrectly opened")
    if claude.get("true_second_independent_ai_artifact_review_count", 0) != 0:
        errors.append("unexpected true second independent review count")
    if decision.get("operator_fuel_created") or decision.get("training_rows_created") or decision.get("forecast_packet_created") or decision.get("source_truth_mutated"):
        errors.append("forbidden capability guard failed")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-root", type=Path, default=DEFAULT_STORY_ROOT)
    parser.add_argument("--review-input-root", type=Path, default=DEFAULT_REVIEW_INPUT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        decision = build(args.story_root, args.review_input_root, args.out)
        print(decision["status"])
    errors = validate(args.out)
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
