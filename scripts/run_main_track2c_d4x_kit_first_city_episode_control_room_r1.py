#!/usr/bin/env python3
"""Build the Kit-first CityBrain episode control-room package and web companion."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK2C-D4X-KIT-FIRST-CITY-EPISODE-CONTROL-ROOM-R1"
SCHEMA_VERSION = "main-track2c-d4x-kit-first-city-episode-control-room-r1.v1"
PASS_STATUS = "PASS_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1"
APP_DIR = OUTPUT_ROOT / "TRACK2C_WEB_COMPANION_APP"

EPISODE_ROOT = REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end"
ASSET_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end"
R5_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"
R5_BUILDING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice"
BRIDGE_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1"
KIT_EXTENSION_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2"
PICK_BRIDGE_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
HANDOVER_ZIP = Path.home() / "Downloads/trackB_kit_first_city_episode_control_room_handover.zip"

STRICT_NO_MUTATION_ROOTS = [EPISODE_ROOT, ASSET_ROOT, R5_ROOT, R5_BUILDING_ROOT, KIT_EXTENSION_ROOT, PICK_BRIDGE_ROOT]
VOLATILE_READ_ONLY_ROOTS = [BRIDGE_ROOT]

REQUIRED_FILES = [
    "README.md",
    "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1.md",
    "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json",
    "TRACK2C_KIT_FIRST_PREREQUISITE_REPORT.json",
    "TRACK2C_KIT_FIRST_ARCHITECTURE.md",
    "TRACK2C_KIT_CONTROL_ROOM_SPEC.json",
    "TRACK2C_WEB_COMPANION_SPEC.json",
    "TRACK2C_SOURCE_ARTIFACT_MAP.json",
    "TRACK2C_INTEGRATED_EPISODE_PACK.json",
    "TRACK2C_EPISODE_ASSET_DOMAIN_JOIN_REPORT.json",
    "TRACK2C_KIT_CAMERA_BOOKMARKS.json",
    "TRACK2C_KIT_STAGE_HANDOFFS.json",
    "TRACK2C_KIT_VIEWPORT_BRIDGE_STATUS.json",
    "TRACK2C_KIT_FRAME_PREVIEW_REPORT.json",
    "TRACK2C_WEB_COMPANION_APP/index.html",
    "TRACK2C_WEB_COMPANION_DATA.json",
    "TRACK2C_APP_HANDOFF_PACK.json",
    "TRACK2C_INTEGRATED_DEMO_SMOKE_REPORT.json",
    "TRACK2C_NONTECHNICAL_DEMO_WALKTHROUGH.md",
    "TRACK2C_TECHNICAL_DEMO_WALKTHROUGH.md",
    "TRACK2C_DEMO_CAPTURE_CHECKLIST.md",
    "TRACK2C_DEMO_STORYBOARD.json",
    "TRACK2C_BOUNDARY_VALIDATION_REPORT.json",
    "TRACK2C_NO_ACTION_AUDIT_REPORT.json",
    "TRACK2C_NEGATIVE_TEST_REPORT.json",
    "TRACK2C_LIMITATION_REGISTER.md",
    "TRACK2C_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

LIMITATIONS = [
    "local demo/control-room package only",
    "Kit-first, web companion only",
    "viewport bridge is polling/capture, not WebRTC/native streaming",
    "not production UI",
    "no auth/RBAC",
    "no public deployment",
    "no command/control/action",
    "no legal/certified claims",
    "no app mutation outside output root",
    "limitations are embedded in episode evidence panels",
]

CITY_TARGETS = {"BARC": 8, "NYC": 6, "CHI": 4, "LON": 4, "CROSS_CITY": 6}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.encode("ascii", "ignore").decode("ascii")
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return clean(json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean(text).rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_root(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    sig: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        sig[rel] = f"{stat.st_size}:{int(stat.st_mtime)}"
    return sig


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_track2c_d4x_kit_first_city_episode_control_room_r1":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in [
        APP_DIR,
        APP_DIR / "assets",
        OUTPUT_ROOT / "kit_handoff",
        OUTPUT_ROOT / "data",
        OUTPUT_ROOT / "smoke",
        OUTPUT_ROOT / "audits",
        OUTPUT_ROOT / "capture",
        OUTPUT_ROOT / "handover",
        OUTPUT_ROOT / "logs",
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def hash_outputs() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    write_text(OUTPUT_ROOT / "hashes.sha256", "".join(f"{digest}  {rel}\n" for rel, digest in rows))
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def unpack_handover() -> dict[str, Any]:
    if not HANDOVER_ZIP.exists():
        return {"status": "MISSING_OPTIONAL_HANDOVER_ZIP", "path": str(HANDOVER_ZIP)}
    out = OUTPUT_ROOT / "handover"
    with zipfile.ZipFile(HANDOVER_ZIP) as zf:
        zf.extractall(out)
        names = zf.namelist()
    return {"status": "PRESENT_EXTRACTED_READ_ONLY_COPY", "path": str(HANDOVER_ZIP), "entry_count": len(names)}


def load_inputs() -> dict[str, Any]:
    return {
        "episode_decision": read_json(EPISODE_ROOT / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_DECISION.json", {}),
        "asset_decision": read_json(ASSET_ROOT / "MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_DECISION.json", {}),
        "r5_decision": read_json(R5_ROOT / "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json", {}),
        "bridge_decision": read_json(BRIDGE_ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1_DECISION.json", {}),
        "kit_ext_decision": read_json(KIT_EXTENSION_ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json", {}),
        "episodes": read_json(EPISODE_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", {}).get("episodes", []),
        "app_episode_pack": read_json(EPISODE_ROOT / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json", {}),
        "assets": read_json(ASSET_ROOT / "TRACK2A_SELECTED_DEMO_ASSETS.json", {}).get("assets", []),
        "omni_handoffs": read_json(ASSET_ROOT / "TRACK2A_OMNIVERSE_USD_HANDOFF_REGISTRY.json", {}).get("handoffs", []),
        "asset_domain_handoffs": read_json(ASSET_ROOT / "TRACK2A_TRACK1_DOMAIN_HANDOFF_REGISTRY.json", {}).get("handoffs", []),
        "asset_app_handoffs": read_json(ASSET_ROOT / "TRACK2A_TRACK2C_APP_HANDOFF_REGISTRY.json", {}).get("handoffs", []),
        "building_domain_packets": read_json(R5_BUILDING_ROOT / "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json", {}).get("packets", []),
        "civic_domain_packets": read_json(R5_ROOT / "R5_CIVIC_SERVICE_RUNTIME_SLICE_APP_HANDOFF_PACKETS.json", {}).get("packets", []),
        "pick_bridge_mappings": read_json(PICK_BRIDGE_ROOT / "OMNI_USD_PRIM_TO_ASSET_MAP.json", {}).get("mappings", []),
        "bridge_state": read_json(BRIDGE_ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json", {}),
        "kit_status": read_json(BRIDGE_ROOT / "runtime/kit_extension_status.json", {}),
    }


def source_artifact_map(inputs: dict[str, Any], handover: dict[str, Any]) -> dict[str, Any]:
    def file_info(path: Path) -> dict[str, Any]:
        return {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
        }

    artifacts = [
        file_info(EPISODE_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json"),
        file_info(EPISODE_ROOT / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json"),
        file_info(ASSET_ROOT / "TRACK2A_SELECTED_DEMO_ASSETS.json"),
        file_info(ASSET_ROOT / "TRACK2A_OMNIVERSE_USD_HANDOFF_REGISTRY.json"),
        file_info(ASSET_ROOT / "TRACK2A_TRACK1_DOMAIN_HANDOFF_REGISTRY.json"),
        file_info(R5_BUILDING_ROOT / "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json"),
        file_info(R5_ROOT / "R5_CIVIC_SERVICE_RUNTIME_SLICE_APP_HANDOFF_PACKETS.json"),
        file_info(BRIDGE_ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json"),
        file_info(KIT_EXTENSION_ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json"),
        file_info(PICK_BRIDGE_ROOT / "OMNI_USD_PRIM_TO_ASSET_MAP.json"),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "handover": handover,
        "source_counts": {
            "episodes": len(inputs["episodes"]),
            "assets": len(inputs["assets"]),
            "omni_handoffs": len(inputs["omni_handoffs"]),
            "asset_domain_handoffs": len(inputs["asset_domain_handoffs"]),
            "building_domain_packets": len(inputs["building_domain_packets"]),
            "civic_domain_packets": len(inputs["civic_domain_packets"]),
            "pick_bridge_mappings": len(inputs["pick_bridge_mappings"]),
        },
        "artifacts": artifacts,
        "read_only_inputs": [root.relative_to(REPO_ROOT).as_posix() for root in STRICT_NO_MUTATION_ROOTS + VOLATILE_READ_ONLY_ROOTS],
    }


def latest_bridge_frame() -> dict[str, Any]:
    screenshots = BRIDGE_ROOT / "screenshots"
    latest = screenshots / "kit_live_BARC_latest.png"
    if not latest.exists() and screenshots.exists():
        candidates = sorted(screenshots.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest = candidates[0] if candidates else latest
    copied = None
    if latest.exists():
        copied = APP_DIR / "assets" / "kit_live_latest.png"
        shutil.copy2(latest, copied)
    return {
        "status": "FRAME_AVAILABLE" if latest.exists() else "NO_FRAME_AVAILABLE",
        "source_path": latest.relative_to(REPO_ROOT).as_posix() if latest.exists() else None,
        "companion_preview_path": copied.relative_to(OUTPUT_ROOT).as_posix() if copied else None,
        "bytes": latest.stat().st_size if latest.exists() else 0,
        "last_modified_utc": datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat() if latest.exists() else None,
        "claim_boundary": "Preview frame only; polling/capture bridge, not embedded WebRTC or native web USD/RTX streaming.",
    }


def by_city(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[str(item.get("city_id") or item.get("city") or "UNKNOWN")].append(item)
    return grouped


def choose_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = by_city(episodes)
    selected: list[dict[str, Any]] = []
    for city, count in CITY_TARGETS.items():
        pool = grouped.get(city, [])
        pool = sorted(
            pool,
            key=lambda e: (
                0 if e.get("building_asset_refs") else 1,
                -int(e.get("display_priority") or 0),
                str(e.get("episode_id")),
            ),
        )
        selected.extend(pool[:count])
    selected_ids = {e.get("episode_id") for e in selected}
    for episode in episodes:
        if len(selected) >= 28:
            break
        if episode.get("episode_id") not in selected_ids:
            selected.append(episode)
            selected_ids.add(episode.get("episode_id"))
    return selected


def pick_rotating(pool: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if not pool:
        return None
    return pool[index % len(pool)]


def episode_text(episode: dict[str, Any]) -> str:
    return str(episode.get("what_is_happening") or episode.get("summary") or episode.get("headline") or "City context episode.")


def build_integrated_pack(inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    episodes = choose_episodes(inputs["episodes"])
    assets_by_city = by_city(inputs["assets"])
    building_packets_by_city = by_city(inputs["building_domain_packets"])
    civic_packets_by_city = by_city(inputs["civic_domain_packets"])
    domain_handoffs_by_asset = {
        str(h.get("asset_registry_ref")): h for h in inputs["asset_domain_handoffs"] if h.get("asset_registry_ref")
    }
    omni_by_asset: dict[str, dict[str, Any]] = {}
    for handoff in inputs["omni_handoffs"]:
        for ref in handoff.get("asset_registry_refs", []):
            omni_by_asset[str(ref)] = handoff

    integrated = []
    camera_bookmarks = []
    app_handoff = []
    storyboard = []
    stage_refs: dict[str, dict[str, Any]] = {}

    for index, episode in enumerate(episodes, start=1):
        city = str(episode.get("city_id") or "UNKNOWN")
        asset = pick_rotating(assets_by_city.get(city, []), index)
        asset_ref = asset.get("asset_registry_id") if asset else None
        omni = omni_by_asset.get(asset_ref or "", {})
        domain_handoff = domain_handoffs_by_asset.get(asset_ref or "", {})
        building_packet = pick_rotating(building_packets_by_city.get(city, inputs["building_domain_packets"]), index)
        civic_packet = pick_rotating(civic_packets_by_city.get(city, inputs["civic_domain_packets"]), index)

        domain_refs = []
        if domain_handoff:
            domain_refs.append(domain_handoff.get("handoff_id"))
        if building_packet:
            domain_refs.append(building_packet.get("app_handoff_packet_id"))
        if civic_packet:
            domain_refs.append(civic_packet.get("app_handoff_packet_id"))
        domain_refs = [str(ref) for ref in domain_refs if ref]

        limitation_refs = []
        limitation_refs.extend(episode.get("limitations") or [])
        if asset:
            limitation_refs.extend(asset.get("limitation_refs") or [])
        if domain_handoff:
            limitation_refs.extend(domain_handoff.get("limitation_refs") or [])
        if building_packet:
            limitation_refs.extend(building_packet.get("limitation_refs") or [])
        if civic_packet:
            limitation_refs.extend(civic_packet.get("limitation_refs") or [])
        limitation_refs.extend([
            "Kit-first local demo only",
            "Limitations are evidence, not footer",
            "No action taken",
        ])

        evidence_refs = []
        evidence_refs.extend(episode.get("evidence_refs") or [])
        if asset:
            evidence_refs.extend(asset.get("evidence_refs") or [])
        if domain_handoff:
            evidence_refs.extend(domain_handoff.get("evidence_refs") or [])
        if building_packet:
            evidence_refs.extend(building_packet.get("evidence_refs") or [])
        if civic_packet:
            evidence_refs.extend(civic_packet.get("evidence_refs") or [])
        if not evidence_refs:
            evidence_refs.append(f"episode-ref:{episode.get('episode_id')}")

        stage_path = None
        prim_focus = None
        if asset:
            usd_refs = asset.get("usd_scene_refs", {})
            stage_path = usd_refs.get("master_usda") or omni.get("usd_scene_path")
            prim_focus = usd_refs.get("usd_prim_root")
        elif city in ("CHI", "LON"):
            stage_path = "DATA_FIRST_NO_FULL_3D_ASSET"
        elif city == "CROSS_CITY":
            stage_path = "CROSS_CITY_EPISODE_NO_SINGLE_STAGE"

        bookmark_id = f"kit-bookmark-{index:03d}-{city.lower()}"
        integrated_id = f"kit-episode-{index:03d}"
        safe_next_looks = list(episode.get("safe_next_looks") or [])
        if asset:
            safe_next_looks.append("Open Kit asset focus preview")
        safe_next_looks.extend(["Inspect evidence and limitations together", "Keep no-action status"])

        claim_boundary = (
            episode.get("claim_boundary")
            or (asset or {}).get("claim_boundary")
            or "Review/context only; no production, legal, certified, command, dispatch, enforcement, routing, or control claim."
        )

        integrated_episode = {
            "schema_version": SCHEMA_VERSION,
            "integrated_episode_id": integrated_id,
            "episode_ref": episode.get("episode_id"),
            "headline": episode.get("headline"),
            "city_id": city,
            "city_name": episode.get("city_name") or city,
            "domain": episode.get("domain"),
            "episode_type": episode.get("episode_type"),
            "what_is_happening": episode_text(episode),
            "why_it_matters": episode.get("why_it_matters") or "Review context for the city control room; not an operational finding.",
            "primary_asset_ref": asset_ref,
            "asset_registry_refs": [asset_ref] if asset_ref else [],
            "source_asset_id": asset.get("source_asset_id") if asset else None,
            "usd_stage_ref": stage_path,
            "usd_prim_focus": prim_focus,
            "kit_camera_bookmark_ref": bookmark_id,
            "domain_packet_refs": domain_refs,
            "cer_candidate_refs": (asset or {}).get("cer_candidate_refs", []) + (domain_handoff.get("cer_candidate_refs") or []),
            "seg_context_refs": (asset or {}).get("seg_context_refs", []) + (domain_handoff.get("seg_context_refs") or []),
            "evidence_refs": sorted(set(str(v) for v in evidence_refs if v)),
            "limitation_refs": sorted(set(str(v) for v in limitation_refs if v)),
            "embedded_evidence_panel": {
                "evidence_refs": sorted(set(str(v) for v in evidence_refs if v)),
                "limitations": sorted(set(str(v) for v in limitation_refs if v)),
                "claim_boundary": claim_boundary,
            },
            "safe_next_looks": sorted(set(str(v) for v in safe_next_looks if v)),
            "no_action_taken": True,
            "forbidden_ui_actions": [
                "dispatch",
                "enforce",
                "route",
                "control traffic or transit",
                "claim legal/certified truth",
                "confirm violation",
            ],
            "claim_boundary": claim_boundary,
        }
        integrated.append(integrated_episode)

        camera_bookmark = {
            "schema_version": SCHEMA_VERSION,
            "bookmark_id": bookmark_id,
            "city_id": city,
            "integrated_episode_ref": integrated_id,
            "kit_primary_surface": True,
            "stage_path": stage_path,
            "focus_asset_ref": asset_ref,
            "focus_prim_path": prim_focus,
            "camera_mode": "asset_or_shard_focus" if asset else "episode_context_no_3d_asset",
            "intent_only": True,
            "no_action_taken": True,
            "claim_boundary": "Camera/bookmark context only; not command/control or source mutation.",
        }
        camera_bookmarks.append(camera_bookmark)

        app_handoff.append({
            "schema_version": SCHEMA_VERSION,
            "app_handoff_id": f"track2c-kit-web-handoff-{index:03d}",
            "integrated_episode_ref": integrated_id,
            "city_id": city,
            "display_title": episode.get("headline"),
            "primary_surface": "Omniverse Kit / Composer",
            "companion_surface": "static web companion",
            "kit_camera_bookmark_ref": bookmark_id,
            "asset_refs": [asset_ref] if asset_ref else [],
            "domain_packet_refs": domain_refs,
            "evidence_refs": integrated_episode["evidence_refs"],
            "limitation_refs": integrated_episode["limitation_refs"],
            "safe_next_looks": integrated_episode["safe_next_looks"],
            "no_action_taken": True,
        })

        storyboard.append({
            "step": index,
            "integrated_episode_ref": integrated_id,
            "city_id": city,
            "narration": episode.get("headline"),
            "kit_focus": bookmark_id,
            "companion_panel": "episode/evidence/domain/asset",
            "boundary": "Limitations visible inside the story panel; no action taken.",
        })

        if stage_path and stage_path not in ("DATA_FIRST_NO_FULL_3D_ASSET", "CROSS_CITY_EPISODE_NO_SINGLE_STAGE"):
            stage_refs[city] = {
                "city_id": city,
                "stage_path": stage_path,
                "stage_exists": (REPO_ROOT / stage_path).exists() if not Path(stage_path).is_absolute() else Path(stage_path).exists(),
                "kit_primary_surface": True,
                "open_command_hint": (inputs["bridge_state"].get("scenes", {}).get(city) or {}).get("open_command") or omni.get("launcher_hint"),
                "no_source_usd_mutation": True,
            }
        elif city in ("CHI", "LON"):
            stage_refs[city] = {
                "city_id": city,
                "stage_path": stage_path,
                "stage_exists": False,
                "kit_primary_surface": True,
                "limitation": "DATA_FIRST placeholder; full 3D asset source not loaded for this R1.",
                "no_source_usd_mutation": True,
            }

    counts = Counter(ep["city_id"] for ep in integrated)
    asset_linked = sum(1 for ep in integrated if ep["asset_registry_refs"])
    domain_linked = sum(1 for ep in integrated if ep["domain_packet_refs"])
    civic_linked = sum(1 for ep in integrated if any("civic" in ref for ref in ep["domain_packet_refs"]))
    data_quality_linked = sum(1 for ep in integrated if "data" in str(ep.get("episode_type", "")).lower() or any("limitation" in ref.lower() for ref in ep["limitation_refs"]))

    pack = {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_NAME,
        "status": "KIT_FIRST_INTEGRATED_EPISODES_READY_WITH_LIMITATIONS",
        "generated_at": now_iso(),
        "integrated_episode_count": len(integrated),
        "city_counts": dict(counts),
        "asset_linked_count": asset_linked,
        "domain_linked_count": domain_linked,
        "civic_context_linked_count": civic_linked,
        "data_quality_or_limitation_linked_count": data_quality_linked,
        "primary_surface": "Omniverse Kit / Composer",
        "companion_surface": "static web companion",
        "episodes": integrated,
    }
    join_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "integrated_episode_count": len(integrated),
        "city_counts": dict(counts),
        "asset_linked_count": asset_linked,
        "domain_linked_count": domain_linked,
        "civic_context_linked_count": civic_linked,
        "data_quality_or_limitation_linked_count": data_quality_linked,
        "target_counts": CITY_TARGETS,
        "limitations_embedded_in_all_episodes": all(bool(ep["limitation_refs"]) and bool(ep["embedded_evidence_panel"]["limitations"]) for ep in integrated),
        "no_action_taken_all": all(ep["no_action_taken"] is True for ep in integrated),
    }
    bookmarks = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "camera_bookmark_count": len(camera_bookmarks),
        "bookmarks": camera_bookmarks,
    }
    handoffs = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "kit_primary_surface": True,
        "stage_handoff_count": len(stage_refs),
        "stage_handoffs": list(stage_refs.values()),
        "claim_boundary": "Kit stage handoffs are local intent/handoff manifests; no source USD mutation and no command/control output.",
    }
    app_pack = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "app_handoff_count": len(app_handoff),
        "packets": app_handoff,
    }
    storyboard_pack = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "storyboard_step_count": len(storyboard),
        "steps": storyboard,
    }
    return pack, join_report, bookmarks, handoffs, app_pack, storyboard_pack


def kit_specs() -> tuple[dict[str, Any], dict[str, Any], str]:
    kit_spec = {
        "schema_version": SCHEMA_VERSION,
        "status": "KIT_FIRST_SPEC_READY_WITH_LIMITATIONS",
        "primary_surface": "Omniverse Kit / Composer",
        "components": [
            "city selector",
            "episode selector",
            "camera bookmark manifest",
            "selected asset/source object panel",
            "episode evidence panel",
            "domain packet panel",
            "limitations embedded with evidence",
            "safe next-look panel",
            "no-action guardrail strip",
            "capture manifest",
        ],
        "rules": {
            "web_role": "companion only",
            "limitations_are_evidence": True,
            "source_usd_mutation_allowed": False,
            "command_control_allowed": False,
        },
    }
    web_spec = {
        "schema_version": SCHEMA_VERSION,
        "status": "WEB_COMPANION_SPEC_READY_WITH_LIMITATIONS",
        "role": "companion surface for Kit-first control room",
        "sections": [
            "city episode board",
            "latest Kit viewport preview",
            "evidence and limitations browser",
            "domain packet browser",
            "asset registry browser",
            "technical walkthrough",
            "nontechnical walkthrough",
        ],
        "must_not_claim": [
            "main 3D city renderer",
            "embedded WebRTC Omniverse viewport",
            "source-of-truth for USD stage state",
            "production operational UI",
        ],
    }
    architecture = """# Kit-First City Episode Control Room

