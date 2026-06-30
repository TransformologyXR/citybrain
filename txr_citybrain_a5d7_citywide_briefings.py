from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import random
import re
import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

GEOMETRY_CAVEAT = (
    "Block geometries are adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block "
    "boundary polygons."
)

EVIDENCE_SCHEMA_VERSION = "EvidenceBundle.v1"
HERO_TOKENS = ["1366080", "GC-0037441", "S&E BRIDGE", "1010607502"]
SEED_BLOCKS = {"1-01060": "certified seed / MN-1060", "1-01158": "volume stress", "2-02316": "shape stress"}
BOROUGH_NAMES = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_name(block_key: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", block_key)


def open_jsonl(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8", newline="\n")
    return path.open(mode, encoding="utf-8", newline="\n")


def export_compact_sqlite(sqlite_path: Path, output_jsonl: Path, node_sample_limit: int = 12) -> dict[str, Any]:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    metadata = {row["key"]: row["value"] for row in con.execute("SELECT key, value FROM metadata")}

    node_samples: dict[str, list[dict[str, Any]]] = {}
    query = """
        SELECT block_key, priority, canonical_id, entity_type, lon, lat, feature_json
        FROM node_samples
        ORDER BY block_key ASC, priority DESC, canonical_id ASC
    """
    for row in con.execute(query):
        block_key = row["block_key"]
        bucket = node_samples.setdefault(block_key, [])
        if len(bucket) >= node_sample_limit:
            continue
        feature = json.loads(row["feature_json"])
        props = feature.get("properties") or {}
        bucket.append(
            {
                "canonical_id": row["canonical_id"],
                "entity_type": row["entity_type"],
                "lon": row["lon"],
                "lat": row["lat"],
                "priority": row["priority"],
                "trace_url": props.get("trace_url"),
            }
        )

    count = 0
    with open_jsonl(output_jsonl, "w") as fh:
        for row in con.execute("SELECT * FROM blocks ORDER BY block_key ASC"):
            record = dict(row)
            feature = json.loads(record.pop("feature_json"))
            record["feature_properties"] = feature.get("properties") or {}
            record["top_contractors"] = json.loads(record.get("top_contractors_json") or "[]")
            record.pop("top_contractors_json", None)
            record["node_samples"] = node_samples.get(record["block_key"], [])
            record["metadata"] = {
                "boundary_statement": metadata.get("boundary_statement", BOUNDARY_STATEMENT),
                "geometry_label": metadata.get("geometry_label", GEOMETRY_CAVEAT),
                "total_blocks": int(metadata.get("total_blocks", 0)),
                "total_nodes": int(metadata.get("total_nodes", 0)),
                "total_edges": int(metadata.get("total_edges", 0)),
                "a4d3b_final_marker": metadata.get("a4d3b_final_marker"),
                "a4d3b_run_hash": metadata.get("a4d3b_run_hash"),
            }
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    con.close()
    return {
        "status": "PASS",
        "sqlite_path": str(sqlite_path),
        "output_jsonl": str(output_jsonl),
        "block_count": count,
        "node_sample_limit": node_sample_limit,
        "sha256": sha256_file(output_jsonl),
    }


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def fmt_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def block_metrics(record: dict[str, Any]) -> dict[str, Any]:
    props = record.get("feature_properties") or {}
    complaints = int(record.get("complaint_count") or props.get("complaint_count") or 0)
    critical = int(record.get("critical_complaint_count") or props.get("critical_complaint_count") or 0)
    permits = int(record.get("permit_count") or props.get("permit_count") or 0)
    now = int(props.get("dob_now_filing_count") or 0)
    issuance = int(props.get("dob_permit_issuance_count") or 0)
    nodes = int(record.get("node_count") or 0)
    edges = int(record.get("edge_count") or 0)
    contractors = record.get("top_contractors") or []
    return {
        "node_count": nodes,
        "edge_count": edges,
        "complaint_count": complaints,
        "critical_complaint_count": critical,
        "permit_count": permits,
        "dob_now_filing_count": now,
        "dob_permit_issuance_count": issuance,
        "critical_complaint_share": ratio(critical, complaints),
        "complaint_permit_ratio": ratio(complaints, permits),
        "now_issuance_ratio": ratio(now, issuance),
        "unique_contractor_count_visible": len({c.get("party_id") for c in contractors if c.get("party_id")}),
        "top_contractor_edge_count": sum(int(c.get("edge_count") or 0) for c in contractors),
    }


def build_facts(record: dict[str, Any], metrics: dict[str, Any], route_status: dict[str, Any] | None) -> list[dict[str, Any]]:
    block_key = record["block_key"]
    facts = [
        {"fact_id": "block_key", "path": "subject.block_key", "value": block_key, "text": f"Block {block_key} is the briefing subject."},
        {"fact_id": "borough", "path": "subject.borough_name", "value": BOROUGH_NAMES.get(str(record["borough_code"]), str(record["borough_code"])), "text": f"The block is in {BOROUGH_NAMES.get(str(record['borough_code']), str(record['borough_code']))}."},
        {"fact_id": "nodes", "path": "metrics.node_count", "value": metrics["node_count"], "text": f"The block has {metrics['node_count']} projected nodes."},
        {"fact_id": "edges", "path": "metrics.edge_count", "value": metrics["edge_count"], "text": f"The block has {metrics['edge_count']} projected edges."},
        {"fact_id": "critical_complaints", "path": "metrics.critical_complaint_count", "value": metrics["critical_complaint_count"], "text": f"The block has {metrics['critical_complaint_count']} critical complaints."},
        {"fact_id": "complaints", "path": "metrics.complaint_count", "value": metrics["complaint_count"], "text": f"The block has {metrics['complaint_count']} total complaints."},
        {"fact_id": "permits", "path": "metrics.permit_count", "value": metrics["permit_count"], "text": f"The block has {metrics['permit_count']} permits."},
        {"fact_id": "critical_share", "path": "metrics.critical_complaint_share", "value": metrics["critical_complaint_share"], "text": f"Critical complaint share is {fmt_ratio(metrics['critical_complaint_share'])}."},
        {"fact_id": "complaint_permit_ratio", "path": "metrics.complaint_permit_ratio", "value": metrics["complaint_permit_ratio"], "text": f"Complaint-permit ratio is {fmt_ratio(metrics['complaint_permit_ratio'])}."},
        {"fact_id": "now_issuance_ratio", "path": "metrics.now_issuance_ratio", "value": metrics["now_issuance_ratio"], "text": f"DOB NOW to issuance ratio is {fmt_ratio(metrics['now_issuance_ratio'])}."},
    ]
    if route_status:
        facts.append(
            {
                "fact_id": "route_status",
                "path": "optimization.route_status",
                "value": route_status.get("route_status"),
                "text": f"A6-D1 route status is {route_status.get('route_status')}.",
            }
        )
    return facts


def build_trace(record: dict[str, Any], metrics: dict[str, Any], route_status: dict[str, Any] | None) -> dict[str, Any]:
    block_key = record["block_key"]
    nodes = [
        {"id": f"block:{block_key}", "label": block_key, "type": "block", "evidence_path": "subject.block_key"},
        {"id": f"metric:{block_key}:complaints", "label": f"{metrics['complaint_count']} complaints", "type": "metric", "evidence_path": "metrics.complaint_count"},
        {"id": f"metric:{block_key}:critical", "label": f"{metrics['critical_complaint_count']} critical", "type": "metric", "evidence_path": "metrics.critical_complaint_count"},
        {"id": f"metric:{block_key}:permits", "label": f"{metrics['permit_count']} permits", "type": "metric", "evidence_path": "metrics.permit_count"},
    ]
    edges = [
        {"src": f"block:{block_key}", "dst": f"metric:{block_key}:complaints", "relation": "has_metric"},
        {"src": f"block:{block_key}", "dst": f"metric:{block_key}:critical", "relation": "has_metric"},
        {"src": f"block:{block_key}", "dst": f"metric:{block_key}:permits", "relation": "has_metric"},
    ]
    for contractor in (record.get("top_contractors") or [])[:5]:
        cid = contractor.get("party_id") or contractor.get("name")
        if not cid:
            continue
        nodes.append({"id": cid, "label": contractor.get("name") or cid, "type": "party", "evidence_path": "top_contractors"})
        edges.append({"src": f"block:{block_key}", "dst": cid, "relation": "top_contractor"})
    for sample in (record.get("node_samples") or [])[:8]:
        nodes.append({"id": sample["canonical_id"], "label": sample["canonical_id"], "type": sample["entity_type"], "evidence_path": "node_samples"})
        edges.append({"src": f"block:{block_key}", "dst": sample["canonical_id"], "relation": "sample_contains"})
    if route_status:
        rid = f"optimization:{block_key}"
        nodes.append({"id": rid, "label": route_status.get("route_status"), "type": "optimization", "evidence_path": "optimization"})
        edges.append({"src": f"block:{block_key}", "dst": rid, "relation": "review_plan_status"})
    return {"nodes": nodes, "edges": edges}


def build_evidence(record: dict[str, Any], route_status: dict[str, Any] | None) -> dict[str, Any]:
    metrics = block_metrics(record)
    block_key = record["block_key"]
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "evidence_id": f"evidence_bundle:v1:block:{block_key}",
        "subject": {
            "type": "block",
            "block_key": block_key,
            "borough_code": str(record["borough_code"]),
            "borough_name": BOROUGH_NAMES.get(str(record["borough_code"]), str(record["borough_code"])),
            "representative_point": [record.get("centroid_lon"), record.get("centroid_lat")],
            "bbox": [record.get("min_lon"), record.get("min_lat"), record.get("max_lon"), record.get("max_lat")],
            "seed_role": SEED_BLOCKS.get(block_key),
        },
        "metrics": metrics,
        "top_contractors": record.get("top_contractors") or [],
        "node_samples": record.get("node_samples") or [],
        "optimization": route_status,
        "trace": build_trace(record, metrics, route_status),
        "answer_facts": build_facts(record, metrics, route_status),
        "provenance": {
            "source": "A8-D2 citywide map cache derived from accepted a4-D3b citywide projection",
            "source_block_key": block_key,
            "fields": [
                "node_count",
                "edge_count",
                "critical_complaint_count",
                "complaint_count",
                "permit_count",
                "dob_now_filing_count",
                "dob_permit_issuance_count",
                "top_contractors_json",
                "node_samples",
            ],
        },
        "governance": {
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
            "truth_policy": "Counts and block facts are deterministic read-model facts from the accepted citywide projection cache. Narration may only restate evidence facts.",
        },
    }
    normalized = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    evidence["normalized_hash"] = sha256_text(normalized)
    return evidence


def route_status_lookup(route_dir: Path | None) -> dict[str, dict[str, Any]]:
    if not route_dir:
        return {}
    sites_path = route_dir / "face_layer_payload" / "a6d1_review_sites.geojson"
    if not sites_path.exists():
        sites_path = route_dir / "a6d1_review_sites.geojson"
    if not sites_path.exists():
        return {}
    geo = read_json(sites_path)
    lookup = {}
    for feature in geo.get("features", []):
        props = feature.get("properties") or {}
        block_key = props.get("block_key")
        if block_key:
            lookup[block_key] = {
                "candidate_id": props.get("candidate_id"),
                "route_status": props.get("route_status") or ("assigned" if props.get("assigned") else "unassigned"),
                "resource_id": props.get("resource_id"),
                "route_sequence": props.get("route_sequence"),
                "priority_score": props.get("priority_score"),
                "why_selected": props.get("why_selected"),
                "operator_boundary": props.get("operator_boundary") or props.get("operator_safe_statement"),
            }
    return lookup


def briefing_markdown(evidence: dict[str, Any]) -> str:
    subject = evidence["subject"]
    metrics = evidence["metrics"]
    route = evidence.get("optimization")
    contractors = evidence.get("top_contractors") or []
    is_hero = subject["block_key"] == "1-01060"
    lines = [
        f"# CityBrain Block Briefing — {subject['block_key']}",
        "",
        f"Block `{subject['block_key']}` is in {subject['borough_name']} and is part of the current accepted citywide projection.",
        "",
        "## Activity Profile",
        "",
        f"- Projected graph shape: {metrics['node_count']} nodes and {metrics['edge_count']} edges.",
        f"- DOB activity: {metrics['permit_count']} permits, {metrics['complaint_count']} complaints, and {metrics['critical_complaint_count']} critical complaints.",
        f"- Ratios: critical complaint share {fmt_ratio(metrics['critical_complaint_share'])}, complaint-permit ratio {fmt_ratio(metrics['complaint_permit_ratio'])}, DOB NOW/issuance ratio {fmt_ratio(metrics['now_issuance_ratio'])}.",
        "",
        "## Review Context",
        "",
    ]
    if route:
        detail = f"A6-D1 route status: {route.get('route_status')}"
        if route.get("resource_id"):
            detail += f", resource `{route.get('resource_id')}`, suggested order {route.get('route_sequence')}"
        if route.get("why_selected"):
            detail += f". {route.get('why_selected')}"
        lines.append(detail + ".")
    else:
        lines.append("This block is not one of the 120 A6-D1 route-overlay review candidates in the current optimization plan.")
    lines.extend(["", "## Visible Contractor Context", ""])
    if contractors:
        if is_hero:
            for contractor in contractors[:3]:
                name = contractor.get("name") or contractor.get("party_id") or "unknown party"
                count = contractor.get("edge_count", "n/a")
                lines.append(f"- {name}: {count} linked edges in the block-level summary.")
        else:
            edge_counts = [int(c.get("edge_count") or 0) for c in contractors[:3]]
            lines.append(
                f"- The block cache includes {len(contractors)} visible top-contractor summaries; "
                f"top linked-edge counts are {', '.join(str(v) for v in edge_counts)}. Names remain in the EvidenceBundle, not this non-hero prose briefing."
            )
    else:
        lines.append("- No top-contractor summary is available in the block cache.")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            BOUNDARY_STATEMENT,
            "",
            GEOMETRY_CAVEAT,
        ]
    )
    return "\n".join(lines) + "\n"


