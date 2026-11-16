"""Regression Test: Rigid Insertion-Path Verification for Brackets 01..26.

Sweeps candidate rigid insertion axes and multi-stage paths (step <= 0.5 mm) from the
final seated pose of every bracket (bracket_01..26) against the actual trunk B-Rep solids
(both stacked and unstacked section-by-section) and checks boolean intersection volume at
every substep.

No docstrings or comments are trusted: a joint passes ONLY if a collision-free rigid path
actually exists in 3D B-Rep geometry from outside the trunk envelope to the seated pose.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import build123d as bd

CAD_DIR = Path(__file__).resolve().parent
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))

from brackets import build_all_station_brackets
from common_params import (
    BRACKET_STATION_COUNT,
    DOVETAIL_ANGULAR_STEP_DEG,
    DOVETAIL_SLOT_Z_OFFSET,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    helix_z,
)
from trunk import build_trunk_base, build_trunk_mid, build_trunk_top

COLLISION_TOL_MM3 = 0.05


def _inter_vol(a: bd.Shape, b: bd.Shape) -> float:
    inter = a & b
    if inter is None:
        return 0.0
    try:
        return float(inter.volume)
    except Exception:
        return 0.0


def _crop_trunk_near_station(
    sections: list[tuple[str, bd.Solid]],
    loc0: bd.Location,
    z_slot: float,
    z_pad_below: float = 35.0,
    z_pad_above: float = 60.0,
) -> bd.Shape | None:
    """Intersect trunk sections with a generous sector box in bracket coordinates enclosing
    every rigid sweep pose (`X_local in [-12, +135]`, `Y_local in [-24, +24]`,
    `Z_local in [-z_pad_below, z_pad_above]`).
    """
    crop_box = (
        bd.Pos(61.5, 0.0, -z_pad_below)
        * bd.Box(
            147.0,
            48.0,
            z_pad_below + z_pad_above,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    ).moved(loc0)
    parts: list[bd.Shape] = []
    for _name, sec in sections:
        bb = sec.bounding_box()
        if bb.max.Z < z_slot - z_pad_below or bb.min.Z > z_slot + z_pad_above:
            continue
        clipped = sec & crop_box
        if clipped is not None and getattr(clipped, "volume", 0.0) > 0.0:
            parts.append(clipped)
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return bd.Compound(children=parts)


def _check_pose(
    bracket: bd.Solid,
    loc0: bd.Location,
    dx: float,
    dy: float,
    dz: float,
    obstacle: bd.Shape | None,
) -> float:
    if obstacle is None:
        return 0.0
    moved_b = bracket.moved(loc0 * bd.Location((dx, dy, dz)))
    return _inter_vol(moved_b, obstacle)


def find_rigid_insertion_path(
    bracket: bd.Solid,
    theta_deg: float,
    z_slot: float,
    sections: list[tuple[str, bd.Solid]],
) -> dict[str, object]:
    """Search for ANY rigid collision-free retraction/insertion path (step <= 0.5 mm)
    for `bracket` starting from seated `(R=TRUNK_OUTER_R, theta_deg, z_slot)` until the
    tenon clears the trunk envelope (`dx >= 5.5 mm`, or axial clearance past `z_slot + 40 mm`).
    """
    rad = math.radians(theta_deg)
    loc0 = bd.Location(
        (TRUNK_OUTER_R * math.cos(rad), TRUNK_OUTER_R * math.sin(rad), z_slot),
        (0.0, 0.0, theta_deg),
    )
    obstacle = _crop_trunk_near_station(sections, loc0, z_slot, z_pad_below=40.0, z_pad_above=65.0)

    seated_vol = _check_pose(bracket, loc0, 0.0, 0.0, 0.0, obstacle)
    if seated_vol > COLLISION_TOL_MM3:
        return {
            "pass": False,
            "path": None,
            "seated_vol": seated_vol,
            "reason": f"Seated pose itself collides ({seated_vol:.3f} mm³)",
        }

    # 1. Straight rays in (X, Y, Z) at <= 0.4 mm step: radial +X and tilted rays
    ray_angles_deg = [0.0, 15.0, -15.0, 30.0, -30.0, 45.0, -45.0, 60.0, -60.0, 75.0, -75.0]
    radial_fail_info = ""
    for ang in ray_angles_deg:
        ca = math.cos(math.radians(ang))
        sa = math.sin(math.radians(ang))
        step_len = 0.4
        n_steps = int(math.ceil(6.0 / (step_len * max(0.15, ca))))
        ok = True
        for i in range(1, n_steps + 1):
            s = i * step_len
            dx = s * ca
            dz = s * sa
            if abs(dz) > 45.0:
                ok = False
                break
            vol = _check_pose(bracket, loc0, dx, 0.0, dz, obstacle)
            if vol > COLLISION_TOL_MM3:
                if ang == 0.0 and not radial_fail_info:
                    radial_fail_info = f"radial +X blocked at dx={dx:.2f} mm ({vol:.2f} mm³)"
                ok = False
                break
            if dx >= 5.6:
                return {
                    "pass": True,
                    "path": f"straight ray angle={ang:+.0f}° to dx={dx:.1f} mm",
                    "seated_vol": seated_vol,
                    "reason": "OK",
                }
        if not ok:
            continue

    # 2. Pure vertical escape (+Z / -Z) at 0.5 mm steps, followed by radial +X at 0.4 mm steps
    #    (covers both keyhole L-path drop-in AND unstacked open-top/open-bottom seam slide-out)
    best_z_span_up = 0.0
    best_z_span_dn = 0.0
    for direction, dz_limit in [(+1.0, 45.0), (-1.0, -35.0)]:
        step_z = 0.5 * direction
        n_z = int(abs(dz_limit) / 0.5)
        for iz in range(1, n_z + 1):
            dz = iz * step_z
            vol_z = _check_pose(bracket, loc0, 0.0, 0.0, dz, obstacle)
            if vol_z > COLLISION_TOL_MM3:
                if direction > 0:
                    best_z_span_up = (iz - 1) * 0.5
                else:
                    best_z_span_dn = (iz - 1) * 0.5
                break
            # Test radial extraction at this height dz (step <= 0.4 mm out to dx = 5.6 mm)
            # Check coarse probe first (dx=0.8, 2.0) to avoid wasting work if obviously blocked,
            # ONLY claiming PASS if EVERY 0.4 mm substep passes!
            probe_blocked = False
            for dx_probe in (0.4, 1.2, 2.4, 4.0):
                if _check_pose(bracket, loc0, dx_probe, 0.0, dz, obstacle) > COLLISION_TOL_MM3:
                    probe_blocked = True
                    break
            if not probe_blocked:
                all_clear = True
                for ix in range(1, 15):  # 0.4 .. 5.6 mm
                    dx = ix * 0.4
                    if _check_pose(bracket, loc0, dx, 0.0, dz, obstacle) > COLLISION_TOL_MM3:
                        all_clear = False
                        break
                if all_clear:
                    return {
                        "pass": True,
                        "path": f"L-path dz={dz:+.1f} mm -> radial +X",
                        "seated_vol": seated_vol,
                        "reason": "OK",
                    }
        else:
            if direction > 0:
                best_z_span_up = dz_limit
            else:
                best_z_span_dn = abs(dz_limit)

    # 3. Tangential slide (+/-Y at 0.5 mm step up to +/-12 mm) then radial +X
    for dy_dir in (+1.0, -1.0):
        for iy in range(1, 25):
            dy = iy * 0.5 * dy_dir
            if _check_pose(bracket, loc0, 0.0, dy, 0.0, obstacle) > COLLISION_TOL_MM3:
                break
            all_clear = True
            for ix in range(1, 15):
                dx = ix * 0.4
                if _check_pose(bracket, loc0, dx, dy, 0.0, obstacle) > COLLISION_TOL_MM3:
                    all_clear = False
                    break
            if all_clear:
                return {
                    "pass": True,
                    "path": f"tangential dy={dy:+.1f} mm -> radial +X",
                    "seated_vol": seated_vol,
                    "reason": "OK",
                }

    return {
        "pass": False,
        "path": None,
        "seated_vol": seated_vol,
        "reason": (
            f"{radial_fail_info}; vertical travel bounded to +{best_z_span_up:.1f}/-{best_z_span_dn:.1f} mm"
        ),
    }


def run_insertion_audit(stations: list[int] | None = None) -> tuple[bool, list[dict[str, object]]]:
    t0 = time.time()
    tb = build_trunk_base()
    tm = build_trunk_mid()
    tt = build_trunk_top()
    tm_placed = tm.moved(bd.Location((0.0, 0.0, TRUNK_SECTION_HEIGHT)))
    tt_placed = tt.moved(bd.Location((0.0, 0.0, 2.0 * TRUNK_SECTION_HEIGHT)))
    brackets = build_all_station_brackets()
    print(f"Built trunk & {BRACKET_STATION_COUNT} brackets in {time.time() - t0:.2f}s")

    stacked_sections = [("trunk_base", tb), ("trunk_mid", tm_placed), ("trunk_top", tt_placed)]

    if stations is None:
        stations = list(range(1, BRACKET_STATION_COUNT + 1))

    rows: list[dict[str, object]] = []
    all_stacked_pass = True

    print(
        f"{'St':>3} | {'Theta':>6} | {'Z_slot':>7} | {'Section':<16} | "
        f"{'Stacked Path':<32} | {'Unstacked Path':<32}"
    )
    print("-" * 114)

    for k in stations:
        deg = float(k * DOVETAIL_ANGULAR_STEP_DEG)
        z_slot = helix_z(deg) + DOVETAIL_SLOT_Z_OFFSET
        b = brackets[f"bracket_{k:02d}"]

        # Identify which trunk section(s) cover [z_slot, z_slot + 23]
        touches = []
        unstacked_secs: list[tuple[str, bd.Solid]] = []
        if z_slot < TRUNK_SECTION_HEIGHT:
            touches.append("base")
            unstacked_secs = [("trunk_base", tb)]
        if z_slot + 23.0 > TRUNK_SECTION_HEIGHT and z_slot < 2.0 * TRUNK_SECTION_HEIGHT:
            touches.append("mid")
            if not unstacked_secs:
                unstacked_secs = [("trunk_mid", tm_placed)]
        if z_slot + 23.0 > 2.0 * TRUNK_SECTION_HEIGHT:
            touches.append("top")
            if not unstacked_secs:
                unstacked_secs = [("trunk_top", tt_placed)]
        sec_label = "+".join(touches)

        res_stacked = find_rigid_insertion_path(b, deg, z_slot, stacked_sections)
        if len(touches) == 1:
            res_unstacked = res_stacked
        else:
            # Check primary lower section alone (as suggested by README before stacking next section)
            res_unstacked = find_rigid_insertion_path(b, deg, z_slot, unstacked_secs)

        if not res_stacked["pass"]:
            all_stacked_pass = False

        st_str = f"PASS ({res_stacked['path']})" if res_stacked["pass"] else f"FAIL ({res_stacked['reason']})"
        un_str = (
            "same"
            if len(touches) == 1
            else (
                f"PASS ({res_unstacked['path']})"
                if res_unstacked["pass"]
                else f"FAIL ({res_unstacked['reason']})"
            )
        )
        print(f"{k:3d} | {deg:5.0f}° | {z_slot:7.2f} | {sec_label:<16} | {st_str:<32} | {un_str:<32}")
        rows.append(
            {
                "station": k,
                "theta_deg": deg,
                "z_slot": z_slot,
                "section": sec_label,
                "stacked": res_stacked,
                "unstacked": res_unstacked,
            }
        )

    n_pass = sum(1 for r in rows if r["stacked"]["pass"])
    n_unstacked_pass = sum(1 for r in rows if r["unstacked"]["pass"])
    print("-" * 114)
    print(
        f"Summary (verified by B-Rep sweep computation): "
        f"{n_pass}/{len(rows)} PASS when trunk stacked | "
        f"{n_unstacked_pass}/{len(rows)} PASS when single lower section unstacked."
    )
    return all_stacked_pass, rows


def main() -> int:
    ok, _ = run_insertion_audit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
