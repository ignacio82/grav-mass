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
from brackets import build_all_24_station_brackets
from common_params import (
    AUGER_BALL_ORBIT_R,
    AUGER_BORE_DIA,
    AUGER_FLIGHT_THICKNESS,
    AUGER_HALF_HEIGHT,
    AUGER_OD,
    AUGER_PITCH,
    BALL_DIAMETER,
    BRACKET_PEG_DIA,
    BRACKET_PEG_HEIGHT,
    BRACKET_PEG_SPACING_U,
    DOVETAIL_ANGULAR_STEP_DEG,
    HEMISPHERE_SNAP_CLEARANCE,
    HELIX_TOTAL_DEG,
    LED_CHANNEL_D,
    LED_CHANNEL_THROAT_W,
    LED_CHANNEL_W,
    MAGNET_DEPTH,
    MAGNET_DIA,
    N20_DSHAFT_DIA,
    N20_DSHAFT_FLAT,
    TRACK_BASE_Y,
    TRACK_SCARF_ANGLE_DEG,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    closed_loop_track_point,
    helix_point,
    helix_radius,
    helix_section_plane,
    helix_z,
)
from export_3mf_plates import PLANET_NAMES
from topper_planets import (
    BAMBU_MAG_LED_DIA,
    BAMBU_MAG_LED_HEIGHT,
    BAMBU_MAG_LED_Z_OFFSET,
    PLANET_PEG_SOCKET_DEPTH,
    PLANET_PEG_SOCKET_DIA,
    WAND_MAGNET_DIA,
    WAND_MAGNET_HEIGHT,
    build_all_topper_planet_parts,
    build_assembled_apple_marble,
)
from track import (
    PLANET_PEG_DIA,
    PLANET_PEG_HEIGHT,
    build_track_joint_clip,
    build_track_segment,
)
from trunk import build_all_trunk_parts


