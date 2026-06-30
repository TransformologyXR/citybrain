import json
from pathlib import Path

import pandas as pd

base = Path("/data/london_d9/outputs/lon_d9b_london_identity_build")
edges_path = base / "canonical" / "london_identity_edges.parquet"
roads_path = base / "canonical" / "london_usrn_road_segments.parquet"

edges = pd.read_parquet(edges_path, columns=["dst", "relation"])
usrn_ids = set(edges.loc[edges["relation"] == "on_street", "dst"].astype(str))
roads = pd.read_parquet(roads_path)
existing = set(roads["canonical_id"].astype(str))
missing = sorted(usrn_ids - existing)

if missing:
    fallback = pd.DataFrame(
        {
            "canonical_id": missing,
            "entity_type": "road_segment",
            "usrn": [item.rsplit(":", 1)[-1] for item in missing],
            "street_type": None,
            "geometry_wkt": None,
            "geometry_status": "no_geometry_fallback_for_lids_referenced_usrn",
        }
    )
    roads = pd.concat([roads, fallback], ignore_index=True)
    roads.to_parquet(roads_path, index=False)

report_path = base / "LON_D9B_GEOMETRY_COVERAGE_REPORT.json"
if report_path.exists():
    report = json.load(open(report_path, encoding="utf-8"))
else:
    report = {}
report.setdefault("road_geometry", {})
report["road_geometry"]["no_geometry_fallback_for_lids_referenced_usrn"] = len(missing)
json.dump(report, open(report_path, "w", encoding="utf-8"), indent=2, sort_keys=True)

harness_path = base / "LON_D9B_HARNESS_REPORT.json"
if harness_path.exists():
    harness = json.load(open(harness_path, encoding="utf-8"))
    harness.setdefault("geometry", {}).setdefault("road_geometry", {})
    harness["geometry"]["road_geometry"]["no_geometry_fallback_for_lids_referenced_usrn"] = len(missing)
    harness["usrn_road_segments"] = int(len(roads))
    json.dump(harness, open(harness_path, "w", encoding="utf-8"), indent=2, sort_keys=True)

print({"missing_added": len(missing), "road_segments": len(roads)})
