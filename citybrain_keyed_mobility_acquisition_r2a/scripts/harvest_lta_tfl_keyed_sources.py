#!/usr/bin/env python3
"""CityBrain keyed mobility harvester for LTA DataMall and TfL.

Secrets are accepted only from environment variables or a local --env-file.
No secrets are written to output reports.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LTA_BASE = "https://datamall2.mytransport.sg/ltaodataservice"
TFL_BASE = "https://api.tfl.gov.uk"
LTA_ENDPOINTS = [
    {"source_id":"lta_busstops", "path":"/BusStops?$skip=0", "city":"Singapore", "domain":"mobility", "smoke":True, "normalization_target":"stop_points"},
    {"source_id":"lta_busroutes", "path":"/BusRoutes?$skip=0", "city":"Singapore", "domain":"mobility", "smoke":True, "normalization_target":"routes"},
    {"source_id":"lta_busservices", "path":"/BusServices?$skip=0", "city":"Singapore", "domain":"mobility", "smoke":True, "normalization_target":"services"},
    {"source_id":"lta_traffic_incidents", "path":"/TrafficIncidents", "city":"Singapore", "domain":"event_fabric/mobility", "smoke":True, "normalization_target":"traffic_incident_events"},
    {"source_id":"lta_roadworks", "path":"/RoadWorks", "city":"Singapore", "domain":"event_fabric/mobility", "smoke":False, "normalization_target":"roadwork_events"},
    {"source_id":"lta_traffic_images_v2", "path":"/Traffic-Imagesv2", "city":"Singapore", "domain":"perception_context/mobility", "smoke":False, "normalization_target":"camera_image_metadata"},
    {"source_id":"lta_taxi_availability", "path":"/Taxi-Availability", "city":"Singapore", "domain":"mobility", "smoke":False, "normalization_target":"taxi_availability_observations"},
    {"source_id":"lta_carpark_availability", "path":"/CarParkAvailabilityv2", "city":"Singapore", "domain":"mobility/public_realm", "smoke":False, "normalization_target":"parking_availability"},
]
TFL_ENDPOINTS = [
    {"source_id":"tfl_line_status_tube", "path":"/Line/Mode/tube/Status", "city":"London", "domain":"mobility", "smoke":True, "normalization_target":"line_status_events"},
    {"source_id":"tfl_road_status_all", "path":"/Road/All/Status", "city":"London", "domain":"mobility/event_fabric", "smoke":True, "normalization_target":"road_status"},
    {"source_id":"tfl_stop_point_tube", "path":"/StopPoint/Mode/tube", "city":"London", "domain":"mobility", "smoke":True, "normalization_target":"stop_points"},
    {"source_id":"tfl_bikepoint", "path":"/BikePoint", "city":"London", "domain":"mobility/public_realm", "smoke":False, "normalization_target":"bike_points"},
    {"source_id":"tfl_air_quality", "path":"/AirQuality", "city":"London", "domain":"environment", "smoke":False, "normalization_target":"air_quality_context"},
    {"source_id":"tfl_disruptions", "path":"/Line/Mode/tube/Disruption", "city":"London", "domain":"event_fabric/mobility", "smoke":False, "normalization_target":"mobility_disruptions"},
]

def load_env_file(path: Optional[str]) -> None:
    if not path: return
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(f"env file not found: {p}")
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def request_json(url: str, headers: Dict[str, str], timeout: int = 30) -> Tuple[Optional[int], bytes, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read(), ""
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return int(e.code), body, str(e)
    except Exception as e:
        return None, b"", f"{type(e).__name__}: {e}"

def classify_status(http_status: Optional[int], err: str, has_key: bool) -> Tuple[str, str]:
    if not has_key: return "MANUAL_OR_KEY_REQUIRED", "KEY_MISSING"
    if http_status in (200, 201): return "PASS_SAMPLE_LANDED", "KEY_ACCEPTED"
    if http_status in (401, 403): return "AUTH_FAILED", "KEY_REJECTED"
    if http_status == 429: return "RATE_LIMITED", "KEY_ACCEPTED_RATE_LIMITED"
    if http_status is None: return "INFRA_BLOCKED_NOT_AUTH_FAILURE", "NOT_TESTED_NETWORK"
    if 500 <= http_status <= 599: return "PROVIDER_ERROR", "KEY_NOT_PROVEN"
    return "FAIL_CLOSED", "KEY_NOT_PROVEN"

def estimate_rows(obj: Any) -> Optional[int]:
    if isinstance(obj, list): return len(obj)
    if isinstance(obj, dict):
        for key in ["value", "features", "items", "results", "lines", "data"]:
            if isinstance(obj.get(key), list): return len(obj[key])
        return 1
    return None

def safe_json_load(body: bytes) -> Tuple[Any, str]:
    if not body: return None, "empty"
    try: return json.loads(body.decode("utf-8-sig")), "json"
    except Exception: return None, "non_json_or_parse_failed"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader()
        for row in rows: w.writerow({k: row.get(k, "") for k in fieldnames})

def harvest_lta(endpoint: Dict[str, Any], key: str, raw_root: Path) -> Dict[str, Any]:
    status, body, err = request_json(LTA_BASE + endpoint["path"], {"AccountKey": key, "accept": "application/json"})
    out_dir = raw_root / "lta" / endpoint["source_id"]; out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = None; parsed, payload_type = safe_json_load(body)
    if body and status in (200, 201):
        sample_path = out_dir / "sample.json"; sample_path.write_bytes(body)
    classified, auth = classify_status(status, err, bool(key))
    return {"source_id": endpoint["source_id"], "provider": "LTA DataMall", "city": endpoint["city"], "domain": endpoint["domain"], "status": classified, "auth_status": auth, "http_status": status, "row_count_estimate": estimate_rows(parsed), "sample_path": str(sample_path) if sample_path else None, "sample_sha256": sha256_file(sample_path) if sample_path else None, "raw_policy": "external_raw_only", "secret_redacted": True, "endpoint_template": endpoint["path"], "normalization_target": endpoint["normalization_target"], "notes": err[:300] if err else payload_type}

def tfl_url(path: str, key: str) -> str:
    return TFL_BASE + path + ("&" if "?" in path else "?") + "app_key=" + urllib.parse.quote(key)

def harvest_tfl(endpoint: Dict[str, Any], primary_key: str, secondary_key: str, raw_root: Path) -> Dict[str, Any]:
    selected = "primary"; key_used = primary_key
    status, body, err = request_json(tfl_url(endpoint["path"], key_used), {"accept": "application/json"}) if key_used else (None, b"", "key missing")
    if status in (401,403) and secondary_key:
        selected = "secondary"; key_used = secondary_key
        status, body, err = request_json(tfl_url(endpoint["path"], key_used), {"accept": "application/json"})
    out_dir = raw_root / "tfl" / endpoint["source_id"]; out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = None; parsed, payload_type = safe_json_load(body)
    if body and status in (200, 201):
        sample_path = out_dir / "sample.json"; sample_path.write_bytes(body)
    classified, auth = classify_status(status, err, bool(key_used))
    if selected == "secondary" and classified.startswith("PASS"): classified = "PASS_WITH_SECONDARY_KEY"
    return {"source_id": endpoint["source_id"], "provider": "Transport for London Unified API", "city": endpoint["city"], "domain": endpoint["domain"], "status": classified, "auth_status": auth, "http_status": status, "row_count_estimate": estimate_rows(parsed), "sample_path": str(sample_path) if sample_path else None, "sample_sha256": sha256_file(sample_path) if sample_path else None, "raw_policy": "external_raw_only", "secret_redacted": True, "endpoint_template": endpoint["path"] + "?app_key=REDACTED", "normalization_target": endpoint["normalization_target"], "notes": (err[:300] if err else payload_type) + f"; key_slot={selected}"}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--raw-root", required=True); ap.add_argument("--env-file")
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--smoke", action="store_true"); g.add_argument("--full", action="store_true")
    args = ap.parse_args(); load_env_file(args.env_file)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    raw_root = Path(args.raw_root); raw_root.mkdir(parents=True, exist_ok=True)
    lta_key = os.environ.get("LTA_DATAMALL_ACCOUNT_KEY", "")
    sdk_key = os.environ.get("LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY", "")
    tfl_primary = os.environ.get("TFL_PRIMARY_KEY", "")
    tfl_secondary = os.environ.get("TFL_SECONDARY_KEY", "")
    rows: List[Dict[str, Any]] = []
    for ep in [e for e in LTA_ENDPOINTS if args.full or e["smoke"]]: rows.append(harvest_lta(ep, lta_key, raw_root)); time.sleep(0.1)
    for ep in [e for e in TFL_ENDPOINTS if args.full or e["smoke"]]: rows.append(harvest_tfl(ep, tfl_primary, tfl_secondary, raw_root)); time.sleep(0.1)
    rows.append({"source_id":"lta_extended_obu_sdk_key", "provider":"LTA Extended OBU Library", "city":"Singapore", "domain":"mobility/sdk", "status":"KEY_PRESENT_NOT_USED_FOR_STANDARD_REST" if sdk_key else "MANUAL_OR_KEY_REQUIRED", "auth_status":"KEY_PRESENT_NOT_VALIDATED" if sdk_key else "KEY_MISSING", "http_status":None, "row_count_estimate":None, "sample_path":None, "sample_sha256":None, "raw_policy":"no_call", "secret_redacted":True, "endpoint_template":"SDK documentation / dedicated SDK task required", "normalization_target":"sdk_specific_obu_records", "notes":"SDK key is tracked separately from REST AccountKey."})
    fields = ["source_id","provider","city","domain","status","auth_status","http_status","row_count_estimate","sample_path","sample_sha256","raw_policy","secret_redacted","endpoint_template","normalization_target","notes"]
    write_csv(out / "SOURCE_STATUS_LEDGER_R2A.csv", rows, fields)
    counts: Dict[str, int] = {}
    for r in rows: counts[r["status"]] = counts.get(r["status"], 0) + 1
    raw_manifest = [{"path":str(p), "bytes":p.stat().st_size, "sha256":sha256_file(p)} for p in raw_root.rglob("*") if p.is_file()]
    (out / "RAW_EXTERNAL_CHECKSUM_MANIFEST_R2A.json").write_text(json.dumps(raw_manifest, indent=2), encoding="utf-8")
    (out / "HARVEST_REPORT_R2A.json").write_text(json.dumps({"run_id":"MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN", "mode":"full" if args.full else "smoke", "status_counts":counts, "credential_presence":{"lta_rest_key":bool(lta_key), "lta_sdk_key":bool(sdk_key), "tfl_primary":bool(tfl_primary), "tfl_secondary":bool(tfl_secondary)}, "secrets_written":False, "raw_root":str(raw_root), "source_count":len(rows)}, indent=2), encoding="utf-8")
    write_csv(out / "SAMPLE_ROW_COUNTS_R2A.csv", [{"source_id":r["source_id"], "row_count_estimate":r.get("row_count_estimate"), "status":r["status"]} for r in rows], ["source_id","row_count_estimate","status"])
    (out / "DOMAIN_FEED_MANIFEST_R2A.json").write_text(json.dumps([{"source_id":r["source_id"], "city":r["city"], "domain":r["domain"], "normalization_target":r["normalization_target"], "status":r["status"], "source_class":"live_or_current_transport_context" if "PASS" in r["status"] else "blocked_or_unvalidated"} for r in rows], indent=2), encoding="utf-8")
    failures = [r for r in rows if r["status"] in {"AUTH_FAILED","INFRA_BLOCKED_NOT_AUTH_FAILURE","FAIL_CLOSED","MANUAL_OR_KEY_REQUIRED","PROVIDER_ERROR","RATE_LIMITED"}]
    (out / "KNOWN_BLOCKERS_RUNTIME.md").write_text("# Known blockers from run\n\n" + "\n".join(f"- {r['source_id']}: {r['status']} / {r['auth_status']} / {r['notes']}" for r in failures) + "\n", encoding="utf-8")
    if any(r["status"].startswith("PASS") for r in rows):
        decision_status = "PASS_KEYED_FULL_WITH_LIMITATIONS" if args.full else "PASS_KEYED_SMOKE_WITH_LIMITATIONS"
    else:
        decision_status = "PARTIAL_KEYED_FULL_NO_PASSING_ENDPOINTS" if args.full else "PARTIAL_KEYED_SMOKE_NO_PASSING_ENDPOINTS"
    (out / "R2A_MASTER_DECISION.json").write_text(json.dumps({"decision_id":"MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A", "status":decision_status, "counts":counts, "secrets_written":False, "no_action_boundary":"transport context only; no dispatch/control/enforcement/certified claim"}, indent=2), encoding="utf-8")
    (out / "CODEX_CLOSEOUT.md").write_text(f"# R2A keyed mobility closeout\n\nStatus: `{decision_status}`\n\nSecrets written: false. Raw payloads are external only.\n", encoding="utf-8")
    print(json.dumps({"status":decision_status, "counts":counts, "out":str(out), "raw_root":str(raw_root)}, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