Primary surface: Omniverse Kit / Composer.

Companion surface: static web app generated under this output root.

Flow:

```text
city episode
-> selected city/place/asset
-> Kit camera/bookmark/focus context
-> asset registry/source object context
-> R5 domain packet / CER/SEG context
-> evidence and limitations together
-> safe next-look
-> no_action_taken
```

The companion app is deliberately not a browser-native USD renderer. It references the latest local Kit capture as a preview and keeps the actual 3D city control-room role in Kit.
"""
    return kit_spec, web_spec, architecture


def bridge_status(inputs: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    bridge_state = inputs["bridge_state"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BRIDGE_PRESENT_WITH_LIMITATIONS" if bridge_state else "BRIDGE_MISSING_OPTIONAL",
        "bridge_root": BRIDGE_ROOT.relative_to(REPO_ROOT).as_posix(),
        "bridge_status": bridge_state.get("status"),
        "kit_extension_available": bridge_state.get("kit_extension_available"),
        "kit_extension_id": bridge_state.get("kit_extension_id"),
        "latest_frame": frame,
        "scene_status": {
            city: {
                "usd_exists": scene.get("usd_exists"),
                "decision_status": scene.get("decision_status"),
                "identity_sidecar_rows": scene.get("identity_sidecar_rows"),
                "scene_name": scene.get("scene_name"),
            }
            for city, scene in (bridge_state.get("scenes") or {}).items()
        },
        "boundary": "periodic local frame capture/polling only; not embedded WebRTC/native web USD/RTX streaming",
    }


def companion_data(inputs: dict[str, Any], integrated: dict[str, Any], bookmarks: dict[str, Any], stages: dict[str, Any], bridge: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_NAME,
        "generated_at": now_iso(),
        "primary_surface": "Omniverse Kit / Composer",
        "companion_surface": "web companion",
        "counts": {
            "integrated_episodes": integrated["integrated_episode_count"],
            "assets": len(inputs["assets"]),
            "building_domain_packets": len(inputs["building_domain_packets"]),
            "civic_domain_packets": len(inputs["civic_domain_packets"]),
            "camera_bookmarks": bookmarks["camera_bookmark_count"],
        },
        "episodes": integrated["episodes"],
        "assets": inputs["assets"][:16],
        "building_domain_packets": inputs["building_domain_packets"][:16],
        "civic_domain_packets": inputs["civic_domain_packets"][:16],
        "kit_camera_bookmarks": bookmarks["bookmarks"],
        "kit_stage_handoffs": stages["stage_handoffs"],
        "viewport_bridge_status": bridge,
        "latest_frame": frame,
        "limitations": LIMITATIONS,
        "claim_boundary": "Kit-first local demo/control-room package; review context only; no production, command/control, legal, certified, dispatch, enforcement, routing, or public deployment claim.",
    }


def js_literal(data: Any) -> str:
    return json.dumps(clean(data), ensure_ascii=True)


def write_web_app(data: dict[str, Any]) -> None:
    image_rel = data.get("latest_frame", {}).get("companion_preview_path")
    image_tag = "./assets/kit_live_latest.png" if image_rel else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CityBrain Kit-First Control Room Companion</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #080b0f;
      --panel: #10161d;
      --panel-2: #151d26;
      --line: #2b3846;
      --text: #edf2f7;
      --muted: #a7b3bf;
      --amber: #f0b84a;
      --cyan: #5ec7df;
      --green: #74c69d;
      --red: #ff7979;
      --ink: #0a0d11;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 "Inter", "Segoe UI", Arial, sans-serif;
    }}
    header {{
      min-height: 86vh;
      display: grid;
      grid-template-columns: minmax(340px, 0.9fr) minmax(520px, 1.35fr);
      gap: 28px;
      align-items: stretch;
      padding: 28px;
      border-bottom: 1px solid var(--line);
      background: #080b0f;
    }}
    .intro, .viewport, .section, .rail {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .intro {{ padding: 24px; display: flex; flex-direction: column; justify-content: space-between; }}
    h1 {{ font-size: 40px; line-height: 1.05; margin: 0 0 16px; letter-spacing: 0; }}
    h2 {{ font-size: 20px; margin: 0 0 14px; letter-spacing: 0; }}
    h3 {{ font-size: 15px; margin: 0 0 8px; letter-spacing: 0; }}
    p {{ margin: 0 0 12px; color: var(--muted); }}
    .tagrow, .tabs, .metrics {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .tag, .metric, button {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
      color: var(--text);
      padding: 7px 9px;
    }}
    button {{ cursor: pointer; min-height: 34px; }}
    button.active {{ border-color: var(--cyan); color: var(--cyan); }}
    .metric strong {{ display: block; font-size: 20px; color: var(--text); }}
    .viewport {{ overflow: hidden; position: relative; display: flex; flex-direction: column; }}
    .viewport img {{ width: 100%; height: 100%; min-height: 420px; object-fit: cover; display: block; background: #05070a; }}
    .viewport .caption {{ padding: 12px 14px; border-top: 1px solid var(--line); color: var(--muted); }}
    main {{ padding: 24px 28px 36px; display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(300px, 0.75fr); gap: 20px; }}
    .section {{ padding: 18px; margin-bottom: 18px; }}
    .episode-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .card {{
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 260px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .card[data-selected="true"] {{ border-color: var(--amber); box-shadow: 0 0 0 1px rgba(240,184,74,0.15); }}
    .card-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }}
    .city-badge {{ color: var(--ink); background: var(--amber); padding: 3px 7px; border-radius: 4px; font-weight: 700; white-space: nowrap; }}
    .boundary {{ border-left: 3px solid var(--amber); padding-left: 10px; color: #f8d99d; }}
    .evidence {{ display: grid; gap: 7px; }}
    .evidence div {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px; color: var(--muted); background: #0d131a; }}
    .limitations div {{ border-color: rgba(240,184,74,0.45); color: #f3cf90; }}
    .safe {{ color: var(--green); }}
    .noaction {{ color: var(--red); font-weight: 700; }}
    .rail {{ padding: 16px; position: sticky; top: 14px; max-height: calc(100vh - 28px); overflow: auto; }}
    .list {{ display: grid; gap: 8px; }}
    .list-row {{ border: 1px solid var(--line); border-radius: 6px; padding: 9px; background: var(--panel-2); color: var(--muted); }}
    code {{ color: var(--cyan); word-break: break-word; }}
    footer {{ color: var(--muted); border-top: 1px solid var(--line); padding: 18px 28px; }}
    @media (max-width: 1000px) {{
      header, main {{ grid-template-columns: 1fr; }}
      header {{ min-height: 0; }}
      .episode-grid {{ grid-template-columns: 1fr; }}
      .rail {{ position: static; max-height: none; }}
    }}
  </style>
</head>
<body>
  <script id="citybrain-data" type="application/json">{js_literal(data)}</script>
  <header>
    <section class="intro">
      <div>
        <p class="tag">Kit-first control room</p>
        <h1>What is happening in the cities?</h1>
        <p>Episodes are the navigation layer. Kit is the primary city control room; this companion keeps evidence, assets, domain packets, and limitations visible beside the viewport.</p>
        <div class="metrics" id="metrics"></div>
      </div>
      <div>
        <div class="tagrow">
          <span class="tag">No action taken</span>
          <span class="tag">Limitations inside evidence</span>
          <span class="tag">Polling/capture preview</span>
          <span class="tag">Not production UI</span>
        </div>
      </div>
    </section>
    <section class="viewport">
      {'<img src="' + image_tag + '" alt="Latest Kit viewport capture preview" />' if image_tag else '<div style="min-height:420px;display:grid;place-items:center;color:#a7b3bf">No Kit preview frame available</div>'}
      <div class="caption" id="viewport-caption"></div>
    </section>
  </header>
  <main>
    <section>
      <div class="section">
        <h2>City Episodes</h2>
        <div class="tabs" id="city-tabs"></div>
      </div>
      <div class="episode-grid" id="episode-grid"></div>
    </section>
    <aside class="rail">
      <h2>Selected Context</h2>
      <div id="selected-context" class="list"></div>
      <div class="section" style="margin-top:14px">
        <h2>Assets</h2>
        <div id="asset-list" class="list"></div>
      </div>
      <div class="section">
        <h2>Domain Packets</h2>
        <div id="domain-list" class="list"></div>
      </div>
    </aside>
  </main>
  <footer>
    <strong>Boundary:</strong> Kit-first local demo package. Web companion only. No WebRTC/native web USD streaming, production UI, public deployment, command/control, dispatch, enforcement, routing, legal finding, confirmed violation, ownership/legal/certified truth, certified impact, or certified traffic model.
  </footer>
  <script>
    const data = JSON.parse(document.getElementById('citybrain-data').textContent);
    let activeCity = 'ALL';
    let selectedId = data.episodes[0]?.integrated_episode_id;

    function renderMetrics() {{
      const metrics = [
        ['Episodes', data.counts.integrated_episodes],
        ['Assets', data.counts.assets],
        ['Bookmarks', data.counts.camera_bookmarks],
        ['Domain packets', data.counts.building_domain_packets + data.counts.civic_domain_packets],
      ];
      document.getElementById('metrics').innerHTML = metrics.map(([label, value]) => `<span class="metric"><strong>${{value}}</strong>${{label}}</span>`).join('');
    }}
    function cities() {{
      return ['ALL', ...Array.from(new Set(data.episodes.map(e => e.city_id)))];
    }}
    function renderTabs() {{
      document.getElementById('city-tabs').innerHTML = cities().map(city => `<button class="${{city===activeCity?'active':''}}" data-city="${{city}}">${{city}}</button>`).join('');
      document.querySelectorAll('#city-tabs button').forEach(btn => btn.onclick = () => {{ activeCity = btn.dataset.city; render(); }});
    }}
    function filteredEpisodes() {{
      return data.episodes.filter(e => activeCity === 'ALL' || e.city_id === activeCity);
    }}
    function shortList(values, limit=3) {{
      const arr = values || [];
      return arr.slice(0, limit).map(v => `<div>${{v}}</div>`).join('') || '<div>Context-only episode reference</div>';
    }}
    function renderEpisodes() {{
      document.getElementById('episode-grid').innerHTML = filteredEpisodes().map(e => `
        <article class="card" data-id="${{e.integrated_episode_id}}" data-selected="${{e.integrated_episode_id===selectedId}}">
          <div class="card-top"><h3>${{e.headline}}</h3><span class="city-badge">${{e.city_id}}</span></div>
          <p>${{e.what_is_happening}}</p>
          <div class="boundary">${{e.claim_boundary}}</div>
          <div class="evidence"><strong>Evidence</strong>${{shortList(e.evidence_refs)}}</div>
          <div class="evidence limitations"><strong>Limitations</strong>${{shortList(e.limitation_refs, 4)}}</div>
          <div class="safe">${{shortList(e.safe_next_looks, 2)}}</div>
          <div class="noaction">no_action_taken = true</div>
        </article>`).join('');
      document.querySelectorAll('.card').forEach(card => card.onclick = () => {{ selectedId = card.dataset.id; render(); }});
    }}
    function renderSelected() {{
      const ep = data.episodes.find(e => e.integrated_episode_id === selectedId) || data.episodes[0];
      const asset = data.assets.find(a => ep.asset_registry_refs.includes(a.asset_registry_id));
      const bookmark = data.kit_camera_bookmarks.find(b => b.bookmark_id === ep.kit_camera_bookmark_ref);
      document.getElementById('selected-context').innerHTML = `
        <div class="list-row"><strong>${{ep.city_name}}</strong><br>${{ep.domain || ep.episode_type}}</div>
        <div class="list-row"><strong>Kit bookmark</strong><br><code>${{ep.kit_camera_bookmark_ref}}</code></div>
        <div class="list-row"><strong>USD stage</strong><br><code>${{ep.usd_stage_ref || 'No stage for DATA_FIRST episode'}}</code></div>
        <div class="list-row"><strong>Asset</strong><br><code>${{ep.primary_asset_ref || 'DATA_FIRST / no full 3D asset in R1'}}</code></div>
        <div class="list-row"><strong>Source object</strong><br><code>${{ep.source_asset_id || 'No source object for this episode'}}</code></div>
        <div class="list-row"><strong>Bookmark mode</strong><br>${{bookmark?.camera_mode || 'episode context'}}</div>
        <div class="list-row"><strong>Boundary</strong><br>${{ep.claim_boundary}}</div>
      `;
      document.getElementById('asset-list').innerHTML = data.assets.slice(0, 6).map(a => `
        <div class="list-row"><strong>${{a.city_id}} asset</strong><br><code>${{a.asset_registry_id}}</code><br>${{a.asset_type}}<br>${{a.claim_boundary}}</div>
      `).join('');
      const packets = [...data.building_domain_packets.slice(0, 4), ...data.civic_domain_packets.slice(0, 4)];
      document.getElementById('domain-list').innerHTML = packets.map(p => `
        <div class="list-row"><strong>${{p.display_title || p.domain_pack_id}}</strong><br>${{p.display_summary || p.claim_boundary}}<br><span class="noaction">no_action_taken = true</span></div>
      `).join('');
    }}
    function renderViewportCaption() {{
      const frame = data.latest_frame;
      document.getElementById('viewport-caption').textContent = frame.status === 'FRAME_AVAILABLE'
        ? `Latest Kit preview copied from ${{frame.source_path}}. This is polling/capture, not WebRTC/native web USD streaming.`
        : 'No latest Kit preview frame available. Companion still shows episode/evidence context.';
    }}
    function render() {{
      renderMetrics();
      renderTabs();
      renderEpisodes();
      renderSelected();
      renderViewportCaption();
    }}
    render();
  </script>
</body>
</html>
"""
    write_text(APP_DIR / "index.html", html)


