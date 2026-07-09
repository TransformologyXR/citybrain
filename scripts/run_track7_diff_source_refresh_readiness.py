from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "track7_diff_source_refresh_readiness"

STATUS_PASS_LIMITATIONS = "PASS_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED"

CITY_LEDGER_REFS = {
    "nyc": REPO_ROOT / "outputs" / "nyc_allflows_data_landing_r1" / "NYC_ALLFLOWS_SOURCE_LEDGER.json",
    "london": REPO_ROOT / "outputs" / "lon_allflows_data_landing_r1" / "LON_ALLFLOWS_SOURCE_LEDGER.json",
    "chicago": REPO_ROOT / "outputs" / "chi_allflows_data_landing_r1" / "CHI_ALLFLOWS_SOURCE_LEDGER.json",
    "barcelona": REPO_ROOT / "outputs" / "barc_allflows_data_landing_r1" / "BARC_ALLFLOWS_SOURCE_LEDGER.json",
}

CITY_PHASE_MANIFEST_REFS = {
    "nyc": REPO_ROOT / "outputs" / "nyc_allflows_data_landing_r1" / "NYC_ALLFLOWS_PHASE_MANIFEST.json",
    "london": REPO_ROOT / "outputs" / "lon_allflows_data_landing_r1" / "LON_ALLFLOWS_PHASE_MANIFEST.json",
    "chicago": REPO_ROOT / "outputs" / "chi_allflows_data_landing_r1" / "CHI_ALLFLOWS_PHASE_MANIFEST.json",
    "barcelona": REPO_ROOT / "outputs" / "barc_allflows_data_landing_r1" / "BARC_ALLFLOWS_PHASE_MANIFEST.json",
}

EXPECTED_OUTPUT_FILES = {
    "SNAPSHOT_INVENTORY.json",
    "SOURCE_REFRESH_STATUS.json",
    "COMPARABLE_SNAPSHOT_DETECTOR.json",
    "DESIGNED_CHANGE_FIXTURE.json",
    "CHANGE_CLASSIFIER_REPORT.json",
    "ENTITY_LEVEL_DIFF_REPORT.json",
    "SOURCE_LEVEL_DIFF_REPORT.json",
    "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json",
    "SUMMARY.md",
    "HASH_MANIFEST.json",
}

