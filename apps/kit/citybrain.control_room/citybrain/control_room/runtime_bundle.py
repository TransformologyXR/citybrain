from __future__ import annotations

import json
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    start = start or Path(__file__).resolve()
    for parent in [start, *start.parents]:
        candidate = parent / "packages" / "fixtures" / "mobility_access" / "runtime_bundle" / "one_truth_index.json"
        if candidate.exists():
            return parent
    raise FileNotFoundError("Could not locate CityBrain runtime bundle from Kit extension source")


def bundle_root() -> Path:
    return find_repo_root() / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"


def read_json(name: str) -> dict:
    with (bundle_root() / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_trace() -> list[dict]:
    rows = []
    with (bundle_root() / "trace.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_bundle() -> dict:
    return {
        "one_truth": read_json("one_truth_index.json"),
        "scenario": read_json("scenario_state.json"),
        "review": read_json("review_state.json"),
        "evidence": read_json("evidence_bundle.json"),
        "options": read_json("option_sets.json"),
        "trace": read_trace(),
        "track_d": read_json("track_d_packets.json"),
        "overlays": read_json("kit_overlay_packets.json"),
        "labels": read_json("claim_labels.json"),
        "limitations": read_json("limitations.json"),
    }
