import json
import pandas as pd

base = "/data/london_d9/outputs"
print(json.load(open(f"{base}/lon_d9e_london_serious_graph/LON_D9E_HARNESS_REPORT.json"))["edge_integrity"])
print(json.load(open(f"{base}/lon_d9b_london_identity_build/LON_D9B_HARNESS_REPORT.json"))["edge_counts_by_relation"])
roads = pd.read_parquet(f"{base}/lon_d9b_london_identity_build/canonical/london_usrn_road_segments.parquet")
print("road_segments", len(roads))
edges = pd.read_parquet(f"{base}/lon_d9b_london_identity_build/canonical/london_identity_edges.parquet", columns=["dst", "relation"])
print(edges["relation"].value_counts().to_dict())
print("unique_usnr_dst", edges.loc[edges["relation"] == "on_street", "dst"].nunique())
print("unique_toid_dst", edges.loc[edges["relation"] == "has_building", "dst"].nunique())
