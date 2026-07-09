#!/usr/bin/env python3
"""R2E keyed mobility depth-pull harvester.

This script deepens the R2A LTA/TfL proof while preserving security boundaries:
- keys only from env or --env-file
- successful 200/201 payloads only are stored under external raw root
- failed response bodies are never persisted
- logs use redacted URL templates
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

LTA_BASE = "https://datamall2.mytransport.sg/ltaodataservice"
TFL_BASE = "https://api.tfl.gov.uk"
PAGE_SIZE = 500
CLIENT_HEADERS = {
    "User-Agent": "CityBrain-R2E/1.0",
    "Accept": "application/json",
}

DEFAULT_TFL_MODES = ["tube", "dlr", "elizabeth-line", "overground", "tram", "national-rail", "bus"]

ENDPOINTS: List[Dict[str, Any]] = [
    {"source_id":"lta_busstops_full", "provider":"LTA DataMall", "endpoint_template":"/BusStops?$skip={skip}", "strategy":"lta_skip_pagination_500", "smoke":True, "city":"Singapore", "domain":"mobility", "normalization_target":"stop_points", "source_class":"donor_context_mobility"},
    {"source_id":"lta_busroutes_full", "provider":"LTA DataMall", "endpoint_template":"/BusRoutes?$skip={skip}", "strategy":"lta_skip_pagination_500", "smoke":True, "city":"Singapore", "domain":"mobility", "normalization_target":"route_stop_sequence", "source_class":"donor_context_mobility"},
    {"source_id":"lta_busservices_full", "provider":"LTA DataMall", "endpoint_template":"/BusServices?$skip={skip}", "strategy":"lta_skip_pagination_500", "smoke":True, "city":"Singapore", "domain":"mobility", "normalization_target":"transit_services", "source_class":"donor_context_mobility"},
    {"source_id":"lta_roadworks_full", "provider":"LTA DataMall", "endpoint_template":"/RoadWorks?$skip={skip}", "strategy":"lta_skip_pagination_500", "smoke":False, "city":"Singapore", "domain":"event_fabric/mobility", "normalization_target":"roadwork_events", "source_class":"donor_context_mobility_event"},
    {"source_id":"lta_traffic_incidents_snapshot", "provider":"LTA DataMall", "endpoint_template":"/TrafficIncidents", "strategy":"lta_snapshot", "smoke":True, "city":"Singapore", "domain":"event_fabric/mobility", "normalization_target":"traffic_incident_events", "source_class":"donor_context_mobility_event"},
    {"source_id":"lta_traffic_images_v2_snapshot", "provider":"LTA DataMall", "endpoint_template":"/Traffic-Imagesv2", "strategy":"lta_snapshot", "smoke":False, "city":"Singapore", "domain":"perception_context/mobility", "normalization_target":"traffic_camera_metadata", "source_class":"donor_context_media_metadata"},
    {"source_id":"lta_taxi_availability_snapshot", "provider":"LTA DataMall", "endpoint_template":"/Taxi-Availability", "strategy":"lta_snapshot", "smoke":False, "city":"Singapore", "domain":"mobility", "normalization_target":"taxi_availability_observations", "source_class":"donor_context_mobility_observation"},
    {"source_id":"lta_carpark_availability_snapshot", "provider":"LTA DataMall", "endpoint_template":"/CarParkAvailabilityv2", "strategy":"lta_snapshot", "smoke":False, "city":"Singapore", "domain":"mobility/public_realm", "normalization_target":"parking_availability_observations", "source_class":"donor_context_mobility_observation"},
    {"source_id":"lta_bus_arrival_sample_optional", "provider":"LTA DataMall", "endpoint_template":"/BusArrivalv2?BusStopCode={bus_stop_code}", "strategy":"lta_bus_arrival_sample_from_stops", "smoke":False, "city":"Singapore", "domain":"event_fabric/mobility", "normalization_target":"bus_arrival_observations", "source_class":"donor_context_mobility_observation", "optional": True},
    {"source_id":"tfl_line_status_by_mode", "provider":"TfL Unified API", "endpoint_template":"/Line/Mode/{mode}/Status", "strategy":"tfl_mode_matrix", "smoke":True, "city":"London", "domain":"mobility", "normalization_target":"line_status_events", "source_class":"donor_context_mobility"},
    {"source_id":"tfl_line_disruption_by_mode", "provider":"TfL Unified API", "endpoint_template":"/Line/Mode/{mode}/Disruption", "strategy":"tfl_mode_matrix", "smoke":False, "city":"London", "domain":"event_fabric/mobility", "normalization_target":"line_disruption_events", "source_class":"donor_context_mobility_event"},
    {"source_id":"tfl_stoppoint_by_mode", "provider":"TfL Unified API", "endpoint_template":"/StopPoint/Mode/{mode}", "strategy":"tfl_mode_matrix", "smoke":True, "city":"London", "domain":"mobility", "normalization_target":"stop_points", "source_class":"donor_context_mobility"},
    {"source_id":"tfl_road_status_all", "provider":"TfL Unified API", "endpoint_template":"/Road/all/Status", "strategy":"tfl_snapshot", "smoke":True, "city":"London", "domain":"mobility/event_fabric", "normalization_target":"road_status", "source_class":"donor_context_mobility_event"},
    {"source_id":"tfl_road_disruptions_all_optional", "provider":"TfL Unified API", "endpoint_template":"/Road/all/Disruption", "strategy":"tfl_snapshot", "smoke":False, "city":"London", "domain":"event_fabric/mobility", "normalization_target":"road_disruption_events", "source_class":"donor_context_mobility_event", "optional": True},
    {"source_id":"tfl_bikepoint_all", "provider":"TfL Unified API", "endpoint_template":"/BikePoint", "strategy":"tfl_snapshot", "smoke":False, "city":"London", "domain":"mobility/public_realm", "normalization_target":"bike_points", "source_class":"donor_context_mobility_observation"},
    {"source_id":"tfl_air_quality", "provider":"TfL Unified API", "endpoint_template":"/AirQuality", "strategy":"tfl_snapshot", "smoke":False, "city":"London", "domain":"environment/mobility_context", "normalization_target":"air_quality_context", "source_class":"donor_context_environment"},
    {"source_id":"tfl_accident_stats_recent_optional", "provider":"TfL Unified API", "endpoint_template":"/AccidentStats/{year}", "strategy":"tfl_year_matrix_optional", "smoke":False, "city":"London", "domain":"mobility/safety_context", "normalization_target":"historical_collision_context", "source_class":"donor_context_mobility_safety", "optional": True},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: Optional[str]) -> None:
    if not path:
        return
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"env file not found: {p}")
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_json_load(body: bytes) -> Tuple[Any, str]:
    if not body:
        return None, "empty"
    try:
        return json.loads(body.decode("utf-8-sig")), "json"
    except Exception:
        return None, "non_json_or_parse_failed"


def get_items(obj: Any) -> List[Any]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("value", "features", "items", "results", "lines", "data", "places", "stopPoints"):
            if isinstance(obj.get(key), list):
                return obj[key]
    return [obj] if obj is not None else []


def count_items(obj: Any) -> int:
    return len(get_items(obj))


def request_bytes(url: str, headers: Dict[str, str], timeout: int) -> Tuple[Optional[int], bytes, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read(), ""
    except urllib.error.HTTPError as e:
        # Do not return body. Some providers may echo request metadata or key values.
        return int(e.code), b"", f"HTTPError: {e.code}"
    except Exception as e:
        return None, b"", f"{type(e).__name__}: {e}"


def classify_status(http_status: Optional[int], has_key: bool, rows: int = 0) -> Tuple[str, str]:
    if not has_key:
        return "MANUAL_OR_KEY_REQUIRED", "KEY_MISSING"
    if http_status in (200, 201):
        return ("PASS_DEPTH_PAGE_OR_SNAPSHOT_LANDED" if rows else "PASS_EMPTY_VALID_RESPONSE"), "KEY_ACCEPTED"
    if http_status in (401, 403):
        return "AUTH_FAILED", "KEY_REJECTED_OR_CLIENT_BLOCKED"
    if http_status == 429:
        return "RATE_LIMITED", "KEY_ACCEPTED_RATE_LIMITED"
    if http_status is None:
        return "INFRA_BLOCKED_NOT_AUTH_FAILURE", "NOT_TESTED_NETWORK"
    if 500 <= http_status <= 599:
        return "PROVIDER_ERROR", "KEY_NOT_PROVEN"
    return "FAIL_CLOSED", "KEY_NOT_PROVEN"


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def save_success_payload(raw_root: Path, provider_slug: str, source_id: str, name: str, body: bytes) -> Path:
    out_dir = raw_root / provider_slug / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.=-]+", "_", name)[:180]
    path = out_dir / f"{safe_name}.json"
    path.write_bytes(body)
    return path


def make_lta_url(path: str, **params: Any) -> str:
    return LTA_BASE + path.format(**params)


def make_tfl_url(path: str, key: str, **params: Any) -> str:
    p = path.format(**params)
    return TFL_BASE + p + ("&" if "?" in p else "?") + "app_key=" + urllib.parse.quote(key)


def harvest_lta_paginated(ep: Dict[str, Any], key: str, raw_root: Path, max_pages: int, smoke: bool, timeout: int, sleep_sec: float) -> Dict[str, Any]:
    all_sample_rows: List[Dict[str, Any]] = []
    page_hashes: set[str] = set()
    pages = 0
    total_rows = 0
    last_status: Optional[int] = None
    last_note = ""
    sample_sha256s: List[str] = []
    max_pages_effective = 1 if smoke else max_pages
    for page_idx in range(max_pages_effective):
        skip = page_idx * PAGE_SIZE
        url = make_lta_url(ep["endpoint_template"], skip=skip)
        status, body, err = request_bytes(url, {**CLIENT_HEADERS, "AccountKey": key, "accept": "application/json"}, timeout)
        last_status = status
        parsed, payload_type = safe_json_load(body)
        rows = get_items(parsed)
        row_count = len(rows)
        if status not in (200, 201):
            last_note = err or payload_type
            break
        if body:
            body_hash = sha256_bytes(body)
            if body_hash in page_hashes:
                last_note = "repeated_page_hash_stop"
                break
            page_hashes.add(body_hash)
            p = save_success_payload(raw_root, "lta", ep["source_id"], f"skip={skip}", body)
            sample_sha256s.append(sha256_file(p))
        pages += 1
        total_rows += row_count
        for item in rows[:50]:
            all_sample_rows.append(make_sample_record(ep, item, f"skip={skip}"))
        if row_count < PAGE_SIZE:
            last_note = "short_or_empty_page_stop"
            break
        time.sleep(sleep_sec)
    status_class, auth = classify_status(last_status, bool(key), total_rows)
    return ledger_row(ep, status_class, auth, last_status, pages, total_rows, sample_sha256s, last_note or "ok", ep["endpoint_template"])


def harvest_lta_snapshot(ep: Dict[str, Any], key: str, raw_root: Path, timeout: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    url = make_lta_url(ep["endpoint_template"])
    status, body, err = request_bytes(url, {**CLIENT_HEADERS, "AccountKey": key, "accept": "application/json"}, timeout)
    parsed, payload_type = safe_json_load(body)
    rows = get_items(parsed)
    hashes: List[str] = []
    if status in (200, 201) and body:
        p = save_success_payload(raw_root, "lta", ep["source_id"], "snapshot", body)
        hashes.append(sha256_file(p))
    status_class, auth = classify_status(status, bool(key), len(rows))
    return ledger_row(ep, status_class, auth, status, 1 if status in (200, 201) else 0, len(rows), hashes, err or payload_type, ep["endpoint_template"]), [make_sample_record(ep, item, "snapshot") for item in rows[:100]]


def harvest_tfl_endpoint(ep: Dict[str, Any], primary_key: str, secondary_key: str, raw_root: Path, timeout: int, **params: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    key_slot = "primary"
    key_used = primary_key
    if not key_used:
        status, body, err = None, b"", "primary key missing"
    else:
        status, body, err = request_bytes(make_tfl_url(ep["endpoint_template"], key_used, **params), CLIENT_HEADERS, timeout)
    if status in (401, 403) and secondary_key:
        key_slot = "secondary"
        key_used = secondary_key
        status, body, err = request_bytes(make_tfl_url(ep["endpoint_template"], key_used, **params), CLIENT_HEADERS, timeout)
    parsed, payload_type = safe_json_load(body)
    rows = get_items(parsed)
    hashes: List[str] = []
    if status in (200, 201) and body:
        tag = "_".join(f"{k}={v}" for k, v in sorted(params.items())) or "snapshot"
        p = save_success_payload(raw_root, "tfl", ep["source_id"], tag, body)
        hashes.append(sha256_file(p))
    status_class, auth = classify_status(status, bool(key_used), len(rows))
    if key_slot == "secondary" and status_class.startswith("PASS"):
        status_class = "PASS_DEPTH_WITH_SECONDARY_KEY"
    endpoint_template = ep["endpoint_template"].format(**{k: str(v) for k, v in params.items()}) + "?app_key=REDACTED"
    note = (err or payload_type) + f"; key_slot={key_slot}; params={params}"
    return ledger_row(ep, status_class, auth, status, 1 if status in (200, 201) else 0, len(rows), hashes, note, endpoint_template), [make_sample_record(ep, item, str(params) if params else "snapshot") for item in rows[:100]]


def ledger_row(ep: Dict[str, Any], status: str, auth: str, http_status: Optional[int], pages: int, rows: int, hashes: List[str], notes: str, endpoint_template: str) -> Dict[str, Any]:
    return {
        "source_id": ep["source_id"],
        "provider": ep["provider"],
        "city": ep["city"],
        "domain": ep["domain"],
        "status": status,
        "auth_status": auth,
        "http_status": http_status,
        "pages_fetched": pages,
        "row_count_estimate": rows,
        "sample_sha256s": ";".join(hashes),
        "raw_policy": "external_raw_success_only",
        "secret_redacted": True,
        "endpoint_template": endpoint_template,
        "normalization_target": ep["normalization_target"],
        "source_class": ep["source_class"],
        "donor_context_only": True,
        "not_dubai_truth": True,
        "notes": (notes or "")[:500],
    }


def make_sample_record(ep: Dict[str, Any], item: Any, page_ref: str) -> Dict[str, Any]:
    # Keep a tiny bounded sample, not the full raw payload.
    if isinstance(item, dict):
        compact = {k: item.get(k) for k in list(item.keys())[:12]}
    else:
        compact = {"value": item}
    return {
        "source_id": ep["source_id"],
        "provider": ep["provider"],
        "city": ep["city"],
        "source_class": ep["source_class"],
        "donor_context_only": True,
        "not_dubai_truth": True,
        "normalization_target": ep["normalization_target"],
        "page_ref": page_ref,
        "sample_payload_compact": compact,
        "limitation_refs": ["R2E_DONOR_CONTEXT_ONLY", "NOT_DUBAI_TRUTH", "NO_ACTION_OR_CERTIFIED_CLAIM"],
    }


def scan_for_secrets(paths: Iterable[Path], secret_values: Iterable[str]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    secrets = [s for s in secret_values if s]
    for base in paths:
        if not base.exists():
            continue
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in files:
            try:
                data = p.read_bytes()
            except Exception:
                continue
            for idx, secret in enumerate(secrets):
                if secret.encode("utf-8") in data:
                    findings.append({"path": str(p), "secret_index": idx})
    return {"passed": not findings, "findings": findings, "scanned_roots": [str(p) for p in paths], "secret_count": len(secrets)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw-root", required=True)
    ap.add_argument("--env-file")
    ap.add_argument("--mode", choices=["smoke", "depth"], required=True)
    ap.add_argument("--max-lta-pages", type=int, default=2000)
    ap.add_argument("--sleep-sec", type=float, default=0.05)
    ap.add_argument("--timeout-sec", type=int, default=45)
    ap.add_argument("--tfl-modes", default=",".join(DEFAULT_TFL_MODES))
    ap.add_argument("--tfl-years", default="2023,2024,2025")
    ap.add_argument("--include-optional", action="store_true")
    ap.add_argument("--bus-arrival-sample-size", type=int, default=0)
    args = ap.parse_args()

    load_env_file(args.env_file)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    raw_root = Path(args.raw_root); raw_root.mkdir(parents=True, exist_ok=True)

    lta_key = os.environ.get("LTA_DATAMALL_ACCOUNT_KEY", "")
    sdk_key = os.environ.get("LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY", "")
    tfl_primary = os.environ.get("TFL_PRIMARY_KEY", "")
    tfl_secondary = os.environ.get("TFL_SECONDARY_KEY", "")

    smoke = args.mode == "smoke"
    tfl_modes = [m.strip() for m in args.tfl_modes.split(",") if m.strip()]
    tfl_years = [y.strip() for y in args.tfl_years.split(",") if y.strip()]
    ledger: List[Dict[str, Any]] = []
    samples: List[Dict[str, Any]] = []

    # LTA first, so bus-stop samples can be reused for optional arrivals later.
    bus_stop_codes: List[str] = []
    for ep in ENDPOINTS:
        if smoke and not ep.get("smoke"):
            continue
        if ep.get("optional") and not args.include_optional:
            continue
        strategy = ep["strategy"]
        if ep["provider"] == "LTA DataMall":
            if strategy == "lta_skip_pagination_500":
                row = harvest_lta_paginated(ep, lta_key, raw_root, args.max_lta_pages, smoke, args.timeout_sec, args.sleep_sec)
                ledger.append(row)
                # Try to collect bus stop codes only from saved successful pages.
                if ep["source_id"] == "lta_busstops_full":
                    for raw_file in (raw_root / "lta" / ep["source_id"]).glob("*.json"):
                        parsed, _ = safe_json_load(raw_file.read_bytes())
                        for item in get_items(parsed):
                            if isinstance(item, dict) and item.get("BusStopCode"):
                                bus_stop_codes.append(str(item["BusStopCode"]))
                            if len(bus_stop_codes) >= max(args.bus_arrival_sample_size, 0):
                                break
                        if len(bus_stop_codes) >= max(args.bus_arrival_sample_size, 0):
                            break
            elif strategy == "lta_snapshot":
                row, ss = harvest_lta_snapshot(ep, lta_key, raw_root, args.timeout_sec)
                ledger.append(row); samples.extend(ss)
            elif strategy == "lta_bus_arrival_sample_from_stops":
                if args.bus_arrival_sample_size <= 0:
                    ledger.append(ledger_row(ep, "SKIPPED_OPTIONAL_BY_CONFIG", "NOT_CALLED", None, 0, 0, [], "Set --bus-arrival-sample-size > 0 to call", ep["endpoint_template"]))
                else:
                    total = 0; pages = 0; hashes: List[str] = []
                    for code in bus_stop_codes[: args.bus_arrival_sample_size]:
                        path = ep["endpoint_template"].format(bus_stop_code=urllib.parse.quote(code))
                        status, body, err = request_bytes(LTA_BASE + path, {**CLIENT_HEADERS, "AccountKey": lta_key, "accept": "application/json"}, args.timeout_sec)
                        parsed, payload_type = safe_json_load(body)
                        rows = get_items(parsed); total += len(rows); pages += 1 if status in (200, 201) else 0
                        if status in (200, 201) and body:
                            p = save_success_payload(raw_root, "lta", ep["source_id"], f"BusStopCode={code}", body)
                            hashes.append(sha256_file(p))
                        time.sleep(args.sleep_sec)
                    status_class = "PASS_DEPTH_PAGE_OR_SNAPSHOT_LANDED" if pages else "FAIL_CLOSED"
                    ledger.append(ledger_row(ep, status_class, "KEY_ACCEPTED" if pages else "KEY_NOT_PROVEN", 200 if pages else None, pages, total, hashes, f"sampled_bus_stops={len(bus_stop_codes[:args.bus_arrival_sample_size])}", ep["endpoint_template"]))
        elif ep["provider"] == "TfL Unified API":
            if strategy == "tfl_mode_matrix":
                for mode in tfl_modes if not smoke else tfl_modes[:3]:
                    ep2 = {**ep, "source_id": f"{ep['source_id']}_{mode}"}
                    row, ss = harvest_tfl_endpoint(ep2, tfl_primary, tfl_secondary, raw_root, args.timeout_sec, mode=mode)
                    ledger.append(row); samples.extend(ss)
                    time.sleep(args.sleep_sec)
            elif strategy in {"tfl_snapshot", "tfl_snapshot_optional"}:
                row, ss = harvest_tfl_endpoint(ep, tfl_primary, tfl_secondary, raw_root, args.timeout_sec)
                ledger.append(row); samples.extend(ss)
            elif strategy == "tfl_year_matrix_optional":
                for year in tfl_years if not smoke else tfl_years[-1:]:
                    ep2 = {**ep, "source_id": f"{ep['source_id']}_{year}"}
                    row, ss = harvest_tfl_endpoint(ep2, tfl_primary, tfl_secondary, raw_root, args.timeout_sec, year=year)
                    ledger.append(row); samples.extend(ss)
                    time.sleep(args.sleep_sec)

    # SDK key tracking, no call.
    ledger.append({
        "source_id": "lta_extended_obu_sdk_key",
        "provider": "LTA Extended OBU Library",
        "city": "Singapore",
        "domain": "mobility/sdk",
        "status": "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST" if sdk_key else "MANUAL_OR_KEY_REQUIRED",
        "auth_status": "KEY_PRESENT_NOT_VALIDATED" if sdk_key else "KEY_MISSING",
        "http_status": None,
        "pages_fetched": 0,
        "row_count_estimate": 0,
        "sample_sha256s": "",
        "raw_policy": "no_call",
        "secret_redacted": True,
        "endpoint_template": "SDK documentation / dedicated SDK task required",
        "normalization_target": "sdk_specific_obu_records",
        "source_class": "sdk_key_only_not_called",
        "donor_context_only": True,
        "not_dubai_truth": True,
        "notes": "SDK key is tracked separately from standard REST acquisition.",
    })

    fields = ["source_id","provider","city","domain","status","auth_status","http_status","pages_fetched","row_count_estimate","sample_sha256s","raw_policy","secret_redacted","endpoint_template","normalization_target","source_class","donor_context_only","not_dubai_truth","notes"]
    write_csv(out / "SOURCE_STATUS_LEDGER_R2E.csv", ledger, fields)
    write_csv(out / "SAMPLE_ROW_COUNTS_R2E.csv", [{"source_id": r["source_id"], "row_count_estimate": r.get("row_count_estimate"), "pages_fetched": r.get("pages_fetched"), "status": r["status"]} for r in ledger], ["source_id","row_count_estimate","pages_fetched","status"])

    with (out / "NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl").open("w", encoding="utf-8") as f:
        for rec in samples[:5000]:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    raw_manifest = [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in raw_root.rglob("*") if p.is_file()]
    (out / "RAW_EXTERNAL_CHECKSUM_MANIFEST_R2E.json").write_text(json.dumps(raw_manifest, indent=2), encoding="utf-8")

    counts: Dict[str, int] = {}
    for row in ledger:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    feed_manifest = [{
        "source_id": r["source_id"],
        "provider": r["provider"],
        "city": r["city"],
        "domain": r["domain"],
        "normalization_target": r["normalization_target"],
        "source_class": r["source_class"],
        "status": r["status"],
        "donor_context_only": True,
        "not_dubai_truth": True,
        "eligible_for_synthetic_factory_distribution_donor": r["status"].startswith("PASS"),
    } for r in ledger]
    (out / "DOMAIN_FEED_MANIFEST_R2E.json").write_text(json.dumps(feed_manifest, indent=2), encoding="utf-8")

    http_policy = {
        "required_headers": CLIENT_HEADERS,
        "failure_body_policy": "Do not persist failed response bodies.",
        "success_payload_policy": "Persist only 200/201 payloads under external raw root.",
        "tfL_auth_logging": "Redact app_key in all persisted endpoint templates.",
        "lta_auth_logging": "Do not persist AccountKey header.",
    }
    (out / "HTTP_CLIENT_POLICY_REPORT_R2E.json").write_text(json.dumps(http_policy, indent=2), encoding="utf-8")

    secret_scan = scan_for_secrets([out, raw_root], [lta_key, sdk_key, tfl_primary, tfl_secondary])
    (out / "SECRET_SCAN_REPORT_R2E.json").write_text(json.dumps(secret_scan, indent=2), encoding="utf-8")

    blockers = [r for r in ledger if r["status"] in {"AUTH_FAILED", "RATE_LIMITED", "INFRA_BLOCKED_NOT_AUTH_FAILURE", "PROVIDER_ERROR", "FAIL_CLOSED", "MANUAL_OR_KEY_REQUIRED"}]
    (out / "KNOWN_BLOCKERS_RUNTIME_R2E.md").write_text("# Known blockers from R2E run\n\n" + "\n".join(f"- {r['source_id']}: {r['status']} / {r['auth_status']} / {r['notes']}" for r in blockers) + "\n", encoding="utf-8")

    pass_count = sum(1 for r in ledger if r["status"].startswith("PASS"))
    status = "PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS" if pass_count else "PARTIAL_R2E_NO_PASSING_ENDPOINTS"
    decision = {
        "decision_id": "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL",
        "status": status,
        "mode": args.mode,
        "status_counts": counts,
        "pass_count": pass_count,
        "source_count": len(ledger),
        "raw_root": str(raw_root),
        "secrets_written": False,
        "secret_scan_passed": bool(secret_scan["passed"]),
        "boundary": "LTA/TfL are donor/context mobility feeds, not Dubai truth; no dispatch/control/enforcement/legal/certified claim.",
        "generated_at": now_iso(),
    }
    (out / "R2E_MASTER_DECISION.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    (out / "DEPTH_PULL_REPORT_R2E.json").write_text(json.dumps({**decision, "credential_presence": {"lta_rest_key": bool(lta_key), "lta_sdk_key": bool(sdk_key), "tfl_primary": bool(tfl_primary), "tfl_secondary": bool(tfl_secondary)}, "raw_file_count": len(raw_manifest), "normalized_sample_rows": min(len(samples), 5000)}, indent=2), encoding="utf-8")
    (out / "CODEX_CLOSEOUT.md").write_text(f"# R2E keyed mobility depth-pull closeout\n\nStatus: `{status}`\n\nRaw root: `{raw_root}`\n\nSecrets written: false. LTA/TfL remain donor/context only.\n", encoding="utf-8")

    print(json.dumps({"status": status, "counts": counts, "out": str(out), "raw_root": str(raw_root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
