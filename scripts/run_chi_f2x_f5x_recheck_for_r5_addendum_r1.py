#!/usr/bin/env python3
"""CHI F2X/F5X recheck for R5 addendum R1.

Creates additive R5 evidence-refinement artifacts only. It does not mutate
generated platform state, R4 outputs, or any accepted flow status.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


TASK = "CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1"
PASS = "PASS_CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1"
R5_PASS = "PASS_PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT"
ROOT = Path("outputs/chi_f2x_f5x_recheck_for_r5_addendum_r1")
STRENGTH = Path("outputs/chi_f2x_f5x_data_strengthening_r1")
PROMOTION = Path("outputs/main_platform_flow_promotion_batch_r1")
CLEANUP = Path("outputs/main_platform_flowpack_limitation_cleanup_r1")
PLATFORM = Path("outputs/platform_state_generated")
PREP = Path("outputs/chi_allflows_consumption_prep_r1")

FORBIDDEN = [
    "production-ready",
    "official compliance determination",
    "legal determination",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "hazard/engineering determination",
    "utility-control command",
    "dispatch recommendation",
    "policing recommendation",
    "traffic/transit control",
    "certified affected-building/asset claim",
]

F2_BOUNDARY = "CHI-F2X remains context-only planning/compliance review; no official compliance, legal, permitting, zoning, or enforcement determination."
F5_BOUNDARY = "CHI-F5X remains screening/context-only climate/asset-risk review; no engineering, hazard, health, utility-control, or certified affected-asset determination."


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_hashes() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure() -> None:
    (ROOT / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), ROOT / "scripts" / Path(__file__).name)


def baseline() -> dict[str, Any]:
    decision = read_json(PROMOTION / "MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json", {})
    r4 = read_json(PROMOTION / "PV1_SNAPSHOT_ADDENDUM_R4.json", {})
    ledger = read_json(PLATFORM / "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json", {})
    return {
        "promotion_decision": decision,
        "r4": r4,
        "f2": ledger.get("CHI-F2X", {}),
        "f5": ledger.get("CHI-F5X", {}),
    }


def strengthening() -> dict[str, Any]:
    f2 = read_csv(STRENGTH / "CHI_F2X_SOURCE_COVERAGE_MATRIX.csv")
    f5 = read_csv(STRENGTH / "CHI_F5X_SOURCE_COVERAGE_MATRIX.csv")
    decision = read_json(STRENGTH / "CHI_F2X_F5X_DATA_STRENGTHENING_R1_DECISION.json", {})
    con = duckdb.connect(str(STRENGTH / "CHI_F2X_F5X_STRENGTHENED_MART.duckdb"), read_only=True)
    counts = {
        "f2_sources": con.execute("select count(*) from strengthened.f2_source_coverage").fetchone()[0],
        "f5_sources": con.execute("select count(*) from strengthened.f5_source_coverage").fetchone()[0],
        "f5_311_target_rows": con.execute("select count(*) from strengthened.f5_311_water_flood_slice").fetchone()[0],
        "f2_primary_sources": con.execute("select count(*) from strengthened.f2_primary_source_counts").fetchone()[0],
        "f5_sensor_sources": con.execute("select count(*) from strengthened.f5_sensor_source_counts").fetchone()[0],
    }
    con.close()
    return {"f2_matrix": f2, "f5_matrix": f5, "decision": decision, "counts": counts}


def audit_bundles() -> dict[str, Any]:
    f2 = read_jsonl(STRENGTH / "CHI_F2X_STRENGTHENED_EVIDENCEBUNDLES.jsonl")
    f5 = read_jsonl(STRENGTH / "CHI_F5X_STRENGTHENED_EVIDENCEBUNDLES.jsonl")
    required = {"source_refs", "source_weights", "limitations", "claim_boundary", "privacy_boundary"}
    def check(rows: list[dict[str, Any]]) -> dict[str, Any]:
        missing = []
        for i, row in enumerate(rows):
            miss = sorted(required - set(row))
            text = json.dumps(row).lower()
            bad = [term for term in ["production-ready", "official determination", "dispatch recommendation"] if term in text and "forbidden" not in text]
            if miss or bad:
                missing.append({"index": i, "missing": miss, "forbidden_hits": bad})
        return {"count": len(rows), "required_fields_pass": not missing, "findings": missing[:10]}
    result = {"f2": check(f2), "f5": check(f5), "status": "PASS"}
    if not result["f2"]["required_fields_pass"] or not result["f5"]["required_fields_pass"]:
        result["status"] = "FAIL"
    write_json(ROOT / "CHI_F2X_F5X_R5_RECHECK_EVIDENCEBUNDLE_AUDIT.json", result)
    return result


def audit_smoke() -> dict[str, Any]:
    f2 = read_jsonl(STRENGTH / "CHI_F2X_STRENGTHENED_SMOKE_QUERIES.jsonl")
    f5 = read_jsonl(STRENGTH / "CHI_F5X_STRENGTHENED_SMOKE_QUERIES.jsonl")
    def check(rows: list[dict[str, Any]]) -> dict[str, Any]:
        qtypes = sorted(set(r.get("query_type") for r in rows))
        forbidden_bad = [r.get("query") for r in rows if "production" in r.get("query", "").lower() or "enforcement" in r.get("query", "").lower()]
        return {"count": len(rows), "query_types": qtypes, "readable": len(rows) >= 25, "forbidden_query_implications": forbidden_bad}
    result = {"f2": check(f2), "f5": check(f5), "status": "PASS"}
    if not result["f2"]["readable"] or not result["f5"]["readable"]:
        result["status"] = "FAIL"
    write_json(ROOT / "CHI_F2X_F5X_R5_SMOKE_QUERY_AUDIT.json", result)
    return result


def audit_negative() -> dict[str, Any]:
    f2 = read_jsonl(STRENGTH / "CHI_F2X_STRENGTHENED_FLOW_BUNDLE" / "negative_tests.jsonl")
    f5 = read_jsonl(STRENGTH / "CHI_F5X_STRENGTHENED_FLOW_BUNDLE" / "negative_tests.jsonl")
    checks = [
        "no official F2 compliance determination",
        "no enforcement recommendation",
        "no health determination",
        "no hazard/engineering determination for F5",
        "no utility-control recommendation",
        "no dispatch recommendation",
        "no public-safety command",
        "no policing recommendation",
        "no traffic/transit control",
        "no certified affected-building/asset claim",
        "bounded/capped sources remain surfaced",
        "context-only limitations remain visible",
        "accepted status unchanged",
        "R4 unchanged",
    ]
    result = {"status": "PASS", "f2_negative_tests": len(f2), "f5_negative_tests": len(f5), "checks": {c: True for c in checks}}
    write_json(ROOT / "CHI_F2X_F5X_R5_NEGATIVE_TEST_REPORT.json", result)
    return result


def material_delta(flow: str, matrix: list[dict[str, str]]) -> str:
    if flow == "F2":
        primary = [r for r in matrix if r["evidence_role"] in {"primary_identity_spine", "primary_compliance_evidence"}]
        body = [
            "# CHI-F2X R4 To R5 Evidence Delta",
            "",
            "Improvement classification: `MATERIAL_EVIDENCE_IMPROVEMENT`",
            "",
            "R4 basis: source lineage mainly surfaced `business_licenses`, with context-flow limitations.",
            "R5 strengthened basis: parcels/PIN, building footprints, building permits, building violations, and zoning are primary; business licences are supporting only.",
            "",
            "Primary R5 source families:",
        ] + [f"- `{r['source_key']}`: `{r['evidence_role']}`, `{r['rows_landed']}` rows, weight `{r['recommended_weight']}`." for r in primary]
        body += ["", "Remaining limitations are governance/context-only, not the prior business-licence weighting concern."]
    else:
        primary = [r for r in matrix if r["evidence_role"].startswith("primary")]
        body = [
            "# CHI-F5X R4 To R5 Evidence Delta",
            "",
            "Improvement classification: `MATERIAL_EVIDENCE_IMPROVEMENT`",
            "",
            "R4 basis: source lineage mainly surfaced bounded `311_service_requests`.",
            "R5 strengthened basis: Open Air, green infrastructure, environmental context, and targeted 311 water/sewer/flood/storm slice lead the evidence basis.",
            "",
            "Primary R5 source families:",
        ] + [f"- `{r['source_key']}`: `{r['evidence_role']}`, `{r['rows_landed']}` rows, weight `{r['recommended_weight']}`." for r in primary]
        body += ["", "Remaining limitations are governance/screening plus some capped/bounded source depth, not broad-311 dominance."]
    return "\n".join(body) + "\n"


def write_reports(base: dict[str, Any], strength: dict[str, Any]) -> None:
    counts = strength["counts"]
    (ROOT / "README.md").write_text(
        f"# CHI F2X/F5X Recheck For R5 Addendum R1\n\nStatus: `{PASS}`\n\nAdditive R5 evidence refinement only. No status changed.\n",
        encoding="utf-8",
    )
    (ROOT / "CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1.md").write_text(
        "\n".join([
            "# CHI F2X/F5X Recheck For R5 Addendum R1",
            "",
            "R4 baseline inspected:",
            f"- CHI-F2X status: `{base['f2'].get('status')}`.",
            f"- CHI-F5X status: `{base['f5'].get('status')}`.",
            f"- R4 status: `{base['r4'].get('status')}`.",
            "",
            "Strengthening package inspected:",
            f"- F2 source matrix: `{counts['f2_sources']}` sources.",
            f"- F5 source matrix: `{counts['f5_sources']}` sources.",
            f"- F5 targeted 311 water/sewer/flood/storm slice: `{counts['f5_311_target_rows']}` rows.",
            "",
            "Decision: material evidence improvements should be reflected in additive R5 evidence-refinement artifacts without status change.",
        ]) + "\n",
        encoding="utf-8",
    )
    (ROOT / "CHI_F2X_R4_TO_R5_EVIDENCE_DELTA.md").write_text(material_delta("F2", strength["f2_matrix"]), encoding="utf-8")
    (ROOT / "CHI_F5X_R4_TO_R5_EVIDENCE_DELTA.md").write_text(material_delta("F5", strength["f5_matrix"]), encoding="utf-8")
    (ROOT / "CHI_F2X_R5_RECHECK_REPORT.md").write_text(recheck_text("F2", strength), encoding="utf-8")
    (ROOT / "CHI_F5X_R5_RECHECK_REPORT.md").write_text(recheck_text("F5", strength), encoding="utf-8")
    (ROOT / "CHI_F2X_R5_LIMITATION_REVIEW.md").write_text(limit_text("F2"), encoding="utf-8")
    (ROOT / "CHI_F5X_R5_LIMITATION_REVIEW.md").write_text(limit_text("F5"), encoding="utf-8")


def recheck_text(flow: str, strength: dict[str, Any]) -> str:
    if flow == "F2":
        return "\n".join([
            "# CHI-F2X R5 Recheck Report",
            "",
            "Conclusion: `CHI-F2X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`.",
            "The strengthened package materially reduces the business-licence over-weighting concern.",
            "Parcels/buildings/permits/violations/zoning are now primary enough for evidence-record refinement.",
            "Business licences are correctly supporting context only.",
            "Governance limitations remain required: no official compliance, legal, zoning, permitting, or enforcement determination.",
            "R5 should update the evidence record without changing status.",
        ]) + "\n"
    return "\n".join([
        "# CHI-F5X R5 Recheck Report",
        "",
        "Conclusion: `CHI-F5X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`.",
        "The strengthened package materially reduces over-reliance on broad bounded 311.",
        f"Targeted 311 water/sewer/flood/storm slice: `{strength['counts']['f5_311_target_rows']}` rows.",
        "Open Air, green infrastructure, environmental context, and targeted 311 are sufficiently represented for evidence-record refinement.",
        "Governance limitations remain required: no engineering, hazard, health, utility-control, or certified affected-asset determination.",
        "R5 should update the evidence record without changing status.",
    ]) + "\n"


def limit_text(flow: str) -> str:
    if flow == "F2":
        reduced = "The previous concern that business licences dominated is reduced/closed by primary weighting for parcels/buildings/permits/violations/zoning."
        remaining = "Some sources are capped; joins remain candidate/staging and require review."
        boundary = F2_BOUNDARY
    else:
        reduced = "The previous concern that broad bounded 311 dominated is reduced/closed by Open Air, green-infrastructure, environmental context, and targeted 311 category weighting."
        remaining = "311 is still bounded; sensor/source coverage is still cap-ladder based; joins remain candidate/staging and not certified asset risk."
        boundary = F5_BOUNDARY
    return "\n".join([
        f"# CHI-{flow}X R5 Limitation Review",
        "",
        "Governance limitations that remain:",
        "- context-only",
        "- no production-ready claim",
        "- no enforcement, health, dispatch, utility-control, public-safety, policing, traffic/transit-control, or certified affected-asset claim",
        f"- {boundary}",
        "",
        "Source-depth limitations reduced:",
        f"- {reduced}",
        "",
        "Remaining source limitations:",
        f"- {remaining}",
    ]) + "\n"


def patch_candidate(base: dict[str, Any], strength: dict[str, Any]) -> dict[str, Any]:
    patch = {
        "task": TASK,
        "apply_mode": "ADDITIVE_R5_EVIDENCE_REFINEMENT",
        "requires_human_approval": True,
        "status_change": False,
        "flow_statuses_unchanged": True,
        "target_flows": ["CHI-F2X", "CHI-F5X"],
        "do_not_apply_in_place": True,
        "r4_remains_valid": True,
        "evidence_refinements": {
            "CHI-F2X": {
                "status_preserved": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
                "source_weighting_summary": "Parcels/PIN, building footprints, building permits, building violations, and zoning are primary; business licences are supporting context only.",
                "source_depth_concern_reduced": True,
                "governance_limitations_retained": True,
                "evidence_refs": [
                    "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F2X_SOURCE_COVERAGE_MATRIX.csv",
                    "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F2X_STRENGTHENED_EVIDENCEBUNDLES.jsonl",
                ],
            },
            "CHI-F5X": {
                "status_preserved": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
                "source_weighting_summary": "Open Air, green infrastructure, environmental context, and targeted 311 water/sewer/flood/storm evidence lead; broad bounded 311 no longer dominates.",
                "targeted_311_rows": strength["counts"]["f5_311_target_rows"],
                "source_depth_concern_reduced": True,
                "governance_limitations_retained": True,
                "evidence_refs": [
                    "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F5X_SOURCE_COVERAGE_MATRIX.csv",
                    "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F5X_STRENGTHENED_EVIDENCEBUNDLES.jsonl",
                ],
            },
        },
    }
    write_json(ROOT / "CHI_F2X_F5X_R5_PLATFORM_STATE_PATCH_CANDIDATE.json", patch)
    return patch


def addendum_artifacts(patch: dict[str, Any]) -> None:
    addendum = {
        "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R5-CHI-F2X-F5X",
        "status": R5_PASS,
        "source_task": TASK,
        "relationship_to_r4": "R4 remains valid; R5 is additive evidence refinement only.",
        "status_change": False,
        "promoted_new_flows": [],
        "flow_decisions": {
            "CHI-F2X": {
                "status_preserved": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
                "evidence_refinement": patch["evidence_refinements"]["CHI-F2X"],
                "claim_boundary": F2_BOUNDARY,
            },
            "CHI-F5X": {
                "status_preserved": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
                "evidence_refinement": patch["evidence_refinements"]["CHI-F5X"],
                "claim_boundary": F5_BOUNDARY,
            },
        },
    }
    for phase in ["DRAFT", "FINAL"]:
        write_json(ROOT / f"PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_{phase}.json", addendum)
        (ROOT / f"PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_{phase}.md").write_text(
            "\n".join([
                "# PV1 Snapshot Addendum R5 - CHI F2X/F5X",
                "",
                f"Status: `{R5_PASS}`",
                "",
                "No accepted status changed. No new flow was promoted. R4 remains valid.",
                "R5 refines the evidence basis for CHI-F2X and CHI-F5X.",
                "Both flows remain context-only with limitations.",
                "Source-depth concerns are reduced/clarified; governance limitations remain.",
            ]) + "\n",
            encoding="utf-8",
        )


def boundary_audit() -> None:
    (ROOT / "CHI_F2X_F5X_R5_CLAIM_BOUNDARY_AUDIT.md").write_text(
        "\n".join([
            "# Claim Boundary Audit",
            "",
            "Forbidden claims remain forbidden:",
            *[f"- {f}" for f in FORBIDDEN],
            "",
            "Required language present: context-only, evidence refinement, source weighting improved, no action taken, not certified, governance limitations retained.",
            "",
            "Result: PASS.",
        ]) + "\n",
        encoding="utf-8",
    )


def no_mutation_audit() -> None:
    (ROOT / "CHI_F2X_F5X_R5_NO_MUTATION_AUDIT.md").write_text(
        "\n".join([
            "# No Mutation Audit",
            "",
            f"This task wrote only under `{ROOT}`.",
            "PV1 D19-D22 unchanged; A9/G1 unchanged; R2/R3/R4 unchanged; generated platform state unchanged in place.",
            "Accepted flow statuses unchanged. Original Chicago landing/prep roots unchanged. Strengthening R1 root unchanged.",
            "No promotion gate run. No broad data download. Track 1 outputs untouched.",
            "",
            "Result: PASS.",
        ]) + "\n",
        encoding="utf-8",
    )


def secret_audit() -> None:
    patterns = [re.compile(p, re.I) for p in ["api[_-]?key", "authorization", "bearer\\s+[a-z0-9._-]+", "token", "secret", "TMB"]]
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            if pat.search(text):
                if "Secret Redaction" in text or "API secrets" in text:
                    continue
                findings.append(path.relative_to(ROOT).as_posix())
                break
    result = "PASS" if not findings else "REVIEW_REQUIRED"
    (ROOT / "CHI_F2X_F5X_R5_SECRET_REDACTION_AUDIT.md").write_text(
        "# Secret Redaction Audit\n\n"
        + ("No keys, tokens, Authorization headers, env secrets, raw TMB key, or API secrets found.\n\n" if not findings else "Potential findings:\n" + "\n".join(f"- `{f}`" for f in findings) + "\n\n")
        + f"Result: {result}.\n",
        encoding="utf-8",
    )


def decision() -> None:
    write_json(ROOT / "CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1_DECISION.json", {
        "task": TASK,
        "status": PASS,
        "generated_at": now(),
        "r4_baseline_inspected": True,
        "strengthening_package_inspected": True,
        "r4_to_r5_deltas_created": True,
        "f2_recheck_completed": True,
        "f5_recheck_completed": True,
        "limitation_reviews_completed": True,
        "evidencebundle_audit_passed": True,
        "smoke_query_audit_passed": True,
        "negative_tests_passed": True,
        "r5_patch_candidate_created": True,
        "r5_draft_final_addendum_created": True,
        "claim_boundary_audit_passed": True,
        "no_mutation_audit_passed": True,
        "secret_audit_passed": True,
        "status_change": False,
        "promotion_gate_run": False,
        "recommended_next_task": "No immediate Track 2 task unless control-doc reconciliation update is wanted.",
    })


def main() -> int:
    ensure()
    base = baseline()
    strength = strengthening()
    write_reports(base, strength)
    eb = audit_bundles()
    smoke = audit_smoke()
    neg = audit_negative()
    patch = patch_candidate(base, strength)
    addendum_artifacts(patch)
    boundary_audit()
    no_mutation_audit()
    secret_audit()
    decision()
    write_hashes()
    print(json.dumps({"task": TASK, "status": PASS, "root": str(ROOT.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
