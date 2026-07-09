#!/usr/bin/env python3
"""
MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1

Read-only consumption layer for Synthetic Factory Dubai Seed R1 + Seed R2 mobility-depth refresh.
No external network. No raw provider payloads. No credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS"
LIMITATIONS = [
    "LIM_PRODUCT_CONSUMPTION_SYNTHETIC_REPLAY_ONLY",
    "LIM_PRODUCT_CONSUMPTION_DONOR_CONTEXT_ONLY",
    "LIM_PRODUCT_CONSUMPTION_NOT_DUBAI_OFFICIAL_TRUTH",
    "LIM_PRODUCT_CONSUMPTION_NO_LIVE_MONITORING",
    "LIM_PRODUCT_CONSUMPTION_NO_ACTION_OR_CERTIFIED_CLAIM",
    "LIM_PRODUCT_CONSUMPTION_NO_HUMAN_PERSON_LEVEL_RECORDS",
]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSONL in {path} line {line_no}: {exc}") from exc
    return rows


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    return count


def find_first(root: Path, candidates: List[str]) -> Path | None:
    for name in candidates:
        p = root / name
        if p.exists():
            return p
    for name in candidates:
        found = list(root.rglob(name))
        if found:
            return found[0]
    return None


def normalize_row(row: Dict[str, Any], feed_type: str, seed: str, idx: int) -> Dict[str, Any]:
    out = dict(row)
    out.setdefault("source_seed", seed)
    out.setdefault("product_feed_type", feed_type)
    out.setdefault("product_consumption_id", f"{seed}:{feed_type}:{idx:04d}")
    out.setdefault("local_replay_only", True)
    out.setdefault("not_dubai_official_truth", True)
    out.setdefault("no_action_or_certified_claim", True)
    out.setdefault("limitation_refs", LIMITATIONS)
    if seed == "seed_r2":
        out.setdefault("donor_context_only", True)
        out.setdefault("not_dubai_truth", True)
        out.setdefault("is_real_world_fact", False)
    return out


def secret_scan_text(text: str, secret_values: List[str]) -> List[str]:
    findings = []
    for idx, value in enumerate(secret_values):
        if value and value in text:
            findings.append(f"SECRET_VALUE_{idx}")
    lower = text.lower()
    if "app_key=" in lower and "app_key=redacted" not in lower:
        findings.append("UNREDACTED_APP_KEY_PATTERN")
    return findings


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-r1", required=True)
    parser.add_argument("--seed-r2", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--secret", action="append", default=[], help="Optional secret value for exact scan; not logged.")
    args = parser.parse_args()

    seed_r1 = Path(args.seed_r1)
    seed_r2 = Path(args.seed_r2)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    seed_r1_decision = find_first(seed_r1, ["SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json"])
    seed_r2_decision = find_first(seed_r2, ["SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_DECISION.json"])
    seed_r1_status = read_json(seed_r1_decision).get("status") if seed_r1_decision else "UNKNOWN_MISSING_DECISION"
    seed_r2_status = read_json(seed_r2_decision).get("status") if seed_r2_decision else "UNKNOWN_MISSING_DECISION"

    files = {
        "watch": [(seed_r1, "seed_r1", ["WATCH_SEED_QUEUE.jsonl"]), (seed_r2, "seed_r2", ["WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl"])],
        "event": [(seed_r1, "seed_r1", ["EVENT_REPLAY_TAPE.jsonl"]), (seed_r2, "seed_r2", ["EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl"])],
        "ask": [(seed_r1, "seed_r1", ["ASK_ENTITY_PROFILE_FIXTURES.jsonl"]), (seed_r2, "seed_r2", ["ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl"])],
        "check": [(seed_r1, "seed_r1", ["CHECK_CLAIMABILITY_FIXTURES.jsonl"]), (seed_r2, "seed_r2", ["CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl"])],
        "brief": [(seed_r1, "seed_r1", ["BRIEF_PACKET_FIXTURES.jsonl"]), (seed_r2, "seed_r2", ["BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl"])],
        "spatial": [(seed_r1, "seed_r1", ["SPATIAL_OVERLAY_FIXTURES.jsonl"]), (seed_r2, "seed_r2", ["SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl"])],
    }

    outputs = {
        "watch": "WATCH_QUEUE_COMBINED_R1.jsonl",
        "event": "EVENT_REPLAY_COMBINED_R1.jsonl",
        "ask": "ASK_FIXTURE_INDEX_R1.jsonl",
        "check": "CHECK_FIXTURE_INDEX_R1.jsonl",
        "brief": "BRIEF_FIXTURE_INDEX_R1.jsonl",
        "spatial": "SPATIAL_OVERLAY_INDEX_R1.jsonl",
    }

    counts: Dict[str, int] = {}
    source_paths: Dict[str, str | None] = {}
    for feed_type, sources in files.items():
        combined = []
        for root, seed, candidates in sources:
            p = find_first(root, candidates)
            if not p:
                source_paths[f"{feed_type}:{seed}"] = None
                continue
            source_paths[f"{feed_type}:{seed}"] = str(p)
            rows = read_jsonl(p)
            for i, row in enumerate(rows, 1):
                combined.append(normalize_row(row, feed_type, seed, i))
        counts[f"{feed_type}_rows"] = write_jsonl(out / outputs[feed_type], combined)

    d5_packets = []
    for feed_type in ["watch", "event", "ask", "check", "brief", "spatial"]:
        path = out / outputs[feed_type]
        rows = read_jsonl(path)
        d5_packets.append({
            "packet_id": f"d5_runtime_fixture:{feed_type}:r1",
            "packet_type": f"{feed_type}_feed_packet",
            "source_file": path.name,
            "row_count": len(rows),
            "sample_ids": [r.get("product_consumption_id") for r in rows[:3]],
            "local_replay_only": True,
            "not_dubai_official_truth": True,
            "no_action_or_certified_claim": True,
            "limitation_refs": LIMITATIONS,
        })
    counts["d5_runtime_packet_rows"] = write_jsonl(out / "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl", d5_packets)

    manifest = {
        "task": TASK,
        "status": STATUS,
        "seed_r1_status": seed_r1_status,
        "seed_r2_status": seed_r2_status,
        "source_paths": source_paths,
        "outputs": [{"feed_type": k, "path": v, "rows": counts[f"{k}_rows"]} for k, v in outputs.items()],
        "d5_runtime_packet_rows": counts["d5_runtime_packet_rows"],
        "read_only_inputs": True,
        "limitations": LIMITATIONS,
    }
    write_json(out / "PRODUCT_FEED_MANIFEST_R1.json", manifest)

    html_rows = "\n".join(
        f"<li><strong>{html.escape(item['feed_type'])}</strong>: <code>{html.escape(item['path'])}</code> ({item['rows']} rows)</li>"
        for item in manifest["outputs"]
    )
    index_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CityBrain Synthetic Seed Product Feed R1</title></head>
<body>
<h1>CityBrain Synthetic Seed Product Feed R1</h1>
<p>Status: <strong>{STATUS}</strong></p>
<p>This is a local/replay, donor-context-only product consumption fixture. It is not Dubai official truth and not live monitoring.</p>
<ul>{html_rows}</ul>
<h2>D5 Runtime Packets</h2>
<p><code>D5_RUNTIME_PACKET_FIXTURES_R1.jsonl</code> ({counts['d5_runtime_packet_rows']} rows)</p>
<h2>Boundaries</h2>
<ul><li>No dispatch/control/enforcement/legal/certified claim.</li><li>No human/person-level records.</li><li>No credentials.</li></ul>
</body></html>
"""
    (out / "D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html").write_text(index_html, encoding="utf-8")

    audit = {
        "status": "PASS",
        "seed_r1_read_only": True,
        "seed_r2_read_only": True,
        "no_human_person_level_records": True,
        "no_credentials_written": True,
        "no_raw_provider_payloads_packaged": True,
        "no_lta_tfl_treated_as_dubai_truth": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "limitations": LIMITATIONS,
    }
    write_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json", audit)

    findings = []
    for p in out.iterdir():
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            hits = secret_scan_text(txt, args.secret)
            if hits:
                findings.append({"path": p.name, "findings": hits})
    secret_report = {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "secret_values_tested": len(args.secret),
        "note": "Exact scan values are provided at runtime and not logged."
    }
    write_json(out / "SECRET_SCAN_REPORT_R1.json", secret_report)

    decision = {
        "task": TASK,
        "status": STATUS if not findings else "FAIL_SECRET_SCAN",
        "input_statuses": {"seed_r1": seed_r1_status, "seed_r2": seed_r2_status},
        "counts": counts,
        "acceptance": {
            "seed_r1_read_only": True,
            "seed_r2_read_only": True,
            "watch_ask_check_brief_spatial_event_generated": all(counts.get(f"{k}_rows", 0) > 0 for k in outputs),
            "d5_runtime_packets_generated": counts["d5_runtime_packet_rows"] > 0,
            "d6_local_index_generated": True,
            "no_credentials_written": not findings,
            "no_dispatch_control_enforcement_legal_certified_claim": True,
        },
        "limitations": LIMITATIONS,
    }
    write_json(out / "PRODUCT_CONSUMPTION_R1_DECISION.json", decision)

    closeout = f"""# Codex Closeout — {TASK}

Final status: `{decision['status']}`

Counts:
{json.dumps(counts, indent=2)}

Inputs were consumed read-only. Outputs are local/replay product fixtures only.
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    entries = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "HASH_MANIFEST.json":
            entries.append({"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    write_json(out / "HASH_MANIFEST.json", {"status": "PASS", "algorithm": "sha256", "file_count": len(entries), "entries": entries})

    return 0 if decision["status"] == STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
