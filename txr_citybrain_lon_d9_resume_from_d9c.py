from __future__ import annotations

import argparse
from pathlib import Path

from txr_citybrain_lon_d9_overnight_pipeline import (
    NO_OVERCLAIM,
    pretty_json,
    read_json,
    run_d9c,
    run_d9d,
    run_d9e,
    run_d9f,
    utc_now,
    write_hashes,
    write_json,
    write_readme,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume LON-D9 overnight pipeline from D9C after completed D9B.")
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--component-edge-limit", type=int, default=8_000_000)
    args = parser.parse_args()
    raw_root = Path(args.raw_root)
    output_root = Path(args.output_root)
    stages = {
        "sitemap_discovery": read_json(output_root / "lon_d9_sitemap_discovery" / "LON_D9_SITEMAP_DISCOVERY_REPORT.json", {}),
        "d9b": read_json(output_root / "lon_d9b_london_identity_build" / "LON_D9B_HARNESS_REPORT.json", {}),
        "d9c": run_d9c(raw_root, output_root),
        "d9d": run_d9d(output_root),
        "d9e": run_d9e(output_root, component_edge_limit=args.component_edge_limit),
        "d9f": run_d9f(output_root),
    }
    d9b = stages["d9b"]
    d9c = stages["d9c"]
    d9d = stages["d9d"]
    d9e = stages["d9e"]
    master = output_root / "lon_d9_overnight_master_report"
    master.mkdir(parents=True, exist_ok=True)
    coverage = {
        "uprn_entities": d9b.get("uprn_entities"),
        "identity_edges": d9b.get("identity_edges"),
        "pld_applications": d9c.get("normalized_pld_applications"),
        "exact_pld_to_uprn_edges": d9d.get("exact_pld_to_uprn_edges"),
        "graph_nodes": d9e.get("nodes_emitted"),
        "graph_edges": d9e.get("edges_emitted"),
    }
    report = {
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "resume_from": "D9C",
        "finished_at": utc_now(),
        "raw_root": str(raw_root),
        "output_root": str(output_root),
        "stages": {key: value.get("status") for key, value in stages.items()},
        "what_ran_on_3090": "D9B full identity scan plus D9C-D9F resume ran under /data/citybrain/london_d9.",
        "what_synced_to_4070": "Not yet synced by this helper; lightweight D9F bundle is ready for a follow-up scp/rsync step.",
        "what_used_cpu_fallback": "D9B-D9F used pandas/geopandas/pyarrow CPU processing inside the RAPIDS container; no cuDF/cuGraph execution is claimed.",
        "raw_files_not_mutated": True,
        "coverage_headline": coverage,
        "source_limited": {
            "d9d": d9d.get("status"),
            "d6": "D6 source limitation carried forward: no bounded machine-readable enforcement/building-control feed.",
        },
        "remaining_gaps": [
            "If PLD extracts do not carry UPRN, D9D cannot certify PLD->UPRN without an official UPRN-bearing extract.",
            "Planning context layers are downloaded/catalogued but not promoted into canonical graph relations in D9E.",
            "Enforcement/building-control remains source-limited per D6.",
        ],
        "recommended_next_task": "Normalize selected London Datastore planning-context layers as D9G, and/or obtain official UPRN-bearing PLD exports for certified D9D alignment.",
        "recommended_board_status": [
            "LON-D9A GREEN - RAW INVENTORY",
            f"LON-D9B {d9b.get('status')} - LONDON-WIDE IDENTITY BUILD",
            f"LON-D9C {d9c.get('status')} - PLD NORMALIZATION / DEDUPE",
            f"LON-D9D {d9d.get('status')} - PLD->IDENTITY ALIGNMENT",
            f"LON-D9E {d9e.get('status')} - SERIOUS LONDON GRAPH",
            f"LON-D9F {stages['d9f'].get('status')} - SERIOUS LONDON QUERY CONTRACT",
        ],
        "no_overclaim": NO_OVERCLAIM,
    }
    write_json(master / "LON_D9_OVERNIGHT_MASTER_REPORT.json", report)
    write_json(
        master / "LON_D9_FAILURES_AND_LIMITATIONS.json",
        {
            "failures": {key: value for key, value in stages.items() if str(value.get("status", "")).startswith("FAIL")},
            "limitations": report["remaining_gaps"],
            "source_limited": report["source_limited"],
        },
    )
    (master / "LON_D9_NEXT_ACTIONS.md").write_text(
        "# LON-D9 Next Actions\n\n"
        "1. Obtain an official UPRN-bearing PLD export if D9D remains source-limited.\n"
        "2. Promote selected London Datastore planning-context layers through a D9G context adapter.\n"
        "3. Keep enforcement/building-control excluded until an official machine-readable register extract is supplied.\n",
        encoding="utf-8",
    )
    md = [
        "# LON-D9 Overnight Master Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## What Completed",
        *[f"- {key}: {value.get('status')}" for key, value in stages.items()],
        "",
        "## What Ran On 3090",
        report["what_ran_on_3090"],
        "",
        "## CPU Fallback",
        report["what_used_cpu_fallback"],
        "",
        "## Coverage Headline",
        *[f"- {key}: {value}" for key, value in coverage.items()],
        "",
        "## Source Limitations",
        *[f"- {item}" for item in report["remaining_gaps"]],
        "",
        "## No-Overclaim Boundary",
        *[f"- {item}" for item in NO_OVERCLAIM],
    ]
    (master / "LON_D9_OVERNIGHT_MASTER_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    write_readme(master, "LON-D9 Overnight Master Report", report["status"], ["See `LON_D9_OVERNIGHT_MASTER_REPORT.md`."])
    write_hashes(master)
    write_json(output_root / "lon_d9_overnight_resume_report.json", report)
    print(pretty_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