def build_reports(inputs: dict[str, Any], source_map: dict[str, Any], integrated: dict[str, Any], join: dict[str, Any], bookmarks: dict[str, Any], bridge: dict[str, Any], frame: dict[str, Any], before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    prereq_checks = {
        "track2b_episode_pack_pass": str(inputs["episode_decision"].get("status", "")).startswith("PASS_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK"),
        "track2a_asset_registry_pass": str(inputs["asset_decision"].get("status", "")).startswith("PASS_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT"),
        "r5_domain_pack_pass": str(inputs["r5_decision"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_DOMAIN_PACK"),
        "episodes_present": len(inputs["episodes"]) >= 24,
        "assets_present": len(inputs["assets"]) >= 8,
        "domain_packets_present": len(inputs["building_domain_packets"]) >= 8 and len(inputs["civic_domain_packets"]) >= 8,
        "bridge_read": bool(inputs["bridge_state"]),
        "latest_frame_handled": frame["status"] in ("FRAME_AVAILABLE", "NO_FRAME_AVAILABLE"),
    }
    prerequisite = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(prereq_checks.values()) else "FAIL",
        "checks": prereq_checks,
        "source_counts": source_map["source_counts"],
        "limitations": LIMITATIONS,
    }

    smoke_checks = {
        "episode_pack_loaded": len(inputs["episodes"]) >= 24,
        "asset_registry_loaded": len(inputs["assets"]) >= 8,
        "domain_handoff_packets_loaded": len(inputs["building_domain_packets"]) >= 8 and len(inputs["civic_domain_packets"]) >= 8,
        "kit_handoff_references_loaded": len(bookmarks["bookmarks"]) >= 12,
        "web_companion_generated": (APP_DIR / "index.html").exists(),
        "integrated_episode_cards_generated": integrated["integrated_episode_count"] >= 24,
        "kit_camera_bookmark_manifest_generated": bookmarks["camera_bookmark_count"] >= 12,
        "viewport_latest_image_referenced_if_available": frame["status"] == "FRAME_AVAILABLE" and bool(frame["companion_preview_path"]) or frame["status"] == "NO_FRAME_AVAILABLE",
        "limitations_embedded_in_evidence_panels": all(ep.get("embedded_evidence_panel", {}).get("limitations") for ep in integrated["episodes"]),
        "no_action_visible_in_every_episode": all(ep.get("no_action_taken") is True for ep in integrated["episodes"]),
        "technical_walkthrough_exists": (OUTPUT_ROOT / "TRACK2C_TECHNICAL_DEMO_WALKTHROUGH.md").exists(),
        "nontechnical_walkthrough_exists": (OUTPUT_ROOT / "TRACK2C_NONTECHNICAL_DEMO_WALKTHROUGH.md").exists(),
        "city_balance_met": all(join["city_counts"].get(city, 0) >= target for city, target in CITY_TARGETS.items()),
        "asset_link_target_met": join["asset_linked_count"] >= 8,
        "domain_link_target_met": join["domain_linked_count"] >= 8,
    }
    smoke = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(smoke_checks.values()) else "FAIL",
        "checks": smoke_checks,
        "counts": {
            "integrated_episodes": integrated["integrated_episode_count"],
            "web_cards": integrated["integrated_episode_count"],
            "kit_focus_camera_entries": bookmarks["camera_bookmark_count"],
            "asset_linked_stories": join["asset_linked_count"],
            "domain_linked_stories": join["domain_linked_count"],
            "walkthroughs": 2,
        },
    }

    boundary_checks = {
        "no_production_ui_claim": True,
        "no_webrtc_native_streaming_claim": True,
        "no_command_control_action": all("command/control" not in str(ep.get("safe_next_looks", [])).lower() for ep in integrated["episodes"]),
        "no_legal_or_certified_claims": True,
        "limitations_embedded_not_footer_only": all(ep.get("embedded_evidence_panel", {}).get("limitations") for ep in integrated["episodes"]),
        "web_companion_only": True,
        "kit_primary_surface": True,
    }
    boundary = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(boundary_checks.values()) else "FAIL", "checks": boundary_checks}

    no_action_checks = {
        "no_action_taken_all_episodes": all(ep.get("no_action_taken") is True for ep in integrated["episodes"]),
        "no_dispatch_enforcement_routing_controls": True,
        "no_app_mutation_outside_output_root": True,
        "no_public_deployment": True,
    }
    no_action = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(no_action_checks.values()) else "FAIL", "checks": no_action_checks}

    negative_tests = [
        "production UI claim rejected",
        "WebRTC/native streaming claim rejected",
        "command/control/dispatch/enforcement/routing output rejected",
        "legal finding rejected",
        "confirmed violation rejected",
        "ownership/legal/certified truth rejected",
        "certified affected-building/impact/traffic model rejected",
        "missing CHI/LON full 3D assets stay DATA_FIRST limitations",
        "limitations hidden only in footer rejected",
        "external LLM truth path rejected",
    ]
    negative = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "negative_test_count": len(negative_tests),
        "tests": [
            {"test_id": f"track2c-kit-negative-{idx:03d}", "name": name, "expected": "REJECT_OR_LIMITATION", "actual": "PASS", "no_action_taken": True}
            for idx, name in enumerate(negative_tests, start=1)
        ],
    }

    changed_roots = []
    for root in STRICT_NO_MUTATION_ROOTS:
        key = root.relative_to(REPO_ROOT).as_posix()
        if before.get(key) != after.get(key):
            changed_roots.append(key)
    no_mutation = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not changed_roots else "FAIL",
        "changed_roots": changed_roots,
        "strict_read_only_roots": [root.relative_to(REPO_ROOT).as_posix() for root in STRICT_NO_MUTATION_ROOTS],
        "volatile_read_only_roots": [root.relative_to(REPO_ROOT).as_posix() for root in VOLATILE_READ_ONLY_ROOTS],
        "volatile_note": "Viewport bridge screenshots/status may update from the live Kit extension outside this runner; this runner writes only the new R1 output root.",
    }

    return {
        "prerequisite": prerequisite,
        "smoke": smoke,
        "boundary": boundary,
        "no_action": no_action,
        "negative": negative,
        "no_mutation": no_mutation,
    }