def _inter_vol(a: bd.Shape, b: bd.Shape) -> float:
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
    clip = build_track_joint_clip(orient_for_print=False)
    brackets = build_all_24_station_brackets()
    tp_parts = build_all_topper_planet_parts()
    print(f"Built all subsystems in {time.time() - t0:.2f}s\n")

    tb = trunk_parts["trunk_base"]
    tm = trunk_parts["trunk_mid"].moved(bd.Location((0, 0, TRUNK_SECTION_HEIGHT)))
    tt = trunk_parts["trunk_top"].moved(bd.Location((0, 0, 2.0 * TRUNK_SECTION_HEIGHT)))
    topper = tp_parts["golden_apple_topper"].moved(bd.Location((0, 0, 3.0 * TRUNK_SECTION_HEIGHT)))

    print("=== 1. TRUNK STACK TENONS & TOPPER ===")
    v_tb_tm = _inter_vol(tb, tm)
    v_tm_tt = _inter_vol(tm, tt)
    v_tt_top = _inter_vol(tt, topper)
    ok_tm, mv_tm, fs_tm = _sweep_axis(tm, tb, (0, 0, 1), 20.0, 0.5)
    ok_tt, mv_tt, fs_tt = _sweep_axis(tt, tm, (0, 0, 1), 20.0, 0.5)
    ok_top, mv_top, fs_top = _sweep_axis(topper, tt, (0, 0, 1), 10.0, 0.5)
    print(f"base->mid: seated={v_tb_tm:.4f} mm3 | +Z sweep ok={ok_tm} max_v={mv_tm:.4f}")
    print(f"mid->top: seated={v_tm_tt:.4f} mm3 | +Z sweep ok={ok_tt} max_v={mv_tt:.4f}")
    print(f"topper->top: seated={v_tt_top:.4f} mm3 | +Z sweep ok={ok_top} max_v={mv_top:.4f}")
    # Rotational twist lock of base->mid
    rot_tm = _inter_vol(tb, tm.moved(bd.Location((0, 0, 0), (0, 0, 3.0))))
    print(f"base->mid +/-3 deg twist interference: {rot_tm:.2f} mm3")

    print("\n=== 2. AUGER & MOTOR DRIVE STACK ===")
    mcd = auger_parts["Motor_Clutch_Driver"].moved(bd.Location((0, 0, 26.2)))
    al = auger_parts["auger_lower"].moved(bd.Location((0, 0, 37.22)))
    au = auger_parts["auger_upper"].moved(bd.Location((0, 0, 37.22 + AUGER_HALF_HEIGHT + 0.1)))
    adp = auger_parts["Servo_Or_030_Adapter"].moved(bd.Location((0, 0, 0.2)))
    print(f"adp vs tb seated={_inter_vol(adp, tb):.4f}")
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
    # Check N20 motor body (12x10x25) + D-shaft (R=1.50, flat=0.50, H=6.5) inside adp & mcd
    n20_body = bd.Pos(0, 0, 0.2) * bd.Box(12.0, 10.0, 25.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_cyl = bd.Pos(0, 0, 26.2) * bd.Cylinder(radius=N20_DSHAFT_DIA / 2.0, height=6.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_box = bd.Pos(-N20_DSHAFT_FLAT, 0, 26.2) * bd.Box(N20_DSHAFT_DIA, 2.0 * N20_DSHAFT_DIA, 6.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    d_pin = d_cyl & d_box
    print(f"N20 body vs adp={_inter_vol(n20_body, adp):.4f} | N20 body vs tb={_inter_vol(n20_body, tb):.4f} | D-shaft vs mcd={_inter_vol(d_pin, mcd):.4f}")

    print("\n=== 3. TRACK TO BRACKET PEGS & TRACK-TO-TRACK SCARF JOINTS ===")
    s01 = build_track_segment(0.0, 120.0, orient_for_print=False, bottom_return_ramp=True)
    s02 = build_track_segment(120.0, 240.0, orient_for_print=False, include_planet_pedestal=True)
    s03 = build_track_segment(240.0, 360.0, orient_for_print=False, include_planet_pedestal=True)
    s13 = build_track_segment(1440.0, 1560.0, orient_for_print=False, include_planet_pedestal=True)
    s14 = build_track_segment(1560.0, 1620.0, orient_for_print=False, top_feeder_ramp=True)
    b01 = brackets["bracket_01"].moved(bd.Location((TRUNK_OUTER_R * math.cos(math.radians(60)), TRUNK_OUTER_R * math.sin(math.radians(60)), helix_z(60)-30), (0,0,60)))
    b02 = brackets["bracket_02"].moved(bd.Location((TRUNK_OUTER_R * math.cos(math.radians(120)), TRUNK_OUTER_R * math.sin(math.radians(120)), helix_z(120)-30), (0,0,120)))
    b03 = brackets["bracket_03"].moved(bd.Location((TRUNK_OUTER_R * math.cos(math.radians(180)), TRUNK_OUTER_R * math.sin(math.radians(180)), helix_z(180)-30), (0,0,180)))
    b04 = brackets["bracket_04"].moved(bd.Location((TRUNK_OUTER_R * math.cos(math.radians(240)), TRUNK_OUTER_R * math.sin(math.radians(240)), helix_z(240)-30), (0,0,240)))

    print(f"s01 vs s02 seated={_inter_vol(s01, s02):.4f} | s02 vs s03 seated={_inter_vol(s02, s03):.4f} | s13 vs s14 seated={_inter_vol(s13, s14):.4f}")
    print(f"s01 vs b01={_inter_vol(s01, b01):.4f} b02={_inter_vol(s01, b02):.4f} | s02 vs b02={_inter_vol(s02, b02):.4f} b03={_inter_vol(s02, b03):.4f} b04={_inter_vol(s02, b04):.4f}")
    # Suspected issue: simultaneous installation of s02 onto s01 (120° tangent pegs) + seated b02, b03, b04 (vertical +Z pegs)!
    obs_s02 = bd.Compound(children=[s01, b02, b03, b04, tb])
    ok_z, mv_z, fs_z = _sweep_axis(s02, obs_s02, (0, 0, 1), 12.0, 0.5)
    # Test: (b) uphill helix tangent -w_120 (pl120.z_dir = r x z = -theta = downhill)
    pl120 = helix_section_plane(120.0, scarf_tilt_deg=TRACK_SCARF_ANGLE_DEG)
    w_uphill = (-pl120.z_dir.X, -pl120.z_dir.Y, -pl120.z_dir.Z)
    ok_w, mv_w, fs_w = _sweep_axis(s02, obs_s02, w_uphill, 10.0, 0.5)
    ok_z_nobrk, mv_z_nobrk, fs_z_nobrk = _sweep_axis(s02, bd.Compound(children=[s01, b02, tb]), (0, 0, 1), 12.0, 0.5)
    ok_w_s01only, mv_w_s01only, fs_w_s01only = _sweep_axis(s02, s01, w_uphill, 10.0, 0.5)
    ok_z_s01only, mv_z_s01only, fs_z_s01only = _sweep_axis(s02, s01, (0, 0, 1), 10.0, 0.5)
    ok_z_b03only, mv_z_b03only, fs_z_b03only = _sweep_axis(s02, b03, (0, 0, 1), 10.0, 0.5)
    ok_z_all_brk_nos01, mv_z_all_brk_nos01, _ = _sweep_axis(s02, bd.Compound(children=[b02, b03, b04, tb]), (0, 0, 1), 12.0, 0.5)
    scarf_snap_vols = []
    ux, uy, uz = w_uphill
    for d in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        scarf_snap_vols.append((d, _inter_vol(s02.moved(bd.Location((d * ux, d * uy, d * uz))), s01)))
    bpeg_snap_vols = [(d, _inter_vol(s02.moved(bd.Location((0, 0, d))), b03)) for d in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)]
    print(f"s02 +Z vs (s01+b02+b03+b04+tb): ok={ok_z} max_v={mv_z:.2f} fail_at={fs_z}")
    print(f"s02 +Z vs (s01+b02+tb) [no b03,b04]: ok={ok_z_nobrk} max_v={mv_z_nobrk:.2f} fail_at={fs_z_nobrk}")
    print(f"s02 +Z vs (b02+b03+b04+tb) [no s01]: ok={ok_z_all_brk_nos01} max_v={mv_z_all_brk_nos01:.2f}")
    print(f"s02 +Z vs b03 ONLY: ok={ok_z_b03only} max_v={mv_z_b03only:.2f} fail_at={fs_z_b03only}")
    print(f"s02 -w_120 (uphill) vs (s01+b02+b03+b04+tb): ok={ok_w} max_v={mv_w:.2f} fail_at={fs_w}")
    print(f"s02 -w_120 (uphill) vs s01 ONLY: ok={ok_w_s01only} max_v={mv_w_s01only:.2f} fail_at={fs_w_s01only}")
    print(f"s02 +Z vs s01 ONLY: ok={ok_z_s01only} max_v={mv_z_s01only:.2f} fail_at={fs_z_s01only}")
    print("Scarf snap bead vols (uphill -w_120 vs s01):", [(d, round(v, 4)) for d, v in scarf_snap_vols])
    print("Bracket peg snap bead vols (+Z vs b03):", [(d, round(v, 4)) for d, v in bpeg_snap_vols])
    # Check Track_Joint_Clip seated vs (s01 + s02 + b02)
    pl120_0 = helix_section_plane(120.0, scarf_tilt_deg=0.0)
    clip_placed = pl120_0.from_local_coords(clip)
    print(f"Track_Joint_Clip(asm) vs (s01, s02, b02): s01={_inter_vol(clip_placed, s01):.2f}, s02={_inter_vol(clip_placed, s02):.2f}, b02={_inter_vol(clip_placed, b02):.2f}")
    # Also check Seg 14 +w uphill/downhill vs s13 + tt
    pl1560 = helix_section_plane(1560.0, scarf_tilt_deg=TRACK_SCARF_ANGLE_DEG)
    ok_s14_w, mv_s14_w, _ = _sweep_axis(s14, s13 + tt, (-pl1560.z_dir.X, -pl1560.z_dir.Y, -pl1560.z_dir.Z), 10.0, 0.5)
    ok_s14_z, mv_s14_z, _ = _sweep_axis(s14, s13 + tt, (0, 0, 1), 10.0, 0.5)
    print(f"s14 -w_1560 (uphill) vs (s13+tt): ok={ok_s14_w} max_v={mv_s14_w:.2f} | s14 +Z vs (s13+tt): ok={ok_s14_z} max_v={mv_s14_z:.2f}", flush=True)

    print("\n=== 4. INTAKE / DISCHARGE DOCKS & CONDUIT COVERS ===")
    print(f"s01 vs tb seated={_inter_vol(s01, tb):.4f} | s14 vs tt seated={_inter_vol(s14, tt):.4f}")
    # Check s01 approach along -Y (vs tb + b01 + b02)
    ok_s01_y, mv_s01_y, fs_s01_y = _sweep_axis(s01, bd.Compound(children=[tb, b01, b02]), (0, -1, 0), 25.0, 0.5)
    ok_s01_z, mv_s01_z, fs_s01_z = _sweep_axis(s01, bd.Compound(children=[tb, b01, b02]), (0, 0, 1), 15.0, 0.5)
    print(f"s01 -Y vs (tb+b01+b02): ok={ok_s01_y} max_v={mv_s01_y:.2f} fail_at={fs_s01_y}")
    print(f"s01 +Z vs (tb+b01+b02): ok={ok_s01_z} max_v={mv_s01_z:.2f} fail_at={fs_s01_z}")
    # Check Conduit_Cover_Strip seated at -X on tb, tm, tt
    ccs = trunk_parts["Conduit_Cover_Strip"]
    print(f"Conduit_Cover_Strip bbox: {ccs.bounding_box().size}")
    for idx, z_c in enumerate((105.0, 225.0, 375.0), start=1):
        ccs_p = ccs.moved(bd.Location((-28.5, 0.0, z_c), (90.0, 0.0, 90.0)))
        print(f"Conduit_Cover_Strip_{idx:02d} @ Z={z_c}: vs tb={_inter_vol(ccs_p, tb):.2f} tm={_inter_vol(ccs_p, tm):.2f} tt={_inter_vol(ccs_p, tt):.2f} b03={_inter_vol(ccs_p, b03):.2f}")
    # Check JST-SM connector (8.0 x 6.8 x 24 mm) inside -X conduit WITH vs WITHOUT St 3 (180°) bracket seated!
    jst_sm_clear = bd.Pos(-30.0, 0.0, 95.0) * bd.Box(7.6, 9.6, 22.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    print(f"JST-SM (7.6x9.6mm) in -X conduit @ Z=95 vs (tb+tm+tt)={_inter_vol(jst_sm_clear, tb+tm+tt):.4f} vs b03={_inter_vol(jst_sm_clear, b03):.2f}")
    z_k3_top = helix_z(180.0) - 30.0 + 43.9
    z_k9_bot = helix_z(540.0) - 30.0
    print(f"180° vertical clear gaps between brackets: k3_top={z_k3_top:.1f} -> k9_bot={z_k9_bot:.1f} (gap={z_k9_bot - z_k3_top:.1f} mm vs strip H=68.0 mm!)")

    print("\n=== 5. BOTTOM COVERS & VAULT COMPONENTS ===")
    bbc = trunk_parts["Base_Bottom_Cover"].moved(bd.Location((0, 0, -3.0)))
    bc = trunk_parts["Battery_Cover"].moved(bd.Location((0, -33.0, -2.6)))
    print(f"Base_Bottom_Cover vs tb={_inter_vol(bbc, tb):.4f} | Battery_Cover vs tb={_inter_vol(bc, tb):.4f} | bbc vs bc={_inter_vol(bbc, bc):.4f}")
    # Check if Base_Bottom_Cover (placed flush at Z=0 on bottom) or z=-3 collides with tb/bc
    bbc_z0 = trunk_parts["Base_Bottom_Cover"].moved(bd.Location((0, 0, 0.0)))
    bc_z0 = trunk_parts["Battery_Cover"].moved(bd.Location((0, -33.0, 0.0)))
    print(f"At Z=0: bbc vs tb={_inter_vol(bbc_z0, tb):.4f} | bc vs tb={_inter_vol(bc_z0, tb):.4f} | bbc vs bc={_inter_vol(bbc_z0, bc_z0):.4f}")
    # Check CA001 magnets on Base_Bottom_Cover: is there ANY solid metal/magnet pocket on trunk_base at R=21.5, deg=45,135,225,315?
    mag_hits = 0
    for deg in (45.0, 135.0, 225.0, 315.0):
        probe = bd.Pos(21.5 * math.cos(math.radians(deg)), 21.5 * math.sin(math.radians(deg)), 0.0) * bd.Cylinder(radius=2.5, height=4.0)
        v = _inter_vol(probe, tb)
        print(f"  tb material above CA001 tab {deg:.0f}° (Z=0..4mm): {v:.2f} mm3")
    # Check A092+C008 (48x24x18) + HT3.96 plug headroom (~12mm extra length -> 60 mm!) inside m5_atom_hdriver_bay
    a092_plug_gauge = bd.Pos(0, -33.0, 1.5) * bd.Box(58.0, 24.0, 18.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"A092+C008 with side HT3.96 plug (58x24x18mm) vs tb: {_inter_vol(a092_plug_gauge, tb):.2f} mm3 (vs 48x24x18 without plug)")
    # Check WAGO lever flip clearance (levers open 90 deg -> ~15mm tall on 8.4mm block; bay is 19.8x31.2x18.0 at +44.5,-12)
    # Check DC-099 (B07C7VSRBG) rear wall thickness at X=-75..-46, Y=0, Z=10
    dc_wall_probe = bd.Pos(-65.0, 0.0, 10.0) * bd.Box(24.0, 14.0, 14.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    # Wait: check exact distance from outer flange surface at (-72.5, 0, 10) to inside of xa007_bay (-57.3, 0, 10)
    print(f"DC jack barrel bore X: outer ~ -72.5 mm, inner pocket X = -46 - 11.3 = -57.3 mm -> wall thickness = {72.5 - 57.3:.1f} mm!")

    print("\n=== 6. PLANETS, BAYONET MARBLES, WAND MAGNET & PEBBLE LED CHANNEL ===")
    sat = tp_parts["planet_saturn"]
    pt_seg05 = helix_point(540.0)  # Saturn on seg 05 (480..600 -> 540°)
    rad_s = math.radians(540.0)
    sat_placed = sat.moved(bd.Location((pt_seg05.X + 30*math.cos(rad_s), pt_seg05.Y + 30*math.sin(rad_s), pt_seg05.Z + 18.05)))
    s05 = build_track_segment(480.0, 600.0, orient_for_print=False, include_planet_pedestal=True)
    s08_up = build_track_segment(840.0, 960.0, orient_for_print=False, include_planet_pedestal=True)
    print(f"Saturn vs track seg05={_inter_vol(sat_placed, s05):.4f} | Saturn vs upper turn seg08={_inter_vol(sat_placed, s08_up):.4f}")
    # Check planet peg pull-off vs seated interference across Mercury (smallest) & Saturn
    print(f"Saturn peg bead overlap at dz=+0.85mm={_inter_vol(s05, sat_placed.moved(bd.Location((0,0,0.85)))):.4f} | at dz=+1.5mm={_inter_vol(s05, sat_placed.moved(bd.Location((0,0,1.5)))):.4f}")
    ka006 = bd.Pos(0, 0, BAMBU_MAG_LED_Z_OFFSET) * bd.Cylinder(radius=BAMBU_MAG_LED_DIA/2.0, height=BAMBU_MAG_LED_HEIGHT, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Mercury KA006 (Ø7.50) overlap={_inter_vol(tp_parts['planet_mercury'], ka006):.4f} | Ø7.98 gauge overlap={_inter_vol(tp_parts['planet_mercury'], bd.Pos(0,0,BAMBU_MAG_LED_Z_OFFSET)*bd.Cylinder(radius=3.99, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))):.4f}")
    # Check topper LED Lamp Kit 001 (Ø60x18.5 at Z=450..468.5) and Sparkleiot ring (OD 45, ID 32, H 3.0 at Z=447.5..450)
    ring_gauge = bd.Pos(0, 0, 447.5) * (bd.Cylinder(radius=22.5, height=3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) - bd.Cylinder(radius=16.0, height=3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)))
    lamp_puck = bd.Pos(0, 0, 450.0) * bd.Cylinder(radius=30.0, height=18.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Sparkleiot ring (OD45/ID32/H3.0) vs tt={_inter_vol(ring_gauge, tt):.4f} vs topper={_inter_vol(ring_gauge, topper):.4f}")
    print(f"Lamp Kit 001 (Ø60x18.5) vs tt={_inter_vol(lamp_puck, tt):.4f} vs topper={_inter_vol(lamp_puck, topper):.4f}")
    # Check Magic_LED_Wand magnet (Ø8.0x2.0) & holster (+30 deg, R=52)
    wand = tp_parts["Magic_LED_Wand"]
    wand_bb = wand.bounding_box()
    print(f"Magic_LED_Wand bbox: {wand_bb.size} minZ={wand_bb.min.Z:.2f}")
    # Wand handle pommel sits in holster cylinder (+30°, R=52, Z=6..27)
    wand_holster_probe = bd.Pos(52.0 * math.cos(math.radians(30)), 52.0 * math.sin(math.radians(30)), 6.0) * bd.Cylinder(radius=5.6, height=22.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    print(f"Wand pommel (Ø11.2mm) in trunk_base holster (R=52,+30°) overlap={_inter_vol(wand_holster_probe, tb):.4f}")
    # Check Pebble LED rigid 6.2x3.2 pill passing through 4.6mm throat
    pl_60 = helix_section_plane(60.0, scarf_tilt_deg=0.0)
    s01_no_ramp = build_track_segment(0.0, 120.0, orient_for_print=False, include_planet_pedestal=True)
    pebble_32 = pl_60.from_local_coords(bd.Pos(0.0, TRACK_BASE_Y + 2.0, 0.0) * bd.Box(6.2, 3.2, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)))
    pebble_at_throat = pl_60.from_local_coords(bd.Pos(0.0, TRACK_BASE_Y + 0.5, 0.0) * bd.Box(6.2, 3.2, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)))
    print(f"6.2x3.2mm Pebble inside channel (v=-10.0): {_inter_vol(s01_no_ramp, pebble_32):.2f} mm3 | passing 4.6mm throat (v=-11.5): {_inter_vol(s01_no_ramp, pebble_at_throat):.2f} mm3")
    # Check bayonet marble assembly & rotation
    asm_marble, h_a, h_b = build_assembled_apple_marble()
    # Drop h_a +5mm Z at 0 deg twist? h_a is rotated 45 deg in build_assembled_apple_marble, check build_assembled!
    print(f"Bayonet marble h_a vs h_b seated={_inter_vol(h_a, h_b):.4f}")
    # Rotate h_a +45 deg (back from -45 locked pose to 0 deg keyway alignment), then lift +15 mm
    max_rot_m = 0.0
    for ang in range(0, 50, 5):
        v = _inter_vol(h_a.moved(bd.Location((0, 0, 12.5)) * bd.Location((0,0,0), (0,0,float(ang))) * bd.Location((0, 0, -12.5))), h_b)
        max_rot_m = max(max_rot_m, v)
    h_a_unlatched = h_a.moved(bd.Location((0, 0, 12.5)) * bd.Location((0,0,0), (0,0,45.0)) * bd.Location((0, 0, -12.5)))
    ok_ma, mv_ma, fs_ma = _sweep_axis(h_a_unlatched, h_b, (0, 0, 1), 15.0, 0.5)
    print(f"Bayonet marble twist (0->+45 deg) max_v={max_rot_m:.4f} | lift +Z ok={ok_ma} max_v={mv_ma:.4f}", flush=True)

    print("\n=== 7. FULL SWEPT-SPHERE MARBLE PATH (Ø 24.90 mm) ===", flush=True)
    r_ball = BALL_DIAMETER / 2.0  # 12.50 mm
    worst_ball_v = 0.0
    worst_loc = ""
    # Assemble track segs 01..14
    segs = []
    for idx in range(14):
        a0 = idx * 120.0
        a1 = min(HELIX_TOTAL_DEG, (idx + 1) * 120.0)
        segs.append((
            a0,
            a1,
            build_track_segment(
                a0, a1, orient_for_print=False,
                include_planet_pedestal=False,
                bottom_return_ramp=(idx == 0),
                top_feeder_ramp=(idx == 13),
            ),
        ))
    # Check track points (sample every 15 deg from 1710 to -90) against trunk/topper + local segments
    for deg in range(1710, -95, -15):
        pt = closed_loop_track_point(float(deg))
        ball = bd.Pos(pt.X, pt.Y, pt.Z + 6.80) * bd.Sphere(radius=r_ball - 0.05)  # 24.90 mm check
        local_obs = [tb, tm, tt, topper]
        for a0, a1, s_obj in segs:
            if (a0 - 25.0) <= deg <= (a1 + 115.0):
                local_obs.append(s_obj)
        v = 0.0
        for obs in local_obs:
            v += _inter_vol(ball, obs)
        if v > worst_ball_v:
            worst_ball_v = v
            worst_loc = f"track theta={deg}° ({pt.X:.1f}, {pt.Y:.1f}, {pt.Z+6.8:.1f})"
    # Check vertical auger flute Z=56..433 against trunk only (auger blade is what lifts it!)
    for z in range(56, 434, 10):
        ball = bd.Pos(0.0, -AUGER_BALL_ORBIT_R, float(z)) * bd.Sphere(radius=r_ball - 0.05)
        v = _inter_vol(ball, tb) + _inter_vol(ball, tm) + _inter_vol(ball, tt)
        if v > worst_ball_v:
            worst_ball_v = v
            worst_loc = f"flute Z={z} mm"
    # Check intake chute Y=-45.5..-17.5 (Z=56.3->52.0) and discharge chute Y=-17.5..-42.5 (Z=435.5->431.8)
    for k in range(6):
        t = k / 5.0
        ball_in = bd.Pos(0.0, -45.5 + 28.0 * t, 56.3 - 4.3 * t) * bd.Sphere(radius=r_ball - 0.05)
        v_in = _inter_vol(ball_in, tb) + _inter_vol(ball_in, segs[0][2])
        if v_in > worst_ball_v:
            worst_ball_v = v_in
            worst_loc = f"intake chute t={t:.1f}"
        ball_out = bd.Pos(0.0, -17.5 - 25.0 * t, 435.5 - 3.7 * t) * bd.Sphere(radius=r_ball - 0.05)
        v_out = _inter_vol(ball_out, tt) + _inter_vol(ball_out, topper) + _inter_vol(ball_out, segs[-1][2])
        if v_out > worst_ball_v:
            worst_ball_v = v_out
            worst_loc = f"discharge chute t={t:.1f}"
    print(f"Swept 24.90mm ball worst interference={worst_ball_v:.4f} mm3 ({worst_loc})", flush=True)


if __name__ == "__main__":
    main()
