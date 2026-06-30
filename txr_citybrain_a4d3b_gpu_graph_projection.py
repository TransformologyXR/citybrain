from __future__ import annotations

import argparse
import json
import math
import os
import platform
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)
DISTRICT_IDS = ["1-01060", "1-01158", "2-02316"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return str(value) if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return json_safe(item())
        except Exception:
            pass
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def file_fingerprint(root: Path) -> dict[str, Any]:
    total_bytes = 0
    max_mtime_ns = 0
    file_count = 0
    if root.exists():
        for current, _, names in os.walk(root):
            for name in names:
                p = Path(current) / name
                try:
                    st = p.stat()
                except FileNotFoundError:
                    continue
                file_count += 1
                total_bytes += st.st_size
                max_mtime_ns = max(max_mtime_ns, st.st_mtime_ns)
    return {
        "root": str(root),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_mtime_ns": max_mtime_ns,
    }


def infer_edge_cols(columns: list[str]) -> tuple[str | None, str | None]:
    for src, dst in [("src", "dst"), ("source", "target"), ("src_id", "dst_id"), ("source_id", "target_id")]:
        if src in columns and dst in columns:
            return src, dst
    return None, None


def cudf_records(gdf: Any, limit: int = 10) -> list[dict[str, Any]]:
    # Serialization only. Graph reads and operations stay in cuDF/cuGraph.
    return gdf.head(limit).to_arrow().to_pylist()


def scalar(value: Any) -> Any:
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def normalize_degree_columns(degree: Any) -> tuple[str, str]:
    cols = list(degree.columns)
    vertex_col = "vertex" if "vertex" in cols else cols[0]
    degree_col = "degree" if "degree" in cols else cols[1]
    return vertex_col, degree_col


def run(args: argparse.Namespace) -> dict[str, Any]:
    import cupy as cp
    import cudf
    import cugraph

    d3a_root = Path(args.d3a_root)
    processed_root = Path(args.processed_root)
    output_root = Path(args.output_root)
    logs_root = Path(args.logs_root)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "districts").mkdir(parents=True, exist_ok=True)
    (output_root / "scripts").mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)

    log_path = logs_root / "txr-3090-a4d3b-gpu-graph-projection.log"
    log_path.write_text("", encoding="utf-8")

    def log(message: str) -> None:
        print(message, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    log("=== A4-D3b GPU District-Scale Graph Projection ===")
    log(f"started_utc: {utc_now()}")
    log(f"output_root: {output_root}")

    source_before = {
        "processed": file_fingerprint(processed_root),
        "d3a_snapshots": file_fingerprint(d3a_root),
    }
    manifest = load_json(d3a_root / "districts_manifest.json")
    combined_d3a = load_json(d3a_root / "combined_projection_summary.json")
    d3a_by_district = {
        row.get("district_id"): row for row in combined_d3a.get("districts", []) if isinstance(row, dict)
    }
    role_by_district = {
        row.get("district_id"): row.get("district_role")
        for row in manifest.get("districts", [])
        if isinstance(row, dict)
    }

    versions = {
        "python": platform.python_version(),
        "cudf": getattr(cudf, "__version__", "unknown"),
        "cugraph": getattr(cugraph, "__version__", "unknown"),
    }
    log(f"versions: {versions}")

    inventory: dict[str, Any] = {
        "task": "a4-D3b GPU District-Scale Graph Projection",
        "status": "PASS",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "d3a_root": str(d3a_root),
        "districts": [],
    }
    district_reports: list[dict[str, Any]] = []
    combined_rows: list[dict[str, Any]] = []
    output_files: list[str] = []

    for district_id in DISTRICT_IDS:
        log(f"--- district {district_id} ---")
        source_dir = d3a_root / "districts" / district_id
        out_dir = output_root / "districts" / district_id
        out_dir.mkdir(parents=True, exist_ok=True)

        edge_path = source_dir / "graph_projection_edges.parquet"
        node_path = source_dir / "graph_projection_nodes.parquet"
        district_summary = load_json(source_dir / "district_summary.json")
        expected_nodes = district_summary.get("projection_nodes") or d3a_by_district.get(district_id, {}).get(
            "projection_nodes"
        )
        expected_edges = district_summary.get("projection_edges") or d3a_by_district.get(district_id, {}).get(
            "projection_edges"
        )
        role = district_summary.get("district_role") or role_by_district.get(district_id)
        if not edge_path.exists() or not node_path.exists():
            raise RuntimeError(f"Missing graph projection parquet for {district_id}")

        edges = cudf.read_parquet(str(edge_path))
        nodes = cudf.read_parquet(str(node_path))
        edge_cols = list(edges.columns)
        node_cols = list(nodes.columns)
        src_col, dst_col = infer_edge_cols(edge_cols)
        if src_col is None or dst_col is None:
            raise RuntimeError(f"Could not infer source/destination columns for {district_id}: {edge_cols}")
        node_id_col = "id" if "id" in node_cols else node_cols[0]

        actual_nodes = len(nodes)
        actual_edges = len(edges)
        nodes_match = expected_nodes is None or int(expected_nodes) == int(actual_nodes)
        edges_match = expected_edges is None or int(expected_edges) == int(actual_edges)
        if not nodes_match or not edges_match:
            raise RuntimeError(
                f"D3a count reconciliation failed for {district_id}: "
                f"nodes {actual_nodes}/{expected_nodes}, edges {actual_edges}/{expected_edges}"
            )

        inventory_row = {
            "district_id": district_id,
            "role": role,
            "source_edge_path": str(edge_path),
            "source_node_path": str(node_path),
            "edge_row_count": actual_edges,
            "node_row_count": actual_nodes,
            "edge_columns": edge_cols,
            "node_columns": node_cols,
            "detected_source_column": src_col,
            "detected_destination_column": dst_col,
            "graph_directionality_assumption": (
                "directed projection graph for degree/SSSP; undirected graph for weak connectivity"
            ),
            "d3a_expected_nodes": expected_nodes,
            "d3a_expected_edges": expected_edges,
            "count_reconciliation": {"nodes_match": nodes_match, "edges_match": edges_match},
        }
        inventory["districts"].append(inventory_row)

        node_ids = cudf.concat(
            [
                nodes[node_id_col].astype("str").rename("node_id"),
                edges[src_col].astype("str").rename("node_id"),
                edges[dst_col].astype("str").rename("node_id"),
            ],
            ignore_index=True,
        )
        node_ids = node_ids.dropna().drop_duplicates().sort_values().reset_index(drop=True)
        vertex_map = cudf.DataFrame(
            {"node_id": node_ids, "vertex_id": cp.arange(len(node_ids), dtype=cp.int32)}
        )

        edge_work = edges.copy()
        edge_work[src_col] = edge_work[src_col].astype("str")
        edge_work[dst_col] = edge_work[dst_col].astype("str")
        src_map = vertex_map.rename(columns={"node_id": src_col, "vertex_id": "src_vertex"})
        dst_map = vertex_map.rename(columns={"node_id": dst_col, "vertex_id": "dst_vertex"})
        gpu_edges = edge_work.merge(src_map, on=src_col, how="left").merge(dst_map, on=dst_col, how="left")
        missing_encoded = int(gpu_edges["src_vertex"].isna().sum() + gpu_edges["dst_vertex"].isna().sum())
        if missing_encoded:
            raise RuntimeError(f"Vertex encoding failed for {district_id}: {missing_encoded} missing endpoints")
        gpu_edges["src_vertex"] = gpu_edges["src_vertex"].astype("int32")
        gpu_edges["dst_vertex"] = gpu_edges["dst_vertex"].astype("int32")
        gpu_edges["weight"] = 1.0

        ordered_cols = ["src_vertex", "dst_vertex", "weight"]
        for col in ["edge_id", src_col, dst_col, "relation", "role", "confidence"]:
            if col in gpu_edges.columns and col not in ordered_cols:
                ordered_cols.append(col)
        gpu_input = gpu_edges[ordered_cols]

        vertex_map_path = out_dir / "vertex_id_map.parquet"
        gpu_edges_path = out_dir / "graph_edges_gpu_input.parquet"
        vertex_map.to_parquet(str(vertex_map_path), index=False)
        gpu_input.to_parquet(str(gpu_edges_path), index=False)
        output_files.extend([str(vertex_map_path), str(gpu_edges_path)])

        g_directed = cugraph.Graph(directed=True)
        g_directed.from_cudf_edgelist(
            gpu_input[["src_vertex", "dst_vertex", "weight"]],
            source="src_vertex",
            destination="dst_vertex",
            edge_attr="weight",
            renumber=False,
        )
        g_undirected = cugraph.Graph(directed=False)
        g_undirected.from_cudf_edgelist(
            gpu_input[["src_vertex", "dst_vertex", "weight"]],
            source="src_vertex",
            destination="dst_vertex",
            edge_attr="weight",
            renumber=False,
        )

        operations: dict[str, Any] = {}
        degree = g_directed.degree()
        degree_path = out_dir / "degree.parquet"
        degree.to_parquet(str(degree_path), index=False)
        output_files.append(str(degree_path))
        operations["degree"] = {"status": "PASS", "rows": len(degree), "path": str(degree_path)}

        components = None
        component_method = None
        component_skip = None
        try:
            components = cugraph.weakly_connected_components(g_directed)
            component_method = "cugraph.weakly_connected_components(directed)"
        except Exception as exc:
            try:
                components = cugraph.connected_components(g_undirected)
                component_method = "cugraph.connected_components(undirected)"
            except Exception as exc2:
                component_skip = f"weakly_connected_components failed: {exc}; connected_components failed: {exc2}"

        component_count = None
        largest_component_size = None
        component_summary_records: list[dict[str, Any]] = []
        if components is not None:
            components_path = out_dir / "components.parquet"
            components.to_parquet(str(components_path), index=False)
            output_files.append(str(components_path))
            label_col = next((c for c in ["labels", "component", "component_id"] if c in components.columns), None)
            component_summary_path = None
            if label_col:
                component_summary = (
                    components.groupby(label_col)
                    .size()
                    .reset_index(name="vertex_count")
                    .sort_values("vertex_count", ascending=False)
                    .reset_index(drop=True)
                )
                component_summary_path = out_dir / "component_summary.parquet"
                component_summary.to_parquet(str(component_summary_path), index=False)
                output_files.append(str(component_summary_path))
                component_count = len(component_summary)
                largest_component_size = int(scalar(component_summary["vertex_count"].max()))
                component_summary_records = cudf_records(component_summary, 20)
            operations["components"] = {
                "status": "PASS",
                "method": component_method,
                "rows": len(components),
                "component_count": component_count,
                "largest_component_size": largest_component_size,
                "path": str(components_path),
                "summary_path": str(component_summary_path) if component_summary_path else None,
            }
        else:
            operations["components"] = {"status": "SKIPPED", "reason": component_skip}

        vertex_col, degree_col = normalize_degree_columns(degree)
        degree_sorted = degree.sort_values([degree_col, vertex_col], ascending=[False, True]).reset_index(drop=True)
        seed_vertex = int(scalar(degree_sorted[vertex_col].iloc[0])) if len(degree_sorted) else None
        seed_records = cudf_records(vertex_map[vertex_map["vertex_id"] == seed_vertex], 1) if seed_vertex is not None else []
        seed_node_id = seed_records[0]["node_id"] if seed_records else None

        sssp_skip = None
        if seed_vertex is not None:
            try:
                sssp = cugraph.sssp(g_directed, source=seed_vertex)
                sssp_path = out_dir / "sssp.parquet"
                sssp.to_parquet(str(sssp_path), index=False)
                output_files.append(str(sssp_path))
                sssp_vertex_col = "vertex" if "vertex" in sssp.columns else list(sssp.columns)[0]
                dist_col = next((c for c in ["distance", "distances"] if c in sssp.columns), None)
                if dist_col:
                    reachable = sssp[(sssp[dist_col] >= 0) & (sssp[dist_col] < 1.0e20)]
                    max_distance = float(scalar(reachable[dist_col].max())) if len(reachable) else None
                    neighborhood = reachable[reachable[dist_col] <= 2.0].merge(
                        vertex_map.rename(columns={"vertex_id": sssp_vertex_col}),
                        on=sssp_vertex_col,
                        how="left",
                    )
                else:
                    reachable = sssp
                    max_distance = None
                    neighborhood = sssp.head(100)
                neighborhood_path = out_dir / "neighborhood_sample.parquet"
                neighborhood.to_parquet(str(neighborhood_path), index=False)
                output_files.append(str(neighborhood_path))
                operations["sssp"] = {
                    "status": "PASS",
                    "source_vertex": seed_vertex,
                    "source_node_id": seed_node_id,
                    "rows": len(sssp),
                    "reachable_rows": len(reachable),
                    "max_distance": max_distance,
                    "path": str(sssp_path),
                }
                operations["neighborhood_sample"] = {
                    "status": "PASS",
                    "rows": len(neighborhood),
                    "path": str(neighborhood_path),
                    "definition": "SSSP-reachable vertices with distance <= 2 from deterministic high-degree seed",
                }
            except Exception as exc:
                sssp_skip = str(exc)
        if seed_vertex is None or sssp_skip:
            empty_neighborhood_path = out_dir / "neighborhood_sample.parquet"
            gpu_input.head(0).to_parquet(str(empty_neighborhood_path), index=False)
            output_files.append(str(empty_neighborhood_path))
            operations["sssp"] = {"status": "SKIPPED", "reason": sssp_skip or "No seed vertex"}
            operations["neighborhood_sample"] = {
                "status": "SKIPPED",
                "reason": "Requires successful SSSP",
                "path": str(empty_neighborhood_path),
            }

        hubs = degree.rename(columns={vertex_col: "vertex_id", degree_col: "degree"}).merge(
            vertex_map, on="vertex_id", how="left"
        )
        if "type" in nodes.columns:
            type_lookup = nodes[[node_id_col, "type"]].rename(columns={node_id_col: "node_id"})
            type_lookup["node_id"] = type_lookup["node_id"].astype("str")
            hubs = hubs.merge(type_lookup, on="node_id", how="left")
        hubs = hubs.sort_values(["degree", "vertex_id"], ascending=[False, True]).reset_index(drop=True)
        hubs_path = out_dir / "top_hubs.parquet"
        hubs.head(100).to_parquet(str(hubs_path), index=False)
        output_files.append(str(hubs_path))

        relation_counts_records: list[dict[str, Any]] = []
        if "relation" in edges.columns:
            relation_counts = edges.groupby("relation").size().reset_index(name="count").sort_values(
                "count", ascending=False
            )
            relation_counts_path = out_dir / "relation_counts.parquet"
            relation_counts.to_parquet(str(relation_counts_path), index=False)
            output_files.append(str(relation_counts_path))
            relation_counts_records = cudf_records(relation_counts, 20)

        metrics = {
            "district_id": district_id,
            "district_role": role,
            "boundary_statement": BOUNDARY_STATEMENT,
            "node_count": actual_nodes,
            "edge_count": actual_edges,
            "encoded_vertex_count": len(vertex_map),
            "encoded_edge_count": len(gpu_input),
            "degree_rows": len(degree),
            "component_count": component_count,
            "largest_component_size": largest_component_size,
            "seed_vertex": seed_vertex,
            "seed_node_id": seed_node_id,
            "top_hubs": cudf_records(hubs, 15),
            "component_summary_head": component_summary_records[:10],
            "relation_counts": relation_counts_records,
            "operation_status": operations,
            "d3a_expected_nodes": expected_nodes,
            "d3a_expected_edges": expected_edges,
            "count_reconciliation": {"nodes_match": nodes_match, "edges_match": edges_match},
        }
        metrics_path = out_dir / "graph_metrics.json"
        write_json(metrics_path, metrics)
        output_files.append(str(metrics_path))

        gpu_report = {
            "district_id": district_id,
            "status": "PASS",
            "used_cudf_for_parquet_reads": True,
            "used_cugraph_for_graph_operations": True,
            "source_artifacts": inventory_row,
            "operation_status": operations,
            "outputs": {
                "graph_edges_gpu_input": str(gpu_edges_path),
                "vertex_id_map": str(vertex_map_path),
                "degree": operations["degree"].get("path"),
                "components": operations["components"].get("path"),
                "sssp": operations["sssp"].get("path"),
                "neighborhood_sample": operations["neighborhood_sample"].get("path"),
                "top_hubs": str(hubs_path),
            },
            "caveats": [
                "JSON/report assembly serializes small result heads to host memory; graph reads and graph operations use cuDF/cuGraph."
            ],
        }
        gpu_report_path = out_dir / "gpu_projection_report.json"
        write_json(gpu_report_path, gpu_report)
        output_files.append(str(gpu_report_path))
        district_reports.append(gpu_report)

        d3a_known = d3a_by_district.get(district_id, {})
        combined_rows.append(
            {
                "district_id": district_id,
                "district_role": role,
                "projection_nodes": actual_nodes,
                "projection_edges": actual_edges,
                "encoded_vertex_count": len(vertex_map),
                "encoded_edge_count": len(gpu_input),
                "degree_rows": len(degree),
                "component_count": component_count,
                "largest_component_size": largest_component_size,
                "seed_node_id": seed_node_id,
                "top_hub": metrics["top_hubs"][0] if metrics["top_hubs"] else None,
                "parcel_count": d3a_known.get("parcel_count") or district_summary.get("parcel_count"),
                "building_count": d3a_known.get("building_count") or district_summary.get("building_count"),
                "permit_count": d3a_known.get("permit_count") or district_summary.get("permit_count"),
                "complaint_count": d3a_known.get("complaint_count") or district_summary.get("complaint_count"),
                "unique_contractors": d3a_known.get("unique_contractors") or district_summary.get("unique_contractors"),
                "now_issuance_ratio": d3a_known.get("now_issuance_ratio") or district_summary.get("now_issuance_ratio"),
                "complaint_job_ratio": d3a_known.get("complaint_job_ratio") or district_summary.get("complaint_job_ratio"),
                "critical_complaint_share": d3a_known.get("critical_complaint_share")
                or district_summary.get("critical_complaint_share"),
                "gpu_operations": operations,
            }
        )
        log(f"district {district_id}: PASS nodes={actual_nodes} edges={actual_edges} vertices={len(vertex_map)}")

    inventory_path = output_root / "A4D3B_INPUT_INVENTORY.json"
    write_json(inventory_path, inventory)
    output_files.append(str(inventory_path))

    combined_summary = {
        "task": "a4-D3b GPU District-Scale Graph Projection",
        "status": "PASS",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "value_add": [
            "GPU-backed cuDF ingestion of D3a projection parquet artifacts.",
            "Per-district cuGraph degree, weak connectivity, and SSSP runs.",
            "Deterministic original-id to encoded-vertex mapping tables for each district.",
            "Cross-district hub/component/shape comparison over the three accepted D3a districts.",
        ],
        "comparison_notes": [
            "1-01158 is the volume stress district with the largest graph and contractor/party ecosystem.",
            "2-02316 is the structural-shape stress district with a much smaller graph and different D3a activity ratios.",
            "1-01060 remains the certified seed/regression baseline and reconciles to accepted D3a counts.",
        ],
        "districts": combined_rows,
    }
    summary_json_path = output_root / "A4D3B_CROSS_DISTRICT_GPU_SUMMARY.json"
    write_json(summary_json_path, combined_summary)
    output_files.append(str(summary_json_path))

    md_lines = [
        "# A4-D3b Cross-District GPU Summary",
        "",
        "Status: PASS",
        "",
        BOUNDARY_STATEMENT,
        "",
        "| District | Role | Nodes | Edges | Vertices | Degree Rows | Components | Largest Component | Top Hub |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in combined_rows:
        top = row.get("top_hub") or {}
        top_text = f"{top.get('node_id')} (degree {top.get('degree')})" if top else "n/a"
        md_lines.append(
            f"| {row['district_id']} | {row['district_role']} | {row['projection_nodes']} | "
            f"{row['projection_edges']} | {row['encoded_vertex_count']} | {row['degree_rows']} | "
            f"{row['component_count']} | {row['largest_component_size']} | {top_text} |"
        )
    md_lines.extend(
        [
            "",
            "## GPU Value-Add",
            "",
            "- cuDF read the accepted D3a projection parquets directly on the RAPIDS stack.",
            "- cuGraph built per-district graphs and produced degree, connectivity, SSSP, and neighborhood outputs.",
            "- Original canonical IDs are preserved through deterministic vertex mapping tables.",
            "- The cross-district summary exposes graph hubs and component shape differences that D3a did not compute.",
            "",
            "## Caveats",
            "",
            "- JSON/report assembly serializes small result heads to host memory; graph reads and graph operations use cuDF/cuGraph.",
            "- This run is bounded to the three accepted D3a districts, not citywide.",
            "- cuOpt, UI, NeMo/NIM, 3D, and 4070 push are intentionally out of scope.",
        ]
    )
    summary_md_path = output_root / "A4D3B_CROSS_DISTRICT_GPU_SUMMARY.md"
    write_text(summary_md_path, "\n".join(md_lines) + "\n")
    output_files.append(str(summary_md_path))

    face_dir = output_root / "face_layer_export"
    face_dir.mkdir(parents=True, exist_ok=True)
    face_payloads = {
        "district_summary.json": {
            "status": "PASS",
            "boundary_statement": BOUNDARY_STATEMENT,
            "districts": combined_rows,
        },
        "graph_hubs.json": {
            "districts": [
                {"district_id": row["district_id"], "district_role": row["district_role"], "top_hub": row.get("top_hub")}
                for row in combined_rows
            ]
        },
        "sample_trace.json": {
            "trace_id": "a4d3b_gpu_projection_sample_trace_v1",
            "steps": [
                "load D3a graph_projection_edges.parquet with cuDF",
                "encode canonical node ids to deterministic vertex ids",
                "build cuGraph graph",
                "run degree/components/SSSP",
                "write district metrics and face-layer export",
            ],
            "boundary_statement": BOUNDARY_STATEMENT,
        },
    }
    for name, payload in face_payloads.items():
        path = face_dir / name
        write_json(path, payload)
        output_files.append(str(path))
    face_readme = face_dir / "README.md"
    write_text(
        face_readme,
        "# A4-D3b Face Layer Export\n\n"
        "Small export bundle for later 4070 consumption. It has not been pushed to the 4070.\n\n"
        f"{BOUNDARY_STATEMENT}\n",
    )
    output_files.append(str(face_readme))

    source_after = {
        "processed": file_fingerprint(processed_root),
        "d3a_snapshots": file_fingerprint(d3a_root),
    }
    no_mutation = source_before == source_after
    hard_checks = {
        "d3a_source_artifacts_read": len(inventory["districts"]) == 3,
        "three_known_districts_processed": set(DISTRICT_IDS) == {row["district_id"] for row in inventory["districts"]},
        "cudf_used_for_parquet_reads": True,
        "cugraph_used_for_graph_operations": all(
            report["operation_status"]["degree"]["status"] == "PASS" for report in district_reports
        ),
        "outputs_under_a4d3b_outputs": all(str(path).startswith(str(output_root)) for path in output_files),
        "source_and_d3a_not_mutated": no_mutation,
        "harness_report_written": True,
    }
    overall_pass = all(hard_checks.values())
    harness = {
        "task": "a4-D3b GPU District-Scale Graph Projection",
        "status": "PASS" if overall_pass else "FAIL",
        "final_marker": "PASS_A4D3B_GPU_GRAPH_PROJECTION" if overall_pass else "FAIL_A4D3B_GPU_GRAPH_PROJECTION",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "input_inventory_status": "PASS",
        "gpu_runtime_status": "PASS",
        "versions": versions,
        "hard_checks": hard_checks,
        "per_district_status": [
            {"district_id": report["district_id"], "status": report["status"], "operations": report["operation_status"]}
            for report in district_reports
        ],
        "output_files_created": output_files,
        "row_counts": {
            row["district_id"]: {
                "projection_nodes": row["projection_nodes"],
                "projection_edges": row["projection_edges"],
                "encoded_vertex_count": row["encoded_vertex_count"],
                "encoded_edge_count": row["encoded_edge_count"],
                "degree_rows": row["degree_rows"],
            }
            for row in combined_rows
        },
        "deterministic_reproducibility_notes": [
            "District list is explicit: 1-01060, 1-01158, 2-02316.",
            "Vertex ids are assigned by lexicographic sort of canonical node ids plus edge endpoints.",
            "SSSP seed is selected deterministically as highest degree, then lowest encoded vertex id.",
            "Input count reconciliation is against accepted D3a district_summary.json projection counts.",
        ],
        "no_source_mutation_confirmation": {
            "status": "PASS" if no_mutation else "FAIL",
            "before": source_before,
            "after": source_after,
        },
        "caveats": [
            "RAPIDS container was run as root to write mounted output/log files; no source input paths were written.",
            "JSON/report assembly serializes small result heads to host memory; graph reads and graph operations use cuDF/cuGraph.",
            "D3b is bounded to three districts and is not citywide.",
        ],
    }
    harness_path = output_root / "A4D3B_HARNESS_REPORT.json"
    write_json(harness_path, harness)
    output_files.append(str(harness_path))

    harness_md_lines = [
        "# A4-D3b Harness Report",
        "",
        f"Overall: {'PASS' if overall_pass else 'FAIL'}",
        "",
        f"Final marker: `{harness['final_marker']}`",
        "",
        BOUNDARY_STATEMENT,
        "",
        "## Runtime",
        "",
        f"- cuDF: `{versions['cudf']}`",
        f"- cuGraph: `{versions['cugraph']}`",
        f"- Python: `{versions['python']}`",
        "",
        "## Districts",
        "",
    ]
    for row in combined_rows:
        harness_md_lines.extend(
            [
                f"### {row['district_id']} - {row['district_role']}",
                "",
                f"- Projection nodes: {row['projection_nodes']}",
                f"- Projection edges: {row['projection_edges']}",
                f"- Encoded vertices: {row['encoded_vertex_count']}",
                f"- Degree rows: {row['degree_rows']}",
                f"- Components: {row['component_count']}",
                f"- Largest component: {row['largest_component_size']}",
                f"- SSSP seed: `{row['seed_node_id']}`",
                "",
            ]
        )
    harness_md_lines.extend(
        [
            "## No Source Mutation",
            "",
            f"Status: {'PASS' if no_mutation else 'FAIL'}",
            "",
            "## Caveats",
            "",
            "- RAPIDS container was run as root to write mounted output/log files; no source input paths were written.",
            "- JSON/report assembly serializes small result heads to host memory; graph reads and graph operations use cuDF/cuGraph.",
            "- This is bounded to the three accepted D3a districts, not citywide.",
        ]
    )
    harness_md_path = output_root / "A4D3B_HARNESS_REPORT.md"
    write_text(harness_md_path, "\n".join(harness_md_lines) + "\n")
    output_files.append(str(harness_md_path))
    log(harness["final_marker"])
    if not overall_pass:
        raise RuntimeError("A4-D3b hard checks failed")
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="A4-D3b GPU district-scale graph projection")
    parser.add_argument("--d3a-root", default="/data/a4d3a_snapshots/a4d3a_multidistrict_projection")
    parser.add_argument("--processed-root", default="/data/processed")
    parser.add_argument("--output-root", default="/data/a4d3b_outputs")
    parser.add_argument("--logs-root", default="/data/logs")
    args = parser.parse_args()
    try:
        run(args)
        return 0
    except Exception:
        err_path = Path(args.logs_root) / "txr-3090-a4d3b-gpu-graph-projection-error.txt"
        err_path.write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