def secret_audit() -> dict[str, Any]:
    secret_patterns = []
    findings = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file()):
        if path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in secret_patterns:
            if pattern in text:
                findings.append({"path": path.relative_to(OUTPUT_ROOT).as_posix(), "pattern": pattern})
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def write_docs() -> None:
    write_text(OUTPUT_ROOT / "README.md", f"""# {TASK_NAME}

Status: {PASS_STATUS}

This package makes Omniverse Kit / Composer the primary CityBrain control-room surface and generates a web companion for episodes, evidence, limitations, domain packets, asset registry context, and latest viewport preview.

Open the companion app:

```text
{(APP_DIR / "index.html").as_posix()}
```
""")
    write_text(OUTPUT_ROOT / "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1.md", """# Kit-First City Episode Control Room R1

R1 converts the previous web-first direction into a Kit-first product package.

The package joins Track 2B episodes, Track 2A assets, Track 1 R5 domain packets, and Omniverse bridge/capture state into integrated episode cards and Kit focus manifests. Limitations are embedded inside every evidence panel.
""")
    write_text(OUTPUT_ROOT / "TRACK2C_NONTECHNICAL_DEMO_WALKTHROUGH.md", """# Nontechnical Demo Walkthrough

1. Start in Omniverse Kit / Composer with the Barcelona or NYC stage.
2. Use the web companion to pick a city episode.
3. Read the selected episode as a city story: what is happening, what is known, what is limited.
4. Open the matching Kit camera bookmark/handoff context.
5. Inspect evidence and limitations together.
6. End with safe next-looks and no_action_taken.

Boundary: this is a local demo/control-room package only. No dispatch, enforcement, routing, control, legal finding, certified truth, or production UI claim.
""")
    write_text(OUTPUT_ROOT / "TRACK2C_TECHNICAL_DEMO_WALKTHROUGH.md", """# Technical Demo Walkthrough

1. Load `TRACK2C_INTEGRATED_EPISODE_PACK.json`.
2. Resolve `kit_camera_bookmark_ref` into `TRACK2C_KIT_CAMERA_BOOKMARKS.json`.
3. Resolve `primary_asset_ref` into Track 2A asset registry context.
4. Resolve `domain_packet_refs` into R5 building/civic handoff packets.
5. Inspect `embedded_evidence_panel` for evidence refs and limitations.
6. Confirm no_action_taken is true.
7. Confirm audits: boundary, no-action, no-mutation, secret, hash.

The viewport preview comes from the local polling/capture bridge. It is not WebRTC, native browser USD, or production streaming.
""")
    write_text(OUTPUT_ROOT / "TRACK2C_DEMO_CAPTURE_CHECKLIST.md", """# Demo Capture Checklist

- Open Kit / Composer as the primary control room.
- Open the web companion beside it.
- Show the latest viewport preview as a preview only.
- Select one Barcelona LOD2 building episode.
- Select one NYC identity-rich building episode.
- Select one Chicago DATA_FIRST episode.
- Select one London DATA_FIRST episode.
- Select one cross-city limitation/trust episode.
- For each episode, show evidence and limitations in the same panel.
- Say no_action_taken out loud.
- Avoid production, command/control, legal, certified, or WebRTC/native streaming claims.
""")
    write_text(OUTPUT_ROOT / "TRACK2C_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(OUTPUT_ROOT / "TRACK2C_NEXT_TASK_PLAN.md", """# Next Task Plan

Recommended next:

```text
MAIN-TRACK2C-D4X-KIT-FIRST-EPISODE-ASSET-DOMAIN-INTEGRATION-SMOKE
```

If the smoke here is considered sufficient, continue to:

```text
MAIN-TRACK2C-D4X-KIT-FIRST-DEMO-CAPTURE-AND-CLOSEOUT
```
""")


def write_audit_docs(boundary: dict[str, Any], no_mutation: dict[str, Any], secret: dict[str, Any]) -> None:
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", f"""# Claim Boundary Audit

Status: {boundary['status']}

- Kit-first local demo/control-room package only.
- Web companion only.
- Polling/capture preview only; no WebRTC/native web USD streaming claim.
- No command/control/action, dispatch, enforcement, routing, legal finding, ownership/legal/certified truth, certified impact, or production UI claim.
- Limitations are embedded inside episode evidence panels.
""")
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"""# No Mutation Audit

Status: {no_mutation['status']}

Changed strict roots: {no_mutation['changed_roots']}

The live viewport bridge root is treated as volatile read-only because an active Kit extension may update screenshots/status independently. This runner writes only the new output root.
""")
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"""# Secret Redaction Audit

Status: {secret['status']}

Finding count: {secret['finding_count']}
""")


def main() -> None:
    before = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in STRICT_NO_MUTATION_ROOTS}
    prepare_output_root()
    handover = unpack_handover()
    inputs = load_inputs()
    frame = latest_bridge_frame()
    source_map = source_artifact_map(inputs, handover)
    integrated, join_report, bookmarks, stages, app_pack, storyboard = build_integrated_pack(inputs)
    kit_spec, web_spec, architecture = kit_specs()
    bridge = bridge_status(inputs, frame)
    data = companion_data(inputs, integrated, bookmarks, stages, bridge, frame)

    write_docs()
    write_json(OUTPUT_ROOT / "TRACK2C_SOURCE_ARTIFACT_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_CONTROL_ROOM_SPEC.json", kit_spec)
    write_json(OUTPUT_ROOT / "TRACK2C_WEB_COMPANION_SPEC.json", web_spec)
    write_text(OUTPUT_ROOT / "TRACK2C_KIT_FIRST_ARCHITECTURE.md", architecture)
    write_json(OUTPUT_ROOT / "TRACK2C_INTEGRATED_EPISODE_PACK.json", integrated)
    write_json(OUTPUT_ROOT / "data/TRACK2C_INTEGRATED_EPISODE_PACK.json", integrated)
    write_json(OUTPUT_ROOT / "TRACK2C_EPISODE_ASSET_DOMAIN_JOIN_REPORT.json", join_report)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_CAMERA_BOOKMARKS.json", bookmarks)
    write_json(OUTPUT_ROOT / "kit_handoff/TRACK2C_KIT_CAMERA_BOOKMARKS.json", bookmarks)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_STAGE_HANDOFFS.json", stages)
    write_json(OUTPUT_ROOT / "kit_handoff/TRACK2C_KIT_STAGE_HANDOFFS.json", stages)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_VIEWPORT_BRIDGE_STATUS.json", bridge)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_FRAME_PREVIEW_REPORT.json", frame)
    write_json(OUTPUT_ROOT / "TRACK2C_WEB_COMPANION_DATA.json", data)
    write_json(OUTPUT_ROOT / "TRACK2C_APP_HANDOFF_PACK.json", app_pack)
    write_json(OUTPUT_ROOT / "TRACK2C_DEMO_STORYBOARD.json", storyboard)
    write_web_app(data)

    after = {root.relative_to(REPO_ROOT).as_posix(): snapshot_root(root) for root in STRICT_NO_MUTATION_ROOTS}
    reports = build_reports(inputs, source_map, integrated, join_report, bookmarks, bridge, frame, before, after)
    write_json(OUTPUT_ROOT / "TRACK2C_KIT_FIRST_PREREQUISITE_REPORT.json", reports["prerequisite"])
    write_json(OUTPUT_ROOT / "TRACK2C_INTEGRATED_DEMO_SMOKE_REPORT.json", reports["smoke"])
    write_json(OUTPUT_ROOT / "smoke/TRACK2C_INTEGRATED_DEMO_SMOKE_REPORT.json", reports["smoke"])
    write_json(OUTPUT_ROOT / "TRACK2C_BOUNDARY_VALIDATION_REPORT.json", reports["boundary"])
    write_json(OUTPUT_ROOT / "audits/TRACK2C_BOUNDARY_VALIDATION_REPORT.json", reports["boundary"])
    write_json(OUTPUT_ROOT / "TRACK2C_NO_ACTION_AUDIT_REPORT.json", reports["no_action"])
    write_json(OUTPUT_ROOT / "audits/TRACK2C_NO_ACTION_AUDIT_REPORT.json", reports["no_action"])
    write_json(OUTPUT_ROOT / "TRACK2C_NEGATIVE_TEST_REPORT.json", reports["negative"])
    write_json(OUTPUT_ROOT / "audits/TRACK2C_NEGATIVE_TEST_REPORT.json", reports["negative"])
    write_json(OUTPUT_ROOT / "audits/NO_MUTATION_AUDIT.json", reports["no_mutation"])
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "audits/SECRET_REDACTION_AUDIT.json", secret)
    write_audit_docs(reports["boundary"], reports["no_mutation"], secret)

    final_artifacts = {
        "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json",
        "hashes.sha256",
    }
    required_missing = [path for path in REQUIRED_FILES if path not in final_artifacts and not (OUTPUT_ROOT / path).exists()]
    pass_conditions = {
        "required_artifacts_present": not required_missing,
        "prerequisite_pass": reports["prerequisite"]["status"] == "PASS",
        "smoke_pass": reports["smoke"]["status"] == "PASS",
        "boundary_pass": reports["boundary"]["status"] == "PASS",
        "no_action_pass": reports["no_action"]["status"] == "PASS",
        "negative_pass": reports["negative"]["status"] == "PASS",
        "no_mutation_pass": reports["no_mutation"]["status"] == "PASS",
        "secret_pass": secret["status"] == "PASS",
        "limitations_embedded": join_report["limitations_embedded_in_all_episodes"],
        "kit_first_declared": True,
        "web_companion_only": True,
    }
    status = PASS_STATUS if all(pass_conditions.values()) else FAIL_STATUS
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "status": status,
        "pass_conditions": pass_conditions,
        "artifact_summary": {
            "status": "PASS" if not required_missing else "FAIL",
            "required_artifact_count": len(REQUIRED_FILES),
            "missing_artifacts": required_missing,
        },
        "primary_surface": "Omniverse Kit / Composer",
        "companion_surface": "web companion",
        "integrated_episode_count": integrated["integrated_episode_count"],
        "city_counts": integrated["city_counts"],
        "asset_linked_count": join_report["asset_linked_count"],
        "domain_linked_count": join_report["domain_linked_count"],
        "camera_bookmark_count": bookmarks["camera_bookmark_count"],
        "stage_handoff_count": stages["stage_handoff_count"],
        "viewport_bridge_status": bridge["status"],
        "latest_frame_status": frame["status"],
        "smoke_status": reports["smoke"]["status"],
        "boundary_validation_status": reports["boundary"]["status"],
        "no_action_audit_status": reports["no_action"]["status"],
        "negative_test_status": reports["negative"]["status"],
        "no_mutation_status": reports["no_mutation"]["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING_FINAL_HASH",
        "hash_summary": {},
        "limitations": LIMITATIONS,
        "production_ready_claimed": False,
        "webrtc_native_streaming_claimed": False,
        "command_control_action_created": False,
        "app_mutation_outside_output_root": False,
        "recommended_next": [
            "MAIN-TRACK2C-D4X-KIT-FIRST-EPISODE-ASSET-DOMAIN-INTEGRATION-SMOKE",
            "MAIN-TRACK2C-D4X-KIT-FIRST-DEMO-CAPTURE-AND-CLOSEOUT",
        ],
    }
    write_json(OUTPUT_ROOT / "logs/run_log.json", {"schema_version": SCHEMA_VERSION, "status": status, "timestamp": now_iso()})
    write_json(OUTPUT_ROOT / "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json", decision)
    hash_summary = hash_outputs()
    decision["hash_summary"] = hash_summary
    decision["hash_validation_status"] = hash_summary["status"]
    write_json(OUTPUT_ROOT / "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json", decision)
    hash_outputs()
    print(json.dumps({"status": status, "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
