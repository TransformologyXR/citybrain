from __future__ import annotations

import asyncio
from pathlib import Path

from .event_overlay_registry import event_fixtures
from .real_scene_review_loop_registry import EVENT_MARKER_ROOT as R5_EVENT_MARKER_ROOT
from .real_scene_review_loop_registry import real_scene_event_fixtures
from .scene_prim_selection_registry import BARCELONA_PREVIEW_USD, BARCELONA_REAL_MESH_USD


def ensure_browser_navigation_test_model() -> dict:
    """Create a review-only CityBrain corridor USD model for browser navigation smoke."""

    try:
        import omni.kit.app  # type: ignore
        import omni.usd  # type: ignore
        from pxr import Gf, Sdf, UsdGeom, UsdLux  # type: ignore
    except Exception as exc:  # pragma: no cover - Kit-only dependency
        return {
            "status": "BLOCKED_KIT_USD_API_UNAVAILABLE",
            "reason": str(exc),
        }

    context = omni.usd.get_context()
    stage = context.get_stage()
    if stage is None:
        context.new_stage()
        stage = context.get_stage()
    if stage is None:
        return {"status": "BLOCKED_NO_STAGE"}

    root_path = "/CityBrainBrowserNavTest"
    root = UsdGeom.Xform.Define(stage, root_path)
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    created_prims: list[str] = []

    def cube(name: str, translate, scale, color, opacity: float | None = None) -> None:
        prim_path = f"{root_path}/{name}"
        prim = UsdGeom.Cube.Define(stage, prim_path)
        prim.CreateSizeAttr(1.0)
        prim.CreateDisplayColorAttr([color])
        if opacity is not None:
            try:
                prim.CreateDisplayOpacityAttr([opacity])
            except Exception:
                pass
        xform = UsdGeom.XformCommonAPI(prim)
        xform.SetTranslate(translate)
        xform.SetScale(scale)
        created_prims.append(prim_path)

    def absolute_cube(prim_path: str, translate, scale, color, attrs: dict[str, str] | None = None) -> None:
        prim = UsdGeom.Cube.Define(stage, prim_path)
        prim.CreateSizeAttr(1.0)
        prim.CreateDisplayColorAttr([color])
        xform = UsdGeom.XformCommonAPI(prim)
        xform.SetTranslate(translate)
        xform.SetScale(scale)
        usd_prim = prim.GetPrim()
        for attr_name, value in (attrs or {}).items():
            try:
                attr = usd_prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String)
                attr.Set(str(value))
            except Exception:
                pass
        created_prims.append(prim_path)

    def event_marker(name: str, translate, scale, color, event_packet: dict) -> None:
        prim_path = event_packet["marker_prim_path"]
        prim = UsdGeom.Cube.Define(stage, prim_path)
        prim.CreateSizeAttr(1.0)
        prim.CreateDisplayColorAttr([color])
        xform = UsdGeom.XformCommonAPI(prim)
        xform.SetTranslate(translate)
        xform.SetScale(scale)
        usd_prim = prim.GetPrim()
        for attr_name, value in (
            ("citybrain:event_id", event_packet["event_id"]),
            ("citybrain:event_type", event_packet["event_type"]),
            ("citybrain:target_prim_path", event_packet["target_prim_path"]),
            ("citybrain:packet_hash", event_packet["packet_hash"]),
            ("citybrain:review_state", event_packet["review_state"]["review_state_ref"]),
            ("citybrain:execution_state", event_packet["no_action_state"]["execution_state"]),
        ):
            try:
                attr = usd_prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String)
                attr.Set(str(value))
            except Exception:
                pass
        created_prims.append(prim_path)

    cube("CorridorDeck", Gf.Vec3d(0.0, -0.04, 0.0), Gf.Vec3f(14.0, 0.08, 5.0), Gf.Vec3f(0.08, 0.09, 0.1))
    cube("LeftKerb", Gf.Vec3d(0.0, 0.14, -2.7), Gf.Vec3f(14.0, 0.26, 0.22), Gf.Vec3f(0.18, 0.28, 0.35))
    cube("RightKerb", Gf.Vec3d(0.0, 0.14, 2.7), Gf.Vec3f(14.0, 0.26, 0.22), Gf.Vec3f(0.18, 0.28, 0.35))
    cube("MobilityAccessFootway", Gf.Vec3d(0.0, 0.03, 3.3), Gf.Vec3f(14.0, 0.08, 0.95), Gf.Vec3f(0.2, 0.22, 0.24))

    for idx, x_pos in enumerate([-5.7, -3.3, -0.9, 1.5, 3.9, 6.3], start=1):
        cube(
            f"YellowCenterlineSegment{idx}",
            Gf.Vec3d(x_pos, 0.06, 0.0),
            Gf.Vec3f(1.2, 0.035, 0.08),
            Gf.Vec3f(1.0, 0.82, 0.06),
        )
    for idx, z_pos in enumerate([-1.35, 1.35], start=1):
        cube(
            f"WhiteLaneBoundary{idx}",
            Gf.Vec3d(0.0, 0.065, z_pos),
            Gf.Vec3f(13.2, 0.035, 0.045),
            Gf.Vec3f(0.78, 0.82, 0.82),
        )
    for idx, z_pos in enumerate([-1.9, -1.15, -0.4, 0.35, 1.1, 1.85], start=1):
        cube(
            f"CrosswalkBar{idx}",
            Gf.Vec3d(-5.95, 0.08, z_pos),
            Gf.Vec3f(0.16, 0.045, 0.44),
            Gf.Vec3f(0.86, 0.9, 0.9),
        )

    cube("BlockedLaneZone", Gf.Vec3d(2.45, 0.18, -0.85), Gf.Vec3f(2.65, 0.28, 0.96), Gf.Vec3f(1.0, 0.4, 0.05))
    cube("TestCube", Gf.Vec3d(2.45, 0.68, -0.85), Gf.Vec3f(0.68, 0.86, 0.68), Gf.Vec3f(0.1, 0.78, 0.35))
    for idx, x_pos in enumerate([1.3, 2.0, 2.9, 3.6], start=1):
        cube(
            f"SafetyCone{idx}",
            Gf.Vec3d(x_pos, 0.43, -1.55),
            Gf.Vec3f(0.22, 0.72, 0.22),
            Gf.Vec3f(1.0, 0.24, 0.02),
        )
    for idx, (x_pos, z_pos, color) in enumerate(
        [
            (-4.15, -0.85, Gf.Vec3f(0.1, 0.36, 0.95)),
            (-3.05, -0.85, Gf.Vec3f(0.1, 0.36, 0.95)),
            (-1.85, 0.85, Gf.Vec3f(0.35, 0.39, 0.42)),
            (-0.65, 0.85, Gf.Vec3f(0.35, 0.39, 0.42)),
        ],
        start=1,
    ):
        cube(f"QueuedVehicle{idx}", Gf.Vec3d(x_pos, 0.34, z_pos), Gf.Vec3f(0.78, 0.34, 0.44), color)

    cube("EvidencePinD7Observations", Gf.Vec3d(-2.7, 1.36, 3.05), Gf.Vec3f(0.28, 2.7, 0.28), Gf.Vec3f(0.0, 0.9, 0.3))
    cube("EvidencePinSimilarCases", Gf.Vec3d(-1.75, 1.12, 3.05), Gf.Vec3f(0.28, 2.2, 0.28), Gf.Vec3f(0.0, 0.55, 1.0))
    cube("EvidencePinCascadeAttachments", Gf.Vec3d(-0.8, 0.98, 3.05), Gf.Vec3f(0.28, 1.95, 0.28), Gf.Vec3f(0.65, 0.35, 1.0))
    cube("LimitationLocalReplayOnly", Gf.Vec3d(2.65, 1.18, 3.05), Gf.Vec3f(0.34, 2.35, 0.34), Gf.Vec3f(1.0, 0.75, 0.05))
    cube("ReviewOnlyNotExecuted", Gf.Vec3d(4.15, 1.18, 3.05), Gf.Vec3f(0.34, 2.35, 0.34), Gf.Vec3f(0.12, 0.65, 1.0))
    cube("NoActionStateMarker", Gf.Vec3d(5.55, 1.02, 3.05), Gf.Vec3f(0.34, 2.04, 0.34), Gf.Vec3f(0.9, 0.92, 0.9))
    cube("NavigationBackdrop", Gf.Vec3d(0.0, 2.45, -3.72), Gf.Vec3f(14.0, 4.9, 0.1), Gf.Vec3f(0.02, 0.13, 0.32))
    cube("CorridorContextWallLeft", Gf.Vec3d(-6.8, 1.15, 0.0), Gf.Vec3f(0.12, 2.3, 5.7), Gf.Vec3f(0.09, 0.16, 0.22))
    cube("CorridorContextWallRight", Gf.Vec3d(6.8, 1.15, 0.0), Gf.Vec3f(0.12, 2.3, 5.7), Gf.Vec3f(0.09, 0.16, 0.22))

    event_marker_positions = {
        "event:replay:blockage:001": (Gf.Vec3d(2.45, 1.75, -0.85), Gf.Vec3f(0.46, 0.96, 0.46), Gf.Vec3f(1.0, 0.14, 0.1)),
        "event:replay:evidence:001": (Gf.Vec3d(-2.7, 2.95, 3.05), Gf.Vec3f(0.42, 0.84, 0.42), Gf.Vec3f(0.05, 0.95, 0.38)),
        "event:replay:limitation:001": (Gf.Vec3d(4.15, 2.95, 3.05), Gf.Vec3f(0.42, 0.84, 0.42), Gf.Vec3f(1.0, 0.76, 0.12)),
    }
    for event_packet in event_fixtures():
        position, scale, color = event_marker_positions[event_packet["event_id"]]
        event_marker(event_packet["event_id"].split(":")[-1], position, scale, color, event_packet)

    absolute_cube(
        f"{R5_EVENT_MARKER_ROOT}/BarcelonaReviewBoundaryMarker001",
        Gf.Vec3d(-4.85, 2.55, 3.05),
        Gf.Vec3f(0.46, 1.02, 0.46),
        Gf.Vec3f(0.24, 0.82, 1.0),
        {
            "citybrain:review_marker": "r5_real_scene_review_loop",
            "citybrain:execution_state": "not_executed",
        },
    )
    r5_event_marker_positions = {
        "event:replay:r5:barcelona-building-proxy-01": (
            Gf.Vec3d(-3.75, 2.75, 3.05),
            Gf.Vec3f(0.42, 0.9, 0.42),
            Gf.Vec3f(0.78, 0.34, 1.0),
        ),
        "event:replay:r5:barcelona-building-proxy-02": (
            Gf.Vec3d(-3.05, 2.75, 3.05),
            Gf.Vec3f(0.42, 0.9, 0.42),
            Gf.Vec3f(0.35, 0.76, 1.0),
        ),
        "event:replay:r5:barcelona-source-pin-00": (
            Gf.Vec3d(-2.35, 2.75, 3.05),
            Gf.Vec3f(0.42, 0.9, 0.42),
            Gf.Vec3f(0.0, 0.96, 0.58),
        ),
    }
    for event_packet in real_scene_event_fixtures():
        position, scale, color = r5_event_marker_positions[event_packet["event_id"]]
        event_marker(event_packet["event_id"].split(":")[-1], position, scale, color, event_packet)

    light = UsdLux.DistantLight.Define(stage, f"{root_path}/KeyLight")
    light.CreateIntensityAttr(850.0)

    try:
        context.get_selection().set_selected_prim_paths([f"{root_path}/TestCube"], True)
    except Exception:
        pass

    frame_status = _frame_test_model_when_viewport_ready(
        [
            f"{root_path}/CorridorDeck",
            f"{root_path}/TestCube",
            f"{root_path}/EvidencePinD7Observations",
            f"{root_path}/LimitationLocalReplayOnly",
            f"{root_path}/ReviewOnlyNotExecuted",
        ]
    )

    r3_scene_targets = ensure_scene_prim_selection_targets()
    r4_event_marker_paths = [event_packet["marker_prim_path"] for event_packet in event_fixtures()]
    r5_event_marker_paths = [event_packet["marker_prim_path"] for event_packet in real_scene_event_fixtures()]

    return {
        "status": "PASS",
        "root_prim_path": root_path,
        "selected_prim_path": f"{root_path}/TestCube",
        "model_prim_count": len(created_prims) + 1,
        "model_semantics": [
            "lane_geometry",
            "blocked_lane_zone",
            "evidence_pins",
            "limitations_marker",
            "review_only_not_executed_marker",
            "no_action_state_marker",
        ],
        "viewport_frame_status": frame_status,
        "r3_scene_prim_selection_targets": r3_scene_targets,
        "r4_event_overlay_marker_paths": r4_event_marker_paths,
        "r5_real_scene_review_marker_paths": [
            f"{R5_EVENT_MARKER_ROOT}/BarcelonaReviewBoundaryMarker001",
            *r5_event_marker_paths,
        ],
        "review_only": True,
        "execution_state": "not_executed",
    }


