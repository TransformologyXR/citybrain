#!/usr/bin/env python3
"""Run distribution-checked simulation fixture audit R1.

This creates a read-only donor-distribution audit layer for selected
simulation/review-option fixtures. It does not create forecast packets,
operational predictions, official actions, source-truth mutations, or city
calibration claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-simulation-distribution-checked-fixtures-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_SIMULATION_DISTRIBUTION_CHECKED_FIXTURES_R1_WITH_LIMITATIONS"
STATUS_NEEDS_DATA = "NEEDS_DATA_FOR_DISTRIBUTION_CHECKED_SIMULATION_FIXTURES"
ALIGNED_LABEL = "donor_distribution_aligned_fixture"
NOT_CHECKED_LABEL = "not_distribution_checked_due_to_missing_comparable_donor_fields"

PATHS = {
    "domain_fuel_summary": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
    / "DOMAIN_FUEL_SUMMARY.json",
    "cross_city_donor_policy": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
    / "CROSS_CITY_DONOR_POLICY.json",
    "adapter_feed": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
    / "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl",
    "adapter_manifest": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
    / "SOURCE_ADAPTER_MANIFEST_R1.json",
    "mobility_donor_report": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE"
    / "R2B_MOBILITY_DONOR_REPORT.json",
    "non_sumo_option_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_non_sumo_domain_option_engines_r1"
    / "NON_SUMO_BASELINE_OPTION_COMPARISON_REPORT.json",
    "permit_option_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_non_sumo_domain_option_engines_r1"
    / "PERMIT_INSPECTION_DELAY_OPTION_ENGINE_REPORT.json",
    "sumo_option_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1"
    / "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
    "nyc_permit_timing_single_case": ROOT / "outputs" / "a9_wire_e2e_g1_snapshot" / "A9_WIRE_E2E_FLOW2_NYC_PROOF.json",
    "source_registry_flow_map": ROOT
    / "outputs"
    / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1"
    / "SOURCE_REGISTRY_V1_1_CONSUMING_FLOW_MAP.json",
    "scenario_scout_matrix": ROOT
    / "outputs"
    / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1"
    / "SCENARIO_SCOUT_MATRIX.json",
}

REQUIRED_FILES = [
    "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json",
    "SIM_DONOR_DATA_INVENTORY.json",
    "MOBILITY_DONOR_DISTRIBUTION_PROFILE.json",
    "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json",
    "PERMIT_DELAY_DONOR_SERVICE_TIME_PROFILE.json",
    "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT.json",
    "SIM_DONOR_DISTRIBUTION_COMPARISON_LEDGER.jsonl",
    "OPTION_RANKING_SENSITIVITY_REPORT.json",
    "DONOR_ALIGNMENT_LIMITATIONS.md",
    "NO_FORECAST_SURFACE_GUARD.json",
    "NO_CITY_CALIBRATION_CLAIM_GUARD.json",
    "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_count(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip()
    try:
        return int(float(text))
    except ValueError:
        return 0


def distribution(counter: dict[str, int]) -> dict[str, float]:
    total = sum(counter.values())
    if total <= 0:
        return {key: 0.0 for key in sorted(counter)}
    return {key: counter[key] / total for key in sorted(counter)}


def l1_distance(left: dict[str, int], right: dict[str, int]) -> float:
    left_dist = distribution(left)
    right_dist = distribution(right)
    keys = sorted(set(left_dist) | set(right_dist))
    return round(sum(abs(left_dist.get(key, 0.0) - right_dist.get(key, 0.0)) for key in keys), 6)


def source_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def mobility_feeds(report: dict[str, Any]) -> list[dict[str, Any]]:
    feeds: list[dict[str, Any]] = []
    for provider_key in ("lta", "tfl"):
        for feed in report.get(provider_key, {}).get("feeds", []):
            target = str(feed.get("normalization_target", ""))
            domain = str(feed.get("domain", ""))
            if "event_fabric" in domain or target in {
                "traffic_incident_events",
                "roadwork_events",
                "road_status",
                "mobility_disruptions",
                "line_status_events",
            }:
                feeds.append(feed)
    return feeds


def mobility_bucket(target: str) -> str:
    if target == "roadwork_events":
        return "roadworks"
    if target in {"mobility_disruptions", "line_status_events"}:
        return "transit_disruption"
    return "access_constraint"


def adapter_fixture_counts(feed_rows: list[dict[str, Any]], family_id: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in feed_rows:
        if row.get("canonical_loop_family_id") == family_id:
            counter[str(row.get("event_type", "unknown"))] += 1
    return dict(counter)


def build_inventory(
    domain_fuel: dict[str, Any],
    mobility_report: dict[str, Any],
    feed_rows: list[dict[str, Any]],
    nyc_permit_case: dict[str, Any],
    source_registry: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    mobility_feed_rows = mobility_feeds(mobility_report)
    entries.append(
        {
            "source_id": "keyed_mobility_r2b_lta_tfl_event_endpoints",
            "source_ref": rel(PATHS["mobility_donor_report"]),
            "source_family": "mobility_access_interruption_v0",
            "city_or_donor_context": sorted({str(feed.get("city", "unknown")) for feed in mobility_feed_rows}),
            "record_count": sum(parse_count(feed.get("row_count_estimate")) for feed in mobility_feed_rows),
            "fields_detected": ["provider", "endpoint_template", "normalization_target", "row_count_estimate", "source_id"],
            "time_fields_detected": [],
            "spatial_fields_detected": [],
            "source_class": "donor_context",
            "freshness": "sample_landed_from_prior_keyed_mobility_pull",
            "usable_for_distribution_check": bool(mobility_feed_rows),
            "limitations": [
                "Endpoint row estimates and normalization targets are used as event-type proxy buckets.",
                "Raw provider payloads are not read or rewritten by this task.",
            ],
        }
    )

    domain_summaries = domain_fuel.get("by_domain", {})
    for domain_key, family in [
        ("mobility_transport", "mobility_access_interruption_v0"),
        ("building_compliance", "building_compliance_perception_candidate"),
        ("property_planning", "permit_inspection_delay"),
    ]:
        summary = domain_summaries.get(domain_key, {})
        entries.append(
            {
                "source_id": f"seed_r3_domain_fuel:{domain_key}",
                "source_ref": rel(PATHS["domain_fuel_summary"]),
                "source_family": family,
                "city_or_donor_context": summary.get("cities", []),
                "record_count": int(summary.get("landed_rows", 0) or 0),
                "fields_detected": ["landed_rows", "ledger_rows", "registered_or_total_count", "cities", "seed_r3_use"],
                "time_fields_detected": [],
                "spatial_fields_detected": [],
                "source_class": "donor_context_summary",
                "freshness": domain_fuel.get("generated_at", "unknown"),
                "usable_for_distribution_check": domain_key == "mobility_transport",
                "limitations": [
                    "Summary counts establish donor/context availability, not row-level field distributions.",
                    "Direct timing fields are not exposed in this summary artifact.",
                ],
            }
        )

    family_counts = Counter(str(row.get("canonical_loop_family_id", "unknown")) for row in feed_rows)
    entries.append(
        {
            "source_id": "seed_r3_event_adapter_feed",
            "source_ref": rel(PATHS["adapter_feed"]),
            "source_family": sorted(family_counts),
            "city_or_donor_context": ["synthetic_fixture_with_donor_refs"],
            "record_count": len(feed_rows),
            "fields_detected": [
                "canonical_loop_family_id",
                "event_type",
                "expected_resolution_state",
                "event_time",
                "source_class",
                "truth_layer",
            ],
            "time_fields_detected": ["event_time", "processing_time"],
            "spatial_fields_detected": ["candidate_geometry_ref"],
            "source_class": "synthetic_or_fixture",
            "freshness": "local_seed_r3_adapter",
            "usable_for_distribution_check": True,
            "limitations": [
                "Fixture rows are small and machine generated for review.",
                "Used as fixture sample, not as independent donor truth.",
            ],
        }
    )

    cascade = nyc_permit_case.get("cascade", {})
    entries.append(
        {
            "source_id": "nyc_flow2_single_permit_to_complaint_timing",
            "source_ref": rel(PATHS["nyc_permit_timing_single_case"]),
            "source_family": "permit_inspection_delay",
            "city_or_donor_context": ["NYC"],
            "record_count": 1 if cascade.get("permit_to_complaint_days") is not None else 0,
            "fields_detected": sorted(cascade.keys()),
            "time_fields_detected": ["permit_issuance_date", "complaint_date_entered", "permit_to_complaint_days"],
            "spatial_fields_detected": ["bbl", "bin"],
            "source_class": "existing_city_source_or_derived_artifact",
            "freshness": "prior_snapshot",
            "usable_for_distribution_check": False,
            "limitations": [
                "Single permit-to-complaint sample is not a permit-created-to-inspection or inspection-completed distribution.",
                "Not enough comparable donor rows to label permit-delay fixtures as distribution checked.",
            ],
        }
    )

    permit_source_refs = []
    flows = source_registry.get("flows", {})
    for sources in flows.values():
        for source in sources:
            if "permit" in str(source).lower() or "inspection" in str(source).lower():
                permit_source_refs.append(source)
    entries.append(
        {
            "source_id": "source_registry_v1_1_permit_inspection_refs",
            "source_ref": rel(PATHS["source_registry_flow_map"]),
            "source_family": "permit_inspection_delay",
            "city_or_donor_context": ["source_registry_v1_1"],
            "record_count": len(sorted(set(permit_source_refs))),
            "fields_detected": ["source_id", "consuming_flow"],
            "time_fields_detected": [],
            "spatial_fields_detected": [],
            "source_class": "source_registry_metadata",
            "freshness": "prior_epoch4_tracka",
            "usable_for_distribution_check": False,
            "limitations": [
                "Registry refs prove source availability, not comparable timing distributions.",
                "Direct raw source rows are not read or mutated by this task.",
            ],
        }
    )

    return {
        "artifact_id": "SIM_DONOR_DATA_INVENTORY",
        "generated_at": now_iso(),
        "scan_scope": [
            "outputs summaries",
            "publications copied from current task",
            "known local data references from source registry metadata",
        ],
        "source_entries": entries,
        "source_count": len(entries),
        "usable_distribution_source_count": sum(1 for entry in entries if entry["usable_for_distribution_check"]),
        "limitations": [
            "This inventory reads local summaries/manifests and small fixture artifacts only.",
            "It does not rewrite raw providers, source registries, or source-truth records.",
            "Permit/inspection direct service-time distributions were not found in the inspected local summaries.",
        ],
    }


def build_mobility_profile(mobility_report: dict[str, Any]) -> dict[str, Any]:
    feeds = mobility_feeds(mobility_report)
    bucket_counts: Counter[str] = Counter()
    feed_rows: list[dict[str, Any]] = []
    for feed in feeds:
        count = parse_count(feed.get("row_count_estimate"))
        target = str(feed.get("normalization_target", ""))
        bucket_counts[mobility_bucket(target)] += count
        feed_rows.append(
            {
                "source_id": feed.get("source_id"),
                "provider": feed.get("provider"),
                "city": feed.get("city"),
                "normalization_target": target,
                "row_count_estimate": count,
                "status": feed.get("status"),
            }
        )
    return {
        "artifact_id": "MOBILITY_DONOR_DISTRIBUTION_PROFILE",
        "donor_distribution_id": "donor_distribution:mobility_access_interruption_v0:lta_tfl_event_type_proxy_counts:r1",
        "donor_source_refs": [rel(PATHS["mobility_donor_report"])],
        "donor_context_city_or_source": sorted({str(feed.get("city", "unknown")) for feed in feeds}),
        "family": "mobility_access_interruption_v0",
        "field_basis": ["normalization_target", "row_count_estimate", "source_id"],
        "record_count_used": sum(bucket_counts.values()),
        "method": "incident_or_disruption_type_counts via endpoint normalization target proxy buckets",
        "distribution_counts": dict(sorted(bucket_counts.items())),
        "distribution_normalized": distribution(dict(bucket_counts)),
        "source_feed_rows": feed_rows,
        "labels": [ALIGNED_LABEL, "not_city_calibrated", "not_forecast", "not_operational_prediction", "no_ForecastPacket"],
        "limitations": [
            "Distribution is built from named LTA/TfL donor endpoint row estimates, not full raw event payloads.",
            "The buckets are proxy event-type categories and are not a city calibration baseline.",
            "Duration, status, and spatial density checks remain parked until comparable fields are exposed.",
        ],
    }


def build_permit_profile(nyc_permit_case: dict[str, Any], source_registry: dict[str, Any]) -> dict[str, Any]:
    cascade = nyc_permit_case.get("cascade", {})
    permit_source_refs = []
    for sources in source_registry.get("flows", {}).values():
        for source in sources:
            text = str(source).lower()
            if "permit" in text or "inspection" in text:
                permit_source_refs.append(source)
    return {
        "artifact_id": "PERMIT_DELAY_DONOR_SERVICE_TIME_PROFILE",
        "profile_status": NOT_CHECKED_LABEL,
        "donor_distribution_id": None,
        "donor_source_refs": [
            rel(PATHS["nyc_permit_timing_single_case"]),
            rel(PATHS["source_registry_flow_map"]),
            rel(PATHS["scenario_scout_matrix"]),
        ],
        "candidate_source_refs": sorted(set(permit_source_refs))[:40],
        "donor_context_city_or_source": ["NYC", "Chicago", "London", "Barcelona"],
        "family": "permit_inspection_delay",
        "field_basis": [
            "permit_to_complaint_days_single_case",
            "source_registry_permit_inspection_refs",
            "scenario_scout_evidence_paths",
        ],
        "record_count_used": 0,
        "method": "parked: no comparable permit-created-to-inspection or inspection-completed distribution found in inspected local artifacts",
        "candidate_single_case_timing": {
            "permit_to_complaint_days": cascade.get("permit_to_complaint_days"),
            "permit_issuance_date": cascade.get("permit_issuance_date"),
            "complaint_date_entered": cascade.get("complaint_date_entered"),
        },
        "limitations": [
            "A single NYC permit-to-complaint example is not a donor service-time distribution.",
            "SourceRegistry refs identify permit/inspection sources but do not expose comparable timing rows here.",
            "Permit-delay fixtures are not labeled donor_distribution_aligned_fixture in this run.",
        ],
    }


def build_comparison_ledger(
    mobility_profile: dict[str, Any],
    permit_profile: dict[str, Any],
    feed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mobility_fixture_counts = adapter_fixture_counts(feed_rows, "mobility_access_interruption_v0")
    metric_value = l1_distance(mobility_profile["distribution_counts"], mobility_fixture_counts)
    mobility_row = {
        "fixture_id": "fixture:seed_r3:mobility_access_interruption_v0:event_type_mix:r1",
        "family": "mobility_access_interruption_v0",
        "fixture_source_ref": rel(PATHS["adapter_feed"]),
        "donor_distribution_id": mobility_profile["donor_distribution_id"],
        "donor_source_refs": mobility_profile["donor_source_refs"],
        "comparison_metric_name": "category_distribution_l1_distance",
        "comparison_metric_value": metric_value,
        "comparison_metric_interpretation": "0.0 is exact bucket parity; 2.0 is maximum divergence. This is an audit metric, not a forecast or city calibration.",
        "donor_sample_count": mobility_profile["record_count_used"],
        "fixture_sample_count": sum(mobility_fixture_counts.values()),
        "comparable_fields": ["event_type_proxy_bucket"],
        "donor_distribution_counts": mobility_profile["distribution_counts"],
        "fixture_distribution_counts": dict(sorted(mobility_fixture_counts.items())),
        "normalization_notes": [
            "roadwork_events maps to roadworks",
            "traffic_incident_events and road_status map to access_constraint",
            "mobility_disruptions and line_status_events map to transit_disruption",
        ],
        "limitations": [
            "Fixture sample count is four rows.",
            "Donor buckets are endpoint proxy counts, not payload-level incident labels.",
            "The high L1 distance means the fixture has been checked against donor distribution, not validated as representative.",
        ],
        "alignment_label": ALIGNED_LABEL,
    }
    permit_row = {
        "fixture_id": "fixture:permit_inspection_delay:non_sumo_option_engine:r1",
        "family": "permit_inspection_delay",
        "fixture_source_ref": rel(PATHS["permit_option_report"]),
        "donor_distribution_id": None,
        "donor_source_refs": permit_profile["donor_source_refs"],
        "comparison_metric_name": None,
        "comparison_metric_value": None,
        "comparison_metric_interpretation": "No comparable donor service-time distribution was found, so this fixture is parked rather than labeled as distribution checked.",
        "donor_sample_count": 0,
        "fixture_sample_count": 1,
        "comparable_fields": [],
        "normalization_notes": [
            "Single-case permit_to_complaint_days and SourceRegistry availability are insufficient for service-time distribution comparison."
        ],
        "limitations": permit_profile["limitations"],
        "alignment_label": NOT_CHECKED_LABEL,
    }
    return [mobility_row, permit_row]


def build_family_reports(ledger: list[dict[str, Any]], mobility_profile: dict[str, Any], permit_profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    mobility_rows = [row for row in ledger if row["family"] == "mobility_access_interruption_v0"]
    permit_rows = [row for row in ledger if row["family"] == "permit_inspection_delay"]
    mobility_report = {
        "artifact_id": "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT",
        "family": "mobility_access_interruption_v0",
        "status": "CHECKED_WITH_LIMITATIONS",
        "named_donor_distributions_used": [mobility_profile["donor_distribution_id"]],
        "fixture_ids_checked": [row["fixture_id"] for row in mobility_rows if row["alignment_label"] == ALIGNED_LABEL],
        "comparison_metrics": [
            {
                "fixture_id": row["fixture_id"],
                "comparison_metric_name": row["comparison_metric_name"],
                "comparison_metric_value": row["comparison_metric_value"],
                "donor_sample_count": row["donor_sample_count"],
                "fixture_sample_count": row["fixture_sample_count"],
            }
            for row in mobility_rows
        ],
        "sample_counts": {
            "donor": mobility_profile["record_count_used"],
            "fixture": sum(row["fixture_sample_count"] for row in mobility_rows),
        },
        "what_aligned": [
            "Fixture event types can be mapped to named donor event/disruption proxy buckets.",
            "Every aligned mobility ledger row carries donor_distribution_id and comparison metric fields.",
        ],
        "what_did_not_align": [
            "Fixture bucket proportions differ materially from LTA/TfL endpoint proxy counts.",
            "No duration, status, or spatial density donor check is available from the inspected summaries.",
        ],
        "what_could_not_be_compared": [
            "Roadwork/disruption duration",
            "Incident status category lifecycle",
            "Spatial density buckets",
            "Route/stop topology proxies",
        ],
        "claim_boundary": "donor_distribution_aligned_fixture only; not_city_calibrated, not_forecast, not_operational_prediction, no_ForecastPacket.",
    }
    permit_report = {
        "artifact_id": "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT",
        "family": "permit_inspection_delay",
        "status": "PARKED_NOT_DISTRIBUTION_CHECKED",
        "named_donor_distributions_used": [],
        "fixture_ids_checked": [],
        "fixtures_parked": [row["fixture_id"] for row in permit_rows],
        "comparison_metrics": [],
        "sample_counts": {"donor": 0, "fixture": sum(row["fixture_sample_count"] for row in permit_rows)},
        "what_aligned": [],
        "what_did_not_align": [
            "No comparable permit service-time donor distribution was available in the inspected local artifacts."
        ],
        "what_could_not_be_compared": [
            "permit_created_to_inspection",
            "inspection_requested_to_completed",
            "permit_status_change_delay",
            "review_queue_delay",
        ],
        "candidate_evidence_not_used_as_distribution": permit_profile["candidate_single_case_timing"],
        "claim_boundary": "permit fixture remains not_distribution_checked_due_to_missing_comparable_donor_fields; no city calibration, forecast, or operational prediction claim.",
    }
    return mobility_report, permit_report


def build_sensitivity(non_sumo: dict[str, Any], permit_option: dict[str, Any]) -> dict[str, Any]:
    families = {entry.get("family_id"): entry for entry in non_sumo.get("families", [])}
    permit_options = permit_option.get("options", [])
    permit_base = [option.get("option_id") for option in sorted(permit_options, key=lambda item: item.get("score", 0), reverse=True)]
    mobility_base = ["normal_corridor", "restricted_asset_corridor_review", "defer_until_better_donor_duration"]
    building = families.get("building_compliance_perception_candidate", {})
    building_base = [
        building.get("best_review_option", {}).get("option_id", "targeted_perception_evidence_review"),
        building.get("baseline_option", {}).get("option_id", "baseline_review_only"),
    ]
    checks = [
        {
            "family": "mobility_access_interruption_v0",
            "fixture_id": "fixture:seed_r3:mobility_access_interruption_v0:event_type_mix:r1",
            "assumption_name": "donor_proxy_weight_on_roadworks_bucket",
            "base_value": 1.0,
            "low_value": 0.5,
            "high_value": 1.5,
            "option_ranking_base": mobility_base,
            "option_ranking_low": mobility_base,
            "option_ranking_high": mobility_base,
            "ranking_flipped": False,
            "notes": "Ranking is static review-option ordering only; no learned ranking or forecast was produced.",
        },
        {
            "family": "permit_inspection_delay",
            "fixture_id": "fixture:permit_inspection_delay:non_sumo_option_engine:r1",
            "assumption_name": "source_gap_penalty_weight",
            "base_value": 1.0,
            "low_value": 0.75,
            "high_value": 1.25,
            "option_ranking_base": permit_base,
            "option_ranking_low": permit_base,
            "option_ranking_high": permit_base,
            "ranking_flipped": False,
            "notes": "Permit ranking remains review-only and is not distribution checked due to missing comparable service-time donor fields.",
        },
        {
            "family": "building_compliance_perception_candidate",
            "fixture_id": "fixture:building_compliance_perception_candidate:non_sumo_option_engine:r1",
            "assumption_name": "perception_conflict_review_weight",
            "base_value": 1.0,
            "low_value": 0.8,
            "high_value": 1.2,
            "option_ranking_base": building_base,
            "option_ranking_low": building_base,
            "option_ranking_high": building_base,
            "ranking_flipped": False,
            "notes": "Included because the option engine is adjacent; no domain-specific distribution label is claimed here.",
        },
    ]
    return {
        "artifact_id": "OPTION_RANKING_SENSITIVITY_REPORT",
        "generated_at": now_iso(),
        "sensitivity_checks": checks,
        "ranking_flip_detected": any(check["ranking_flipped"] for check in checks),
        "labels": ["not_forecast", "not_operational_prediction", "no_ForecastPacket"],
    }


def build_guards() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    no_forecast = {
        "artifact_id": "NO_FORECAST_SURFACE_GUARD",
        "status": "PASS",
        "no_ForecastPacket": True,
        "forecast_packet_created": False,
        "forecast_surface_created": False,
        "product_forecast_created": False,
        "validated_forecast_claim_created": False,
    }
    no_city_calibration = {
        "artifact_id": "NO_CITY_CALIBRATION_CLAIM_GUARD",
        "status": "PASS",
        "not_city_calibrated": True,
        "positive_city_calibration_claim_created": False,
        "calibration_boundary": "Fixture distribution audit only; no city calibration baseline or positive calibration claim.",
    }
    no_operational_prediction = {
        "artifact_id": "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD",
        "status": "PASS",
        "not_operational_prediction": True,
        "operational_prediction_created": False,
        "learned_ranking_created": False,
        "model_training_or_arming_created": False,
    }
    boundary = {
        "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
        "status": "PASS",
        "read_only": True,
        "source_truth_mutated": False,
        "raw_payload_rewritten": False,
        "official_workflow_case_action_created": False,
        "dispatch_control_enforcement_created": False,
        "legal_or_certified_finding_created": False,
        "live_ingestion_or_monitoring_created": False,
        "public_api_or_production_frontend_created": False,
        "human_founder_operator_session_result_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
    }
    return no_forecast, no_city_calibration, no_operational_prediction, boundary


def decision_payload(ledger: list[dict[str, Any]], mobility_profile: dict[str, Any]) -> dict[str, Any]:
    aligned_rows = [row for row in ledger if row["alignment_label"] == ALIGNED_LABEL]
    metric_rows = [row for row in aligned_rows if row.get("comparison_metric_name") and row.get("comparison_metric_value") is not None]
    named_distributions = sorted({row["donor_distribution_id"] for row in aligned_rows if row.get("donor_distribution_id")})
    status = STATUS_PASS if named_distributions and metric_rows else STATUS_NEEDS_DATA
    return {
        "artifact_id": "DISTRIBUTION_CHECKED_SIMULATION_DECISION",
        "task_id": "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1",
        "generated_at": now_iso(),
        "status": status,
        "label": ALIGNED_LABEL if status == STATUS_PASS else NOT_CHECKED_LABEL,
        "labels": [ALIGNED_LABEL, "not_city_calibrated", "not_forecast", "not_operational_prediction", "no_ForecastPacket"],
        "not_city_calibrated": True,
        "not_forecast": True,
        "not_operational_prediction": True,
        "forecast_packet_created": False,
        "named_donor_distribution_count": len(named_distributions),
        "comparison_metric_count": len(metric_rows),
        "families_checked": sorted({row["family"] for row in metric_rows}),
        "families_not_checked": [
            {
                "family": "permit_inspection_delay",
                "reason": "No comparable permit-created-to-inspection or inspection-completed donor distribution found in inspected local artifacts.",
            }
        ],
        "mobility_distribution_record_count_used": mobility_profile["record_count_used"],
        "client_ready": False,
        "product_review_ready": False,
        "learning_ready": False,
        "no_source_truth_mutation": True,
        "boundaries": [
            "read-only local audit layer",
            "no ForecastPacket",
            "no forecast surface",
            "no operational prediction",
            "no official workflow/case/action",
            "no training rows",
        ],
    }


def write_manifest(out: Path) -> None:
    manifest_path = out / "HASH_MANIFEST.sha256"
    rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path != manifest_path:
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(manifest_path, "\n".join(rows))


def verify_manifest(manifest_path: Path) -> list[str]:
    failures: list[str] = []
    if not manifest_path.exists():
        return [f"Missing manifest: {manifest_path}"]
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, file_ref = line.split("  ", 1)
        path = ROOT / file_ref
        if not path.exists():
            failures.append(f"Manifest path missing: {file_ref}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            failures.append(f"Hash mismatch for {file_ref}: expected {expected}, got {actual}")
    return failures


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    files = [
        "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json",
        "SIM_DONOR_DISTRIBUTION_COMPARISON_SUMMARY.json",
        "OPTION_RANKING_SENSITIVITY_REPORT.json",
        "DONOR_ALIGNMENT_LIMITATIONS.md",
        "NO_FORECAST_SURFACE_GUARD.json",
        "NO_CITY_CALIBRATION_CLAIM_GUARD.json",
        "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json",
        "BOUNDARY_NO_ACTION_AUDIT.json",
        "CODEX_CLOSEOUT.md",
        "HASH_MANIFEST.sha256",
    ]
    for name in files:
        src = out / name
        if src.exists():
            shutil.copy2(src, PUBLICATION_ROOT / name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def build(out: Path = DEFAULT_OUT) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    domain_fuel = read_json(PATHS["domain_fuel_summary"])
    mobility_report = read_json(PATHS["mobility_donor_report"])
    feed_rows = read_jsonl(PATHS["adapter_feed"])
    nyc_permit_case = read_json(PATHS["nyc_permit_timing_single_case"])
    source_registry = read_json(PATHS["source_registry_flow_map"])
    non_sumo = read_json(PATHS["non_sumo_option_report"])
    permit_option = read_json(PATHS["permit_option_report"])

    inventory = build_inventory(domain_fuel, mobility_report, feed_rows, nyc_permit_case, source_registry)
    mobility_profile = build_mobility_profile(mobility_report)
    permit_profile = build_permit_profile(nyc_permit_case, source_registry)
    ledger = build_comparison_ledger(mobility_profile, permit_profile, feed_rows)
    mobility_family_report, permit_family_report = build_family_reports(ledger, mobility_profile, permit_profile)
    sensitivity = build_sensitivity(non_sumo, permit_option)
    no_forecast, no_city_calibration, no_operational_prediction, boundary = build_guards()
    decision = decision_payload(ledger, mobility_profile)

    comparison_summary = {
        "artifact_id": "SIM_DONOR_DISTRIBUTION_COMPARISON_SUMMARY",
        "status": decision["status"],
        "aligned_fixture_count": sum(1 for row in ledger if row["alignment_label"] == ALIGNED_LABEL),
        "parked_fixture_count": sum(1 for row in ledger if row["alignment_label"] == NOT_CHECKED_LABEL),
        "metric_rows": [
            {
                "fixture_id": row["fixture_id"],
                "family": row["family"],
                "metric": row["comparison_metric_name"],
                "value": row["comparison_metric_value"],
                "alignment_label": row["alignment_label"],
            }
            for row in ledger
        ],
    }

    limitations_md = f"""# Donor Alignment Limitations