def grounding_check(evidence: dict[str, Any], markdown: str) -> dict[str, Any]:
    fact_texts = [fact["text"] for fact in evidence.get("answer_facts", [])]
    covered = [fact for fact in fact_texts if any(str(part) in markdown for part in re.findall(r"[A-Za-z0-9_.:-]+", fact))]
    not_echo = markdown.count("{") == 0 and markdown.count("[") < 3 and len(markdown.splitlines()) < 80
    boundary = BOUNDARY_STATEMENT in markdown
    min_coverage = all(str(evidence["metrics"][key]) in markdown for key in ["node_count", "edge_count", "complaint_count", "critical_complaint_count", "permit_count"])
    return {
        "status": "PASS" if not_echo and boundary and min_coverage else "FAIL",
        "not_echo": not_echo,
        "boundary": boundary,
        "minimum_coverage": min_coverage,
        "covered_fact_count": len(covered),
        "fact_count": len(fact_texts),
    }


def write_sha256s(root: Path) -> dict[str, str]:
    hashes = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.json":
            hashes[p.relative_to(root).as_posix()] = sha256_file(p)
    write_json(root / "SHA256SUMS.json", hashes)
    return hashes


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with open_jsonl(path, "r") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def generate_citywide(
    input_jsonl: Path,
    output_dir: Path,
    route_dir: Path | None = None,
    limit: int | None = None,
    write_full_sha256: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence_json"
    briefing_dir = output_dir / "briefings"
    trace_dir = output_dir / "traces"
    for d in [evidence_dir, briefing_dir, trace_dir]:
        d.mkdir(parents=True, exist_ok=True)

    route_lookup = route_status_lookup(route_dir)
    rows = []
    failures = []
    nonhero_leaks = []
    count = 0
    for record in iter_jsonl(input_jsonl):
        block_key = record["block_key"]
        evidence = build_evidence(record, route_lookup.get(block_key))
        markdown = briefing_markdown(evidence)
        grounding = grounding_check(evidence, markdown)
        if grounding["status"] != "PASS":
            failures.append({"block_key": block_key, "grounding": grounding})
        if block_key != "1-01060":
            leaks = [token for token in HERO_TOKENS if token in markdown]
            if leaks:
                nonhero_leaks.append({"block_key": block_key, "tokens": leaks})
        trace = {
            "status": "PASS",
            "block_key": block_key,
            "trace_id": f"a5d7_trace:block:{block_key}",
            "evidence_bundle_id": evidence["evidence_id"],
            "graph": evidence["trace"],
            "grounding": grounding,
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
        }
        evidence_path = evidence_dir / f"block_{safe_name(block_key)}_evidence.json"
        briefing_path = briefing_dir / f"block_{safe_name(block_key)}_briefing.md"
        trace_path = trace_dir / f"block_{safe_name(block_key)}_trace.json"
        write_json(evidence_path, evidence)
        briefing_path.write_text(markdown, encoding="utf-8")
        write_json(trace_path, trace)
        rows.append(
            {
                "block_key": block_key,
                "borough_code": evidence["subject"]["borough_code"],
                "evidence_id": evidence["evidence_id"],
                "evidence_json": json.dumps(evidence, sort_keys=True, ensure_ascii=False),
                "briefing_md": markdown,
                "trace_json": json.dumps(trace, sort_keys=True, ensure_ascii=False),
                "normalized_hash": evidence["normalized_hash"],
                "grounding_status": grounding["status"],
            }
        )
        count += 1
        if limit and count >= limit:
            break

    import pandas as pd

    pd.DataFrame(rows).to_parquet(output_dir / "citywide_block_evidence.parquet", index=False)
    pd.DataFrame(rows)[["block_key", "borough_code", "briefing_md", "normalized_hash", "grounding_status"]].to_parquet(
        output_dir / "citywide_block_briefings.parquet", index=False
    )
    pd.DataFrame(rows)[["block_key", "trace_json", "normalized_hash", "grounding_status"]].to_parquet(
        output_dir / "citywide_block_traces.parquet", index=False
    )
    block_index = {
        row["block_key"]: {
            "evidence": f"evidence_json/block_{safe_name(row['block_key'])}_evidence.json",
            "briefing": f"briefings/block_{safe_name(row['block_key'])}_briefing.md",
            "trace": f"traces/block_{safe_name(row['block_key'])}_trace.json",
            "normalized_hash": row["normalized_hash"],
            "grounding_status": row["grounding_status"],
        }
        for row in rows
    }
    write_json(output_dir / "block_index.json", block_index)
    sample_rng = random.Random(1987)
    nonhero = [key for key in block_index if key != "1-01060"]
    random_sample = sample_rng.sample(nonhero, min(10, len(nonhero)))
    spot = {
        key: {
            "grounding_status": block_index[key]["grounding_status"],
            "hero_token_leaks": [token for token in HERO_TOKENS if token in (briefing_dir / f"block_{safe_name(key)}_briefing.md").read_text(encoding="utf-8")],
        }
        for key in random_sample
    }
    report = {
        "status": "PASS" if not failures and not nonhero_leaks and count == (limit or 27997) else "FAIL",
        "task": "A5-D7 citywide block EvidenceBundles and governed briefings",
        "created_utc": utc_now(),
        "input_jsonl": str(input_jsonl),
        "output_dir": str(output_dir),
        "block_count": count,
        "expected_block_count": limit or 27997,
        "grounding_failures": failures[:20],
        "grounding_failure_count": len(failures),
        "nonhero_leak_count": len(nonhero_leaks),
        "nonhero_leaks": nonhero_leaks[:20],
        "spot_check_blocks": spot,
        "boundary_statement": BOUNDARY_STATEMENT,
        "geometry_caveat": GEOMETRY_CAVEAT,
    }
    write_json(output_dir / "A5D7_GENERATION_REPORT.json", report)
    write_json(output_dir / "snapshot" / "a5d7_citywide_briefings_v1.json", report)
    if write_full_sha256:
        hashes = write_sha256s(output_dir)
        report["sha256_file_count"] = len(hashes)
    else:
        report["sha256_file_count"] = None
        report["sha256_note"] = "Full per-file SHA256 manifest skipped for local batch speed; transfer tarball/hash manifest is produced separately."
    write_json(output_dir / "A5D7_GENERATION_REPORT.json", report)
    return report


def make_tarball(output_dir: Path, tar_path: Path) -> dict[str, Any]:
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(output_dir, arcname=output_dir.name)
    return {"status": "PASS", "tarball": str(tar_path), "bytes": tar_path.stat().st_size, "sha256": sha256_file(tar_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="A5-D7 citywide EvidenceBundles and briefings")
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export-sqlite")
    exp.add_argument("--sqlite", required=True)
    exp.add_argument("--output-jsonl", required=True)
    exp.add_argument("--node-sample-limit", type=int, default=12)
    gen = sub.add_parser("generate")
    gen.add_argument("--input-jsonl", required=True)
    gen.add_argument("--output-dir", required=True)
    gen.add_argument("--route-dir")
    gen.add_argument("--limit", type=int)
    gen.add_argument("--tarball")
    gen.add_argument("--skip-full-sha256", action="store_true")
    args = parser.parse_args()
    if args.cmd == "export-sqlite":
        result = export_compact_sqlite(Path(args.sqlite), Path(args.output_jsonl), args.node_sample_limit)
    else:
        result = generate_citywide(
            Path(args.input_jsonl),
            Path(args.output_dir),
            Path(args.route_dir) if args.route_dir else None,
            args.limit,
            write_full_sha256=not args.skip_full_sha256,
        )
        if args.tarball:
            result["tarball"] = make_tarball(Path(args.output_dir), Path(args.tarball))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
