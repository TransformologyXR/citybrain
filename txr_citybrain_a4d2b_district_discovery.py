from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped "
    "depending on the local harvest status. The prep report records row counts, caps, and source "
    "chunks used. Discovery counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

AS_OF_DATE = "2026-06-25"
HERO_BLOCK_KEY = "1-01060"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _json_default(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprints(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            out[str(path)] = _sha256(path)
    return out


def _canonical_guard_paths(repo: Path) -> list[Path]:
    return [
        repo / "txr_citybrain_schema_v1.py",
        repo / "outputs" / "a5_dob_district_enrichment" / "canonical_entities.parquet",
        repo / "outputs" / "a5_dob_district_enrichment" / "canonical_edges.parquet",
        repo / "outputs" / "a5_dob_district_enrichment" / "graph_projection_nodes.parquet",
        repo / "outputs" / "a5_dob_district_enrichment" / "graph_projection_edges.parquet",
        repo / "outputs" / "a5_dob_district_enrichment" / "snapshot" / "a5_district_v1.json",
    ]


def _clean_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_category_mix(value: Any) -> dict[str, int]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return {str(k): _safe_int(v) for k, v in parsed.items()}


def _top_categories(value: Any, limit: int = 5) -> list[dict[str, Any]]:
    mix = _parse_category_mix(value)
    return [
        {"category_code": code, "count": count}
        for code, count in sorted(mix.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    ]


def _load_prep_summary(prep_output_dir: Path) -> dict[str, Any]:
    summary_path = prep_output_dir / "harvest_prep_summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    return {}


def _score_blocks(blocks: pd.DataFrame) -> pd.DataFrame:
    df = blocks.copy()
    numeric_columns = [
        "parcel_count",
        "building_count",
        "parcels_with_any_dob_activity",
        "dob_now_filing_count",
        "dob_permit_issuance_count",
        "dob_complaint_count",
        "unique_job_count",
        "critical_complaint_count",
        "exact_bin_complaint_count",
        "unresolved_bin_complaint_count",
        "unique_bins_involved",
        "unique_contractors_or_license_parties",
        "unique_license_parties",
        "business_name_only_party_count",
        "activity_span_years",
    ]
    for col in numeric_columns:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    latest = pd.to_datetime(df.get("latest_activity_date"), errors="coerce")
    as_of = pd.Timestamp(AS_OF_DATE)
    years_since_latest = (as_of - latest).dt.days / 365.25
    years_since_latest = years_since_latest.where(years_since_latest >= 0, 0).fillna(99)

    permit_norm = (
        df["unique_job_count"].map(math.log1p)
        + 0.5 * df["dob_now_filing_count"].map(math.log1p)
        + 0.5 * df["dob_permit_issuance_count"].map(math.log1p)
    )
    complaint_norm = df["dob_complaint_count"].map(math.log1p) + 1.5 * df[
        "critical_complaint_count"
    ].map(math.log1p)
    activity_share = (
        df["parcels_with_any_dob_activity"] / df["parcel_count"].where(df["parcel_count"] > 0, 1)
    ).clip(0, 1)
    party_norm = df["unique_contractors_or_license_parties"].map(math.log1p)
    recency_bonus = (5.0 - years_since_latest).clip(lower=0, upper=5)

    denominator = permit_norm.where(permit_norm > complaint_norm, complaint_norm)
    diversity_balance = (permit_norm.where(permit_norm < complaint_norm, complaint_norm) / denominator).fillna(0)
    diversity_balance = diversity_balance.where((permit_norm > 0) & (complaint_norm > 0), 0).clip(0, 1)

    df["permit_activity_score"] = permit_norm.round(6)
    df["complaint_activity_score"] = complaint_norm.round(6)
    df["parcel_activity_share"] = activity_share.round(6)
    df["party_activity_score"] = party_norm.round(6)
    df["recency_bonus"] = recency_bonus.round(6)
    df["diversity_balance"] = diversity_balance.round(6)

    base_score = 2.0 * permit_norm + 3.0 * complaint_norm + 2.0 * activity_share + party_norm + recency_bonus
    df["balanced_discovery_score"] = (base_score * (0.5 + 0.5 * diversity_balance)).round(6)
    df["permit_heavy_score"] = (2.5 * permit_norm + 0.75 * activity_share + party_norm + recency_bonus).round(6)
    df["complaint_heavy_score"] = (3.5 * complaint_norm + 0.75 * activity_share + recency_bonus).round(6)
    df["critical_complaint_score"] = (
        5.0 * df["critical_complaint_count"].map(math.log1p) + complaint_norm + recency_bonus
    ).round(6)
    df["recent_activity_score"] = (
        recency_bonus
        + (df["unique_job_count"] + df["dob_complaint_count"]).map(math.log1p)
        + 0.5 * activity_share
    ).round(6)

    df["now_to_issuance_ratio"] = (
        df["dob_now_filing_count"] / (df["dob_permit_issuance_count"] + 1)
    ).round(6)
    df["complaint_to_job_ratio"] = (df["dob_complaint_count"] / (df["unique_job_count"] + 1)).round(6)
    df["critical_complaint_share"] = (
        df["critical_complaint_count"] / df["dob_complaint_count"].where(df["dob_complaint_count"] > 0, 1)
    ).round(6)
    df["exact_bin_complaint_rate"] = (
        df["exact_bin_complaint_count"] / df["dob_complaint_count"].where(df["dob_complaint_count"] > 0, 1)
    ).round(6)
    df["unresolved_bin_complaint_rate"] = (
        df["unresolved_bin_complaint_count"]
        / (df["dob_complaint_count"] + df["unresolved_bin_complaint_count"]).where(
            (df["dob_complaint_count"] + df["unresolved_bin_complaint_count"]) > 0,
            1,
        )
    ).round(6)
    df["license_to_name_hash_party_ratio"] = (
        df["unique_license_parties"] / (df["business_name_only_party_count"] + 1)
    ).round(6)
    df["jobs_per_active_parcel"] = (
        df["unique_job_count"] / df["parcels_with_any_dob_activity"].where(
            df["parcels_with_any_dob_activity"] > 0, 1
        )
    ).round(6)

    hero = df[df["block_key"].astype(str) == HERO_BLOCK_KEY]
    vector_cols = [
        "parcel_activity_share",
        "now_to_issuance_ratio",
        "complaint_to_job_ratio",
        "critical_complaint_share",
        "exact_bin_complaint_rate",
        "license_to_name_hash_party_ratio",
        "jobs_per_active_parcel",
    ]
    if not hero.empty:
        hero_vec = hero.iloc[0][vector_cols]
        diffs = []
        for _, row in df.iterrows():
            diff = 0.0
            for col in vector_cols:
                hv = _safe_float(hero_vec[col])
                rv = _safe_float(row[col])
                scale = max(abs(hv), abs(rv), 1.0)
                diff += abs(rv - hv) / scale
            diffs.append(round(diff, 6))
        df["hero_shape_distance"] = diffs
        df["hero_shape_similarity"] = (1 / (1 + df["hero_shape_distance"])).round(6)
    else:
        df["hero_shape_distance"] = None
        df["hero_shape_similarity"] = None

    def classify(row: pd.Series) -> str:
        permit = _safe_float(row["permit_activity_score"])
        complaint = _safe_float(row["complaint_activity_score"])
        critical = _safe_int(row["critical_complaint_count"])
        if permit > 0 and complaint > 0 and _safe_float(row["diversity_balance"]) >= 0.55:
            return "balanced_compliance"
        if critical >= 10:
            return "critical_complaint_specialist"
        if permit >= complaint * 1.8 and permit > 0:
            return "permit_heavy"
        if complaint >= permit * 1.8 and complaint > 0:
            return "complaint_heavy"
        if permit > 0 or complaint > 0:
            return "mixed_activity"
        return "low_or_no_dob_activity"

    df["candidate_family"] = df.apply(classify, axis=1)
    df["top_complaint_categories"] = df["complaint_category_mix"].map(_top_categories)
    return df


def _record(row: pd.Series, include_mix: bool = True) -> dict[str, Any]:
    keys = [
        "block_key",
        "borough_code",
        "block",
        "parcel_count",
        "building_count",
        "parcels_with_any_dob_activity",
        "dob_now_filing_count",
        "dob_permit_issuance_count",
        "dob_complaint_count",
        "unique_job_count",
        "critical_complaint_count",
        "exact_bin_complaint_count",
        "unresolved_bin_complaint_count",
        "unique_bins_involved",
        "unique_contractors_or_license_parties",
        "unique_license_parties",
        "business_name_only_party_count",
        "latest_activity_date",
        "earliest_activity_date",
        "activity_span_years",
        "permit_activity_score",
        "complaint_activity_score",
        "parcel_activity_share",
        "party_activity_score",
        "recency_bonus",
        "diversity_balance",
        "balanced_discovery_score",
        "permit_heavy_score",
        "complaint_heavy_score",
        "critical_complaint_score",
        "recent_activity_score",
        "now_to_issuance_ratio",
        "complaint_to_job_ratio",
        "critical_complaint_share",
        "exact_bin_complaint_rate",
        "unresolved_bin_complaint_rate",
        "license_to_name_hash_party_ratio",
        "jobs_per_active_parcel",
        "hero_shape_distance",
        "hero_shape_similarity",
        "candidate_family",
        "top_complaint_categories",
    ]
    out = {key: row.get(key) for key in keys if key in row.index}
    if include_mix:
        out["complaint_category_mix"] = _parse_category_mix(row.get("complaint_category_mix"))
    out["boundary_statement"] = BOUNDARY_STATEMENT
    return out


def _select_records(df: pd.DataFrame, mask: pd.Series, sort_col: str, limit: int = 10) -> list[dict[str, Any]]:
    selected = df[mask].sort_values(sort_col, ascending=False).head(limit)
    return [_record(row) for _, row in selected.iterrows()]


def _candidate_districts(scored: pd.DataFrame) -> dict[str, Any]:
    active = scored[
        (scored["dob_now_filing_count"] + scored["dob_permit_issuance_count"] + scored["dob_complaint_count"]) > 0
    ]
    both = active[(active["unique_job_count"] > 0) & (active["dob_complaint_count"] > 0)]
    permit_heavy = active[active["permit_activity_score"] >= active["complaint_activity_score"] * 1.8]
    complaint_heavy = active[active["complaint_activity_score"] >= active["permit_activity_score"] * 1.8]
    critical = active[active["critical_complaint_count"] > 0]
    recent = active[pd.to_datetime(active["latest_activity_date"], errors="coerce") >= pd.Timestamp("2025-01-01")]
    fallback_problematic = active[
        ((active["dob_complaint_count"] > 0) & (active["unique_job_count"] == 0))
        | (active["exact_bin_complaint_rate"] < 0.95)
        | (active["unresolved_bin_complaint_rate"] > 0)
    ]

    complementary = both[both["block_key"].astype(str) != HERO_BLOCK_KEY].copy()
    if not complementary.empty:
        max_bal = complementary["balanced_discovery_score"].max() or 1
        max_dist = complementary["hero_shape_distance"].max() or 1
        complementary["complementary_score"] = (
            (complementary["balanced_discovery_score"] / max_bal)
            + (complementary["hero_shape_distance"].fillna(0) / max_dist)
        ).round(6)
    else:
        complementary["complementary_score"] = []

    similar = both[both["block_key"].astype(str) != HERO_BLOCK_KEY].copy()
    if not similar.empty:
        similar["similarity_rank_score"] = (
            similar["hero_shape_similarity"].fillna(0) * 0.7
            + (similar["balanced_discovery_score"] / (similar["balanced_discovery_score"].max() or 1)) * 0.3
        ).round(6)
    else:
        similar["similarity_rank_score"] = []

    return {
        "boundary_statement": BOUNDARY_STATEMENT,
        "selection_method": {
            "balanced_compliance_blocks": "both permit/job and complaint activity, ranked by balanced_discovery_score",
            "hero_complementary_blocks": "high activity blocks with shapes unlike MN block 1060",
            "hero_similar_blocks": "high activity blocks with shapes similar to MN block 1060",
            "permit_heavy_blocks": "permit/job activity dominates complaint activity",
            "complaint_heavy_blocks": "complaint activity dominates permit/job activity",
            "critical_complaint_blocks": "blocks with category-91 or other critical complaint volume",
            "recent_activity_blocks": "blocks with harvested activity during or after 2025-01-01",
            "fallback_problematic_blocks": "complaint-only or lower-resolution complaint attachment blocks worth QA review",
        },
        "balanced_compliance_blocks": _select_records(both, both["diversity_balance"] >= 0.55, "balanced_discovery_score", 10),
        "hero_complementary_blocks": [
            _record(row)
            for _, row in complementary.sort_values("complementary_score", ascending=False).head(10).iterrows()
        ],
        "hero_similar_blocks": [
            _record(row)
            for _, row in similar.sort_values("similarity_rank_score", ascending=False).head(10).iterrows()
        ],
        "permit_heavy_blocks": _select_records(permit_heavy, permit_heavy.index == permit_heavy.index, "permit_heavy_score", 10),
        "complaint_heavy_blocks": _select_records(
            complaint_heavy, complaint_heavy.index == complaint_heavy.index, "complaint_heavy_score", 10
        ),
        "critical_complaint_blocks": _select_records(critical, critical.index == critical.index, "critical_complaint_score", 10),
        "recent_activity_blocks": _select_records(recent, recent.index == recent.index, "recent_activity_score", 10),
        "fallback_problematic_blocks": _select_records(
            fallback_problematic, fallback_problematic.index == fallback_problematic.index, "complaint_heavy_score", 10
        ),
    }


def _hero_comparison(scored: pd.DataFrame, top: pd.DataFrame) -> dict[str, Any]:
    hero_df = scored[scored["block_key"].astype(str) == HERO_BLOCK_KEY]
    if hero_df.empty:
        return {
            "status": "FAIL",
            "reason": f"Hero block {HERO_BLOCK_KEY} not present in block_dob_activity_base.parquet",
            "boundary_statement": BOUNDARY_STATEMENT,
        }

    hero = hero_df.iloc[0]
    rank_by_balanced = int((scored["balanced_discovery_score"] > hero["balanced_discovery_score"]).sum() + 1)
    rank_by_jobs = int((scored["unique_job_count"] > hero["unique_job_count"]).sum() + 1)
    rank_by_complaints = int((scored["dob_complaint_count"] > hero["dob_complaint_count"]).sum() + 1)
    comparisons = []
    for _, row in top.head(10).iterrows():
        comparisons.append(
            {
                "candidate_block": row["block_key"],
                "balanced_score_delta_vs_hero": round(
                    _safe_float(row["balanced_discovery_score"]) - _safe_float(hero["balanced_discovery_score"]), 6
                ),
                "unique_job_delta_vs_hero": _safe_int(row["unique_job_count"]) - _safe_int(hero["unique_job_count"]),
                "complaint_delta_vs_hero": _safe_int(row["dob_complaint_count"]) - _safe_int(hero["dob_complaint_count"]),
                "critical_complaint_delta_vs_hero": _safe_int(row["critical_complaint_count"])
                - _safe_int(hero["critical_complaint_count"]),
                "hero_shape_distance": row.get("hero_shape_distance"),
            }
        )

    return {
        "status": "PASS",
        "as_of_date": AS_OF_DATE,
        "baseline_block": HERO_BLOCK_KEY,
        "hero_baseline": _record(hero),
        "hero_ranks": {
            "balanced_discovery_score_rank": rank_by_balanced,
            "unique_job_count_rank": rank_by_jobs,
            "dob_complaint_count_rank": rank_by_complaints,
            "rank_scope": "all blocks in current local harvested NYC prep block base",
        },
        "top_balanced_comparisons": comparisons,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def _write_unresolved_complaints_report(prep_output_dir: Path, output_dir: Path) -> dict[str, Any]:
    source = prep_output_dir / "unresolved_dob_records.csv"
    target = output_dir / "unresolved_complaints_report.csv"
    if not source.exists():
        pd.DataFrame(
            columns=["source_dataset", "source_row_key", "bin_norm", "bbl_norm", "reason", "boundary_statement"]
        ).to_csv(target, index=False)
        return {"status": "WARN", "source": str(source), "complaint_rows": 0, "reason": "prep unresolved report missing"}

    chunks = []
    for chunk in pd.read_csv(source, dtype=str, chunksize=200_000):
        filtered = chunk[chunk["source_dataset"].eq("nyc__dob_complaints_received")].copy()
        if not filtered.empty:
            chunks.append(filtered)
    unresolved = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    if unresolved.empty:
        unresolved = pd.DataFrame(
            columns=["source_dataset", "source_row_key", "bin_norm", "bbl_norm", "reason"]
        )
    unresolved["boundary_statement"] = BOUNDARY_STATEMENT
    unresolved.to_csv(target, index=False)
    reasons = unresolved["reason"].value_counts(dropna=False).to_dict() if "reason" in unresolved.columns else {}
    return {
        "status": "PASS",
        "source": str(source),
        "output": str(target),
        "complaint_rows": int(len(unresolved)),
        "reason_counts": reasons,
    }


def _write_readme(output_dir: Path, report: dict[str, Any]) -> None:
    text = f"""# a4·D2b Data-Driven NYC District Discovery

Status: **{report['status']}**

Boundary: {BOUNDARY_STATEMENT}

This is a data-driven discovery layer over the NYC Harvest Prep v0.2 block staging outputs. It ranks blocks from the current local harvested DOB subset, compares candidates to the MN block 1060 / 425 W 50th baseline, and identifies balanced, complementary, and specialist candidate districts for later canonical district cuts.

This is not a canonical graph mutation, not a new schema, not a citywide graph projection, and not a claim about complete NYC DOB history unless a source dataset is marked full in the prep inventory.

## Inputs

- Prep output directory: `{report['inputs']['prep_output_dir']}`
- Discovery staging directory: `{report['inputs']['staging_dir']}`
- Block base: `{report['inputs']['block_base']}`
- Frozen as-of date: `{AS_OF_DATE}`

## Counts

- Blocks ranked: {report['counts']['blocks_ranked']}
- Active blocks: {report['counts']['active_blocks']}
- Blocks with both DOB permit/job and complaint activity: {report['counts']['blocks_with_permits_and_complaints']}
- Top candidates emitted: {report['counts']['top_25_count']}
- Hero baseline present: {report['counts']['hero_baseline_present']}
- Unresolved complaint rows reported: {report['counts']['unresolved_complaint_rows']}

## Candidate Families

The discovery report emits balanced compliance blocks, hero-complementary blocks, hero-similar blocks, permit-heavy blocks, complaint-heavy blocks, critical-complaint blocks, recent-activity blocks, and fallback/problematic blocks for QA.

## Gates

{chr(10).join(f'- {name}: {gate["status"]}' for name, gate in report['gates'].items())}

## Known Limitations

- The scoring layer uses harvested DOB/MapPLUTO lookup resolution prepared by NYC Harvest Prep v0.2.
- Unresolved DOB complaints are reported for QA but excluded from block scoring until they can be resolved by a labelled fallback.
- D2b ranks candidate blocks; it does not create canonical district graph entities or edges.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def _sha256sums(output_dir: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = _sha256(path)
    return sums


def run_a4d2b_discovery(
    staging_dir: str = "data/processed/nyc/harvest_v0_2/discovery_staging",
    prep_output_dir: str = "outputs/nyc_harvest_prep_v0_2",
    output_dir: str = "outputs/a4d2b_district_discovery",
) -> dict[str, Any]:
    repo = _repo_root()
    staging = (repo / staging_dir).resolve() if not Path(staging_dir).is_absolute() else Path(staging_dir)
    prep = (repo / prep_output_dir).resolve() if not Path(prep_output_dir).is_absolute() else Path(prep_output_dir)
    out = (repo / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir)

    guard_paths = _canonical_guard_paths(repo)
    before_fingerprints = _fingerprints(guard_paths)

    _clean_output_dir(out)

    block_base = staging / "block_dob_activity_base.parquet"
    prep_summary = _load_prep_summary(prep)
    blocks = pd.read_parquet(block_base)
    scored = _score_blocks(blocks)
    ranked = scored.sort_values("balanced_discovery_score", ascending=False).reset_index(drop=True)
    active = scored[
        (scored["dob_now_filing_count"] + scored["dob_permit_issuance_count"] + scored["dob_complaint_count"]) > 0
    ]
    both = scored[(scored["unique_job_count"] > 0) & (scored["dob_complaint_count"] > 0)]

    csv_cols = [
        "block_key",
        "borough_code",
        "block",
        "candidate_family",
        "balanced_discovery_score",
        "permit_activity_score",
        "complaint_activity_score",
        "parcel_activity_share",
        "diversity_balance",
        "hero_shape_distance",
        "hero_shape_similarity",
        "parcel_count",
        "building_count",
        "parcels_with_any_dob_activity",
        "dob_now_filing_count",
        "dob_permit_issuance_count",
        "dob_complaint_count",
        "unique_job_count",
        "critical_complaint_count",
        "exact_bin_complaint_count",
        "unresolved_bin_complaint_count",
        "unique_bins_involved",
        "unique_contractors_or_license_parties",
        "unique_license_parties",
        "business_name_only_party_count",
        "latest_activity_date",
        "earliest_activity_date",
        "activity_span_years",
        "source_boundary_label",
    ]
    ranked[csv_cols].to_csv(out / "block_rankings.csv", index=False)

    top_25 = ranked.head(25)
    _write_json(
        out / "top_25_blocks.json",
        {
            "as_of_date": AS_OF_DATE,
            "boundary_statement": BOUNDARY_STATEMENT,
            "ranking_method": "balanced_discovery_score over prepared block_dob_activity_base.parquet",
            "blocks": [_record(row) for _, row in top_25.iterrows()],
        },
    )

    candidates = _candidate_districts(scored)
    _write_json(out / "candidate_districts.json", candidates)

    hero_comparison = _hero_comparison(scored, top_25)
    _write_json(out / "mn_1060_baseline_comparison.json", hero_comparison)

    unresolved_report = _write_unresolved_complaints_report(prep, out)

    after_fingerprints = _fingerprints(guard_paths)
    no_mutation = before_fingerprints == after_fingerprints

    gates = {
        "A4D2B-PRECOND": {
            "status": "PASS" if block_base.exists() and prep_summary.get("acceptance", {}).get("block_activity_base_exists") else "FAIL",
            "detail": "Prep v0.2 block base and acceptance summary are present.",
        },
        "A4D2B-BOUNDARY": {
            "status": "PASS" if prep_summary.get("boundary_statement") == BOUNDARY_STATEMENT else "FAIL",
            "detail": "Boundary statement is preserved verbatim from prep output.",
        },
        "A4D2B-RANKING": {
            "status": "PASS" if len(ranked) >= 25 and len(active) >= 25 else "FAIL",
            "detail": f"Ranked {len(ranked)} blocks, {len(active)} active blocks.",
        },
        "A4D2B-HERO-BASELINE": {
            "status": "PASS" if hero_comparison.get("status") == "PASS" else "FAIL",
            "detail": f"Baseline block {HERO_BLOCK_KEY} comparison generated.",
        },
        "A4D2B-CANDIDATE-DIVERSITY": {
            "status": "PASS"
            if candidates["balanced_compliance_blocks"]
            and candidates["hero_complementary_blocks"]
            and candidates["permit_heavy_blocks"]
            and candidates["complaint_heavy_blocks"]
            else "FAIL",
            "detail": "Balanced, complementary, permit-heavy, and complaint-heavy candidate families are populated.",
        },
        "A4D2B-NOT-PERMIT-ONLY": {
            "status": "PASS"
            if int((top_25["dob_complaint_count"] > 0).sum()) >= 10
            and int((top_25["critical_complaint_count"] > 0).sum()) >= 1
            else "FAIL",
            "detail": "Top ranking includes complaint and critical-complaint signals, not permit volume alone.",
        },
        "A4D2B-UNRESOLVED-COMPLAINTS": {
            "status": "PASS" if unresolved_report.get("status") in {"PASS", "WARN"} else "FAIL",
            "detail": f"Unresolved DOB complaint rows reported: {unresolved_report.get('complaint_rows', 0)}.",
        },
        "A4D2B-NO-CANONICAL-MUTATION": {
            "status": "PASS" if no_mutation else "FAIL",
            "detail": "Guarded canonical files have identical SHA-256 fingerprints before and after discovery.",
        },
    }

    status = "PASS" if all(gate["status"] == "PASS" for gate in gates.values()) else "FAIL"
    report = {
        "task": "a4·D2b Data-Driven NYC District Discovery",
        "status": status,
        "as_of_date": AS_OF_DATE,
        "boundary_statement": BOUNDARY_STATEMENT,
        "inputs": {
            "prep_output_dir": str(prep),
            "staging_dir": str(staging),
            "block_base": str(block_base),
            "prep_summary": str(prep / "harvest_prep_summary.json"),
        },
        "outputs": {
            "output_dir": str(out),
            "discovery_manifest": str(out / "discovery_manifest.json"),
            "block_rankings": str(out / "block_rankings.csv"),
            "top_25_blocks": str(out / "top_25_blocks.json"),
            "candidate_districts": str(out / "candidate_districts.json"),
            "mn_1060_baseline_comparison": str(out / "mn_1060_baseline_comparison.json"),
            "unresolved_complaints_report": str(out / "unresolved_complaints_report.csv"),
            "discovery_report": str(out / "discovery_report.json"),
            "readme": str(out / "README.md"),
        },
        "counts": {
            "blocks_ranked": int(len(ranked)),
            "active_blocks": int(len(active)),
            "blocks_with_permits_and_complaints": int(len(both)),
            "top_25_count": int(len(top_25)),
            "hero_baseline_present": bool(hero_comparison.get("status") == "PASS"),
            "unresolved_complaint_rows": int(unresolved_report.get("complaint_rows", 0)),
        },
        "method": {
            "resolution_source": "NYC Harvest Prep v0.2 discovery staging",
            "scoring": "balanced_discovery_score combines permit/job activity, complaint activity, parcel coverage, party diversity, recency, and permit/complaint balance",
            "complaint_rule": "DOB complaints are resolved by BIN -> building -> BBL -> block; unresolved BIN complaints are excluded from scoring and reported for QA",
            "canonical_mutation": "No canonical graph/schema artifacts are written by this task",
        },
        "unresolved_complaints_report": unresolved_report,
        "canonical_guard": {
            "paths_checked": list(before_fingerprints.keys()),
            "before": before_fingerprints,
            "after": after_fingerprints,
            "unchanged": no_mutation,
        },
        "gates": gates,
    }

    manifest = {
        "task": "a4·D2b Data-Driven NYC District Discovery",
        "status": status,
        "as_of_date": AS_OF_DATE,
        "boundary_statement": BOUNDARY_STATEMENT,
        "source_artifacts": {
            "prep_summary": str(prep / "harvest_prep_summary.json"),
            "block_activity_base": str(block_base),
            "dob_now_staging": str(staging / "dob_now_filings.parquet"),
            "dob_permit_staging": str(staging / "dob_permit_issuance.parquet"),
            "dob_complaint_staging": str(staging / "dob_complaints.parquet"),
            "building_lookup": str(staging / "building_bin_bbl_lookup.parquet"),
            "parcel_lookup": str(staging / "parcel_bbl_block_lookup.parquet"),
        },
        "source_records_included": {
            "dob_now_records_resolved_to_block": prep_summary.get("discovery_resolution_report", {}).get(
                "dob_now_records_resolved_to_block"
            ),
            "dob_permit_records_resolved_to_block": prep_summary.get("discovery_resolution_report", {}).get(
                "dob_permit_records_resolved_to_block"
            ),
            "dob_complaints_resolved_by_exact_bin": prep_summary.get("discovery_resolution_report", {}).get(
                "dob_complaints_resolved_by_exact_bin"
            ),
            "records_excluded_from_discovery_scoring": prep_summary.get("discovery_resolution_report", {}).get(
                "records_excluded_from_discovery_scoring"
            ),
        },
        "excluded_records_with_reason": {
            "unresolved_dob_records_csv": str(prep / "unresolved_dob_records.csv"),
            "unresolved_complaints_report_csv": str(out / "unresolved_complaints_report.csv"),
            "policy": "Unresolved DOB records are excluded from discovery scoring until resolved by exact key or labelled fallback.",
        },
        "candidate_outputs": {
            "block_rankings": "block_rankings.csv",
            "top_25_blocks": "top_25_blocks.json",
            "candidate_districts": "candidate_districts.json",
            "mn_1060_baseline_comparison": "mn_1060_baseline_comparison.json",
        },
        "non_goals": [
            "No canonical entity or edge mutation",
            "No citywide graph build",
            "No NeMo/NIM narration",
            "No LL84/EMS/FDNY/collisions/traffic fold-in",
            "No action resolver or UI",
        ],
    }
    _write_json(out / "discovery_manifest.json", manifest)
    _write_json(out / "discovery_report.json", report)
    _write_readme(out, report)
    _write_json(out / "SHA256SUMS.json", _sha256sums(out))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a4-D2b data-driven NYC district discovery.")
    parser.add_argument("--staging-dir", default="data/processed/nyc/harvest_v0_2/discovery_staging")
    parser.add_argument("--prep-output-dir", default="outputs/nyc_harvest_prep_v0_2")
    parser.add_argument("--output-dir", default="outputs/a4d2b_district_discovery")
    args = parser.parse_args()

    report = run_a4d2b_discovery(
        staging_dir=args.staging_dir,
        prep_output_dir=args.prep_output_dir,
        output_dir=args.output_dir,
    )
    print(f"a4-D2b Data-Driven NYC District Discovery: {report['status']}")
    print(f"As of date: {report['as_of_date']}")
    print(f"Output directory: {report['outputs']['output_dir']}")
    print(f"Blocks ranked: {report['counts']['blocks_ranked']}")
    print(f"Active blocks: {report['counts']['active_blocks']}")
    print(f"Top candidates: {report['counts']['top_25_count']}")
    print(f"Unresolved complaint rows: {report['counts']['unresolved_complaint_rows']}")
    for name, gate in report["gates"].items():
        print(f"- {name}: {gate['status']}")
        if gate["status"] != "PASS":
            print(f"  {gate['detail']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