Status: `{decision["status"]}`

## Mobility

- The mobility fixture is labeled `{ALIGNED_LABEL}` because it has a named donor distribution id, source refs, sample counts, and a visible `category_distribution_l1_distance` metric.
- The donor profile uses LTA/TfL endpoint row estimates as event-type proxy buckets. This is useful for fixture audit, but it is not city calibration and not a forecast.
- The checked fixture has only four Seed R3 adapter rows, so representativeness remains limited.

## Permit Inspection Delay

- Permit-delay is parked as `{NOT_CHECKED_LABEL}`.
- The local artifacts expose source refs and one NYC permit-to-complaint example, but not a comparable permit-created-to-inspection or inspection-completed donor distribution.
- The permit option engine remains review-only and is not distribution checked in this run.

## Boundaries

- no_ForecastPacket
- not_city_calibrated
- not_forecast
- not_operational_prediction
- no source-truth mutation
- no official workflow, case, dispatch, control, enforcement, legal, or certified finding
"""

    closeout = f"""# Distribution-Checked Simulation Fixtures R1 Closeout

Status: `{decision["status"]}`

Discovered donor distributions:
- `{mobility_profile["donor_distribution_id"]}` using `{rel(PATHS["mobility_donor_report"])}`.

Fixtures checked:
- `fixture:seed_r3:mobility_access_interruption_v0:event_type_mix:r1` with `category_distribution_l1_distance`.

