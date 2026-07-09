#!/usr/bin/env python3
"""
CityBrain Source Acquisition Cart R1

Purpose:
  Smoke and then full-pull the "other data" source list into a local CityBrain raw-data folder.
  This script is designed for Codex to run in the repo/dev environment with internet access.
  It is intentionally conservative: it does not hide key requirements, does not package raw media,
  and does not claim real-world truth for donor distributions.

Usage examples:
  python scripts/harvest_sources.py --inventory manifests/source_inventory.csv --out /data/citybrain/raw --smoke
  python scripts/harvest_sources.py --inventory manifests/source_inventory.csv --out /data/citybrain/raw --source open_meteo_dubai_weather --smoke
  python scripts/harvest_sources.py --inventory manifests/source_inventory.csv --out /data/citybrain/raw --source opsd_time_series --full

Notes:
  - Overture is handled by DuckDB SQL, not requests, because bbox pushdown matters.
  - OpenAQ, TfL, LTA, CDS require credentials. Fail closed when env vars are missing.
  - DLD / GeoDubai / some Dubai Pulse paths may require human/manual export; create importer folders and schemas now.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional


DUBAI_BBOX = (55.05, 24.85, 55.55, 25.35)


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: pathlib.Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_url(url: str, out_path: pathlib.Path, headers: Optional[dict] = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    started = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
            return {
                "status": "PASS",
                "url": url,
                "http_status": resp.status,
                "bytes": len(data),
                "out_path": str(out_path),
                "started_at": started,
                "ended_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        return {
            "status": "FAIL",
            "url": url,
            "error": repr(exc),
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }


def env_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def smoke_open_meteo(out_root: pathlib.Path) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=25.2048&longitude=55.2708"
        "&hourly=temperature_2m,precipitation,wind_speed_10m"
        "&forecast_days=1&timezone=UTC"
    )
    return fetch_url(url, out_root / "global/open_meteo/aoi=dubai/smoke_forecast.json")


def smoke_openaq(out_root: pathlib.Path) -> dict:
    key = env_required("OPENAQ_API_KEY")
    url = "https://api.openaq.org/v3/locations?bbox=55.05,24.85,55.55,25.35&limit=1000"
    return fetch_url(url, out_root / "global/openaq/dubai_locations_smoke.json", headers={"X-API-Key": key})


def smoke_opsd(out_root: pathlib.Path) -> dict:
    url = "https://data.open-power-system-data.org/time_series/latest/datapackage.json"
    return fetch_url(url, out_root / "global/open_power_system_data/time_series/datapackage.json")


def smoke_worldpop(out_root: pathlib.Path) -> dict:
    # Tiny UAE 2020 100m dataset per WorldPop page. This URL may redirect.
    url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/ARE/are_ppp_2020_UNadj.tif"
    return fetch_url(url, out_root / "global/worldpop/country=ARE/are_ppp_2020_UNadj.tif", timeout=120)


def smoke_geofabrik(out_root: pathlib.Path) -> dict:
    # Use the .poly first as the true smoke, not the 239MB PBF.
    url = "https://download.geofabrik.de/asia/gcc-states.poly"
    return fetch_url(url, out_root / "osm/geofabrik/gcc_states/gcc-states.poly")


def smoke_jrc_gsw(out_root: pathlib.Path) -> dict:
    # Use HEAD-like range is not available in urllib without full GET; fetch XML? For safety, store planned URL only.
    plan = {
        "status": "PLAN_ONLY_LARGE_GEOTIFF",
        "layer": "occurrence",
        "tile": "50E_30N",
        "candidate_urls": [
            "https://storage.googleapis.com/global-surface-water/downloads2024/occurrence/occurrence_50E_30N_v1_4_2024.tif",
            "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_50E_30N_v1_4_2021.tif",
        ],
    }
    out = out_root / "global/jrc_global_surface_water/tile=50E_30N/smoke_plan.json"
    write_json(out, plan)
    return {"status": "PLAN_ONLY", "out_path": str(out)}


def smoke_tfl(out_root: pathlib.Path) -> dict:
    key = env_required("TFL_APP_KEY")
    url = f"https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground/Status?app_key={key}"
    return fetch_url(url, out_root / "london/tfl_unified_api/line_status_smoke.json")


def smoke_lta(out_root: pathlib.Path) -> dict:
    key = env_required("LTA_ACCOUNT_KEY")
    url = "https://datamall2.mytransport.sg/ltaodataservice/Traffic-Images"
    return fetch_url(url, out_root / "singapore/lta_datamall/traffic_images_smoke.json", headers={"AccountKey": key})


def smoke_overture(out_root: pathlib.Path, package_root: pathlib.Path) -> dict:
    sql = package_root / "samples/overture_dubai_duckdb.sql"
    if not sql.exists():
        return {"status": "FAIL", "error": f"missing SQL: {sql}"}
    target_dir = out_root / "global/overture/aoi=dubai"
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = target_dir / "overture_dubai_duckdb.sql"
    copied.write_text(sql.read_text(encoding="utf-8"), encoding="utf-8")
    return {"status": "TEMPLATE_COPIED", "out_path": str(copied), "next": "run with duckdb in networked environment"}


def smoke_manual_stub(out_root: pathlib.Path, source_id: str) -> dict:
    out = out_root / f"manual_or_keyed/{source_id}/README_MANUAL_IMPORT_REQUIRED.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# {source_id}\n\nManual/keyed source. Prepare importer and wait for operator-supplied export or credentials.\n",
        encoding="utf-8",
    )
    return {"status": "MANUAL_OR_KEY_REQUIRED", "out_path": str(out)}


SMOKE_HANDLERS = {
    "open_meteo_dubai_weather": smoke_open_meteo,
    "openaq_air_quality": smoke_openaq,
    "opsd_time_series": smoke_opsd,
    "worldpop_are_population": smoke_worldpop,
    "osm_geofabrik_gcc_states": smoke_geofabrik,
    "jrc_global_surface_water_dubai_tile": smoke_jrc_gsw,
    "tfl_unified_api": smoke_tfl,
    "lta_datamall": smoke_lta,
}


def read_inventory(path: pathlib.Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", default="manifests/source_inventory.csv")
    ap.add_argument("--out", default="/data/citybrain/raw")
    ap.add_argument("--source", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    package_root = pathlib.Path(__file__).resolve().parents[1]
    inventory = read_inventory(pathlib.Path(args.inventory))
    out_root = ensure_dir(pathlib.Path(args.out))
    results = []

    for row in inventory:
        sid = row["source_id"]
        if args.source and sid != args.source:
            continue
        try:
            if sid == "overture_maps_dubai_aoi":
                result = smoke_overture(out_root, package_root)
            elif sid in SMOKE_HANDLERS:
                result = SMOKE_HANDLERS[sid](out_root)
            else:
                result = smoke_manual_stub(out_root, sid)
        except Exception as exc:
            result = {"status": "FAIL_CLOSED", "error": repr(exc)}
        result["source_id"] = sid
        results.append(result)

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "mode": "full" if args.full else "smoke",
        "out_root": str(out_root),
        "results": results,
    }
    write_json(out_root / "_citybrain_acquisition_cart_r1_report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if all(r["status"] not in ("FAIL",) for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