CLASSIFICATIONS = ["new", "changed", "expired", "stale", "unchanged"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def safe_prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        unexpected = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.name not in EXPECTED_OUTPUT_FILES)
        if unexpected:
            raise RuntimeError(f"Refusing to write over unexpected Track 7 artifacts: {unexpected}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def load_sources(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path, {})
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return payload["sources"]
    if isinstance(payload, list):
        return payload
    return []


def source_key(source: dict[str, Any], index: int) -> str:
    for key in ["key", "source_key", "dataset_id", "id", "name", "title", "source_name"]:
        value = source.get(key)
        if value not in (None, ""):
            return str(value)
    return f"source_{index:04d}"


def source_name(source: dict[str, Any], fallback: str) -> str:
    return str(source.get("name") or source.get("title") or source.get("source_name") or fallback)


def source_row_count(source: dict[str, Any]) -> int | None:
    for key in ["row_count", "row_count_total", "count_observed", "probed_total_sum", "feature_count"]:
        value = source.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def source_status(source: dict[str, Any]) -> str:
    for key in ["scan_status", "status", "probe_status", "classification", "soda2_status"]:
        value = source.get(key)
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN"


def source_updated_at(source: dict[str, Any]) -> Any:
    for key in ["rows_updated_at", "metadata_updated_at", "last_updated", "updated_at", "generated_utc"]:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def source_columns(source: dict[str, Any]) -> list[str]:
    columns = source.get("columns") or source.get("shape_fields") or source.get("fields") or []
    if isinstance(columns, list):
        normalized = []
        for column in columns:
            if isinstance(column, dict):
                normalized.append(str(column.get("field_name") or column.get("name") or column.get("id") or "unknown"))
            else:
                normalized.append(str(column))
        return sorted(set(normalized))
    return []


def source_refresh_class(source: dict[str, Any]) -> str:
    status = source_status(source).lower()
    row_count = source_row_count(source)
    has_endpoint = any(source.get(key) for key in ["url", "human_url", "soda2_json_endpoint", "soda2_csv_endpoint", "count_query_url"])
    if any(token in status for token in ["error", "fail", "blocked", "missing"]):
        return "refresh_blocked"
    if row_count is None:
        return "needs_probe"
    if has_endpoint:
        return "refresh_ready"
    return "inventory_only"


def source_record(city: str, source: dict[str, Any], index: int) -> dict[str, Any]:
    key = source_key(source, index)
    columns = source_columns(source)
    row_count = source_row_count(source)
    record = {
        "source_id": f"{city}:source:{key}",
        "city": city,
        "source_key": key,
        "name": source_name(source, key),
        "status": source_status(source),
        "refresh_status": source_refresh_class(source),
        "row_count": row_count,
        "updated_at": source_updated_at(source),
        "column_count": len(columns) or source.get("column_count"),
        "schema_fields_sample": columns[:20],
        "has_endpoint": any(source.get(key) for key in ["url", "human_url", "soda2_json_endpoint", "soda2_csv_endpoint", "count_query_url"]),
    }
    record["content_fingerprint"] = stable_hash(
        {
            "source_key": record["source_key"],
            "name": record["name"],
            "row_count": record["row_count"],
            "status": record["status"],
            "columns": columns,
            "updated_at": record["updated_at"],
        }
    )
    return record


def build_snapshot_inventory() -> dict[str, Any]:
    snapshots = []
    for city, ledger_path in CITY_LEDGER_REFS.items():
        sources = load_sources(ledger_path)
        source_records = [source_record(city, source, index) for index, source in enumerate(sources)]
        phase_manifest = CITY_PHASE_MANIFEST_REFS[city]
        snapshots.append(
            {
                "snapshot_id": f"track7:{city}:current_source_ledger",
                "city": city,
                "snapshot_kind": "source_ledger_current",
                "ledger_ref": rel(ledger_path),
                "ledger_exists": ledger_path.exists(),
                "ledger_sha256": sha256_file(ledger_path) if ledger_path.exists() else None,
                "phase_manifest_ref": rel(phase_manifest),
                "phase_manifest_exists": phase_manifest.exists(),
                "phase_manifest_sha256": sha256_file(phase_manifest) if phase_manifest.exists() else None,
                "source_count": len(source_records),
                "refresh_status_counts": dict(sorted(Counter(row["refresh_status"] for row in source_records).items())),
                "status_counts": dict(sorted(Counter(row["status"] for row in source_records).items())),
                "sample_sources": source_records[:8],
            }
        )
    return {
        "schema_version": "citybrain.track7.diff_source_refresh.snapshot_inventory.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "source_snapshots": snapshots,
        "snapshot_count": len(snapshots),
        "total_source_count": sum(row["source_count"] for row in snapshots),
        "read_only": True,
        "limitations": [
            "Inventory is built from existing local source ledgers only.",
            "No live refresh or upstream source mutation is performed.",
        ],
    }


def build_source_refresh_status(snapshot_inventory: dict[str, Any]) -> dict[str, Any]:
    source_rows = []
    for snapshot in snapshot_inventory["source_snapshots"]:
        for row in snapshot["sample_sources"]:
            source_rows.append(row)

    city_counts: dict[str, dict[str, int]] = {}
    for snapshot in snapshot_inventory["source_snapshots"]:
        city_counts[snapshot["city"]] = snapshot["refresh_status_counts"]

    return {
        "schema_version": "citybrain.track7.diff_source_refresh.source_refresh_status.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "policy": {
            "refresh_ready": "Source has a row/count signal and a retrievable endpoint or ledgered access path.",
            "needs_probe": "Source lacks a row/count signal and should be probed before future DIFF.",
            "refresh_blocked": "Ledger status indicates failure, missing source, or blocked access.",
            "inventory_only": "Source can be inventoried but not yet refreshed deterministically from this track.",
        },
        "city_refresh_status_counts": city_counts,
        "sample_source_rows": source_rows,
        "readiness": {
            "has_snapshot_inventory": snapshot_inventory["snapshot_count"] >= 1,
            "has_multi_city_coverage": snapshot_inventory["snapshot_count"] >= 2,
            "can_prepare_future_snapshot_diff": True,
            "requires_future_real_changed_snapshot": True,
        },
    }