def ensure_scene_prim_selection_targets() -> dict:
    """Load lightweight R3 selectable scene roots, including local Barcelona USD assets."""

    try:
        import omni.usd  # type: ignore
        from pxr import UsdGeom  # type: ignore
    except Exception as exc:  # pragma: no cover - Kit-only dependency
        return {"status": "BLOCKED_KIT_USD_API_UNAVAILABLE", "reason": str(exc)}

    context = omni.usd.get_context()
    stage = context.get_stage()
    if stage is None:
        return {"status": "BLOCKED_NO_STAGE"}

    workspace_root = Path(__file__).resolve().parents[5]
    scene_root_path = "/CityBrainR3Scene"
    UsdGeom.Xform.Define(stage, scene_root_path)

    references = []
    for name, rel_path in (
        ("BarcelonaRealMesh", BARCELONA_REAL_MESH_USD),
        ("BarcelonaPreview", BARCELONA_PREVIEW_USD),
    ):
        asset_path = workspace_root / rel_path
        prim_path = f"{scene_root_path}/{name}"
        prim = UsdGeom.Xform.Define(stage, prim_path).GetPrim()
        status = "MISSING"
        if asset_path.exists():
            try:
                prim.GetReferences().AddReference(str(asset_path).replace("\\", "/"))
                status = "REFERENCED"
            except Exception as exc:
                status = f"REFERENCE_FAILED: {exc}"
        references.append(
            {
                "name": name,
                "reference_prim_path": prim_path,
                "asset_path": str(asset_path),
                "status": status,
            }
        )

    return {
        "status": "PASS" if any(ref["status"] == "REFERENCED" for ref in references) else "PARTIAL",
        "scene_root_prim_path": scene_root_path,
        "references": references,
        "review_only": True,
        "execution_state": "not_executed",
    }


def _frame_test_model_when_viewport_ready(prims: list[str]) -> str:
    try:
        import omni.kit.app  # type: ignore
        from omni.kit.viewport.utility import frame_viewport_prims, get_active_viewport  # type: ignore
    except Exception as exc:  # pragma: no cover - Kit-only dependency
        return f"BLOCKED_VIEWPORT_API_UNAVAILABLE: {exc}"

    def _try_frame() -> bool:
        viewport = get_active_viewport()
        if not viewport:
            return False
        return bool(frame_viewport_prims(viewport, prims=prims))

    if _try_frame():
        return "FRAMED_IMMEDIATE"

    async def _deferred_frame() -> None:
        app = omni.kit.app.get_app()
        for _ in range(30):
            await app.next_update_async()
            if _try_frame():
                return

    asyncio.ensure_future(_deferred_frame())
    return "DEFERRED_FRAME_REQUESTED"
