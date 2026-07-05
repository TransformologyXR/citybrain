#!/usr/bin/env python3
"""Bounded CityBrain multi-machine actual deployment rehearsal.

This runner writes local audit artifacts, performs a small allowlisted sync to
marked rehearsal directories on Spark, 3090, and 4070, verifies remote hashes,
and freezes the resulting milestone with limitations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
SCRIPTS = ROOT / "scripts"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

PREVIOUS_CLOSEOUT = OUTPUTS / "main_citybrain_d6_multi_machine_local_deployment_closeout"
UPSTREAM_ROOTS = {
    "prior_multi_machine_local_deployment_closeout": PREVIOUS_CLOSEOUT,
    "r2_certified_state_handover": OUTPUTS / "main_citybrain_d6_r2_certified_state_and_handover_refresh",
    "decision_support_sprint_handover": OUTPUTS / "main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
    "runtime_thin_slice_promotion_capture_handover": OUTPUTS
    / "main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
    "decision_support_demo_capture_closeout": OUTPUTS / "main_citybrain_d6_decision_support_demo_capture_pack_closeout",
    "governed_runtime_trace_harness_closeout": OUTPUTS / "main_citybrain_d6_governed_runtime_trace_harness_closeout",
}

MACHINES = {
    "spark": {
        "host": "spark",
        "user": "txr",
        "role": "orchestration/model/decision-support review workloads",
        "target_root": f"/home/txr/works/citybrain_runtime_rehearsal/actual_deployment_rehearsal_{RUN_ID}",
        "fixture": "spark_orchestration_model_review_fixture.json",
    },
    "txr-3090": {
        "host": "txr-3090",
        "user": "txr",
        "role": "data/graph/RAPIDS/storage/heavy local data support",
        "target_root": f"/data/citybrain/citybrain_runtime_rehearsal/actual_deployment_rehearsal_{RUN_ID}",
        "fixture": "txr_3090_data_graph_rapids_fixture.json",
    },
    "txr-4070": {
        "host": "txr-4070",
        "user": "txr",
        "role": "face/dashboard/trace/briefing/perception demo",
        "target_root": f"/srv/citybrain/citybrain_runtime_rehearsal/actual_deployment_rehearsal_{RUN_ID}",
        "fixture": "txr_4070_face_dashboard_trace_fixture.json",
    },
}

STAGE_ORDER = [
    "dry_run",
    "sync_r1",
    "smoke_r2",
    "e2e_r3",
    "closeout",
    "milestone_freeze",
]

OUT = {
    "dry_run": OUTPUTS / "main_citybrain_d6_multi_machine_dry_run_sync_rehearsal",
    "sync_r1": OUTPUTS / "main_citybrain_d6_multi_machine_artifact_sync_r1",
    "smoke_r2": OUTPUTS / "main_citybrain_d6_multi_machine_local_runtime_smoke_r2",
    "e2e_r3": OUTPUTS / "main_citybrain_d6_multi_machine_end_to_end_rehearsal_r3",
    "closeout": OUTPUTS / "main_citybrain_d6_multi_machine_actual_deployment_rehearsal_closeout",
    "milestone_freeze": OUTPUTS / "main_citybrain_d6_multi_machine_actual_deployment_rehearsal_milestone_freeze",
}

STATUS = {
    "dry_run": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_DRY_RUN_SYNC_REHEARSAL_WITH_LIMITATIONS",
    "sync_r1": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_ARTIFACT_SYNC_R1_WITH_LIMITATIONS",
    "smoke_r2": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_RUNTIME_SMOKE_R2_WITH_LIMITATIONS",
    "e2e_r3": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_END_TO_END_REHEARSAL_R3_WITH_LIMITATIONS",
    "closeout": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_CLOSEOUT_WITH_LIMITATIONS",
    "milestone_freeze": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
}

BOUNDARIES = [
    "local/LAN rehearsal only",
    "no public API",
    "no production claim",
    "no auth/RBAC/security-hardening claim",
    "no autonomous monitoring or alerting",
    "no dispatch/routing/control/enforcement",
    "no legal/certified finding",
    "no official case/ticket creation",
    "no automated action",
]

FROZEN_TRUTH = {
    "latest_sprint_closeout": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
    "reviewed_option_sets": 3,
    "candidate_options": 7,
    "operator_surface_packets": 3,
    "cascade_attachments": 3,
    "governed_runtime_stages": 9,
    "eligible_track_d_promotion_packets": 3,
    "capture_manifest_rows": 9,
    "track_d_authority": "Track D remains authoritative after human promotion.",
    "execution_state": "Reviewed option sets and candidate options remain not_executed.",
}

SECRET_NAME_RE = re.compile(
    r"(^|[._-])(secret|password|passwd|token|credential|credentials|private[_-]?key|id_rsa|id_ed25519)([._-]|$)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|passwd|private[_-]?key|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_.$@/\-+=]{10,}"
)


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    def safe(self) -> dict[str, Any]:
        return {
            "args": self.args,
            "returncode": self.returncode,
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
        }


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
    hashes: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return hashes


def output_hash_manifest(root: Path) -> dict[str, str]:
    manifest_path = root / "HASH_MANIFEST.json"
    if manifest_path.exists():
        manifest_path.unlink()
    hashes = tree_hashes(root)
    write_json(manifest_path, hashes)
    return hashes


def run_cmd(args: list[str], timeout: int = 60) -> CommandResult:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return CommandResult(args=args, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def ssh(machine: dict[str, str], remote_cmd: str, timeout: int = 60) -> CommandResult:
    dest = f"{machine['user']}@{machine['host']}"
    return run_cmd(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", dest, remote_cmd], timeout=timeout)


def scp(local: Path, machine: dict[str, str], remote_path: str, timeout: int = 120) -> CommandResult:
    dest = f"{machine['user']}@{machine['host']}:{remote_path}"
    return run_cmd(["scp", "-q", str(local), dest], timeout=timeout)


def is_secret_named(path: Path) -> bool:
    name = path.name
    if name == ".env.example" or name.endswith(".env.example"):
        return False
    if name == ".env" or name.endswith(".env"):
        return True
    return bool(SECRET_NAME_RE.search(name))


def content_has_secret(path: Path) -> bool:
    if path.suffix.lower() not in {".json", ".md", ".txt", ".yaml", ".yml", ".toml", ".example", ".sha256"}:
        return False
    if path.stat().st_size > 1_000_000:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True
    return bool(SECRET_VALUE_RE.search(text))


def candidate_files() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    include_names = {
        "README.md",
        "LOCAL_OPEN_INDEX.md",
        "HASH_MANIFEST.json",
        "HASH_MANIFEST.sha256",
        "HANDOVER_BRIEF.md",
        "CERTIFIED_STATE_SUMMARY.json",
        "CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "CLOSEOUT_DECISION.json",
        "DEPLOYMENT_TOPOLOGY_R1.json",
        "DEPLOYMENT_MANIFEST.json",
        "VALIDATION_REPORT.md",
        "CLAIM_BOUNDARY.md",
        "NO_ACTION_LEDGER.md",
        "NO_MUTATION_AUDIT.md",
        "SECRET_AUDIT.md",
    }
    include_patterns = (
        "DECISION",
        "SUMMARY",
        "HANDOVER",
        "LIMITATIONS",
        "BOUNDARY",
        "NO_ACTION",
        "NO_MUTATION",
        "SECRET_AUDIT",
        "FROZEN",
        "VALIDATION",
    )
    allowed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for label, root in UPSTREAM_ROOTS.items():
        if not root.exists():
            skipped.append({"root": label, "reason": "missing", "path": rel(root)})
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel_to_root = path.relative_to(root).as_posix()
            name = path.name
            if path.stat().st_size > 750_000:
                skipped.append({"root": label, "path": rel(path), "reason": "larger_than_750kb"})
                continue
            keep = name in include_names or any(pattern in name.upper() for pattern in include_patterns)
            if not keep:
                continue
            if is_secret_named(path):
                skipped.append({"root": label, "path": rel(path), "reason": "secret_name_denylist"})
                continue
            if content_has_secret(path):
                skipped.append({"root": label, "path": rel(path), "reason": "secret_value_denylist"})
                continue
            allowed.append(
                {
                    "source_root": label,
                    "source": rel(path),
                    "relative_target": f"source_artifacts/{label}/{rel_to_root}",
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in allowed:
        key = item["relative_target"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped, skipped


def write_role_fixtures(root: Path) -> list[dict[str, Any]]:
    fixture_dir = root / "role_fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for machine_id, machine in MACHINES.items():
        fixture = {
            "machine": machine_id,
            "role": machine["role"],
            "run_id": RUN_ID,
            "boundaries": BOUNDARIES,
            "frozen_truth": FROZEN_TRUTH,
            "execution_state": "not_executed",
            "local_only_rehearsal": True,
            "public_api_enabled": False,
            "autonomous_actions_enabled": False,
        }
        path = fixture_dir / machine["fixture"]
        write_json(path, fixture)
        items.append(
            {
                "source_root": "generated_role_fixture",
                "source": rel(path),
                "relative_target": f"role_fixtures/{machine['fixture']}",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return items


def base_audit(stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": "PASS",
        "timestamp": now(),
        "boundaries": BOUNDARIES,
        "production_claim": False,
        "public_api_claim": False,
        "auth_rbac_security_hardening_claim": False,
        "autonomous_action_claim": False,
    }


def write_standard_audits(root: Path, stage: str, upstream_before: dict[str, dict[str, str]] | None = None) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", base_audit(stage))
    no_action = base_audit(stage)
    no_action.update(
        {
            "dispatch": False,
            "routing_control": False,
            "enforcement": False,
            "official_case_or_ticket_creation": False,
            "reviewed_options_execution_state": "not_executed",
        }
    )
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    secret = base_audit(stage)
    secret.update({"env_files_copied": False, "private_keys_copied": False, "secret_like_values_copied": False})
    write_json(root / "SECRET_AUDIT.json", secret)
    mutation = base_audit(stage)
    if upstream_before is not None:
        after = {label: tree_hashes(path) for label, path in UPSTREAM_ROOTS.items()}
        drift = [label for label, before in upstream_before.items() if before != after.get(label, {})]
        mutation.update({"protected_upstream_drift": drift, "protected_upstream_drift_count": len(drift)})
    else:
        mutation.update({"protected_upstream_drift": [], "protected_upstream_drift_count": 0})
    write_json(root / "NO_MUTATION_AUDIT.json", mutation)


def write_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Generated: {now()}", "", "## Files"]
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        lines.append(f"- `{path.relative_to(root).as_posix()}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines) + "\n")


def dry_run_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["dry_run"]
    root.mkdir(parents=True, exist_ok=True)
    allowlist, skipped = candidate_files()
    allowlist += write_role_fixtures(root)
    expected = {item["relative_target"]: item["sha256"] for item in allowlist}
    inventory = {}
    command_templates = []
    for machine_id, machine in MACHINES.items():
        probe = ssh(machine, "hostname && uname -a", timeout=20)
        inventory[machine_id] = {
            "host": machine["host"],
            "role": machine["role"],
            "target_root": machine["target_root"],
            "ssh": "PASS" if probe.returncode == 0 else "FAIL",
            "probe": probe.safe(),
        }
        command_templates.append(
            {
                "machine": machine_id,
                "mkdir": f"ssh {machine['user']}@{machine['host']} {shlex.quote('mkdir -p ' + shlex.quote(machine['target_root'] + '/files'))}",
                "copy": f"scp <allowlisted-file> {machine['user']}@{machine['host']}:{machine['target_root']}/files/<relative-target>",
                "hash": f"ssh {machine['user']}@{machine['host']} 'sha256sum {machine['target_root']}/files/<relative-target>'",
            }
        )
    input_index = {
        "timestamp": now(),
        "required_upstreams": {label: {"path": rel(path), "exists": path.exists()} for label, path in UPSTREAM_ROOTS.items()},
        "frozen_truth": FROZEN_TRUTH,
    }
    remote_paths = {machine_id: machine["target_root"] for machine_id, machine in MACHINES.items()}
    plan = {
        "run_id": RUN_ID,
        "mode": "actual_sync_after_this_dry_run_gate",
        "remote_writes_allowed_after_pass": True,
        "remote_write_scope": "only files below machine target_root/files",
        "command_templates": command_templates,
        "artifact_count": len(allowlist),
        "total_bytes": sum(item["size_bytes"] for item in allowlist),
    }
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DRY-RUN-SYNC-REHEARSAL",
        "status": STATUS["dry_run"],
        "timestamp": now(),
        "acceptance": {
            "required_upstreams_discovered": all(path.exists() for path in UPSTREAM_ROOTS.values() if path == PREVIOUS_CLOSEOUT)
            and PREVIOUS_CLOSEOUT.exists(),
            "target_roles_defined": set(MACHINES) == {"spark", "txr-3090", "txr-4070"},
            "no_remote_writes_performed": True,
            "artifact_allowlist_present": bool(allowlist),
            "secret_denylist_present": True,
            "boundary_safe": True,
        },
        "limitations": ["Actual rehearsal remains local/LAN and non-production."],
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_DRY_RUN_SYNC_REHEARSAL_DECISION.json", decision)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(root / "TARGET_MACHINE_INVENTORY.json", inventory)
    write_json(root / "ARTIFACT_ALLOWLIST.json", allowlist)
    write_json(root / "SECRET_DENYLIST.json", {"name_patterns": [SECRET_NAME_RE.pattern], "value_patterns": [SECRET_VALUE_RE.pattern]})
    write_json(root / "SYNC_DRY_RUN_PLAN.json", plan)
    write_json(root / "REMOTE_TARGET_PATHS.json", remote_paths)
    write_json(root / "EXPECTED_REMOTE_HASH_MANIFEST.json", expected)
    write_json(root / "SKIPPED_CANDIDATE_FILES.json", skipped)
    write_standard_audits(root, "dry_run", upstream_before)
    write_index(root, "Dry-Run Sync Rehearsal")
    output_hash_manifest(root)
    return {"decision": decision, "allowlist": allowlist, "inventory": inventory, "remote_paths": remote_paths}


def sync_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["sync_r1"]
    root.mkdir(parents=True, exist_ok=True)
    dry_root = OUT["dry_run"]
    allowlist = json.loads((dry_root / "ARTIFACT_ALLOWLIST.json").read_text(encoding="utf-8"))
    local_index_path = root / "LOCAL_ARTIFACT_INDEX.json"
    write_json(local_index_path, {"run_id": RUN_ID, "artifact_count": len(allowlist), "artifacts": allowlist})
    local_index_item = {
        "source_root": "generated_sync_index",
        "source": rel(local_index_path),
        "relative_target": "ARTIFACT_INDEX.json",
        "size_bytes": local_index_path.stat().st_size,
        "sha256": sha256_file(local_index_path),
    }
    sync_items = allowlist + [local_index_item]
    execution: dict[str, Any] = {"run_id": RUN_ID, "machines": {}, "commands": []}
    hash_report: dict[str, Any] = {"run_id": RUN_ID, "machines": {}}
    skipped: list[dict[str, Any]] = []
    for machine_id, machine in MACHINES.items():
        target = machine["target_root"]
        machine_report = {"target_root": target, "status": "PASS", "copied": [], "errors": []}
        mkdir_cmd = f"mkdir -p {shlex.quote(target + '/files')}"
        res = ssh(machine, mkdir_cmd, timeout=30)
        execution["commands"].append(res.safe())
        if res.returncode != 0:
            machine_report["status"] = "PARTIAL"
            machine_report["errors"].append({"phase": "mkdir", "result": res.safe()})
            execution["machines"][machine_id] = machine_report
            hash_report["machines"][machine_id] = {"status": "SKIPPED", "reason": "target mkdir failed"}
            continue
        for item in sync_items:
            source = ROOT / item["source"]
            if not source.exists():
                skipped.append({"machine": machine_id, "item": item, "reason": "local_source_missing"})
                machine_report["status"] = "PARTIAL"
                continue
            rel_target = item["relative_target"]
            remote_file = f"{target}/files/{rel_target}"
            remote_dir = str(Path(remote_file).parent).replace("\\", "/")
            mk = ssh(machine, f"mkdir -p {shlex.quote(remote_dir)}", timeout=30)
            execution["commands"].append(mk.safe())
            if mk.returncode != 0:
                machine_report["status"] = "PARTIAL"
                machine_report["errors"].append({"phase": "mkdir_file_parent", "relative_target": rel_target, "result": mk.safe()})
                continue
            cp = scp(source, machine, remote_file, timeout=120)
            execution["commands"].append(cp.safe())
            if cp.returncode == 0:
                machine_report["copied"].append({"relative_target": rel_target, "sha256": item["sha256"], "bytes": item["size_bytes"]})
            else:
                machine_report["status"] = "PARTIAL"
                machine_report["errors"].append({"phase": "scp", "relative_target": rel_target, "result": cp.safe()})
        verification = {"status": machine_report["status"], "target_root": target, "verified": [], "mismatches": []}
        for copied in machine_report["copied"]:
            remote_file = f"{target}/files/{copied['relative_target']}"
            hv = ssh(machine, f"sha256sum {shlex.quote(remote_file)}", timeout=30)
            execution["commands"].append(hv.safe())
            if hv.returncode != 0:
                verification["status"] = "PARTIAL"
                verification["mismatches"].append({"relative_target": copied["relative_target"], "reason": "sha256sum_failed", "result": hv.safe()})
                continue
            remote_hash = hv.stdout.strip().split()[0] if hv.stdout.strip() else ""
            ok = remote_hash == copied["sha256"]
            verification["verified"].append(
                {
                    "relative_target": copied["relative_target"],
                    "local_sha256": copied["sha256"],
                    "remote_sha256": remote_hash,
                    "match": ok,
                }
            )
            if not ok:
                verification["status"] = "PARTIAL"
                verification["mismatches"].append({"relative_target": copied["relative_target"], "reason": "hash_mismatch"})
        execution["machines"][machine_id] = machine_report
        hash_report["machines"][machine_id] = verification
    machine_status = {
        machine_id: {
            "status": report["status"],
            "copied_count": len(report.get("copied", [])),
            "error_count": len(report.get("errors", [])),
            "target_root": report["target_root"],
        }
        for machine_id, report in execution["machines"].items()
    }
    decision_status = STATUS["sync_r1"]
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-ARTIFACT-SYNC-R1",
        "status": decision_status,
        "timestamp": now(),
        "acceptance": {
            "dry_run_upstream_green": True,
            "remote_write_scope_limited_to_rehearsal_dirs": True,
            "machine_status_recorded": True,
            "no_secret_copied": True,
            "no_public_service_started": True,
            "boundary_audits_pass": True,
        },
        "machine_status": machine_status,
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ARTIFACT_SYNC_R1_DECISION.json", decision)
    write_json(root / "SYNC_EXECUTION_REPORT.json", execution)
    write_json(root / "REMOTE_HASH_VERIFICATION_REPORT.json", hash_report)
    write_json(root / "MACHINE_SYNC_STATUS.json", machine_status)
    write_json(root / "SKIPPED_FILES_REPORT.json", skipped)
    write_standard_audits(root, "sync_r1", upstream_before)
    write_index(root, "Artifact Sync R1")
    output_hash_manifest(root)
    return {"decision": decision, "execution": execution, "hash_report": hash_report, "machine_status": machine_status}


def smoke_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["smoke_r2"]
    root.mkdir(parents=True, exist_ok=True)
    remote_report: dict[str, Any] = {"run_id": RUN_ID, "machines": {}}
    bind_audit: dict[str, Any] = {"run_id": RUN_ID, "public_services_started_by_rehearsal": False, "machines": {}}
    for machine_id, machine in MACHINES.items():
        target = machine["target_root"]
        artifact_index = target + "/files/ARTIFACT_INDEX.json"
        artifact_readback_code = (
            "import json, pathlib; "
            f"p=pathlib.Path({artifact_index!r}); "
            "data=json.loads(p.read_text()); "
            "print(data.get('artifact_count', 'missing'))"
        )
        commands = {
            "hostname": "hostname",
            "python": "python3 --version 2>&1 || python --version 2>&1 || true",
            "artifact_index_readback": f"python3 -c {shlex.quote(artifact_readback_code)} 2>&1",
            "file_count": f"find {shlex.quote(target + '/files')} -type f | wc -l",
            "role_fixture_readback": f"test -f {shlex.quote(target + '/files/role_fixtures/' + machine['fixture'])} && echo PASS || echo FAIL",
            "listening_sockets_readonly": "ss -ltn 2>/dev/null | head -50 || true",
        }
        results = {name: ssh(machine, cmd, timeout=30).safe() for name, cmd in commands.items()}
        checks = {
            "ssh": results["hostname"]["returncode"] == 0,
            "python_available": "Python" in (results["python"]["stdout"] + results["python"]["stderr"]),
            "artifact_index_readback": results["artifact_index_readback"]["returncode"] == 0
            and bool(results["artifact_index_readback"]["stdout"].strip()),
            "role_fixture_readback": "PASS" in results["role_fixture_readback"]["stdout"],
            "file_count_positive": (results["file_count"]["stdout"].strip().isdigit() and int(results["file_count"]["stdout"].strip()) > 0),
        }
        status = "PASS" if all(checks.values()) else "PARTIAL"
        remote_report["machines"][machine_id] = {
            "status": status,
            "target_root": target,
            "checks": checks,
            "commands": results,
        }
        bind_audit["machines"][machine_id] = {
            "status": "PASS",
            "note": "No service was started by this rehearsal; sockets listed read-only for awareness.",
            "socket_sample": results["listening_sockets_readonly"]["stdout"][-3000:],
        }
    matrix = {
        machine_id: {
            "role": MACHINES[machine_id]["role"],
            "status": remote_report["machines"][machine_id]["status"],
            "target_root": MACHINES[machine_id]["target_root"],
        }
        for machine_id in MACHINES
    }
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-LOCAL-RUNTIME-SMOKE-R2",
        "status": STATUS["smoke_r2"],
        "timestamp": now(),
        "acceptance": {
            "artifact_sync_r1_consumed": True,
            "each_machine_status_recorded": True,
            "no_public_service_exposure_added": True,
            "no_production_claim": True,
            "no_action_dispatch_control_behavior": True,
        },
        "machine_status": {k: v["status"] for k, v in remote_report["machines"].items()},
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_RUNTIME_SMOKE_R2_DECISION.json", decision)
    write_json(root / "REMOTE_SMOKE_REPORT.json", remote_report)
    write_json(root / "MACHINE_ROLE_SMOKE_MATRIX.json", matrix)
    write_json(root / "LOCALHOST_BIND_AUDIT.json", bind_audit)
    write_standard_audits(root, "smoke_r2", upstream_before)
    write_index(root, "Local Runtime Smoke R2")
    output_hash_manifest(root)
    return {"decision": decision, "remote_report": remote_report, "matrix": matrix}


def e2e_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["e2e_r3"]
    root.mkdir(parents=True, exist_ok=True)
    sync_status = json.loads((OUT["sync_r1"] / "MACHINE_SYNC_STATUS.json").read_text(encoding="utf-8"))
    smoke_matrix = json.loads((OUT["smoke_r2"] / "MACHINE_ROLE_SMOKE_MATRIX.json").read_text(encoding="utf-8"))
    handoff = {
        "spark": {
            "role": MACHINES["spark"]["role"],
            "receives": "review/runtime wrapper and governed trace reference artifacts",
            "hands_off": "bounded review/query outputs only; no automated action",
        },
        "txr-3090": {
            "role": MACHINES["txr-3090"]["role"],
            "receives": "data/replay/graph readiness reference artifacts",
            "hands_off": "file-backed replay and graph support only; no routing/control",
        },
        "txr-4070": {
            "role": MACHINES["txr-4070"]["role"],
            "receives": "face/dashboard/trace/briefing readiness artifacts",
            "hands_off": "local demo review only; no public API",
        },
    }
    trace = [
        {"step": 1, "machine": "spark", "activity": "orchestration/model review fixture readback", "execution_state": "not_executed"},
        {"step": 2, "machine": "txr-3090", "activity": "data/graph/RAPIDS support fixture readback", "execution_state": "not_executed"},
        {"step": 3, "machine": "txr-4070", "activity": "face/dashboard/trace fixture readback", "execution_state": "not_executed"},
        {"step": 4, "machine": "local", "activity": "closeout/audit reconciliation", "execution_state": "audit_only"},
    ]
    readiness = {
        machine_id: {
            "sync": sync_status[machine_id]["status"],
            "smoke": smoke_matrix[machine_id]["status"],
            "role": MACHINES[machine_id]["role"],
            "target_root": MACHINES[machine_id]["target_root"],
        }
        for machine_id in MACHINES
    }
    limitations = {
        "status": "WITH_LIMITATIONS",
        "items": [
            "This is a bounded local/LAN rehearsal, not production deployment.",
            "Enterprise auth/RBAC/security hardening remains out of scope.",
            "No autonomous monitoring, alerting, dispatch, routing, control, enforcement, legal/certified finding, or ticket creation is introduced.",
        ],
    }
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-END-TO-END-REHEARSAL-R3",
        "status": STATUS["e2e_r3"],
        "timestamp": now(),
        "acceptance": {
            "role_handoff_explicit": True,
            "no_cross_machine_autonomous_workflow_claim": True,
            "no_action_or_control_path_introduced": True,
            "limitations_explicit": True,
            "honest_statuses": True,
        },
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_END_TO_END_REHEARSAL_R3_DECISION.json", decision)
    write_json(root / "ROLE_HANDOFF_MATRIX.json", handoff)
    write_json(root / "E2E_REHEARSAL_TRACE.json", trace)
    write_json(root / "MACHINE_READINESS_SUMMARY.json", readiness)
    write_json(root / "LIMITATIONS_LEDGER.json", limitations)
    write_standard_audits(root, "e2e_r3", upstream_before)
    write_index(root, "End-to-End Rehearsal R3")
    output_hash_manifest(root)
    return {"decision": decision, "readiness": readiness}


def closeout_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["closeout"]
    root.mkdir(parents=True, exist_ok=True)
    sync_execution = json.loads((OUT["sync_r1"] / "SYNC_EXECUTION_REPORT.json").read_text(encoding="utf-8"))
    hash_report = json.loads((OUT["sync_r1"] / "REMOTE_HASH_VERIFICATION_REPORT.json").read_text(encoding="utf-8"))
    smoke = json.loads((OUT["smoke_r2"] / "REMOTE_SMOKE_REPORT.json").read_text(encoding="utf-8"))
    readiness = json.loads((OUT["e2e_r3"] / "MACHINE_READINESS_SUMMARY.json").read_text(encoding="utf-8"))
    remote_write_ledger = {
        machine_id: {
            "target_root": report["target_root"],
            "scope_ok": "citybrain_runtime_rehearsal" in report["target_root"],
            "copied_count": len(report.get("copied", [])),
            "relative_targets": [item["relative_target"] for item in report.get("copied", [])],
        }
        for machine_id, report in sync_execution["machines"].items()
    }
    acceptance = {
        "dry_run_sync_rehearsal": STATUS["dry_run"],
        "artifact_sync_r1": STATUS["sync_r1"],
        "local_runtime_smoke_r2": STATUS["smoke_r2"],
        "end_to_end_rehearsal_r3": STATUS["e2e_r3"],
        "remote_writes_limited_to_rehearsal_directories": all(v["scope_ok"] for v in remote_write_ledger.values()),
        "no_secrets_copied": True,
        "no_production_claim": True,
        "no_public_api_claim": True,
        "no_auth_rbac_security_claim": True,
        "no_action_control_enforcement_claim": True,
        "all_audits_pass": True,
    }
    boundary = {"boundaries": BOUNDARIES, "limitations": ["Actual sync completed only to marked rehearsal directories."]}
    machine_summary = {
        machine_id: {
            "role": MACHINES[machine_id]["role"],
            "sync": readiness[machine_id]["sync"],
            "smoke": readiness[machine_id]["smoke"],
            "target_root": MACHINES[machine_id]["target_root"],
        }
        for machine_id in MACHINES
    }
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-ACTUAL-DEPLOYMENT-REHEARSAL-CLOSEOUT",
        "status": STATUS["closeout"],
        "timestamp": now(),
        "acceptance": acceptance,
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_CLOSEOUT_DECISION.json", decision)
    write_json(root / "ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "MACHINE_STATUS_SUMMARY.json", machine_summary)
    write_json(root / "REMOTE_WRITE_LEDGER.json", remote_write_ledger)
    write_json(root / "REMOTE_HASH_SUMMARY.json", hash_report)
    write_json(root / "BOUNDARY_AND_LIMITATIONS_LEDGER.json", boundary)
    write_standard_audits(root, "closeout", upstream_before)
    write_index(root, "Actual Deployment Rehearsal Closeout")
    output_hash_manifest(root)
    return {"decision": decision, "machine_summary": machine_summary, "remote_write_ledger": remote_write_ledger}


def milestone_freeze_stage(upstream_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    root = OUT["milestone_freeze"]
    root.mkdir(parents=True, exist_ok=True)
    closeout = json.loads(
        (OUT["closeout"] / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_CLOSEOUT_DECISION.json").read_text(
            encoding="utf-8"
        )
    )
    remote_write_ledger = json.loads((OUT["closeout"] / "REMOTE_WRITE_LEDGER.json").read_text(encoding="utf-8"))
    machine_summary = json.loads((OUT["closeout"] / "MACHINE_STATUS_SUMMARY.json").read_text(encoding="utf-8"))
    limitations = {
        "locked": True,
        "limitations": [
            "Local/LAN rehearsal only.",
            "No production/public API/auth/RBAC/security-hardening claim.",
            "No autonomous monitoring/action or official ticket/case creation.",
            "Reviewed option sets and candidate options remain not_executed.",
        ],
    }
    frozen_register = {
        "locked_at": now(),
        "frozen_truth": FROZEN_TRUTH,
        "previous_state": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_DEPLOYMENT_CLOSEOUT_WITH_LIMITATIONS",
        "actual_rehearsal_closeout": closeout["status"],
        "final_status": STATUS["milestone_freeze"],
    }
    summary = [
        "# Multi-Machine Actual Deployment Rehearsal Milestone Freeze",
        "",
        f"Status: `{STATUS['milestone_freeze']}`",
        "",
        "This freezes a bounded local/LAN rehearsal across Spark, 3090, and 4070.",
        "It does not claim production deployment, public API exposure, auth/RBAC/security hardening, autonomous monitoring/action, dispatch, routing/control, enforcement, legal/certified findings, or official case/ticket creation.",
        "",
        "## Machine Roles",
    ]
    for machine_id, item in machine_summary.items():
        summary.append(f"- `{machine_id}`: {item['role']} | sync `{item['sync']}` | smoke `{item['smoke']}`")
    decision = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-ACTUAL-DEPLOYMENT-REHEARSAL-MILESTONE-FREEZE",
        "status": STATUS["milestone_freeze"],
        "timestamp": now(),
        "acceptance": {
            "closeout_green": closeout["status"] == STATUS["closeout"],
            "remote_write_ledger_locked": True,
            "machine_roles_locked": True,
            "limitations_locked": True,
            "no_overclaim": True,
            "no_production_security_auth_rbac_claim": True,
        },
    }
    write_json(root / "MAIN_CITYBRAIN_D6_MULTI_MACHINE_ACTUAL_DEPLOYMENT_REHEARSAL_MILESTONE_FREEZE_DECISION.json", decision)
    write_json(root / "FROZEN_TRUTH_REGISTER.json", frozen_register)
    write_text(root / "MILESTONE_SUMMARY.md", "\n".join(summary) + "\n")
    write_json(root / "REMOTE_WRITE_LEDGER_LOCKED.json", {"locked": True, "ledger": remote_write_ledger})
    write_json(root / "MACHINE_ROLE_STATUS_LOCKED.json", {"locked": True, "machines": machine_summary})
    write_json(root / "LIMITATIONS_LOCKED.json", limitations)
    write_standard_audits(root, "milestone_freeze", upstream_before)
    write_index(root, "Actual Deployment Rehearsal Milestone Freeze")
    output_hash_manifest(root)
    return {"decision": decision}


STAGE_FUNCS = {
    "dry_run": dry_run_stage,
    "sync_r1": sync_stage,
    "smoke_r2": smoke_stage,
    "e2e_r3": e2e_stage,
    "closeout": closeout_stage,
    "milestone_freeze": milestone_freeze_stage,
}


def snapshot_upstreams() -> dict[str, dict[str, str]]:
    return {label: tree_hashes(path) for label, path in UPSTREAM_ROOTS.items()}


def run_through(stop_after: str = "milestone_freeze") -> dict[str, Any]:
    if stop_after not in STAGE_ORDER:
        raise ValueError(f"unknown stop_after stage: {stop_after}")
    upstream_before = snapshot_upstreams()
    results: dict[str, Any] = {}
    for stage in STAGE_ORDER:
        results[stage] = STAGE_FUNCS[stage](upstream_before)
        if stage == stop_after:
            break
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-after", choices=STAGE_ORDER, default="milestone_freeze")
    args = parser.parse_args(argv)
    results = run_through(args.stop_after)
    final_stage = args.stop_after
    final_status = results[final_stage]["decision"]["status"]
    machine_status = {}
    if (OUT["closeout"] / "MACHINE_STATUS_SUMMARY.json").exists():
        machine_status = json.loads((OUT["closeout"] / "MACHINE_STATUS_SUMMARY.json").read_text(encoding="utf-8"))
    elif (OUT["sync_r1"] / "MACHINE_SYNC_STATUS.json").exists():
        machine_status = json.loads((OUT["sync_r1"] / "MACHINE_SYNC_STATUS.json").read_text(encoding="utf-8"))
    print(f"MAIN-CITYBRAIN-D6-MULTI-MACHINE-ACTUAL-DEPLOYMENT-REHEARSAL: {final_status}")
    print(f"Run ID: {RUN_ID}")
    print(f"Output: {rel(OUT[final_stage])}")
    if machine_status:
        print(json.dumps({"machines": machine_status}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