def build_designed_change_fixture() -> dict[str, Any]:
    baseline_observed_at = "2026-06-01T00:00:00Z"
    target_observed_at = "2026-07-07T00:00:00Z"
    baseline_sources = [
        {
            "id": "source:nyc:street_closure_feed",
            "source_key": "street_closure_feed",
            "city": "nyc",
            "row_count": 120,
            "schema_fields": ["id", "status", "street"],
            "content_updated_at": "2026-06-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "source:london:roadworks_planning",
            "source_key": "roadworks_planning",
            "city": "london",
            "row_count": 88,
            "schema_fields": ["id", "status", "road"],
            "content_updated_at": "2026-05-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "source:chicago:permit_reviews",
            "source_key": "permit_reviews",
            "city": "chicago",
            "row_count": 500,
            "schema_fields": ["id", "status", "parcel"],
            "content_updated_at": "2026-04-01T00:00:00Z",
            "refresh_cadence_days": 30,
        },
        {
            "id": "source:barcelona:traffic_counters",
            "source_key": "traffic_counters",
            "city": "barcelona",
            "row_count": 1000,
            "schema_fields": ["id", "count", "segment"],
            "content_updated_at": "2026-07-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
    ]
    target_sources = [
        {
            "id": "source:nyc:street_closure_feed",
            "source_key": "street_closure_feed",
            "city": "nyc",
            "row_count": 121,
            "schema_fields": ["id", "status", "street", "borough"],
            "content_updated_at": "2026-07-05T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "source:london:roadworks_planning",
            "source_key": "roadworks_planning",
            "city": "london",
            "row_count": 88,
            "schema_fields": ["id", "status", "road"],
            "content_updated_at": "2026-05-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "source:barcelona:traffic_counters",
            "source_key": "traffic_counters",
            "city": "barcelona",
            "row_count": 1000,
            "schema_fields": ["id", "count", "segment"],
            "content_updated_at": "2026-07-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "source:helsinki:weather_pilot",
            "source_key": "weather_pilot",
            "city": "helsinki",
            "row_count": 44,
            "schema_fields": ["id", "temperature", "station"],
            "content_updated_at": "2026-07-07T00:00:00Z",
            "refresh_cadence_days": 1,
        },
    ]
    baseline_entities = [
        {
            "id": "entity:nyc:block-100",
            "source_id": "source:nyc:street_closure_feed",
            "attributes": {"status": "open", "street": "1 Ave"},
            "content_updated_at": "2026-06-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:london:road-22",
            "source_id": "source:london:roadworks_planning",
            "attributes": {"status": "planned", "road": "A10"},
            "content_updated_at": "2026-05-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:chicago:permit-7",
            "source_id": "source:chicago:permit_reviews",
            "attributes": {"status": "review", "parcel": "P-7"},
            "content_updated_at": "2026-04-01T00:00:00Z",
            "refresh_cadence_days": 30,
        },
        {
            "id": "entity:barcelona:counter-3",
            "source_id": "source:barcelona:traffic_counters",
            "attributes": {"count": 55, "segment": "B-3"},
            "content_updated_at": "2026-07-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:nyc:noise-5",
            "source_id": "source:nyc:street_closure_feed",
            "attributes": {"status": "unchanged", "street": "2 Ave"},
            "content_updated_at": "2026-07-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
    ]
    target_entities = [
        {
            "id": "entity:nyc:block-100",
            "source_id": "source:nyc:street_closure_feed",
            "attributes": {"status": "mitigated", "street": "1 Ave"},
            "content_updated_at": "2026-07-05T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:london:road-22",
            "source_id": "source:london:roadworks_planning",
            "attributes": {"status": "planned", "road": "A10"},
            "content_updated_at": "2026-05-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:barcelona:counter-3",
            "source_id": "source:barcelona:traffic_counters",
            "attributes": {"count": 59, "segment": "B-3"},
            "content_updated_at": "2026-07-07T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:nyc:noise-5",
            "source_id": "source:nyc:street_closure_feed",
            "attributes": {"status": "unchanged", "street": "2 Ave"},
            "content_updated_at": "2026-07-01T00:00:00Z",
            "refresh_cadence_days": 14,
        },
        {
            "id": "entity:singapore:new-sensor-1",
            "source_id": "source:singapore:pilot_sensor",
            "attributes": {"status": "new", "zone": "SG-1"},
            "content_updated_at": "2026-07-07T00:00:00Z",
            "refresh_cadence_days": 1,
        },
    ]
    return {
        "schema_version": "citybrain.track7.diff_source_refresh.designed_change_fixture.v1",
        "status": "PASS",
        "generated_at": utc_now(),
        "purpose": "Designed fixture to prove new/changed/expired/stale/unchanged classification before real changed snapshots arrive.",
        "baseline_snapshot": {
            "snapshot_id": "track7:fixture:baseline",
            "observed_at": baseline_observed_at,
            "sources": baseline_sources,
            "entities": baseline_entities,
        },
        "target_snapshot": {
            "snapshot_id": "track7:fixture:target",
            "observed_at": target_observed_at,
            "sources": target_sources,
            "entities": target_entities,
        },
        "expected_classifications": {
            "entity": {"new": 1, "changed": 2, "expired": 1, "stale": 1, "unchanged": 1},
            "source": {"new": 1, "changed": 1, "expired": 1, "stale": 1, "unchanged": 1},
        },
        "non_claims": [
            "not a live refresh",
            "not a current-truth assertion",
            "not a learned ranking or prediction signal",
        ],
    }


def content_hash(record: dict[str, Any], level: str) -> str:
    if level == "entity":
        payload = {"attributes": record.get("attributes", {}), "source_id": record.get("source_id")}
    else:
        payload = {
            "row_count": record.get("row_count"),
            "schema_fields": record.get("schema_fields", []),
            "source_key": record.get("source_key"),
        }
    return stable_hash(payload)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def age_days(target_observed_at: str, content_updated_at: str) -> int:
    return (parse_utc(target_observed_at) - parse_utc(content_updated_at)).days


def classify_records(
    baseline: list[dict[str, Any]],
    target: list[dict[str, Any]],
    target_observed_at: str,
    *,
    level: str,
) -> list[dict[str, Any]]:
    baseline_by_id = {row["id"]: row for row in baseline}
    target_by_id = {row["id"]: row for row in target}
    diff_rows = []
    for record_id in sorted(set(baseline_by_id) | set(target_by_id)):
        base = baseline_by_id.get(record_id)
        current = target_by_id.get(record_id)
        if base is None and current is not None:
            classification = "new"
            reasons = ["id_absent_from_baseline_present_in_target"]
        elif base is not None and current is None:
            classification = "expired"
            reasons = ["id_present_in_baseline_absent_from_target"]
        elif base is not None and current is not None and content_hash(base, level) != content_hash(current, level):
            classification = "changed"
            reasons = ["stable_id_present_in_both_content_hash_changed"]
        elif current is not None and age_days(target_observed_at, current["content_updated_at"]) > int(current["refresh_cadence_days"]):
            classification = "stale"
            reasons = ["stable_id_present_in_both_content_same_but_refresh_cadence_exceeded"]
        else:
            classification = "unchanged"
            reasons = ["stable_id_present_in_both_content_same_and_within_cadence"]
        diff_rows.append(
            {
                "id": record_id,
                "level": level,
                "classification": classification,
                "reasons": reasons,
                "baseline_hash": content_hash(base, level) if base else None,
                "target_hash": content_hash(current, level) if current else None,
                "baseline_present": base is not None,
                "target_present": current is not None,
                "source_id": (current or base or {}).get("source_id") if level == "entity" else record_id,
            }
        )
    return diff_rows


def build_classifier_and_diff_reports(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    baseline = fixture["baseline_snapshot"]
    target = fixture["target_snapshot"]
    entity_diffs = classify_records(
        baseline["entities"],
        target["entities"],
        target["observed_at"],
        level="entity",
    )
    source_diffs = classify_records(
        baseline["sources"],
        target["sources"],
        target["observed_at"],
        level="source",
    )
    entity_counts = dict(sorted(Counter(row["classification"] for row in entity_diffs).items()))
    source_counts = dict(sorted(Counter(row["classification"] for row in source_diffs).items()))
    classifier = {
        "schema_version": "citybrain.track7.diff_source_refresh.change_classifier_report.v1",
        "status": "PASS",
        "generated_at": utc_now(),
        "classification_order": CLASSIFICATIONS,
        "rules": {
            "new": "stable id absent from baseline and present in target",
            "changed": "stable id present in both snapshots with content hash change",
            "expired": "stable id present in baseline and absent from target",
            "stale": "stable id present in both snapshots with same content but refresh cadence exceeded",
            "unchanged": "stable id present in both snapshots with same content and within cadence",
        },
        "entity_counts": entity_counts,
        "source_counts": source_counts,
        "expected_counts": fixture["expected_classifications"],
        "expected_counts_match": entity_counts == fixture["expected_classifications"]["entity"]
        and source_counts == fixture["expected_classifications"]["source"],
    }
    entity_report = {
        "schema_version": "citybrain.track7.diff_source_refresh.entity_level_diff_report.v1",
        "status": "PASS",
        "generated_at": utc_now(),
        "baseline_snapshot_id": baseline["snapshot_id"],
        "target_snapshot_id": target["snapshot_id"],
        "counts": entity_counts,
        "diffs": entity_diffs,
        "non_claims": [
            "Entity diffs are fixture-level readiness outputs, not current live claims.",
            "No official action or automated workflow is triggered by any diff.",
        ],
    }
    source_report = {
        "schema_version": "citybrain.track7.diff_source_refresh.source_level_diff_report.v1",
        "status": "PASS",
        "generated_at": utc_now(),
        "baseline_snapshot_id": baseline["snapshot_id"],
        "target_snapshot_id": target["snapshot_id"],
        "counts": source_counts,
        "diffs": source_diffs,
        "non_claims": [
            "Source diffs are fixture-level readiness outputs, not a live source refresh.",
            "No upstream source, ledger, or raw data is modified.",
        ],
    }
    return classifier, entity_report, source_report


def build_comparable_snapshot_detector(
    snapshot_inventory: dict[str, Any],
    fixture: dict[str, Any],
    classifier: dict[str, Any],
) -> dict[str, Any]:
    baseline_sources = {row["id"]: row for row in fixture["baseline_snapshot"]["sources"]}
    target_sources = {row["id"]: row for row in fixture["target_snapshot"]["sources"]}
    comparable = sorted(set(baseline_sources).intersection(target_sources))
    city_source_counts = {
        snapshot["city"]: snapshot["source_count"] for snapshot in snapshot_inventory["source_snapshots"]
    }
    return {
        "schema_version": "citybrain.track7.diff_source_refresh.comparable_snapshot_detector.v1",
        "status": "PASS",
        "generated_at": utc_now(),
        "detector_contract": {
            "requires_snapshot_id": True,
            "requires_observed_at": True,
            "requires_stable_entity_or_source_id": True,
            "compares_content_hash": True,
            "compares_refresh_cadence_for_stale": True,
            "does_not_merge_global_identity": True,
            "does_not_claim_live_current_truth": True,
        },
        "current_inventory_readiness": {
            "source_snapshot_count": snapshot_inventory["snapshot_count"],
            "city_source_counts": city_source_counts,
            "ready_for_future_comparable_snapshots": snapshot_inventory["snapshot_count"] >= 2,
            "future_snapshot_needed": True,
        },
        "designed_fixture_detection": {
            "baseline_snapshot_id": fixture["baseline_snapshot"]["snapshot_id"],
            "target_snapshot_id": fixture["target_snapshot"]["snapshot_id"],
            "comparable_source_ids": comparable,
            "comparable_source_count": len(comparable),
            "classification_contract_pass": classifier["expected_counts_match"],
        },
    }


def write_summary(decision: dict[str, Any], classifier: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Track 7 DIFF / Source Refresh Readiness\n\n"
        f"Status: `{decision['status']}`\n\n"
        "Track 7 now has a read-only snapshot/source-refresh readiness pack. It inventories current source ledgers, "
        "defines comparable snapshot detection, and proves new/changed/expired/stale/unchanged classification with a designed-change fixture.\n\n"
        "## Classifier Counts\n"
        f"- Entity: `{classifier['entity_counts']}`\n"
        f"- Source: `{classifier['source_counts']}`\n\n"
        "## Boundaries\n"
        "- No live source refresh was performed.\n"
        "- No upstream ledgers, raw data, inputs, or credentials were mutated.\n"
        "- Reports are readiness artifacts for future changed snapshots, not current-truth claims.\n",
    )


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.track7.diff_source_refresh.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    branch = current_branch()
    missing_ledgers = [rel(path) for path in CITY_LEDGER_REFS.values() if not path.exists()]
    if branch != "main":
        return {"status": STATUS_BLOCKED, "blocked_reason": "branch_is_not_main", "observed_branch": branch}
    if missing_ledgers:
        return {"status": STATUS_BLOCKED, "blocked_reason": "missing_source_ledgers", "missing_ledgers": missing_ledgers}

    safe_prepare_output_root()
    snapshot_inventory = build_snapshot_inventory()
    refresh_status = build_source_refresh_status(snapshot_inventory)
    fixture = build_designed_change_fixture()
    classifier, entity_report, source_report = build_classifier_and_diff_reports(fixture)
    detector = build_comparable_snapshot_detector(snapshot_inventory, fixture, classifier)
    contract_check = {
        "main_branch_only": branch == "main",
        "read_only_inputs": True,
        "snapshot_inventory_built": snapshot_inventory["snapshot_count"] >= 4,
        "source_refresh_status_built": bool(refresh_status["city_refresh_status_counts"]),
        "comparable_snapshot_detector_built": detector["status"] == "PASS",
        "designed_change_fixture_built": fixture["status"] == "PASS",
        "new_changed_expired_stale_classifier_built": classifier["expected_counts_match"],
        "entity_level_diff_report_built": entity_report["status"] == "PASS",
        "source_level_diff_report_built": source_report["status"] == "PASS",
        "no_live_refresh": True,
        "no_upstream_mutation": True,
        "no_current_truth_claim": True,
    }
    status = STATUS_PASS_LIMITATIONS if all(contract_check.values()) else STATUS_BLOCKED
    decision = {
        "schema_version": "citybrain.track7.diff_source_refresh.decision.v1",
        "status": status,
        "detail_status": "PASS_WITH_LIMITATIONS_TRACK7_DIFF_SOURCE_REFRESH_READINESS"
        if status == STATUS_PASS_LIMITATIONS
        else "BLOCKED_TRACK7_DIFF_SOURCE_REFRESH_READINESS",
        "created_at": utc_now(),
        "branch": branch,
        "track": "Track 7",
        "package": "DIFF_SOURCE_REFRESH_READINESS",
        "contract_check": contract_check,
        "artifacts": sorted(EXPECTED_OUTPUT_FILES),
        "limitations": [
            "Readiness only; future real changed snapshots are still required for production DIFF.",
            "Designed-change fixture proves classifier behavior but is not a live source refresh.",
            "Source refresh status is derived from existing local ledgers and does not fetch upstream sources.",
        ],
        "blockers": [] if status == STATUS_PASS_LIMITATIONS else [key for key, value in contract_check.items() if not value],
    }

    write_json(OUTPUT_ROOT / "SNAPSHOT_INVENTORY.json", snapshot_inventory)
    write_json(OUTPUT_ROOT / "SOURCE_REFRESH_STATUS.json", refresh_status)
    write_json(OUTPUT_ROOT / "COMPARABLE_SNAPSHOT_DETECTOR.json", detector)
    write_json(OUTPUT_ROOT / "DESIGNED_CHANGE_FIXTURE.json", fixture)
    write_json(OUTPUT_ROOT / "CHANGE_CLASSIFIER_REPORT.json", classifier)
    write_json(OUTPUT_ROOT / "ENTITY_LEVEL_DIFF_REPORT.json", entity_report)
    write_json(OUTPUT_ROOT / "SOURCE_LEVEL_DIFF_REPORT.json", source_report)
    write_json(OUTPUT_ROOT / "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json", decision)
    write_summary(decision, classifier)
    manifest = write_hash_manifest()
    return {
        "status": status,
        "decision": decision,
        "snapshot_inventory": snapshot_inventory,
        "source_refresh_status": refresh_status,
        "comparable_snapshot_detector": detector,
        "change_classifier_report": classifier,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = build_outputs()
    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result.get("decision"),
                "hash_manifest": result.get("hash_manifest"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] != STATUS_BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
