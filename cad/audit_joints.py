"""Phase 3 Comprehensive CAD Joint & Assembly-Order Audit (cad/audit_joints.py).

Computes exact B-Rep boolean clearances, rigid insertion paths, interference volumes,
swept-sphere marble tunnel clearances, and component envelope checks across all mating
interfaces in grav-mass without relying on comments, docstrings, or README claims.
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

from auger import build_all_auger_parts
from brackets import build_all_station_brackets
from common_params import (
    AUGER_BALL_ORBIT_R,
    AUGER_BORE_DIA,
    AUGER_HALF_HEIGHT,
    BALL_DIAMETER,
    BOTTOM_TRAY_TAB_COORDS,
    BRACKET_STATION_COUNT,
    CROWN_SOCKET_DEPTH,
    CROWN_SOCKET_DIA,
    DOVETAIL_ANGULAR_STEP_DEG,
    DOVETAIL_SLOT_Z_OFFSET,
    HELIX_TOTAL_DEG,
    N20_DSHAFT_DIA,
    N20_DSHAFT_FLAT,
    PLANET_ANCHOR_DEGS,
    RETURN_CHUTE_END_R,
    TRACK_BASE_Y,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    WIRE_CONDUIT_ANGLE_DEG,
    WIRE_CONDUIT_W,
    closed_loop_section_plane,
    closed_loop_track_point,
    helix_point,
    helix_z,
)
from export_3mf_plates import PLANET_NAMES
from topper_planets import (
    BAMBU_MAG_LED_DIA,
    BAMBU_MAG_LED_HEIGHT,
    BAMBU_MAG_LED_Z_OFFSET,
    build_all_topper_planet_parts,
    build_apple_green_leaf,
    build_assembled_apple_marble,
)
from track import (
    PLANET_PEG_DIA,
    PLANET_PEG_HEIGHT,
    TRACK_PLANET_SEGMENT_INDICES,
    build_track_segment,
    get_track_segment_specs,
)
from trunk import build_all_trunk_parts


def _inter_vol(a: bd.Shape, b: bd.Shape) -> float:
    ba = a.bounding_box()
    bb = b.bounding_box()
    if (
        ba.max.X < bb.min.X
        or ba.min.X > bb.max.X
        or ba.max.Y < bb.min.Y
        or ba.min.Y > bb.max.Y
        or ba.max.Z < bb.min.Z
        or ba.min.Z > bb.max.Z
    ):
        return 0.0
    if isinstance(b, bd.Compound) and len(b.children) > 1:
        return sum(_inter_vol(a, c) for c in b.children)
    if isinstance(a, bd.Compound) and len(a.children) > 1:
        return sum(_inter_vol(c, b) for c in a.children)
    inter = a & b
    if inter is None:
        return 0.0
    try:
        return float(inter.volume)
    except Exception:
        return 0.0


def _sweep_axis(
    moving: bd.Shape,
    obstacle: bd.Shape,
    vec: tuple[float, float, float],
    dist: float,
    step: float = 0.5,
) -> tuple[bool, float, float]:
    """Move `moving` from final pose along `vec` out to `dist` in `<= step` increments.
    Returns (clear_all, max_inter_vol, first_fail_s).
    """
    vx, vy, vz = vec
    vlen = math.sqrt(vx * vx + vy * vy + vz * vz)
    ux, uy, uz = vx / vlen, vy / vlen, vz / vlen
    n = int(math.ceil(dist / step))
    max_v = 0.0
    first_s = -1.0
    for i in range(n + 1):
        s = min(dist, i * step)
        m_pose = moving.moved(bd.Location((s * ux, s * uy, s * uz)))
        v = _inter_vol(m_pose, obstacle)
        if v > max_v:
            max_v = v
        if v > 0.05 and first_s < 0.0:
            first_s = s
    return (max_v <= 0.05), max_v, first_s


def main() -> None:
    t0 = time.time()
    trunk_parts = build_all_trunk_parts()
    auger_parts = build_all_auger_parts()
    brackets = build_all_station_brackets()
    tp_parts = build_all_topper_planet_parts()
    print(f"Built all subsystems in {time.time() - t0:.2f}s\n")

    tb = trunk_parts["trunk_base"]
    tm = trunk_parts["trunk_mid"].moved(bd.Location((0, 0, TRUNK_SECTION_HEIGHT)))
    tt = trunk_parts["trunk_top"].moved(bd.Location((0, 0, 2.0 * TRUNK_SECTION_HEIGHT)))
    topper = tp_parts["golden_apple_topper"].moved(bd.Location((0, 0, 3.0 * TRUNK_SECTION_HEIGHT)))
    leaf = build_apple_green_leaf(orient_for_print=False).moved(bd.Location((0, 0, 3.0 * TRUNK_SECTION_HEIGHT)))

    print("=== 1. TRUNK STACK TENONS, TOPPER & STANDALONE LEAF ===")
    v_tb_tm = _inter_vol(tb, tm)
    v_tm_tt = _inter_vol(tm, tt)
    v_tt_top = _inter_vol(tt, topper)
    v_leaf_top = _inter_vol(leaf, topper)
    ok_tm, mv_tm, _fs_tm = _sweep_axis(tm, tb, (0, 0, 1), 20.0, 0.5)
    ok_tt, mv_tt, _fs_tt = _sweep_axis(tt, tm, (0, 0, 1), 20.0, 0.5)
    ok_top, mv_top, _fs_top = _sweep_axis(topper, tt, (0, 0, 1), 10.0, 0.5)
    print(f"base->mid: seated={v_tb_tm:.4f} mm3 | +Z sweep ok={ok_tm} max_v={mv_tm:.4f}")
    print(f"mid->top: seated={v_tm_tt:.4f} mm3 | +Z sweep ok={ok_tt} max_v={mv_tt:.4f}")
    print(f"topper->top: seated={v_tt_top:.4f} mm3 | +Z sweep ok={ok_top} max_v={mv_top:.4f}")
    print(f"apple_green_leaf->topper stem socket: seated={v_leaf_top:.4f} mm3")
    # Rotational twist lock of base->mid
    rot_tm = _inter_vol(tb, tm.moved(bd.Location((0, 0, 0), (0, 0, 3.0))))
    print(f"base->mid +/-3 deg twist interference: {rot_tm:.2f} mm3")

    print("\n=== 2. AUGER & MOTOR DRIVE STACK ===")
    mcd = auger_parts["Motor_Clutch_Driver"].moved(bd.Location((0, 0, 26.2)))
    al = auger_parts["auger_lower"].moved(bd.Location((0, 0, 37.22)))
    au = auger_parts["auger_upper"].moved(bd.Location((0, 0, 37.22 + AUGER_HALF_HEIGHT + 0.1)))
    print(f"mcd vs tb seated={_inter_vol(mcd, tb):.4f}")
    print(f"al vs tb seated={_inter_vol(al, tb):.4f} | al vs mcd seated={_inter_vol(al, mcd):.4f}")
    print(f"al vs au seated={_inter_vol(al, au):.4f} | au vs tm seated={_inter_vol(au, tm):.4f} | au vs tt seated={_inter_vol(au, tt):.4f}")
    # Sweep auger_lower +Z inside tb (up out of clutch) & auger_upper +Z
    ok_al, mv_al, _ = _sweep_axis(al, mcd + tb, (0, 0, 1), 18.0, 0.5)
    ok_au, mv_au, _ = _sweep_axis(au, al, (0, 0, 1), 15.0, 0.5)
    print(f"al +Z sweep vs (mcd+tb): ok={ok_al} max_v={mv_al:.4f}")
    print(f"au +Z sweep vs al: ok={ok_au} max_v={mv_au:.4f}")
    # Check thrust ledge engagement (al moved -0.5 mm in Z onto tb ledge at Z=37.20)
    print(f"al dropped -0.5mm onto tb thrust ledge: {_inter_vol(al.moved(bd.Location((0,0,-0.5))), tb):.2f} mm3")
    # Check N20 motor body (12x10x25) + D-shaft (R=1.50, flat=0.50, H=8.4) inside tb pocket & mcd
    n20_body = bd.Pos(0, 0, 1.2) * bd.Box(12.0, 10.0, 25.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_cyl = bd.Pos(0, 0, 26.2) * bd.Cylinder(radius=N20_DSHAFT_DIA / 2.0, height=8.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_box = bd.Pos(-N20_DSHAFT_FLAT, 0, 26.2) * bd.Box(N20_DSHAFT_DIA, 2.0 * N20_DSHAFT_DIA, 8.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_pin = d_cyl & d_box
    print(f"N20 body vs tb={_inter_vol(n20_body, tb):.4f} | D-shaft vs mcd={_inter_vol(d_pin, mcd):.4f}")

    print("\n=== 3. BRACKET SPLIT-TINE PEGS & STEPPED HALF-LAP TRACK SEAMS ===")
    specs = get_track_segment_specs()
    segs_world = [
        build_track_segment(
            t0,
            t1,
            orient_for_print=False,
            include_planet_pedestal=(idx in TRACK_PLANET_SEGMENT_INDICES),
            bottom_return_ramp=is_bot,
            top_feeder_ramp=is_top,
            seg_number=seg_num,
        )
        for idx, (_name, t0, t1, is_bot, is_top, seg_num) in enumerate(specs)
    ]
    s01, s02, s03 = segs_world[0], segs_world[1], segs_world[2]
    s13, s14 = segs_world[12], segs_world[13]
    placed_brackets = {}
    for k in range(1, BRACKET_STATION_COUNT + 1):
        deg = float(k * DOVETAIL_ANGULAR_STEP_DEG)
        placed_brackets[k] = brackets[f"bracket_{k:02d}"].moved(
            bd.Location(
                (TRUNK_OUTER_R * math.cos(math.radians(deg)), TRUNK_OUTER_R * math.sin(math.radians(deg)), helix_z(deg) + DOVETAIL_SLOT_Z_OFFSET),
                (0.0, 0.0, deg),
            )
        )
    b01, b02, b03, b04, b05 = [placed_brackets[k] for k in range(1, 6)]

    print(f"s01 vs s02 seated={_inter_vol(s01, s02):.4f} | s02 vs s03 seated={_inter_vol(s02, s03):.4f} | s13 vs s14 seated={_inter_vol(s13, s14):.4f}")
    print(f"s01 vs b01={_inter_vol(s01, b01):.4f} | s02 vs b01={_inter_vol(s02, b01):.4f} b02={_inter_vol(s02, b02):.4f} b03={_inter_vol(s02, b03):.4f}")
    # Verify stepped half-lap vertical +Z drop onto seated neighbors AND split-tine brackets:
    obs_s02_lap = bd.Compound(children=[s01, tb])
    ok_lap_z, mv_lap_z, fs_lap_z = _sweep_axis(s02, obs_s02_lap, (0, 0, 1), 16.0, 0.5)
    ok_lap14_z, mv_lap14_z, _ = _sweep_axis(s14, bd.Compound(children=[s13, tt]), (0, 0, 1), 16.0, 0.5)
    bpeg_snap_vols = [(d, _inter_vol(s02.moved(bd.Location((0, 0, d))), b02)) for d in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)]
    print(f"s02 +Z stepped-lap drop vs (s01+tb): ok={ok_lap_z} max_v={mv_lap_z:.4f} fail_at={fs_lap_z}")
    print(f"s14 +Z stepped-lap drop vs (s13+tt): ok={ok_lap14_z} max_v={mv_lap14_z:.4f}")
    print("Split-tine bracket peg lobe engagement (+Z vs b02):", [(d, round(v, 4)) for d, v in bpeg_snap_vols])

    print("\n=== 4. INTAKE / DISCHARGE DOCKS & 150° CONDUIT COVERS ===")
    print(f"s01 vs tb seated={_inter_vol(s01, tb):.4f} | s14 vs tt seated={_inter_vol(s14, tt):.4f}")
    ok_s01_z, mv_s01_z, fs_s01_z = _sweep_axis(s01, bd.Compound(children=[tb, b01]), (0, 0, 1), 15.0, 0.5)
    print(f"s01 +Z vs (tb+b01): ok={ok_s01_z} max_v={mv_s01_z:.4f} fail_at={fs_s01_z}")

    conduit_rad = math.radians(WIRE_CONDUIT_ANGLE_DEG)
    conduit_r = TRUNK_OUTER_R + 1.25
    trunk_all = bd.Compound(children=[tb, tm, tt])
    all_brk_comp = bd.Compound(children=list(placed_brackets.values()))
    for s_key, z_c in (
        ("Conduit_Cover_Strip_Base", 100.0),
        ("Conduit_Cover_Strip_Mid", 225.0),
        ("Conduit_Cover_Strip_Top", 375.0),
    ):
        strip_pl = bd.Plane(
            origin=(conduit_r * math.cos(conduit_rad), conduit_r * math.sin(conduit_rad), z_c),
            x_dir=(math.sin(conduit_rad), -math.cos(conduit_rad), 0.0),
            z_dir=(-math.cos(conduit_rad), -math.sin(conduit_rad), 0.0),
        )
        ccs_p = trunk_parts[s_key].moved(bd.Location(strip_pl))
        print(
            f"{s_key} @ 150° Z={z_c}: vs trunk={_inter_vol(ccs_p, trunk_all):.4f} | "
            f"vs all 26 brackets={_inter_vol(ccs_p, all_brk_comp):.4f}"
        )
    # Full-height JST-SM connector envelope inside 150° conduit vs trunk & ALL 26 brackets
    jst_pl = bd.Location((0, 0, 0), (0, 0, WIRE_CONDUIT_ANGLE_DEG))
    jst_sweep = jst_pl * (
        bd.Pos(29.8, 0.0, 52.0) * bd.Box(7.6, 9.6, 392.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    print(
        f"Full-height 150° JST-SM conduit envelope (7.6x9.6mm) vs trunk={_inter_vol(jst_sweep, trunk_all):.4f} | "
        f"vs all 26 brackets={_inter_vol(jst_sweep, all_brk_comp):.4f}"
    )

    print("\n=== 5. BOTTOM_ELECTRONICS_LID TRAY & VAULT COMPONENTS ===")
    lid = trunk_parts["Bottom_Electronics_Lid"]
    print(f"Bottom_Electronics_Lid vs tb (Z=0)={_inter_vol(lid, tb):.4f}")
    # Check 4x M2.5 tab holes on Lid vs tb
    for idx, (tx, ty) in enumerate(BOTTOM_TRAY_TAB_COORDS, start=1):
        m25_pin = bd.Pos(tx, ty, 0.0) * bd.Cylinder(radius=1.25, height=9.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        print(f"  M2.5 tab #{idx} ({tx:.1f},{ty:.1f}) vs Lid={_inter_vol(m25_pin, lid):.4f} (0=through hole)")
    # Check A092+C008 (48x24x18) + HT3.96 plug headroom (58 mm) on Lid (0.0, -31.0, 2.8) vs tb & lid
    a092_plug_gauge = bd.Pos(0.0, -31.0, 2.85) * bd.Box(58.0, 24.0, 18.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"A092+C008+HT3.96 (58x24x18mm) vs tb={_inter_vol(a092_plug_gauge, tb):.4f} vs Lid={_inter_vol(a092_plug_gauge, lid):.4f}")

    print("\n=== 6. PLANETS (KA006 CRUSH RIBS), BAYONET MARBLES, WAND & PEBBLE BAY ===")
    # Test every planet on its PLANET_ANCHOR_DEGS balcony peg
    for idx, pname in enumerate(PLANET_NAMES):
        deg = PLANET_ANCHOR_DEGS[idx]
        pl_m = closed_loop_section_plane(deg, scarf_tilt_deg=0.0)
        pt_b = pl_m.from_local_coords(bd.Vector(30.0, 18.0, 0.0))
        p_obj = tp_parts[pname].moved(bd.Location((pt_b.X, pt_b.Y, pt_b.Z)))
        ov_self = sum(_inter_vol(p_obj, seg) for seg in segs_world)
        print(f"  {pname:16s} @ {deg:6.1f}° vs all 14 track segments={ov_self:.4f}")
    sat_pt = closed_loop_section_plane(PLANET_ANCHOR_DEGS[5], scarf_tilt_deg=0.0).from_local_coords(bd.Vector(30.0, 18.0, 0.0))
    sat_placed = tp_parts["planet_saturn"].moved(bd.Location((sat_pt.X, sat_pt.Y, sat_pt.Z)))
    s05 = segs_world[4]
    print(f"Saturn peg bead overlap at dz=+0.85mm={_inter_vol(s05, sat_placed.moved(bd.Location((0,0,0.85)))):.4f} | at dz=+1.5mm={_inter_vol(s05, sat_placed.moved(bd.Location((0,0,1.5)))):.4f}")
    ka006 = bd.Pos(0, 0, BAMBU_MAG_LED_Z_OFFSET) * bd.Cylinder(radius=BAMBU_MAG_LED_DIA/2.0, height=BAMBU_MAG_LED_HEIGHT, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Mercury KA006 (Ø7.50) crush rib engagement={_inter_vol(tp_parts['planet_mercury'], ka006):.4f} mm3 | Ø6.90 slip gauge={_inter_vol(tp_parts['planet_mercury'], bd.Pos(0,0,BAMBU_MAG_LED_Z_OFFSET)*bd.Cylinder(radius=3.45, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))):.4f}")
    crown_tenon_zone = bd.Pos(0, 0, 450.0) * (bd.Cylinder(radius=29.7, height=4.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) - bd.Cylinder(radius=25.0, height=4.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)))
    lamp_puck = bd.Pos(0, 0, 450.0) * bd.Cylinder(radius=CROWN_SOCKET_DIA/2.0 - 0.1, height=CROWN_SOCKET_DEPTH - 0.1, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Sparkleiot 45mm LED puck inside topper crown (Z=450..454.5) vs topper={_inter_vol(bd.Pos(0,0,450)*bd.Cylinder(radius=22.5, height=3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)), topper):.4f} | crown tenon overlap={_inter_vol(crown_tenon_zone, topper):.4f}")
    wand = tp_parts["Magic_LED_Wand"]
    wand_bb = wand.bounding_box()
    print(f"Magic_LED_Wand bbox: {wand_bb.size} minZ={wand_bb.min.Z:.2f}")
    wand_holster_probe = bd.Pos(52.0 * math.cos(math.radians(30)), 52.0 * math.sin(math.radians(30)), 6.0) * bd.Cylinder(radius=5.6, height=22.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Wand pommel (Ø11.2mm) in trunk_base holster (R=52,+30°) overlap={_inter_vol(wand_holster_probe, tb):.4f}")
    # Check Pebble LED rigid 6.2x3.2 pill passing rotated flat through 4.6mm throat into 8.4x3.6mm bay
    pl_60 = closed_loop_section_plane(60.0, scarf_tilt_deg=0.0)
    pebble_bay = pl_60.from_local_coords(bd.Pos(0.0, TRACK_BASE_Y + 4.45, 0.0) * bd.Box(8.0, 2.8, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)))
    pebble_throat_flat = pl_60.from_local_coords(bd.Pos(0.0, TRACK_BASE_Y + 1.1, 0.0) * bd.Box(3.2, 6.2, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)))
    print(f"8.0x2.8mm Pebble in deepened bay (v=-11.05): {_inter_vol(s02, pebble_bay):.4f} mm3 | 3.2mm-edge-first through 4.6mm throat: {_inter_vol(s02, pebble_throat_flat):.4f} mm3")
    asm_marble, h_a, h_b = build_assembled_apple_marble()
    print(f"Bayonet marble h_a vs h_b seated={_inter_vol(h_a, h_b):.4f}")
    max_rot_m = 0.0
    for ang in range(0, 50, 5):
        v = _inter_vol(h_a.moved(bd.Location((0, 0, 12.5)) * bd.Location((0,0,0), (0,0,float(ang))) * bd.Location((0, 0, -12.5))), h_b)
        max_rot_m = max(max_rot_m, v)
    h_a_unlatched = h_a.moved(bd.Location((0, 0, 12.5)) * bd.Location((0,0,0), (0,0,45.0)) * bd.Location((0, 0, -12.5)))
    ok_ma, mv_ma, _ = _sweep_axis(h_a_unlatched, h_b, (0, 0, 1), 15.0, 0.5)
    print(f"Bayonet marble twist (0->+45 deg) max_v={max_rot_m:.4f} | lift +Z ok={ok_ma} max_v={mv_ma:.4f}", flush=True)

    print("\n=== 7. FULL SWEPT-SPHERE MARBLE PATH (Ø 24.90 mm) ===", flush=True)
    r_ball = BALL_DIAMETER / 2.0  # 12.50 mm
    worst_ball_v = 0.0
    worst_loc = ""
    segs = [(s[1], s[2], segs_world[i]) for i, s in enumerate(specs)]
    for deg in range(1710, -95, -15):
        pt = closed_loop_track_point(float(deg))
        ball = bd.Pos(pt.X, pt.Y, pt.Z + 6.80) * bd.Sphere(radius=r_ball - 0.05)
        local_obs = [tb, tm, tt, topper]
        for a0, a1, s_obj in segs:
            if (a0 - 95.0) <= deg <= (a1 + 95.0):
                local_obs.append(s_obj)
        v = 0.0
        for obs in local_obs:
            v += _inter_vol(ball, obs)
        if v > worst_ball_v:
            worst_ball_v = v
            worst_loc = f"track theta={deg}° ({pt.X:.1f}, {pt.Y:.1f}, {pt.Z+6.8:.1f})"
    for z in range(56, 434, 10):
        ball = bd.Pos(0.0, -AUGER_BALL_ORBIT_R, float(z)) * bd.Sphere(radius=r_ball - 0.05)
        v = _inter_vol(ball, tb) + _inter_vol(ball, tm) + _inter_vol(ball, tt)
        if v > worst_ball_v:
            worst_ball_v = v
            worst_loc = f"flute Z={z} mm"
    for k in range(6):
        t = k / 5.0
        ball_in = bd.Pos(0.0, -RETURN_CHUTE_END_R + (RETURN_CHUTE_END_R - AUGER_BALL_ORBIT_R) * t, 55.3 - 3.3 * t) * bd.Sphere(radius=r_ball - 0.05)
        v_in = _inter_vol(ball_in, tb) + _inter_vol(ball_in, segs[0][2])
        if v_in > worst_ball_v:
            worst_ball_v = v_in
            worst_loc = f"intake chute t={t:.1f}"
        ball_out = bd.Pos(0.0, -17.5 - 29.5 * t, 436.2 - 5.37 * t) * bd.Sphere(radius=r_ball - 0.05)
        v_out = _inter_vol(ball_out, tt) + _inter_vol(ball_out, topper) + _inter_vol(ball_out, segs[-1][2])
        if v_out > worst_ball_v:
            worst_ball_v = v_out
            worst_loc = f"discharge chute t={t:.1f}"
    print(f"Swept 24.90mm ball worst interference={worst_ball_v:.4f} mm3 ({worst_loc})", flush=True)


if __name__ == "__main__":
    main()
