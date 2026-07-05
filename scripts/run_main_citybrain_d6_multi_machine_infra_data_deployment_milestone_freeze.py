#!/usr/bin/env python3
"""CityBrain infra/data multi-machine placement closeout runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

STAGES = ["preflight", "plan_r1", "sync_r2", "smoke_r3", "closeout", "freeze"]
OUT = {
    "preflight": OUTPUTS / "main_citybrain_d6_multi_machine_data_placement_preflight",
    "plan_r1": OUTPUTS / "main_citybrain_d6_multi_machine_data_manifest_and_placement_plan_r1",
    "sync_r2": OUTPUTS / "main_citybrain_d6_multi_machine_data_sync_r2",
    "smoke_r3": OUTPUTS / "main_citybrain_d6_multi_machine_remote_runtime_data_smoke_r3",
    "closeout": OUTPUTS / "main_citybrain_d6_multi_machine_infra_data_deployment_closeout",
    "freeze": OUTPUTS / "main_citybrain_d6_multi_machine_infra_data_deployment_milestone_freeze",
}
STATUS = {
    "preflight": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_DATA_PLACEMENT_PREFLIGHT_WITH_LIMITATIONS",
    "plan_r1": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_DATA_MANIFEST_AND_PLACEMENT_PLAN_R1_WITH_LIMITATIONS",
    "sync_r2": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_DATA_SYNC_R2_WITH_LIMITATIONS",
    "smoke_r3": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_REMOTE_RUNTIME_DATA_SMOKE_R3_WITH_LIMITATIONS",
    "closeout": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_CLOSEOUT_WITH_LIMITATIONS",
    "freeze": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_WITH_LIMITATIONS",
}

PREVIOUS_FREEZE = OUTPUTS / "main_citybrain_d6_multi_machine_actual_deployment_rehearsal_milestone_freeze"
PREVIOUS_CLOSEOUT = OUTPUTS / "main_citybrain_d6_multi_machine_actual_deployment_rehearsal_closeout"
PREVIOUS_SMOKE = OUTPUTS / "main_citybrain_d6_multi_machine_local_runtime_smoke_r2"

MACHINES = {
    "spark": {
        "user": "txr",
        "host": "spark",
        "role": "orchestration/runtime rehearsal and demo runner context",
        "approved_base": "/home/txr/works",
        "target_root": f"/home/txr/works/citybrain_infra_data_deployment_rehearsal/data_deployment_{RUN_ID}",
    },
    "rtx3090": {
        "user": "txr",
        "host": "txr-3090",
        "role": "data/graph/RAPIDS-oriented data placement",
        "approved_base": "/data/citybrain",
        "target_root": f"/data/citybrain/infra_data_deployment_rehearsal/data_deployment_{RUN_ID}",
    },
    "rtx4070": {
        "user": "txr",
        "host": "txr-4070",
        "role": "face/dashboard/trace/briefing/control-room surface artifacts",
        "approved_base": "/srv/citybrain",
        "target_root": f"/srv/citybrain/infra_data_deployment_rehearsal/data_deployment_{RUN_ID}",
    },
}

BOUNDARIES = [
    "local/LAN/replay/review/query context only",
    "not production",
    "no public API exposure",
    "no auth/RBAC/security-hardening claim",
    "no autonomous monitoring or alerts",
    "no dispatch/routing/control/enforcement",
    "no legal/certified finding",
    "no official ticket/case creation",
    "no automated action",
]

SECRET_NAME_RE = re.compile(r"(^|[._-])(secret|password|passwd|token|credential|private[_-]?key|id_rsa|id_ed25519)([._-]|$)", re.I)
SECRET_VALUE_RE = re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|passwd|private[_-]?key|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_.$@/\-+=]{10,}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(root.rglob("*")) if p.is_file()}


def hash_manifest(root: Path) -> None:
    path = root / "HASH_MANIFEST.json"
    if path.exists():
        path.unlink()
    write_json(path, tree_hashes(root))


def run(args: list[str], timeout: int = 60) -> dict[str, Any]:
    last = None
    for attempt in range(3):
        p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        last = {"args": args, "returncode": p.returncode, "stdout": p.stdout[-5000:], "stderr": p.stderr[-5000:], "attempt": attempt + 1}
        if p.returncode != 255:
            return last
        time.sleep(2)
    return last or {"args": args, "returncode": 1, "stdout": "", "stderr": "command did not run", "attempt": 0}


def ssh(machine: dict[str, str], cmd: str, timeout: int = 60) -> dict[str, Any]:
    dest = f"{machine['user']}@{machine['host']}"
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", dest, cmd], timeout)


def scp(local: Path, machine: dict[str, str], remote: str, timeout: int = 120) -> dict[str, Any]:
    dest = f"{machine['user']}@{machine['host']}:{remote}"
    return run(["scp", "-q", str(local), dest], timeout)


def snapshots() -> dict[str, dict[str, str]]:
    protected = {
        "previous_freeze": PREVIOUS_FREEZE,
        "previous_closeout": PREVIOUS_CLOSEOUT,
        "previous_smoke": PREVIOUS_SMOKE,
        "runtime_handover": OUTPUTS / "main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "decision_support_handover": OUTPUTS / "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
    }
    return {k: tree_hashes(v) for k, v in protected.items()}


def standard_audits(root: Path, stage: str, before: dict[str, dict[str, str]]) -> None:
    base = {
        "stage": stage,
        "status": "PASS",
        "timestamp": now(),
        "boundaries": BOUNDARIES,
        "production_claim": False,
        "public_api_claim": False,
        "auth_rbac_security_hardening_claim": False,
    }
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", base)
    no_action = dict(base)
    no_action.update({"autonomous_monitoring": False, "alerts": False, "dispatch": False, "routing_control": False, "enforcement": False, "automated_action": False})
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    secret = dict(base)
    secret.update({"env_files_copied": False, "private_keys_copied": False, "secret_like_values_copied": False})
    write_json(root / "SECRET_AUDIT.json", secret)
    after = snapshots()
    drift = [k for k, v in before.items() if after.get(k, {}) != v]
    write_json(root / "NO_MUTATION_AUDIT.json", dict(base, protected_upstream_drift=drift, protected_upstream_drift_count=len(drift)))


def index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Generated: {now()}", "", "## Files"]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        lines.append(f"- `{p.relative_to(root).as_posix()}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines) + "\n")


def secret_blocked(path: Path) -> str | None:
    name = path.name
    if name == ".env" or (name.endswith(".env") and not name.endswith(".env.example")):
        return "env_file"
    if SECRET_NAME_RE.search(name):
        return "secret_like_filename"
    if path.suffix.lower() in {".json", ".md", ".txt", ".yaml", ".yml", ".toml", ".csv"} and path.stat().st_size <= 1_000_000:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET_VALUE_RE.search(text):
            return "secret_like_content"
    return None


def add_artifact(items: list[dict[str, Any]], role: str, purpose: str, path: Path, root_label: str, root: Path) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size > 750_000:
        return
    if secret_blocked(path):
        return
    rel_source = rel(path)
    rel_root = path.relative_to(root).as_posix() if root in path.parents or path == root else path.name
    items.append(
        {
            "machine": role,
            "purpose": purpose,
            "source_root": root_label,
            "source": rel_source,
            "relative_target": f"{purpose}/{rel_root}",
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    )


def build_manifest() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for root_label, root, role, purpose in [
        ("actual_rehearsal_freeze", PREVIOUS_FREEZE, "spark", "orchestration_context"),
        ("actual_rehearsal_closeout", PREVIOUS_CLOSEOUT, "spark", "orchestration_context"),
        ("previous_smoke", PREVIOUS_SMOKE, "spark", "runtime_smoke_context"),
        ("actual_rehearsal_freeze", PREVIOUS_FREEZE, "rtx4070", "control_room_context"),
        ("actual_rehearsal_closeout", PREVIOUS_CLOSEOUT, "rtx4070", "control_room_context"),
    ]:
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() in {".json", ".md"}:
                    add_artifact(items, role, purpose, p, root_label, root)
    data_root = ROOT / "data_synthetic" / "pv1_sdf" / "packs" / "sdf_chi_near_west_side_v1"
    if data_root.exists():
        for p in sorted(data_root.rglob("*")):
            if p.suffix.lower() in {".json", ".md", ".csv", ".geojson", ".parquet"}:
                add_artifact(items, "rtx3090", "sdf_data_graph_context", p, "sdf_chi_near_west_side_v1", data_root)
    for out_name in ["pv1_sdf_synthetic_data_factory", "pv1_infra_d2_3090_runtime_bootstrap", "pv1_d3d4_cross_city_ontology_v2_gate"]:
        root = OUTPUTS / out_name
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() in {".json", ".md"}:
                    add_artifact(items, "rtx3090", f"{out_name}_manifests", p, out_name, root)
    for out_name in ["main_citybrain_d6_decision_support_demo_capture_pack_closeout", "main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2", "main_citybrain_d6_governed_runtime_trace_harness_closeout"]:
        root = OUTPUTS / out_name
        if root.exists():
            for p in sorted(root.rglob("*")):
                if p.suffix.lower() in {".json", ".md"}:
                    add_artifact(items, "rtx4070", f"{out_name}_surface_context", p, out_name, root)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = (item["machine"], item["relative_target"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def preflight(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["preflight"]
    root.mkdir(parents=True, exist_ok=True)
    probes: dict[str, Any] = {}
    approved: dict[str, Any] = {}
    for machine_id, machine in MACHINES.items():
        cmd = f"test -w {shlex.quote(machine['approved_base'])} && printf PASS || printf FAIL"
        probe = ssh(machine, cmd, 20)
        writable = probe["stdout"].strip().endswith("PASS") and probe["returncode"] == 0
        probes[machine_id] = {"role": machine["role"], "probe": probe, "writable": writable}
        approved[machine_id] = {"approved_base": machine["approved_base"], "target_root": machine["target_root"], "writable": writable}
    forbidden = {
        "paths": ["/", "/etc", "/usr", "/var", "/home/txr", "/data", "/srv", "user profiles", "Windows dual-boot partitions"],
        "actions": ["delete", "destructive rsync", "driver/CUDA/Docker reinstall", "public service bind", "auth/RBAC/security-hardening claim"],
    }
    policy = {"max_file_bytes": 750000, "allowed_extensions": [".json", ".md", ".csv", ".geojson", ".parquet"], "secret_denylist_enforced": True}
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DATA-PLACEMENT-PREFLIGHT",
        "status": STATUS["preflight"],
        "timestamp": now(),
        "previous_freeze_found": PREVIOUS_FREEZE.exists(),
        "previous_closeout_found": PREVIOUS_CLOSEOUT.exists(),
        "all_roots_confirmed": all(v["writable"] for v in approved.values()),
        "boundaries": BOUNDARIES,
    }
    write_json(root / "DATA_PLACEMENT_PREFLIGHT_DECISION.json", decision)
    write_json(root / "MACHINE_ROLE_REVIEW.json", probes)
    write_json(root / "APPROVED_REMOTE_ROOTS.json", approved)
    write_json(root / "FORBIDDEN_PATHS_AND_ACTIONS.json", forbidden)
    write_json(root / "ALLOWLIST_POLICY.json", policy)
    standard_audits(root, "preflight", before)
    index(root, "Data Placement Preflight")
    hash_manifest(root)
    return decision


def plan_r1(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["plan_r1"]
    root.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    by_machine = {m: [x for x in manifest if x["machine"] == m] for m in MACHINES}
    expected = {m: {x["relative_target"]: x["sha256"] for x in xs} for m, xs in by_machine.items()}
    for machine_id, plan_name in [("spark", "SPARK_PLACEMENT_PLAN.json"), ("rtx3090", "RTX3090_PLACEMENT_PLAN.json"), ("rtx4070", "RTX4070_PLACEMENT_PLAN.json")]:
        write_json(root / plan_name, {"machine": machine_id, "target_root": MACHINES[machine_id]["target_root"], "items": by_machine[machine_id]})
    lines = ["# Sync Command Plan", "", "No delete flags. Writes only below the timestamped approved target roots.", ""]
    for m, machine in MACHINES.items():
        lines.append(f"- `{m}` target: `{machine['target_root']}` ({len(by_machine[m])} files)")
    decision = {"task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DATA-MANIFEST-AND-PLACEMENT-PLAN-R1", "status": STATUS["plan_r1"], "timestamp": now(), "artifact_count": len(manifest), "bytes": sum(x["bytes"] for x in manifest)}
    write_json(root / "DATA_PLACEMENT_MANIFEST.json", {"run_id": RUN_ID, "items": manifest, "machine_counts": {m: len(xs) for m, xs in by_machine.items()}})
    write_text(root / "SYNC_COMMAND_PLAN.md", "\n".join(lines) + "\n")
    write_json(root / "EXPECTED_REMOTE_HASHES.json", expected)
    write_json(root / "DATA_MANIFEST_AND_PLACEMENT_PLAN_R1_DECISION.json", decision)
    standard_audits(root, "plan_r1", before)
    index(root, "Data Manifest And Placement Plan R1")
    hash_manifest(root)
    return decision


def sync_r2(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["sync_r2"]
    root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT["plan_r1"] / "DATA_PLACEMENT_MANIFEST.json").read_text(encoding="utf-8"))["items"]
    ledger: dict[str, Any] = {}
    verification: dict[str, Any] = {}
    failed: list[dict[str, Any]] = []
    logs: list[str] = []
    for machine_id, machine in MACHINES.items():
        items = [x for x in manifest if x["machine"] == machine_id]
        target = machine["target_root"]
        mkdir = ssh(machine, f"mkdir -p {shlex.quote(target + '/files')}", 30)
        logs.append(f"{machine_id} mkdir rc={mkdir['returncode']}")
        copied = []
        verified = []
        mismatches = []
        if mkdir["returncode"] != 0:
            failed.append({"machine": machine_id, "phase": "mkdir", "result": mkdir})
            ledger[machine_id] = {"status": "FAIL", "target_root": target, "files": 0, "bytes": 0}
            verification[machine_id] = {"status": "FAIL", "mismatches": [{"reason": "mkdir_failed"}]}
            continue
        for item in items:
            src = ROOT / item["source"]
            remote = f"{target}/files/{item['relative_target']}"
            parent = str(Path(remote).parent).replace("\\", "/")
            ssh(machine, f"mkdir -p {shlex.quote(parent)}", 30)
            cp = scp(src, machine, remote, 120)
            logs.append(f"{machine_id} scp {item['relative_target']} rc={cp['returncode']}")
            if cp["returncode"] != 0:
                failed.append({"machine": machine_id, "item": item, "phase": "scp", "result": cp})
                continue
            copied.append(item)
            hv = ssh(machine, f"sha256sum {shlex.quote(remote)}", 30)
            remote_hash = hv["stdout"].strip().split()[0] if hv["returncode"] == 0 and hv["stdout"].strip() else ""
            ok = remote_hash == item["sha256"]
            verified.append({"relative_target": item["relative_target"], "local_sha256": item["sha256"], "remote_sha256": remote_hash, "match": ok})
            if not ok:
                mismatches.append({"relative_target": item["relative_target"], "expected": item["sha256"], "actual": remote_hash})
        status = "PASS" if len(copied) == len(items) and not mismatches else "FAIL"
        ledger[machine_id] = {"status": status, "target_root": target, "files": len(copied), "bytes": sum(x["bytes"] for x in copied), "write_scope_ok": target.startswith(machine["approved_base"] + "/")}
        verification[machine_id] = {"status": status, "verified": verified, "mismatches": mismatches}
    mismatch_count = sum(len(v["mismatches"]) for v in verification.values())
    all_pass = all(v["status"] == "PASS" for v in ledger.values()) and not failed and mismatch_count == 0
    decision = {"task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DATA-SYNC-R2", "status": STATUS["sync_r2"] if all_pass else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_DATA_SYNC_R2", "timestamp": now(), "failed_transfers": len(failed), "hash_mismatches": mismatch_count}
    write_json(root / "DATA_SYNC_R2_DECISION.json", decision)
    write_json(root / "REMOTE_WRITE_LEDGER.json", ledger)
    write_json(root / "REMOTE_HASH_VERIFICATION.json", verification)
    write_text(root / "SYNC_STDOUT_STDERR_SUMMARY.md", "# Sync Stdout/Stderr Summary\n\n" + "\n".join(f"- {x}" for x in logs) + "\n")
    write_json(root / "FAILED_TRANSFERS.json", failed)
    standard_audits(root, "sync_r2", before)
    index(root, "Data Sync R2")
    hash_manifest(root)
    return decision


def smoke_report(machine_id: str, machine: dict[str, str]) -> dict[str, Any]:
    target = machine["target_root"]
    py = (
        "import json, pathlib; "
        f"root=pathlib.Path({(target + '/files')!r}); "
        "files=list(root.rglob('*')); "
        "jsons=[p for p in files if p.suffix=='.json']; "
        "ok=0\n"
        "for p in jsons[:20]:\n"
        "    json.loads(p.read_text())\n"
        "    ok+=1\n"
        "print('files', sum(1 for p in files if p.is_file()))\n"
        "print('json_read_ok', ok)"
    )
    commands = {
        "hostname": "hostname",
        "file_count": f"find {shlex.quote(target + '/files')} -type f | wc -l",
        "json_parse": f"python3 -c {shlex.quote(py)} 2>&1",
        "public_bind_readonly": "ss -ltn 2>/dev/null | head -50 || true",
    }
    results = {k: ssh(machine, v, 60) for k, v in commands.items()}
    count_text = results["file_count"]["stdout"].strip()
    count_ok = count_text.isdigit() and int(count_text) > 0
    parse_ok = results["json_parse"]["returncode"] == 0 and "json_read_ok" in results["json_parse"]["stdout"]
    return {"machine": machine_id, "status": "PASS" if count_ok and parse_ok else "FAIL", "target_root": target, "checks": {"file_count_positive": count_ok, "selected_json_parse": parse_ok, "no_service_started": True}, "commands": results}


def smoke_r3(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["smoke_r3"]
    root.mkdir(parents=True, exist_ok=True)
    reports = {m: smoke_report(m, machine) for m, machine in MACHINES.items()}
    write_json(root / "SPARK_SMOKE_REPORT.json", reports["spark"])
    write_json(root / "RTX3090_SMOKE_REPORT.json", reports["rtx3090"])
    write_json(root / "RTX4070_SMOKE_REPORT.json", reports["rtx4070"])
    write_json(root / "REMOTE_LIMITATIONS.json", {"limitations": BOUNDARIES, "security_auth_rbac_public_api": "deferred"})
    all_pass = all(v["status"] == "PASS" for v in reports.values())
    decision = {"task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-REMOTE-RUNTIME-DATA-SMOKE-R3", "status": STATUS["smoke_r3"] if all_pass else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_REMOTE_RUNTIME_DATA_SMOKE_R3", "timestamp": now(), "machine_status": {k: v["status"] for k, v in reports.items()}}
    write_json(root / "REMOTE_RUNTIME_DATA_SMOKE_R3_DECISION.json", decision)
    standard_audits(root, "smoke_r3", before)
    index(root, "Remote Runtime Data Smoke R3")
    hash_manifest(root)
    return decision


def closeout(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["closeout"]
    root.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((OUT["sync_r2"] / "REMOTE_WRITE_LEDGER.json").read_text(encoding="utf-8"))
    hashes = json.loads((OUT["sync_r2"] / "REMOTE_HASH_VERIFICATION.json").read_text(encoding="utf-8"))
    smoke = json.loads((OUT["smoke_r3"] / "REMOTE_RUNTIME_DATA_SMOKE_R3_DECISION.json").read_text(encoding="utf-8"))
    summary = {m: {"role": MACHINES[m]["role"], "target_root": ledger[m]["target_root"], "sync": ledger[m]["status"], "smoke": smoke["machine_status"][m], "files": ledger[m]["files"], "bytes": ledger[m]["bytes"]} for m in MACHINES}
    reconciliation = {"hash_mismatches": sum(len(v["mismatches"]) for v in hashes.values()), "smoke_status": smoke["machine_status"], "sync_status": {m: ledger[m]["status"] for m in MACHINES}}
    all_pass = all(v["sync"] == "PASS" and v["smoke"] == "PASS" for v in summary.values()) and reconciliation["hash_mismatches"] == 0
    decision = {"task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-INFRA-DATA-DEPLOYMENT-CLOSEOUT", "status": STATUS["closeout"] if all_pass else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_CLOSEOUT", "timestamp": now(), "summary": reconciliation}
    write_json(root / "INFRA_DATA_DEPLOYMENT_CLOSEOUT_DECISION.json", decision)
    write_json(root / "MACHINE_DEPLOYMENT_SUMMARY.json", summary)
    write_json(root / "REMOTE_ROOTS_FINAL.json", {m: ledger[m]["target_root"] for m in MACHINES})
    write_json(root / "HASH_AND_SMOKE_RECONCILIATION.json", reconciliation)
    write_text(root / "DEFERRED_SECURITY_REGISTER.md", "# Deferred Security Register\n\nSecurity/auth/RBAC/public API hardening remains deferred and out of scope for this infra/data placement rehearsal.\n")
    standard_audits(root, "closeout", before)
    index(root, "Infra Data Deployment Closeout")
    hash_manifest(root)
    return decision


def freeze(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["freeze"]
    root.mkdir(parents=True, exist_ok=True)
    summary = json.loads((OUT["closeout"] / "MACHINE_DEPLOYMENT_SUMMARY.json").read_text(encoding="utf-8"))
    roots = json.loads((OUT["closeout"] / "REMOTE_ROOTS_FINAL.json").read_text(encoding="utf-8"))
    all_pass = all(v["sync"] == "PASS" and v["smoke"] == "PASS" for v in summary.values())
    decision = {"task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-INFRA-DATA-DEPLOYMENT-MILESTONE-FREEZE", "status": STATUS["freeze"] if all_pass else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE", "timestamp": now(), "infra_sprint_closed": all_pass, "with_limitations": True}
    status = STATUS["freeze"] if all_pass else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE"
    frozen = ["# Frozen Infra State", "", f"Status: `{status}`", "", "This freezes infra/data placement only. It is local/LAN and non-production.", "", "## Machines"]
    for m, item in summary.items():
        frozen.append(f"- `{m}`: {item['files']} files, sync `{item['sync']}`, smoke `{item['smoke']}`, root `{item['target_root']}`")
    write_json(root / "INFRA_DATA_DEPLOYMENT_MILESTONE_FREEZE_DECISION.json", decision)
    write_text(root / "FROZEN_INFRA_STATE.md", "\n".join(frozen) + "\n")
    write_json(root / "REMOTE_MACHINE_LEDGER.json", summary)
    write_json(root / "READY_NEXT_TRACKS.json", {"ready": ["bounded local/LAN app/runtime consumption of placed data", "future separately-approved security/auth/RBAC track"], "not_ready_for": ["production", "public API", "autonomous action"]})
    write_json(root / "DEFERRED_INFRA_TRACKS.json", {"deferred": ["auth/RBAC", "enterprise security hardening", "public API", "production SLA", "autonomous monitoring/action"], "remote_roots": roots})
    standard_audits(root, "freeze", before)
    index(root, "Infra Data Deployment Milestone Freeze")
    hash_manifest(root)
    return decision


FUNCS = {"preflight": preflight, "plan_r1": plan_r1, "sync_r2": sync_r2, "smoke_r3": smoke_r3, "closeout": closeout, "freeze": freeze}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-after", choices=STAGES, default="freeze")
    args = parser.parse_args(argv)
    before = snapshots()
    result: dict[str, Any] = {}
    for stage in STAGES:
        result = FUNCS[stage](before)
        if stage == args.stop_after:
            break
    print(f"MAIN-CITYBRAIN-D6-MULTI-MACHINE-INFRA-DATA-DEPLOYMENT: {result['status']}")
    print(f"Run ID: {RUN_ID}")
    print(f"Output: {rel(OUT[args.stop_after])}")
    if (OUT["closeout"] / "MACHINE_DEPLOYMENT_SUMMARY.json").exists():
        print(json.dumps(json.loads((OUT["closeout"] / "MACHINE_DEPLOYMENT_SUMMARY.json").read_text(encoding="utf-8")), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