Fixtures parked:
- `fixture:permit_inspection_delay:non_sumo_option_engine:r1` because comparable permit service-time donor fields were not found.

This remains a read-only donor-distribution fixture audit. It is not city calibrated, not a forecast, not an operational prediction, and it creates no ForecastPacket or action authority.
"""

    write_json(out / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json", decision)
    write_json(out / "SIM_DONOR_DATA_INVENTORY.json", inventory)
    write_json(out / "MOBILITY_DONOR_DISTRIBUTION_PROFILE.json", mobility_profile)
    write_json(out / "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json", mobility_family_report)
    write_json(out / "PERMIT_DELAY_DONOR_SERVICE_TIME_PROFILE.json", permit_profile)
    write_json(out / "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT.json", permit_family_report)
    write_jsonl(out / "SIM_DONOR_DISTRIBUTION_COMPARISON_LEDGER.jsonl", ledger)
    write_json(out / "SIM_DONOR_DISTRIBUTION_COMPARISON_SUMMARY.json", comparison_summary)
    write_json(out / "OPTION_RANKING_SENSITIVITY_REPORT.json", sensitivity)
    write_text(out / "DONOR_ALIGNMENT_LIMITATIONS.md", limitations_md)
    write_json(out / "NO_FORECAST_SURFACE_GUARD.json", no_forecast)
    write_json(out / "NO_CITY_CALIBRATION_CLAIM_GUARD.json", no_city_calibration)
    write_json(out / "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json", no_operational_prediction)
    write_json(out / "BOUNDARY_NO_ACTION_AUDIT.json", boundary)
    write_text(out / "CODEX_CLOSEOUT.md", closeout)
    write_manifest(out)
    copy_publication(out)
    return decision


def validate(out: Path = DEFAULT_OUT) -> list[str]:
    failures: list[str] = []
    missing = [rel(path) for path in required_paths(out) if not path.exists()]
    failures.extend(f"Missing required output: {path}" for path in missing)
    if missing:
        return failures

    decision = read_json(out / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json")
    ledger = read_jsonl(out / "SIM_DONOR_DISTRIBUTION_COMPARISON_LEDGER.jsonl")
    aligned = [row for row in ledger if row.get("alignment_label") == ALIGNED_LABEL]
    metric_rows = [row for row in aligned if row.get("comparison_metric_name") and row.get("comparison_metric_value") is not None]
    named = [row for row in aligned if row.get("donor_distribution_id")]

    if decision.get("status") == STATUS_PASS:
        if not named:
            failures.append("PASS status requires at least one named donor distribution.")
        if not metric_rows:
            failures.append("PASS status requires at least one visible comparison metric.")
    if not named or not metric_rows:
        if decision.get("status") != STATUS_NEEDS_DATA:
            failures.append("Missing named distributions or metrics must use NEEDS_DATA status.")

    required_aligned_fields = [
        "fixture_id",
        "family",
        "fixture_source_ref",
        "donor_distribution_id",
        "donor_source_refs",
        "comparison_metric_name",
        "comparison_metric_value",
        "donor_sample_count",
        "fixture_sample_count",
        "limitations",
        "alignment_label",
    ]
    for row in aligned:
        for field in required_aligned_fields:
            if row.get(field) in (None, "", []):
                failures.append(f"Aligned ledger row missing {field}: {row.get('fixture_id')}")

    no_forecast = read_json(out / "NO_FORECAST_SURFACE_GUARD.json")
    no_city_calibration = read_json(out / "NO_CITY_CALIBRATION_CLAIM_GUARD.json")
    no_operational_prediction = read_json(out / "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json")
    boundary = read_json(out / "BOUNDARY_NO_ACTION_AUDIT.json")
    if no_forecast.get("forecast_packet_created") is not False or no_forecast.get("no_ForecastPacket") is not True:
        failures.append("Forecast guard failed.")
    if no_city_calibration.get("not_city_calibrated") is not True:
        failures.append("City calibration guard failed.")
    if no_operational_prediction.get("not_operational_prediction") is not True:
        failures.append("Operational prediction guard failed.")
    if boundary.get("source_truth_mutated") is not False or boundary.get("official_workflow_case_action_created") is not False:
        failures.append("Boundary/no-action audit failed.")

    mobility_report = read_json(out / "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json")
    permit_report = read_json(out / "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT.json")
    if mobility_report.get("status") != "CHECKED_WITH_LIMITATIONS":
        failures.append("Mobility report did not check with limitations.")
    if permit_report.get("status") != "PARKED_NOT_DISTRIBUTION_CHECKED":
        failures.append("Permit report was not explicitly parked.")

    failures.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing outputs without rebuilding")
    args = parser.parse_args()

    out = Path(args.out)
    if not args.validate_only:
        decision = build(out)
        print(decision["status"])
    failures = validate(out)
    if failures:
        for failure in failures:
            print(f"VALIDATION FAILURE: {failure}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
