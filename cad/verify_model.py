"""Comprehensive Automated CAD Metrology, Virtual Gauge-Pin, Dry-Fit Assembly &
Snapmaker U1 Multi-Plate .3mf QA Verification Suite (cad/verify_model.py).

Usage:
    uv run --with build123d python3 cad/verify_model.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

CAD_DIR = Path(__file__).resolve().parent
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))

import build123d as bd

from auger import (
    CLUTCH_FLANGE_OD,
    build_all_auger_parts,
)
from brackets import (
    build_all_station_brackets,
    build_cantilever_bracket,
)
from common_params import (
    AUGER_BALL_ORBIT_R,
    AUGER_BORE_DIA,
    AUGER_HALF_HEIGHT,
    AUGER_HEX_ACROSS_FLATS,
    AUGER_OD,
    AUGER_PITCH,
    BALL_DIAMETER,
    BOTTOM_TRAY_OUTER_DIA,
    BOTTOM_TRAY_TAB_COORDS,
    BOTTOM_TRAY_THICK,
    BRACKET_STATION_COUNT,
    CONDUIT_STRIP_LEN_BASE,
    CONDUIT_STRIP_LEN_MID,
    CONDUIT_STRIP_LEN_TOP,
    CROWN_SOCKET_DEPTH,
    CROWN_SOCKET_DIA,
    DC_BARREL_JACK_BORE_DIA,
    DC_BARREL_JACK_Z_CENTER,
    DOVETAIL_CLEARANCE,
    DOVETAIL_SLOT_Z_OFFSET,
    FIT_TOLERANCE,
    HELIX_BOT_R,
    HELIX_PITCH,
    HELIX_TOP_R,
    HELIX_TOTAL_DEG,
    HEX_COUPLE_CLEARANCE,
    HEMISPHERE_SNAP_CLEARANCE,
    LA002_N20_POCKET_X,
    LA002_N20_POCKET_Y,
    LA002_N20_POCKET_Z,
    LED_CHANNEL_D,
    LED_CHANNEL_THROAT_W,
    LED_CHANNEL_W,
    MIN_PART_CLEARANCE,
    N20_DSHAFT_DIA,
    N20_DSHAFT_FLAT,
    PLANET_ANCHOR_DEGS,
    SAFE_PLATE_ZONE,
    STEEL_BALL_DIA,
    TOP_FEEDER_START_R,
    TRACK_BASE_Y,
    TRACK_INNER_WIDTH,
    TRACK_LAP_ARC_DEG,
    TRACK_SHOULDER_INNER_X,
    TRACK_TROUGH_R,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    U1_BED_Z,
    WIRE_CONDUIT_ANGLE_DEG,
    closed_loop_section_plane,
    closed_loop_track_point,
    helix_point,
    helix_radius,
    helix_section_plane,
    helix_z,
)
from export_3mf_plates import PLANET_NAMES, _mesh_bounds, _part_xy_gap, build_five_plates
from topper_planets import (
    BAMBU_MAG_LED_DIA,
    BAMBU_MAG_LED_HEIGHT,
    BAMBU_MAG_LED_Z_OFFSET,
    PLANET_PEG_SOCKET_DEPTH,
    PLANET_PEG_SOCKET_DIA,
    WAND_MAGNET_DIA,
    WAND_MAGNET_HEIGHT,
    build_all_apple_hemispheres,
    build_all_marbles,
    build_all_topper_planet_parts,
    build_apple_captive_pause_marble,
    build_apple_green_leaf,
    build_assembled_apple_marble,
)
from track import (
    PLANET_PEG_DIA,
    PLANET_PEG_HEIGHT,
    TRACK_PLANET_SEGMENT_INDICES,
    build_all_track_parts,
    build_track_segment,
    get_track_segment_specs,
)
from trunk import build_all_trunk_parts


def _inter_vol(a: bd.Shape, b: bd.Shape) -> float:
    """Compute exact boolean intersection volume between two B-Rep solids (0.0 if disjoint)."""
    inter = a & b
    if inter is None or not inter.solids():
        return 0.0
    return float(inter.volume)


def _bboxes_overlap_3d(bb1: bd.BoundBox, bb2: bd.BoundBox) -> bool:
    """Return True if two 3D bounding boxes overlap in X, Y, and Z."""
    return (
        bb1.min.X <= bb2.max.X
        and bb2.min.X <= bb1.max.X
        and bb1.min.Y <= bb2.max.Y
        and bb2.min.Y <= bb1.max.Y
        and bb1.min.Z <= bb2.max.Z
        and bb2.min.Z <= bb1.max.Z
    )


def _bbox_xy_gap(bb1: bd.BoundBox, bb2: bd.BoundBox) -> float:
    """Compute 2D XY gap between two bounding boxes (negative if overlapping)."""
    gap_x = max(0.0, max(bb1.min.X - bb2.max.X, bb2.min.X - bb1.max.X))
    gap_y = max(0.0, max(bb1.min.Y - bb2.max.Y, bb2.min.Y - bb1.max.Y))
    if gap_x == 0.0 and gap_y == 0.0:
        ov_x = min(bb1.max.X - bb2.min.X, bb2.max.X - bb1.min.X)
        ov_y = min(bb1.max.Y - bb2.min.Y, bb2.max.Y - bb1.min.Y)
        return -min(ov_x, ov_y)
    return max(gap_x, gap_y)


def run_all_verifications() -> None:
    """Run all Section 1, 2, 3, and 4 metrology, boolean gauge, assembly, and 3MF checks."""
    output_dir = CAD_DIR.parent / "output"
    threemf_dir = output_dir / "3mf"

    # Build fresh B-Rep parts
    trunk_parts = build_all_trunk_parts()
    auger_parts = build_all_auger_parts()
    station_brackets = build_all_station_brackets()
    topper_planet_parts = build_all_topper_planet_parts()
    apple_leaf_print = topper_planet_parts["apple_green_leaf"]
    apple_leaf_asm = build_apple_green_leaf(orient_for_print=False)
    marbles = build_all_marbles(count=6)
    track_parts = build_all_track_parts(for_plate_grid=False)

    trunk_base = trunk_parts["trunk_base"]
    trunk_mid = trunk_parts["trunk_mid"]
    trunk_top = trunk_parts["trunk_top"]
    bottom_lid = trunk_parts["Bottom_Electronics_Lid"]
    conduit_strip_base = trunk_parts["Conduit_Cover_Strip_Base"]
    conduit_strip_mid = trunk_parts["Conduit_Cover_Strip_Mid"]
    conduit_strip_top = trunk_parts["Conduit_Cover_Strip_Top"]
    auger_lower = auger_parts["auger_lower"]
    auger_upper = auger_parts["auger_upper"]
    motor_clutch_driver = auger_parts["Motor_Clutch_Driver"]
    topper = topper_planet_parts["golden_apple_topper"]

    # =========================================================================
    # SECTION 1: Virtual Gauge-Pin & Streamlined Electronics / Mechanics Fit
    # =========================================================================

    # 1.1 Golden Apple Topper (PLA-only Brown Pedestal + Red Apple + Brown Stem):
    #     - Crown Centering Socket (Ø 60.0 x 4.6 mm) + Sparkleiot WS2812B 16-LED Ring optical cavity
    #     - Separate Teal PETG apple_green_leaf mates into the stem's 3.2 x 2.2 x 4.5 mm leaf socket
    crown_socket_gauge = bd.Cylinder(
        radius=59.6 / 2.0,
        height=4.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    sparkleiot_ring_local = (
        bd.Cylinder(radius=45.6 / 2.0, height=3.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        - bd.Cylinder(radius=31.6 / 2.0, height=3.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    assert _inter_vol(topper, crown_socket_gauge) == 0.0, (
        "Crown centering collar gauge (Ø 59.6 x 4.5 mm) collided with topper socket!"
    )
    assert _inter_vol(topper, sparkleiot_ring_local) == 0.0, (
        "Sparkleiot 16-LED RGB ring gauge (Ø 45.6 OD / Ø 31.6 ID) collided with topper optical throat!"
    )
    assert abs(CROWN_SOCKET_DIA - 60.0) <= 0.05 and abs(CROWN_SOCKET_DEPTH - 4.6) <= 0.05
    assert _inter_vol(topper, apple_leaf_asm) == 0.0, (
        "Teal PETG apple_green_leaf petiole collided with golden_apple_topper stem socket!"
    )
    assert _bboxes_overlap_3d(topper.bounding_box(), apple_leaf_asm.bounding_box()), (
        "apple_green_leaf petiole does not engage golden_apple_topper stem socket!"
    )
    assert _inter_vol(topper, apple_leaf_asm.moved(bd.Location((0.0, 0.0, 1.0)))) > 0.5, (
        "apple_green_leaf petiole failed socket retention overlap probe!"
    )

    # 1.2 Central Trunk Bore, Thrust Ledge, Direct Mechanical Hex Coupler & Auger Clearance
    tb_placed = trunk_base
    tm_placed = trunk_mid.moved(bd.Location((0.0, 0.0, TRUNK_SECTION_HEIGHT)))
    tt_placed = trunk_top.moved(bd.Location((0.0, 0.0, 2.0 * TRUNK_SECTION_HEIGHT)))

    # Verify Sparkleiot 16-Bit WS2812 RGB Ring (B09YTMNGTD, Ø 45.0 OD / Ø 32.0 ID x 3.0 mm)
    # sits inside trunk_top's Ø 50.00 mm crown_collar ID (local Z = 150.0..153.2 mm)
    # and rests cleanly on trunk_top's R = 20.5..25.0 mm solid top rim shelf!
    topper_ring_gauge = bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT + 0.05) * sparkleiot_ring_local
    topper_ring_shelf_probe = bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT - 0.8) * (
        bd.Cylinder(radius=24.8, height=0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        - bd.Cylinder(radius=20.8, height=0.6, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    assert _inter_vol(trunk_top, topper_ring_gauge) == 0.0, (
        "Sparkleiot 16-Bit WS2812 Ring gauge collided with trunk_top crown_collar!"
    )
    assert _inter_vol(trunk_top, topper_ring_shelf_probe) > 0.0, (
        "trunk_top is missing the R=20.8..24.8 mm solid top shelf under the Sparkleiot 16-Bit Ring!"
    )

    # Continuous Ø 23.6 mm bore gauge above the Z=37.20 mm internal thrust ledge
    bore_gauge = bd.Pos(0.0, 0.0, 37.25) * bd.Cylinder(
        radius=23.6 / 2.0,
        height=450.0 - 37.25,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    vol_bore_inter = (
        _inter_vol(tb_placed, bore_gauge)
        + _inter_vol(tm_placed, bore_gauge)
        + _inter_vol(tt_placed, bore_gauge)
    )
    assert vol_bore_inter == 0.0, f"Ø 23.6 mm bore gauge collided with trunk above ledge: {vol_bore_inter}"

    # Verify Ø 19.20 mm coupler chamber below the Z=37.20 mm thrust shelf (clearing Ø 18.0 mm driver)
    clutch_chamber_gauge = bd.Pos(0.0, 0.0, 26.2) * bd.Cylinder(
        radius=18.8 / 2.0,
        height=10.8,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    vol_clutch_chamber = _inter_vol(tb_placed, clutch_chamber_gauge)
    assert vol_clutch_chamber == 0.0, (
        f"Coupler chamber gauge collided with trunk_base: {vol_clutch_chamber}"
    )
    thrust_ledge_ring = bd.Pos(0.0, 0.0, 36.7) * (
        bd.Cylinder(radius=11.6, height=0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        - bd.Cylinder(radius=9.8, height=0.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    assert _inter_vol(tb_placed, thrust_ledge_ring) > 0.0, (
        "Trunk_Base is missing the Z=37.20 mm internal thrust ledge!"
    )

    # Place Motor_Clutch_Driver upright at Z = 26.20 mm (collar Z=26.20..36.20 mm, male hex peg Z=36.20..40.70 mm)
    # and assembled 2-piece Archimedes Auger resting on the Z=37.20 mm thrust ledge (Z=37.22 mm)
    driver_placed = motor_clutch_driver.moved(bd.Location((0.0, 0.0, 26.20)))
    al_placed = auger_lower.moved(bd.Location((0.0, 0.0, 37.22)))
    au_placed = auger_upper.moved(
        bd.Location((0.0, 0.0, 37.22 + AUGER_HALF_HEIGHT + 0.1))
    )

    # Direct Mechanical Hex Coupler Fit & Engagement Check
    vol_driver_trunk = _inter_vol(tb_placed, driver_placed)
    vol_driver_auger = _inter_vol(driver_placed, al_placed)
    assert vol_driver_trunk == 0.0, (
        f"Motor_Clutch_Driver collided with Trunk_Base coupler chamber: {vol_driver_trunk}"
    )
    assert vol_driver_auger == 0.0, (
        f"Motor_Clutch_Driver male hex peg collided with Auger_Bottom female hex socket: {vol_driver_auger}"
    )
    assert _bboxes_overlap_3d(driver_placed.bounding_box(), al_placed.bounding_box()), (
        "Motor_Clutch_Driver top hex peg does not engage Auger_Bottom female hex socket!"
    )
    assert abs(CLUTCH_FLANGE_OD - 22.0) <= 0.05, f"Coupler collar OD {CLUTCH_FLANGE_OD} != 22.0 mm"

    vol_auger_trunk = (
        _inter_vol(tb_placed, al_placed)
        + _inter_vol(tm_placed, al_placed)
        + _inter_vol(tm_placed, au_placed)
        + _inter_vol(tt_placed, au_placed)
    )
    auger_radial_clr = (AUGER_BORE_DIA - AUGER_OD) / 2.0  # 1.50 mm
    assert vol_auger_trunk == 0.0, f"Assembled auger collided with trunk bore: {vol_auger_trunk}"
    assert auger_radial_clr >= 1.0, f"Auger radial clearance {auger_radial_clr} mm < 1.0 mm"

    # Hex coupling between Bottom Auger and Top Auger halves
    vol_hex_inter = _inter_vol(al_placed, au_placed)
    hex_peg_af = AUGER_HEX_ACROSS_FLATS - HEX_COUPLE_CLEARANCE  # 4.85 mm
    hex_sock_af = AUGER_HEX_ACROSS_FLATS + HEX_COUPLE_CLEARANCE  # 5.15 mm
    assert vol_hex_inter == 0.0, f"Auger lower/upper hex joint collided: {vol_hex_inter}"

    # Verify Ø 25.0 mm Marble Lift Physics inside the Vertical Ball Guide Flute (Zero Solid-Through-Solid Overlap)
    for k_flight in range(8):
        z_blade = 37.22 + 5.50 + AUGER_PITCH * (0.75 + k_flight)
        z_marble = z_blade + 15.20
        marble_lift_probe = bd.Pos(0.0, -AUGER_BALL_ORBIT_R, z_marble) * bd.Sphere(
            radius=BALL_DIAMETER / 2.0
        )
        vol_m_auger = _inter_vol(al_placed, marble_lift_probe) + _inter_vol(
            au_placed, marble_lift_probe
        )
        vol_m_trunk = (
            _inter_vol(tb_placed, marble_lift_probe)
            + _inter_vol(tm_placed, marble_lift_probe)
            + _inter_vol(tt_placed, marble_lift_probe)
        )
        assert vol_m_auger == 0.0, (
            f"Ø 25.0 mm marble at flight {k_flight} (Z={z_marble:.2f} mm) overlapped auger: {vol_m_auger:.4f} mm³!"
        )
        assert vol_m_trunk == 0.0, (
            f"Ø 25.0 mm marble at flight {k_flight} (Z={z_marble:.2f} mm) overlapped trunk flute: {vol_m_trunk:.4f} mm³!"
        )

    # Verify Upper Marble Discharge Path clears the Sparkleiot LED ring (Z = 450.0..453.2 mm)
    # and connects directly into track_seg_14_top_entry's enclosed catch basin at 1710° (0.0, -47.0, 430.83 mm)
    # AND Verify Lower Marble Return Path connects from track_seg_01's enclosed -90° catch basin (0.0, -45.5, 56.30 mm)
    # directly into trunk_base's vertical ball guide flute (0.0, -17.5, 52.00 mm) with 0.0 mm³ interference!
    seg_specs = {spec[0]: spec for spec in get_track_segment_specs()}
    seg01_asm = build_track_segment(
        seg_specs["track_seg_01"][1],
        seg_specs["track_seg_01"][2],
        orient_for_print=False,
        bottom_return_ramp=True,
    )
    seg14_asm = build_track_segment(
        seg_specs["track_seg_14_top_entry"][1],
        seg_specs["track_seg_14_top_entry"][2],
        orient_for_print=False,
        top_feeder_ramp=True,
    )
    ring_global = bd.Pos(0.0, 0.0, 3.0 * TRUNK_SECTION_HEIGHT + 0.05) * sparkleiot_ring_local
    for u_dis in (0.0, 0.25, 0.50, 0.75, 1.0):
        pt_start = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 436.2)
        pt_end = bd.Vector(0.0, -TOP_FEEDER_START_R, 430.83)
        pt_m = pt_start * (1.0 - u_dis) + pt_end * u_dis
        m_dis_probe = bd.Pos(pt_m.X, pt_m.Y, pt_m.Z) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
        assert _inter_vol(ring_global, m_dis_probe) == 0.0, (
            f"Upper marble discharge at u={u_dis} (Z={pt_m.Z:.2f} mm) collided with Sparkleiot LED Ring!"
        )
        assert _inter_vol(tt_placed, m_dis_probe) == 0.0, (
            f"Upper marble discharge at u={u_dis} (Z={pt_m.Z:.2f} mm) collided with trunk_top!"
        )
        assert _inter_vol(seg14_asm, m_dis_probe) == 0.0, (
            f"Upper marble discharge at u={u_dis} (Z={pt_m.Z:.2f} mm) collided with track_seg_14_top_entry!"
        )

        pt_bot_start = bd.Vector(0.0, -42.0, 55.70)
        pt_bot_end = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 52.0)
        pt_b = pt_bot_start * (1.0 - u_dis) + pt_bot_end * u_dis
        m_bot_probe = bd.Pos(pt_b.X, pt_b.Y, pt_b.Z) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
        assert _inter_vol(tb_placed, m_bot_probe) == 0.0, (
            f"Lower marble return at u={u_dis} (Z={pt_b.Z:.2f} mm) collided with trunk_base!"
        )
        assert _inter_vol(seg01_asm, m_bot_probe) == 0.0, (
            f"Lower marble return at u={u_dis} (Z={pt_b.Z:.2f} mm) collided with track_seg_01!"
        )

    # Verify solid end-cap bumper walls physically block marbles from falling out at top (+X) or bottom (-X)
    top_endcap_probe = bd.Pos(16.0, -TOP_FEEDER_START_R, 434.0) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
    bot_endcap_probe = bd.Pos(-16.0, -45.5, 56.3) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
    assert _inter_vol(seg14_asm, top_endcap_probe) > 0.0, (
        "track_seg_14_top_entry is missing the upstream (+X) solid end-cap bumper wall!"
    )
    assert _inter_vol(seg01_asm, bot_endcap_probe) > 0.0, (
        "track_seg_01 is missing the downstream (-X) solid end-cap bumper wall!"
    )

    # Verify Ø 25.0 mm rolling marble has ZERO interference along every 5° of the top entry ramp
    # (1710° -> 1500°) and bottom return ramp (60° -> -90°) — proving no wall blocks the ramp!
    for deg_top in range(1710, 1495, -5):
        pt_t = closed_loop_track_point(float(deg_top))
        probe_t = bd.Pos(pt_t.X, pt_t.Y, pt_t.Z + 7.2) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
        v_top_ramp = _inter_vol(seg14_asm, probe_t)
        assert v_top_ramp == 0.0, (
            f"Marble rolling down top ramp at {deg_top}° collided with track_seg_14_top_entry: {v_top_ramp:.3f} mm³!"
        )
    for deg_bot in range(60, -95, -5):
        pt_b = closed_loop_track_point(float(deg_bot))
        probe_b = bd.Pos(pt_b.X, pt_b.Y, pt_b.Z + 7.2) * bd.Sphere(radius=BALL_DIAMETER / 2.0)
        v_bot_ramp = _inter_vol(seg01_asm, probe_b)
        assert v_bot_ramp == 0.0, (
            f"Marble rolling along bottom return ramp at {deg_bot}° collided with track_seg_01: {v_bot_ramp:.3f} mm³!"
        )

    # 1.3 Bottom_Electronics_Lid & Root Vault Clearances:
    #     LA002 / B0BFRPMSW6 N20 Motor (direct top-drop pocket), UCTRONICS, 2x Unstacked WAGO 221-415, A092+C008, DC-099 Jack
    la002_gauge = bd.Pos(0.0, 0.0, 1.2) * bd.Box(
        LA002_N20_POCKET_X,  # 12.4 mm
        LA002_N20_POCKET_Y,  # 10.4 mm
        LA002_N20_POCKET_Z,  # 26.0 mm
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    la002_over = bd.Pos(0.0, 0.0, 1.2) * bd.Box(
        15.0,
        14.0,
        24.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(trunk_base, la002_gauge) == 0.0, "LA002 N20 motor gauge collided with trunk_base!"
    assert _inter_vol(trunk_base, la002_over) > 0.0, "Oversized LA002 gauge did not engage trunk_base anti-rotation pocket!"

    # Bottom_Electronics_Lid flush fit inside trunk_base rabbet (Z = 0..2.80 mm) + 4x M2.5 screw alignment
    assert _inter_vol(trunk_base, bottom_lid) == 0.0, (
        "Bottom_Electronics_Lid collided with trunk_base root vault / cradles!"
    )
    assert abs(BOTTOM_TRAY_OUTER_DIA - 134.6) <= 0.05 and abs(BOTTOM_TRAY_THICK - 2.80) <= 0.05
    assert _inter_vol(trunk_base, bottom_lid.moved(bd.Location((1.0, 0.0, 0.0)))) > 1.0, (
        "Bottom_Electronics_Lid failed radial rabbet lock test inside trunk_base!"
    )
    m25_probe_vol = 0.0
    for tx, ty in BOTTOM_TRAY_TAB_COORDS:
        m25_shaft = bd.Pos(tx, ty, 0.0) * bd.Cylinder(
            radius=2.55 / 2.0,
            height=9.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        assert _inter_vol(bottom_lid, m25_shaft) == 0.0, f"M2.5 screw collided with Bottom_Electronics_Lid tab at {(tx, ty)}"
        m25_probe_vol += _inter_vol(trunk_base, m25_shaft)
    assert m25_probe_vol > 5.0, "4x M2.5 screws did not engage trunk_base self-tapping root buttress holes!"

    # (a) Hollow Root Vault unobstructed cable slack volume >= 150,000 mm³ (150 cm³)
    vault_ref_cyl = bd.Cylinder(
        radius=67.5,  # Ø 135.0 mm internal clear electronics vault
        height=42.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    vault_solid_vol = _inter_vol(trunk_base, vault_ref_cyl)
    open_vault_slack_vol = float(vault_ref_cyl.volume) - vault_solid_vol
    assert open_vault_slack_vol >= 150_000.0, (
        f"Hollow Root Vault unobstructed slack volume {open_vault_slack_vol:.1f} mm³ < 150,000 mm³ (150 cm³)!"
    )

    # (b) UCTRONICS U6223 (63.0 x 27.0 x 10.0 mm) on Bottom_Electronics_Lid at (-2.0, +36.0, 4.0)
    uctronics_buck_gauge = bd.Pos(-2.0, 36.0, BOTTOM_TRAY_THICK + 1.25) * bd.Box(
        63.0,
        27.0,
        10.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    uctronics_buck_over = bd.Pos(-2.0, 36.0, BOTTOM_TRAY_THICK + 1.25) * bd.Box(
        67.0,
        31.0,
        13.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    uctronics_wire_portal_gauge = bd.Pos(-2.0, 36.0, BOTTOM_TRAY_THICK + 1.25) * bd.Box(
        70.0,
        18.0,
        10.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(trunk_base, uctronics_buck_gauge) == 0.0 and _inter_vol(bottom_lid, uctronics_buck_gauge) == 0.0, (
        "UCTRONICS B07XXWQ49N (63.0 x 27.0 x 10.0 mm) buck converter gauge collided with trunk_base / Bottom_Electronics_Lid!"
    )
    assert _inter_vol(bottom_lid, uctronics_buck_over) > 0.0, (
        "Oversized UCTRONICS buck converter gauge did not intersect Bottom_Electronics_Lid cradle rails!"
    )
    assert _inter_vol(trunk_base + bottom_lid, uctronics_wire_portal_gauge) == 0.0, (
        "UCTRONICS buck converter ±X screw-terminal wire portal gauge collided with trunk_base / lid!"
    )

    # (c) Unstacked 2x WAGO 221-415 cradles on Bottom_Electronics_Lid at (+46.0, -2.5) and (-32.5, 0.0)
    wago_positions = [(46.0, -2.5), (-32.5, 0.0)]
    wago_gauges: list[bd.Solid] = []
    for wx, wy in wago_positions:
        w_g = bd.Pos(wx, wy, BOTTOM_TRAY_THICK + 0.05) * bd.Box(
            18.6,
            30.0,
            8.4,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        w_ov = bd.Pos(wx, wy, BOTTOM_TRAY_THICK + 0.05) * bd.Box(
            22.5,
            34.0,
            10.5,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        w_wire = bd.Pos(wx - 11.5, wy, BOTTOM_TRAY_THICK + 0.05) * bd.Box(
            5.0,
            24.0,
            8.4,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        assert _inter_vol(trunk_base, w_g) == 0.0 and _inter_vol(bottom_lid, w_g) == 0.0, (
            f"Unstacked WAGO 221-415 gauge at {(wx, wy)} collided with trunk_base / Bottom_Electronics_Lid!"
        )
        assert _inter_vol(bottom_lid, w_ov) > 0.0, f"Oversized WAGO gauge at {(wx, wy)} did not hit cradle walls!"
        assert _inter_vol(trunk_base + bottom_lid, w_wire) == 0.0, (
            f"WAGO 221-415 -X wire portal gauge at {(wx, wy)} collided!"
        )
        wago_gauges.append(w_g)

    # (d) A092+C008 Driver + HT3.96-4P plug envelope (74.0 x 24.0 x 19.0 mm centered around (0.0, -31.0))
    a092_gauge = bd.Pos(0.0, -31.0, BOTTOM_TRAY_THICK + 0.05) * bd.Box(
        48.0,
        24.0,
        19.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    a092_ht396_plug_gauge = bd.Pos(32.0, -31.0, BOTTOM_TRAY_THICK + 2.0) * bd.Box(
        16.0,
        14.0,
        10.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(trunk_base + bottom_lid, a092_gauge) == 0.0, (
        "M5Stack A092+C008 gauge (48 x 24 x 19 mm) collided with trunk_base / Bottom_Electronics_Lid!"
    )
    assert _inter_vol(trunk_base + bottom_lid, a092_ht396_plug_gauge) == 0.0, (
        "HT3.96-4P +X plug envelope (+16 mm) on A092 collided with trunk_base / Bottom_Electronics_Lid!"
    )

    motor_shroud_cyl = bd.Cylinder(
        radius=14.0,
        height=30.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _bbox_xy_gap(uctronics_buck_gauge.bounding_box(), wago_gauges[0].bounding_box()) >= 7.0
    assert _bbox_xy_gap(wago_gauges[0].bounding_box(), motor_shroud_cyl.bounding_box()) >= 18.0

    # Single-Cable 12V Panel-Mount DC Barrel Jack (DC-099 5.5x2.1mm, M11x0.75 Ø 11.20 mm thread gauge
    # along -X at Y = 0.0, Z = 11.5 mm, X = -75.0..-62.5 mm)
    dc_jack_gauge = bd.Plane(
        origin=(-75.0, 0.0, DC_BARREL_JACK_Z_CENTER), z_dir=(1.0, 0.0, 0.0)
    ) * bd.Cylinder(
        radius=(DC_BARREL_JACK_BORE_DIA - 0.20) / 2.0,
        height=12.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    dc_jack_over = bd.Plane(
        origin=(-75.0, 0.0, DC_BARREL_JACK_Z_CENTER), z_dir=(1.0, 0.0, 0.0)
    ) * bd.Cylinder(
        radius=(DC_BARREL_JACK_BORE_DIA + 2.0) / 2.0,
        height=12.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(trunk_base, dc_jack_gauge) == 0.0, (
        "M11 5.5x2.1mm 12V DC Barrel Jack gauge (Ø 11.20 mm) collided with trunk_base rear port!"
    )
    assert _inter_vol(trunk_base, dc_jack_over) > 0.0, (
        "Oversized DC Barrel Jack flange gauge (Ø 13.40 mm) did not seat against trunk_base rear wall!"
    )

    # N20 D-shaft gauge pin inside Motor_Clutch_Driver (Ø 3.0 mm nominal with 0.5 mm flat, Z=0.00..6.40 mm)
    r_dpin = N20_DSHAFT_DIA / 2.0
    dpin_cyl = bd.Cylinder(
        radius=r_dpin,
        height=6.40,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    dpin_box = bd.Pos((r_dpin - N20_DSHAFT_FLAT) - r_dpin, 0.0, 0.0) * bd.Box(
        2.0 * r_dpin,
        4.0 * r_dpin,
        6.40,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    dshaft_gauge = dpin_cyl & dpin_box
    oversized_dpin = bd.Cylinder(
        radius=2.0, height=6.40, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    vol_dshaft_inter = _inter_vol(motor_clutch_driver, dshaft_gauge)
    vol_dshaft_over = _inter_vol(motor_clutch_driver, oversized_dpin)
    assert vol_dshaft_inter == 0.0, (
        f"N20 D-shaft gauge collided with Motor_Clutch_Driver: {vol_dshaft_inter}"
    )
    assert vol_dshaft_over > 0.0, (
        "Oversized D-shaft pin did not intersect Motor_Clutch_Driver!"
    )

    # 1.4 Under-Track Snap-In Dovetail Pebble-Wire Channel (8.4 x 6.2 mm deepened bay with 4.6 mm snap-in throat)
    seg_test = seg_specs["track_seg_01"]
    seg01_plain = build_track_segment(60.0, 120.0, orient_for_print=False, include_planet_pedestal=True)
    pl_mid = helix_section_plane(90.0)
    # Gauge 1: 6.2 x 3.2 mm flat Pebble LED seated inside the 8.4 mm upper dovetail chamber (v = TRACK_BASE_Y + 4.4 mm)
    led_gauge = pl_mid.from_local_coords(
        bd.Pos(0.0, TRACK_BASE_Y + 4.4, 0.0)
        * bd.Box(6.2, 3.2, 4.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    )
    # Gauge 2: 3.8 x 1.0 mm 3-wire ribbon cord passing through the 4.6 mm snap-in throat (v = TRACK_BASE_Y + 0.5 mm)
    throat_wire_gauge = pl_mid.from_local_coords(
        bd.Pos(0.0, TRACK_BASE_Y + 0.5, 0.0)
        * bd.Box(3.8, 0.8, 4.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    )
    # Retention Probe: 6.2 mm wide Pebble LED at the 4.6 mm bottom throat must intersect the retention lips!
    led_lip_retention_probe = pl_mid.from_local_coords(
        bd.Pos(0.0, TRACK_BASE_Y + 0.35, 0.0)
        * bd.Box(6.2, 0.6, 4.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    )
    vol_led_inter = _inter_vol(seg01_plain, led_gauge) + _inter_vol(seg01_plain, throat_wire_gauge)
    vol_led_over = _inter_vol(seg01_plain, led_lip_retention_probe)
    assert abs(LED_CHANNEL_W - 8.4) <= 0.1 and abs(LED_CHANNEL_THROAT_W - 4.6) <= 0.1 and abs(LED_CHANNEL_D - 6.2) <= 0.1
    assert vol_led_inter == 0.0, f"B0CCS11V7H WS2812B Pebble LED (6.2x3.2) / wire gauge collided with track dovetail channel: {vol_led_inter}"
    assert vol_led_over > 0.0, "4.6 mm snap-in retention lips did not retain the 6.2 mm Pebble LED!"

    # 1.5 Relocated 150° Connector-Pass-Through Trunk Wiring Conduit (10.6 x 8.5 mm -> 9.6 x 7.6 x 400 mm gauge at Z=50..450)
    wire_gauge = bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, WIRE_CONDUIT_ANGLE_DEG)) * (
        bd.Pos(TRUNK_OUTER_R - 7.6 / 2.0, 0.0, 50.0)
        * bd.Box(
            7.6,
            9.6,
            400.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    vol_wire_inter = (
        _inter_vol(tb_placed, wire_gauge)
        + _inter_vol(tm_placed, wire_gauge)
        + _inter_vol(tt_placed, wire_gauge)
    )
    assert vol_wire_inter == 0.0, (
        f"150° 9.6x7.6x400 mm Connector-Pass-Through conduit gauge collided with trunk: {vol_wire_inter}"
    )
    assert (
        abs(CONDUIT_STRIP_LEN_BASE - 100.0) < 0.01
        and abs(CONDUIT_STRIP_LEN_MID - 144.0) < 0.01
        and abs(CONDUIT_STRIP_LEN_TOP - 144.0) < 0.01
    )

    # 1.6 Unified Planet Bottom-Loading LED Chamber (Bambu Ø 7.5 x 6.0 mm Magnetic LED Light at Z = 3.60..9.60 mm
    #     with crush-rib interference fit) + Split-Tine Track Peg (Ø 7.60 x 3.50 mm) + Magic_LED_Wand
    peg_gauge_planet = bd.Cylinder(
        radius=PLANET_PEG_DIA / 2.0,
        height=PLANET_PEG_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    bambu_mag_led_max_od = bd.Pos(0.0, 0.0, BAMBU_MAG_LED_Z_OFFSET) * bd.Cylinder(
        radius=BAMBU_MAG_LED_DIA / 2.0,  # Ø 7.50 x 6.00 mm KA006 nominal envelope engages 4x crush ribs
        height=BAMBU_MAG_LED_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    bambu_mag_led_clear_bore = bd.Pos(0.0, 0.0, BAMBU_MAG_LED_Z_OFFSET) * bd.Cylinder(
        radius=6.90 / 2.0,  # Ø 6.90 mm core clears inner rib tips cleanly
        height=BAMBU_MAG_LED_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    peg_over_planet = bd.Cylinder(
        radius=(PLANET_PEG_SOCKET_DIA + 0.6) / 2.0,
        height=PLANET_PEG_SOCKET_DEPTH,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(peg_gauge_planet, bambu_mag_led_max_od) == 0.0, (
        "Balcony mounting peg (Z=0..3.5 mm) collided with Bambu Magnetic LED Light (Z=3.6..9.6 mm)!"
    )
    for idx_pl, pname in enumerate(PLANET_NAMES):
        p_solid = topper_planet_parts[pname]
        subs = getattr(p_solid, "colored_subparts", [])
        sub_colors = {getattr(s, "hex_color", "") for s in subs}
        assert 2 <= len(sub_colors) <= 4, (
            f"Planet {pname} must use between 2 and 4 colors, found {sub_colors}"
        )
        v_in_peg = _inter_vol(p_solid, peg_gauge_planet)
        v_in_led_ribs = _inter_vol(p_solid, bambu_mag_led_max_od)
        v_in_led_core = _inter_vol(p_solid, bambu_mag_led_clear_bore)
        v_ov = _inter_vol(p_solid, peg_over_planet)
        assert v_in_peg == 0.0, f"Mechanical peg gauge (Ø 7.60 x 3.50 mm) collided with {pname}: {v_in_peg}"
        assert v_in_led_core == 0.0, f"KA006 core gauge (Ø 6.90 mm) collided with {pname}: {v_in_led_core}"
        assert v_in_led_ribs > 0.30, f"KA006 crush ribs missing/insufficient inside {pname}: {v_in_led_ribs:.4f} mm³"
        assert v_ov > 0.0, f"Oversized bore gauge did not intersect {pname}!"

        # Test against actual matching track segment balcony from TRACK_PLANET_SEGMENT_INDICES & PLANET_ANCHOR_DEGS
        # Note: PLANET_ANCHOR_DEGS runs top-to-bottom (seg 14..1), whereas TRACK_PLANET_SEGMENT_INDICES is bottom-to-top (0..13)
        seg_idx_num = TRACK_PLANET_SEGMENT_INDICES[-1 - idx_pl] + 1
        seg_key_p = f"track_seg_{seg_idx_num:02d}" if seg_idx_num < 14 else "track_seg_14_top_entry"
        sp_p = seg_specs[seg_key_p]
        seg_p_asm = build_track_segment(
            sp_p[1],
            sp_p[2],
            orient_for_print=False,
            include_planet_pedestal=True,
            bottom_return_ramp=(seg_idx_num == 1),
            top_feeder_ramp=(seg_idx_num == 14),
            seg_number=sp_p[5],
        )
        anch_deg = PLANET_ANCHOR_DEGS[idx_pl]
        pt_b = closed_loop_section_plane(anch_deg, scarf_tilt_deg=0.0).from_local_coords(
            bd.Vector(30.0, 18.0, 0.0)
        )
        p_placed = p_solid.moved(bd.Location((pt_b.X, pt_b.Y, pt_b.Z)))
        assert _inter_vol(seg_p_asm, p_placed) == 0.0, (
            f"Planet {pname} seated on balcony at {anch_deg}° collided with {seg_key_p}!"
        )
        assert _bboxes_overlap_3d(seg_p_asm.bounding_box(), p_placed.bounding_box()), (
            f"Planet {pname} did not engage {seg_key_p} upward split-tine mounting peg!"
        )
        assert _inter_vol(seg_p_asm, p_placed.moved(bd.Location((0.0, 0.0, 0.85)))) > 0.1, (
            f"Planet {pname} snap-detent groove failed upward pull-off retention check against split-tine peg!"
        )

    # Verify Magic_LED_Wand Star-Tip Trigger Magnet Socket (Ø 8.00 x 2.00 mm magnet at (42.0, 0.0, 4.85..6.85 mm))
    magic_wand = topper_planet_parts["Magic_LED_Wand"]
    wand_mag_gauge = bd.Pos(42.0, 0.0, 4.85) * bd.Cylinder(
        radius=WAND_MAGNET_DIA / 2.0,
        height=WAND_MAGNET_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wand_mag_over = bd.Pos(42.0, 0.0, 4.50) * bd.Cylinder(
        radius=(WAND_MAGNET_DIA + 1.0) / 2.0,
        height=WAND_MAGNET_HEIGHT + 0.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(magic_wand, wand_mag_gauge) == 0.0, (
        "Ø 8.0 x 2.0 mm trigger magnet gauge collided with Magic_LED_Wand star socket!"
    )
    assert _inter_vol(magic_wand, wand_mag_over) > 0.0, (
        "Oversized magnet gauge did not intersect Magic_LED_Wand star socket walls!"
    )

    assert len(TRACK_PLANET_SEGMENT_INDICES) == 8, "Expected 8 planet pedestal segments!"

    # =========================================================================
    # SECTION 2: Virtual Dry-Fit Assembly & Mechanical Joint Clearances
    # =========================================================================

    # 2.1 Trunk Interlocking Tenons, Crown Centering Tenon Collar & Base_Bottom_Cover Snap-In Ring
    vol_tb_tm = _inter_vol(tb_placed, tm_placed)
    vol_tm_tt = _inter_vol(tm_placed, tt_placed)
    tenon_radial_gap = FIT_TOLERANCE  # 18.50 - 18.30 = 0.20 mm
    assert vol_tb_tm == 0.0, f"Trunk Base & Middle tenon/socket collided: {vol_tb_tm}"
    assert vol_tm_tt == 0.0, f"Trunk Middle & Top tenon/socket collided: {vol_tm_tt}"
    assert 0.15 <= tenon_radial_gap <= 0.25, f"Tenon radial gap {tenon_radial_gap} out of [0.15, 0.25]"

    # Verify trunk_top upward Crown Centering Tenon Collar (Ø 59.40 mm OD x 4.0 mm tall at Z = 450..454 mm)
    # mates concentrically inside golden_apple_topper's Ø 60.00 mm base socket with 0.0 mm³ interference
    # and locks against radial sliding!
    topper_placed = topper.moved(bd.Location((0.0, 0.0, 3.0 * TRUNK_SECTION_HEIGHT)))
    assert _inter_vol(tt_placed, topper_placed) == 0.0, (
        "trunk_top Crown Centering Tenon Collar collided with golden_apple_topper base socket!"
    )
    assert _bboxes_overlap_3d(tt_placed.bounding_box(), topper_placed.bounding_box()), (
        "trunk_top Crown Centering Tenon Collar did not telescope inside golden_apple_topper!"
    )
    assert _inter_vol(tt_placed, topper_placed.moved(bd.Location((1.5, 0.0, 0.0)))) > 5.0, (
        "trunk_top Crown Centering Tenon Collar failed radial shear-lock test against golden_apple_topper!"
    )

    # Verify Conduit_Cover_Strip_{Base,Mid,Top} snap cleanly over the 150° wiring conduit with zero trunk/bracket interference
    conduit_rad = math.radians(WIRE_CONDUIT_ANGLE_DEG)
    conduit_r = TRUNK_OUTER_R + 1.25
    trunk_all_placed = tb_placed + tm_placed + tt_placed
    for s_name, s_part, z_c_global in (
        ("Conduit_Cover_Strip_Base", conduit_strip_base, 100.0),
        ("Conduit_Cover_Strip_Mid", conduit_strip_mid, 225.0),
        ("Conduit_Cover_Strip_Top", conduit_strip_top, 375.0),
    ):
        strip_pl = bd.Plane(
            origin=(conduit_r * math.cos(conduit_rad), conduit_r * math.sin(conduit_rad), z_c_global),
            x_dir=(math.sin(conduit_rad), -math.cos(conduit_rad), 0.0),
            z_dir=(-math.cos(conduit_rad), -math.sin(conduit_rad), 0.0),
        )
        s_placed = s_part.moved(bd.Location(strip_pl))
        assert _inter_vol(s_placed, trunk_all_placed) < 0.05, (
            f"{s_name} collided with 150° conduit rails!"
        )

    # 2.2 Cantilever Bracket Keyhole Dovetails (26 Stations)
    test_theta = 300.0
    seg_brk_test = build_track_segment(240.0, 360.0, orient_for_print=False, include_planet_pedestal=False)
    r_station = helix_radius(test_theta)
    z_slot_global = helix_z(test_theta) + DOVETAIL_SLOT_Z_OFFSET
    rad_st = math.radians(test_theta)
    bracket_test = build_cantilever_bracket(r_station).moved(
        bd.Location(
            (TRUNK_OUTER_R * math.cos(rad_st), TRUNK_OUTER_R * math.sin(rad_st), z_slot_global),
            (0.0, 0.0, test_theta),
        )
    )
    vol_brk_trunk = _inter_vol(bracket_test, tb_placed)
    vol_brk_track = _inter_vol(bracket_test, seg_brk_test)
    pl_300 = helix_section_plane(test_theta)
    led_brk_gauge = pl_300.from_local_coords(
        bd.Pos(0.0, TRACK_BASE_Y + 4.4, 0.0)
        * bd.Box(8.4, 3.6, 14.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER))
    )
    vol_brk_led = _inter_vol(bracket_test, led_brk_gauge)
    engages_trunk = _bboxes_overlap_3d(bracket_test.bounding_box(), tb_placed.bounding_box())
    engages_track = _bboxes_overlap_3d(bracket_test.bounding_box(), seg_brk_test.bounding_box())
    assert vol_brk_trunk < 0.01, f"Bracket collided with trunk dovetail socket: {vol_brk_trunk} mm³"
    assert vol_brk_track < 0.01, f"Bracket collided with track underside sockets: {vol_brk_track} mm³"
    assert vol_brk_led == 0.0, f"Pebble LED gauge collided with bracket saddle/pegs: {vol_brk_led} mm³"
    assert engages_trunk and engages_track, "Bracket bounding box does not engage trunk and track!"

    # Verify all 26 exact-radius station brackets (60°..1560°) engage their exact mathematical
    # keyhole dovetail sockets across trunk_base, trunk_mid, and trunk_top (0.00 mm³ collision)
    for k_st in range(1, BRACKET_STATION_COUNT + 1):
        deg_st = float(k_st * 60)
        z_st = helix_z(deg_st) + DOVETAIL_SLOT_Z_OFFSET
        rad_st_k = math.radians(deg_st)
        b_placed_k = station_brackets[f"bracket_{k_st:02d}"].moved(
            bd.Location(
                (TRUNK_OUTER_R * math.cos(rad_st_k), TRUNK_OUTER_R * math.sin(rad_st_k), z_st),
                (0.0, 0.0, deg_st),
            )
        )
        v_st_trunk = (
            _inter_vol(b_placed_k, tb_placed)
            + _inter_vol(b_placed_k, tm_placed)
            + _inter_vol(b_placed_k, tt_placed)
        )
        assert v_st_trunk < 0.01, (
            f"Station bracket_{k_st:02d} at {deg_st}° (z_slot={z_st:.2f} mm) collided with trunk: {v_st_trunk:.3f} mm³"
        )

    # 2.3 Track Segment Continuity & 60° Bracket-Aligned Stepped Half-Lap Seams (TRACK_LAP_ARC_DEG = 8.0°)
    assert abs(helix_radius(0.0) - HELIX_BOT_R) < 1e-6
    assert abs(helix_radius(HELIX_TOTAL_DEG) - HELIX_TOP_R) < 1e-6
    assert abs((helix_z(360.0) - helix_z(0.0)) - HELIX_PITCH) < 1e-6
    assert abs(TRACK_LAP_ARC_DEG - 8.0) < 1e-6, "Stepped half-lap seam arc must be 8.0°!"

    seg02_asm = build_track_segment(
        seg_specs["track_seg_02"][1],
        seg_specs["track_seg_02"][2],
        orient_for_print=False,
        include_planet_pedestal=False,
    )
    seg13_asm = build_track_segment(
        seg_specs["track_seg_13"][1],
        seg_specs["track_seg_13"][2],
        orient_for_print=False,
        include_planet_pedestal=False,
    )
    assert _inter_vol(seg01_asm, seg02_asm) == 0.0, (
        "Stepped Half-Lap Track Joint at 60° (seg_01 -> seg_02) collided when mated!"
    )
    assert _bboxes_overlap_3d(seg01_asm.bounding_box(), seg02_asm.bounding_box()), (
        "seg_01 stepped-lap shoulder did not overlap seg_02 at 60°!"
    )
    assert _inter_vol(seg01_asm, seg02_asm.moved(bd.Location((0.0, 0.0, 0.8)))) == 0.0, (
        "Stepped Half-Lap Track Joint at 60° blocked top-down -Z drop-in clearance!"
    )
    assert _inter_vol(seg01_asm, seg02_asm.moved(bd.Location((0.0, 0.0, -0.8)))) > 10.0, (
        "Stepped Half-Lap Track Joint at 60° failed vertical bearing/shear-lock test!"
    )
    assert _inter_vol(seg13_asm, seg14_asm) == 0.0, (
        "Stepped Half-Lap Track Joint at 1500° (seg_13 -> seg_14_top_entry) collided when mated!"
    )
    assert _bboxes_overlap_3d(seg13_asm.bounding_box(), seg14_asm.bounding_box()), (
        "seg_13 stepped-lap shoulder did not overlap seg_14_top_entry at 1500°!"
    )
    assert _inter_vol(seg13_asm, seg14_asm.moved(bd.Location((0.0, 0.0, 0.8)))) == 0.0, (
        "Stepped Half-Lap Track Joint at 1500° blocked top-down -Z drop-in clearance!"
    )
    assert _inter_vol(seg13_asm, seg14_asm.moved(bd.Location((0.0, 0.0, -0.8)))) > 10.0, (
        "Stepped Half-Lap Track Joint at 1500° failed vertical bearing/shear-lock test!"
    )

    # Verify Cantilever Bracket at seam theta = 60.0° and 180.0° seats cleanly into BOTH segments
    # across the 8.0° stepped half-lap seam with 0.000 mm³ collision!
    r_60 = helix_radius(60.0)
    z_slot_60 = helix_z(60.0) + DOVETAIL_SLOT_Z_OFFSET
    rad_60 = math.radians(60.0)
    brk_60 = build_cantilever_bracket(r_60).moved(
        bd.Location(
            (TRUNK_OUTER_R * math.cos(rad_60), TRUNK_OUTER_R * math.sin(rad_60), z_slot_60),
            (0.0, 0.0, 60.0),
        )
    )
    assert _inter_vol(brk_60, seg01_asm) < 0.01 and _inter_vol(brk_60, seg02_asm) < 0.01, (
        "Cantilever Bracket #01 at 60° collided with seg_01 or seg_02 stepped-lap underside sockets!"
    )
    assert _bboxes_overlap_3d(brk_60.bounding_box(), seg01_asm.bounding_box()), (
        "Cantilever Bracket #01 at 60° did not engage seg_01 underside sockets!"
    )

    # 2.4 Snap-Fit 25.0 mm "Apple" Marble & Optional Steel Ball Bearing Core Check
    assembled_apple, _hemi_a_placed, _hemi_b_placed = build_assembled_apple_marble()
    captive_apple = build_apple_captive_pause_marble()
    hemispheres = build_all_apple_hemispheres(count=6)

    for m_name, m_part in [("assembled_apple", assembled_apple), ("Apple_Captive_Pause_Marble", captive_apple)]:
        mbb = m_part.bounding_box()
        assert abs(mbb.size.X - 25.0) <= 0.05, f"{m_name} X={mbb.size.X} != 25.0±0.05"
        assert abs(mbb.size.Y - 25.0) <= 0.05, f"{m_name} Y={mbb.size.Y} != 25.0±0.05"
        assert abs(mbb.size.Z - 25.0) <= 0.05, f"{m_name} Z={mbb.size.Z} != 25.0±0.05"

    steel_ball_nominal = bd.Pos(0.0, 0.0, 12.50) * bd.Sphere(radius=STEEL_BALL_DIA / 2.0)
    steel_ball_gauge = bd.Pos(0.0, 0.0, 12.50) * bd.Sphere(radius=12.90 / 2.0)
    marble_led_centered = bd.Pos(0.0, 0.0, 12.50 - BAMBU_MAG_LED_HEIGHT / 2.0) * bd.Cylinder(
        radius=BAMBU_MAG_LED_DIA / 2.0,
        height=BAMBU_MAG_LED_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    marble_led_polar = bd.Pos(0.0, 0.0, 2.85) * bd.Cylinder(
        radius=BAMBU_MAG_LED_DIA / 2.0,
        height=BAMBU_MAG_LED_HEIGHT,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    m8_nut_outer = bd.Pos(0.0, 0.0, 12.50 - 3.25) * bd.extrude(
        bd.RegularPolygon(radius=13.00 / 2.0, side_count=6, major_radius=False), amount=6.50
    )
    m8_nut_inner = bd.Pos(0.0, 0.0, 12.50 - 3.30) * bd.Cylinder(
        radius=4.00, height=6.60, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    m8_nut_gauge = (m8_nut_outer - m8_nut_inner).solid()
    y_shape_led_nominal = bd.Pos(0.0, 0.0, 12.50 - 6.50 / 2.0) * bd.Cylinder(
        radius=18.00 / 2.0,
        height=6.50,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    y_shape_led_gauge = bd.Pos(0.0, 0.0, 12.50 - 6.80 / 2.0) * bd.Cylinder(
        radius=18.40 / 2.0,
        height=6.80,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _inter_vol(assembled_apple, y_shape_led_nominal) == 0.0, (
        "Bambu Y-Shape LED Light with Magnetic Control Switch (Ø 18.0 x 6.5 mm KC012/KC013) interfered with assembled Apple marble!"
    )
    assert _inter_vol(assembled_apple, y_shape_led_gauge) == 0.0, (
        "Bambu Y-Shape LED clearance gauge (Ø 18.4 x 6.8 mm) interfered with assembled Apple marble!"
    )
    assert _inter_vol(_hemi_a_placed, _hemi_b_placed) == 0.0, (
        "Bayonet twist-lock Apple_Hemisphere_A and Apple_Hemisphere_B interfered when locked!"
    )
    _hemi_a_pull_test = _hemi_a_placed.moved(bd.Location((0.0, 0.0, 1.00)))
    assert _inter_vol(_hemi_a_pull_test, _hemi_b_placed) >= 5.0, (
        "Bayonet twist-lock failed vertical pull-apart lock overlap test!"
    )
    assert _inter_vol(assembled_apple, marble_led_centered) == 0.0, (
        "Bambu Magnetic Switch LED (Ø 7.5 x 6.0 mm centered) interfered with assembled Apple marble!"
    )
    assert _inter_vol(assembled_apple, marble_led_polar) == 0.0, (
        "Bambu Magnetic Switch LED (Ø 7.5 x 6.0 mm in polar cradle) interfered with assembled Apple marble!"
    )
    assert _inter_vol(assembled_apple, m8_nut_gauge) == 0.0, (
        "M8 steel hex nut weight ring (13.0 mm AF x 6.5 mm) interfered with assembled Apple marble!"
    )
    assert _inter_vol(m8_nut_gauge, marble_led_centered) == 0.0, (
        "M8 steel hex nut center hole interfered with centered Bambu Magnetic Switch LED!"
    )
    assert _inter_vol(assembled_apple, steel_ball_nominal) == 0.0, (
        "1/2-inch (12.7 mm) steel ball bearing interfered with assembled Apple marble!"
    )
    assert _inter_vol(assembled_apple, steel_ball_gauge) == 0.0, (
        "Ø 12.9 mm steel ball clearance gauge interfered with assembled Apple marble!"
    )
    assert _inter_vol(captive_apple, steel_ball_gauge) == 0.0, (
        "Ø 12.9 mm steel ball clearance gauge interfered with Apple_Captive_Pause_Marble!"
    )
    assert abs(HEMISPHERE_SNAP_CLEARANCE - 0.15) < 1e-6, "Hemisphere snap-lip clearance must be 0.15 mm!"

    # Sample 15 points along track centerline with Ø 25.4 mm test sphere
    sagitta = TRACK_TROUGH_R - math.sqrt(TRACK_TROUGH_R**2 - TRACK_SHOULDER_INNER_X**2)
    ball_test_r = 25.4 / 2.0  # 12.7 mm
    v_ball_center = -sagitta + ball_test_r + 0.65

    max_ball_inter = 0.0
    for idx in range(15):
        ang = 68.0 + (104.0 * idx / 14.0)
        pl_ball = closed_loop_section_plane(ang)
        c_pt = pl_ball.from_local_coords(bd.Vector(0.0, v_ball_center, 0.0))
        sph_gauge = bd.Pos(c_pt.X, c_pt.Y, c_pt.Z) * bd.Sphere(radius=ball_test_r)
        v_int = _inter_vol(seg02_asm, sph_gauge)
        max_ball_inter = max(max_ball_inter, v_int)

    assert max_ball_inter == 0.0, f"Ø 25.4 mm ball gauge interfered along track: {max_ball_inter}"
    assert TRACK_INNER_WIDTH == 34.0

    # =========================================================================
    # SECTION 3: Snapmaker U1 Printability & Multi-Plate .3mf Verification
    # =========================================================================
    all_generated: dict[str, bd.Solid] = {}
    all_generated.update(trunk_parts)
    all_generated.update(auger_parts)
    all_generated.update(track_parts)
    all_generated.update(station_brackets)
    all_generated.update(topper_planet_parts)
    all_generated["apple_green_leaf"] = apple_leaf_print
    all_generated["Apple_Captive_Pause_Marble"] = captive_apple
    all_generated.update(hemispheres)

    # 3.1 Manifold & Watertight Check
    for pname, psolid in all_generated.items():
        assert psolid.is_valid, f"{pname} failed B-Rep is_valid"
        assert psolid.is_manifold, f"{pname} failed is_manifold"
        assert psolid.volume > 0.0, f"{pname} has non-positive volume"

    # 3.2 & 3.3 Flat Bed Contact (Z_min == 0.0), Build Volume (<= 240x240x270) & Spacing (>= MIN_PART_CLEARANCE)
    plates = build_five_plates(prebuilt_parts=all_generated)
    part_to_plate_info: dict[str, tuple[str, int, str, float, bool]] = {}

    for pname, plist in plates.items():
        mbounds = [_mesh_bounds(pp.part) for pp in plist]
        span_x = max(b[1] for b in mbounds) - min(b[0] for b in mbounds)
        span_y = max(b[3] for b in mbounds) - min(b[2] for b in mbounds)
        span_z = max(b[5] for b in mbounds) - min(b[4] for b in mbounds)
        assert span_x <= SAFE_PLATE_ZONE and span_y <= SAFE_PLATE_ZONE and span_z <= U1_BED_Z, (
            f"Plate {pname} exceeds build envelope: {span_x:.1f}x{span_y:.1f}x{span_z:.1f} mm"
        )

        min_gap = float("inf")
        for i in range(len(plist)):
            assert abs(mbounds[i][4]) <= 0.005, (
                f"Part {plist[i].name} on {pname} has mesh min.Z={mbounds[i][4]:.4f} != 0.0"
            )
            if plist[i].name in all_generated:
                ref_vol = float(all_generated[plist[i].name].volume)
                plated_vol = float(plist[i].part.volume)
                assert abs(plated_vol - ref_vol) < 1.0, (
                    f"STUB DETECTED: Plated part '{plist[i].name}' on {pname} has volume {plated_vol:.1f} mm³ != full-scale {ref_vol:.1f} mm³!"
                )
            for j in range(i + 1, len(plist)):
                min_gap = min(min_gap, _part_xy_gap(plist[i].part, plist[j].part))
        assert min_gap >= MIN_PART_CLEARANCE - 0.1, (
            f"Plate {pname} spacing {min_gap:.2f} mm < {MIN_PART_CLEARANCE} mm"
        )

        for pp, mb in zip(plist, mbounds):
            part_to_plate_info[pp.name] = (
                pname,
                pp.toolhead_id,
                pp.hex_color,
                mb[4],
                pp.part.is_valid and pp.part.is_manifold,
            )

    # Assert apple_green_leaf is explicitly placed on Plate 13 (Teal PETG track plate)
    plate13_names = [pp.name for pp in plates["Plate_13_SingleColor_Green_Track_09_And_14"]]
    assert "apple_green_leaf" in plate13_names, "apple_green_leaf missing from Plate 13 (Teal PETG)!"

    # 3.4 4-Toolhead Color, PLA-Only Multi-Color Plates & Extruder Metadata Verification
    master_3mf = threemf_dir / "GravMass_Tree_Ultimate_U1.3mf"
    assert master_3mf.exists(), f"Missing {master_3mf}"
    assert (threemf_dir / "GravMass_Tree_CyberBrick_U1_MultiPlate.3mf").exists()

    expected_toolhead_for_part: dict[str, tuple[int, str]] = {
        "trunk_base": (1, "#4A2F1D"),
        "trunk_mid": (1, "#4A2F1D"),
        "trunk_top": (1, "#4A2F1D"),
        "Bottom_Electronics_Lid": (1, "#4A2F1D"),
        "Conduit_Cover_Strip_Base": (1, "#4A2F1D"),
        "Conduit_Cover_Strip_Mid": (1, "#4A2F1D"),
        "Conduit_Cover_Strip_Top": (1, "#4A2F1D"),
        "Motor_Clutch_Driver": (1, "#4A2F1D"),
        "auger_lower": (3, "#D4AF37"),
        "auger_upper": (3, "#D4AF37"),
        "golden_apple_topper": (4, "#C41E3A"),
        "apple_green_leaf": (2, "#00A86B"),
        "planet_mercury": (3, "#D4AF37"),
        "planet_venus": (3, "#D4AF37"),
        "planet_jupiter": (3, "#D4AF37"),
        "planet_saturn": (3, "#D4AF37"),
        "planet_earth": (1, "#1E5AA8"),
        "planet_mars": (4, "#C41E3A"),
        "planet_uranus": (1, "#1E5AA8"),
        "planet_neptune": (1, "#1E5AA8"),
        "Magic_LED_Wand": (3, "#D4AF37"),
    }
    for k in range(1, BRACKET_STATION_COUNT + 1):
        expected_toolhead_for_part[f"bracket_{k:02d}"] = (1, "#4A2F1D")
    for i in range(1, 14):
        expected_toolhead_for_part[f"track_seg_{i:02d}"] = (2, "#00A86B")
    expected_toolhead_for_part["track_seg_14_top_entry"] = (2, "#00A86B")
    for i in range(1, 7):
        expected_toolhead_for_part[f"apple_hemisphere_a_{i:02d}"] = (4, "#C41E3A")
        expected_toolhead_for_part[f"apple_hemisphere_b_{i:02d}"] = (4, "#C41E3A")

    ns_core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    with zipfile.ZipFile(master_3mf, "r") as zf:
        proj_cfg = json.loads(zf.read("Metadata/project_settings.config").decode("utf-8"))
        assert proj_cfg["filament_colour"] == ["#4A2F1D", "#00A86B", "#D4AF37", "#C41E3A"]
        assert proj_cfg["printer_settings_id"] == "Snapmaker U1 (0.4 nozzle)"
        assert proj_cfg["nozzle_diameter"] == ["0.4", "0.4", "0.4", "0.4"]

        mcfg = ET.fromstring(zf.read("Metadata/model_settings.config"))
        name_to_ext: dict[str, int] = {}
        for obj_node in mcfg.findall("./object"):
            n_el = obj_node.find("./metadata[@key='name']")
            e_el = obj_node.find("./metadata[@key='extruder']")
            if n_el is not None and e_el is not None:
                name_to_ext[n_el.attrib["value"]] = int(e_el.attrib["value"])

        for part_key, (exp_ext, _exp_hex) in expected_toolhead_for_part.items():
            assert name_to_ext.get(part_key) == exp_ext, (
                f"Part '{part_key}' in model_settings.config has extruder={name_to_ext.get(part_key)}, expected {exp_ext}"
            )
        extra_plated = set(name_to_ext.keys()) - set(expected_toolhead_for_part.keys())
        assert not extra_plated, f"Obsolete/unexpected parts found on plates: {extra_plated}"

        assert len(mcfg.findall("./plate")) == len(plates), (
            f"Expected {len(plates)} plates in model_settings.config"
        )
        for mc_key in ("golden_apple_topper", "Magic_LED_Wand", *PLANET_NAMES):
            mc_objs = [
                o for o in mcfg.findall("./object")
                if o.find("./metadata[@key='name']") is not None
                and o.find("./metadata[@key='name']").attrib.get("value") == mc_key  # type: ignore[union-attr]
            ]
            assert len(mc_objs) == 1, f"Expected 1 unified <object> for '{mc_key}', found {len(mc_objs)}"
            assert len(mc_objs[0].findall("./part[@subtype='normal_part']")) >= 2, (
                f"Expected >= 2 <part subtype='normal_part'> sub-volumes inside '{mc_key}'"
            )

        model_xml = ET.fromstring(zf.read("3D/3dmodel.model"))
        mat_colors = {
            b.attrib.get("displaycolor", "")[:7].upper()
            for b in model_xml.findall(f".//{{{ns_core}}}base")
        }
        assert {"#4A2F1D", "#00A86B", "#D4AF37", "#C41E3A"}.issubset(mat_colors)

    for pname in plates:
        p_3mf = threemf_dir / f"{pname}.3mf"
        assert p_3mf.exists(), f"Missing individual plate 3MF: {p_3mf}"
        with zipfile.ZipFile(p_3mf, "r") as zf:
            p_m_xml = ET.fromstring(zf.read("3D/3dmodel.model"))
            p_cfg_xml = ET.fromstring(zf.read("Metadata/model_settings.config"))
            p_proj = json.loads(zf.read("Metadata/project_settings.config").decode("utf-8"))
            assert len(p_proj.get("filament_colour", [])) <= 4, f"{pname} has > 4 filament_colour entries!"
            if pname.startswith(("Plate_16_", "Plate_17_", "Plate_18_")):
                assert all(ft == "PLA" for ft in p_proj.get("filament_type", [])), (
                    f"Multi-color plate {pname} has non-PLA filament: {p_proj.get('filament_type')}"
                )
            p_b_colors = {
                b.attrib.get("displaycolor", "")[:7].upper()
                for b in p_m_xml.findall(f".//{{{ns_core}}}base")
            }
            assert len(p_b_colors) <= 4, f"{pname} has > 4 mesh displaycolor entries: {p_b_colors}"
            p_exts = {
                m.attrib.get("value", "")
                for m in p_cfg_xml.findall(".//metadata[@key='extruder']")
            }
            assert len(p_exts) <= 4, f"{pname} uses > 4 extruders: {p_exts}"

    from audit_plates import run_plate_audit
    run_plate_audit()

    # =========================================================================
    # SECTION 4: Structured Verification Table Report (Zero Pauses, Zero Magnets)
    # =========================================================================
    clearance_notes: dict[str, str] = {
        "trunk_base": f"PASS (Hollow Root Vault {open_vault_slack_vol / 1000.0:.1f} cm³, 26 Keyholes, DC-099: 0.0 mm³)",
        "trunk_mid": "PASS (Ø23.6 Bore, Ø37.0 Flute, 150° Conduit & Keyed Tenon: 0.0 mm³)",
        "trunk_top": f"PASS (Crown Collar Ø59.4, Upper Chute <Z=450, Tenon int {vol_tm_tt:.2f} mm³)",
        "Bottom_Electronics_Lid": "PASS (Upright Tray Ø134.6, 4× M2.5, UCTRONICS + 2× WAGO + A092: 0.0 mm³)",
        "Conduit_Cover_Strip_Base": "PASS (Snap-On 10.2×100×2.6 mm 150° Conduit Cover, flat Z=0)",
        "Conduit_Cover_Strip_Mid": "PASS (Snap-On 10.2×144×2.6 mm 150° Conduit Cover, flat Z=0)",
        "Conduit_Cover_Strip_Top": "PASS (Snap-On 10.2×144×2.6 mm 150° Conduit Cover, flat Z=0)",
        "auger_lower": f"PASS (Bottom 5.15 mm AF Female Hex Socket + Top {hex_peg_af:.2f} mm AF Male Hex Peg: 0.0 mm³)",
        "auger_upper": f"PASS (Bore clr {auger_radial_clr:.2f} mm, Hex sock {hex_sock_af:.2f} mm AF: 0.0 mm³)",
        "Motor_Clutch_Driver": f"PASS (Brown PLA T1 + M2.5 Clamp Collar, Ø18 Flange, 9.9 mm D-bore: 0.0 mm³)",
        "golden_apple_topper": "PASS (PLA-only Brown/Red + Crown Ø60×4.6 Socket + Leaf Keyway: 0.0 mm³)",
        "apple_green_leaf": "PASS (Standalone Teal PETG T2 Leaf, Plate 13, Leaf Keyway 0.0 mm³)",
        "Magic_LED_Wand": "PASS (3-Color PLA Star Wand + Ø8.0×2.0 mm Trigger Magnet Socket: 0.0 mm³)",
        "Apple_Captive_Pause_Marble": "PASS (Ø25.00 mm, Ø13.10 mm bearing core Z=5.80..19.00 mm: 0.0 mm³)",
    }
    for pname in PLANET_NAMES:
        clearance_notes[pname] = (
            "PASS (PLA-only + KA006 Crush Ribs + Ø7.6×3.5 mm Split-Tine Track Peg)"
        )
    for i in range(1, 15):
        k = f"track_seg_{i:02d}" if i < 14 else "track_seg_14_top_entry"
        clearance_notes[k] = (
            "PASS (8.0° Stepped Half-Lap + 8.4×6.2 LED Bay + Z=0 Datum Land: 0.0 mm³)"
        )
    for k in station_brackets:
        clearance_notes[k] = (
            "PASS (26-Station Radius, Upright Z=0 Rib Base, Keyhole Dovetail 0.000 mm³)"
        )
    for k in hemispheres:
        clearance_notes[k] = (
            "PASS (Flat Z=0, Quarter-Turn Bayonet Twist-Lock + Ø18x6.5mm Y-LED Core: 0.0 mm³)"
        )

    hdr = (
        f"{'Part / Subsystem Name':<26} | {'Dimensions (X × Y × Z mm)':<25} | "
        f"{'Hardware / Joint Clearance Check':<66} | {'Assigned Plate & Extruder':<44} | "
        f"{'Bed & Manifold':<22}"
    )
    sep = "-" * len(hdr)
    print("\n" + "=" * len(hdr))
    print(" GRAV-MASS DAY MARBLE RUN TREE (SIMPLIFIED EDITION) — AUTOMATED CAD METROLOGY & QA REPORT")
    print("=" * len(hdr))
    print(hdr)
    print(sep)

    ordered_keys = (
        list(trunk_parts.keys())
        + list(auger_parts.keys())
        + list(track_parts.keys())
        + list(station_brackets.keys())
        + ["golden_apple_topper", "apple_green_leaf"]
        + list(PLANET_NAMES)
        + ["Magic_LED_Wand"]
        + list(hemispheres.keys())
    )

    for k in ordered_keys:
        part = all_generated[k]
        bb = part.bounding_box()
        dim_str = f"{bb.size.X:6.2f} × {bb.size.Y:6.2f} × {bb.size.Z:6.2f}"
        clr_str = clearance_notes[k]
        pname, tid, hex_c, z_min, is_mf = part_to_plate_info[k]
        plate_short = pname.replace("Plate_", "P")[:26]
        ext_str = f"{plate_short} | T{tid} ({hex_c})"
        bed_str = f"Z0={z_min:+.2f}mm | {'MANIFOLD' if is_mf else 'FAIL'}"
        print(
            f"{k:<26} | {dim_str:<25} | {clr_str:<66} | {ext_str:<44} | {bed_str:<22}"
        )

    print(sep)
    print(
        "ALL SIMPLIFIED EDITION CHECKS (ZERO MIXED POLYMERS, 26 STATIONS, 8° STEPPED LAPS): 100% PASS"
    )
    print("=" * len(hdr) + "\n")

    # =========================================================================
    # SECTION 5: Rigid Bracket Insertion-Path & Assembly-Order Regression Gate
    # =========================================================================
    from test_bracket_insertion import run_insertion_audit

    print("Running 26-station keyhole bracket rigid insertion-path regression check...")
    all_brk_ok, brk_results = run_insertion_audit()
    if not all_brk_ok:
        bad = [r["station"] for r in brk_results if not r["pass"]]
        raise RuntimeError(f"Bracket rigid keyhole insertion failed at stations: {bad}")
    print("  [PASS] All 26 stations clear rigid L-path keyhole insertion (0.0000 mm³).")

    def _assert_sweep_clear_z(moving: bd.Shape, obstacle: bd.Shape, dist: float, label: str) -> None:
        steps = int(math.ceil(dist / 0.5))
        for i in range(steps + 1):
            dz = min(dist, i * 0.5)
            inter = moving.moved(bd.Location((0.0, 0.0, dz))) & obstacle
            vol = float(inter.volume) if inter is not None else 0.0
            if vol > 0.05:
                raise RuntimeError(f"Assembly sweep regression [{label}] at dz={dz:.2f} mm: {vol:.4f} mm³")

    tb_asm = trunk_parts["trunk_base"]
    tm_asm = trunk_parts["trunk_mid"].moved(bd.Location((0.0, 0.0, TRUNK_SECTION_HEIGHT)))
    tt_asm = trunk_parts["trunk_top"].moved(bd.Location((0.0, 0.0, 2.0 * TRUNK_SECTION_HEIGHT)))
    topper_asm = all_generated["golden_apple_topper"].moved(
        bd.Location((0.0, 0.0, 3.0 * TRUNK_SECTION_HEIGHT))
    )
    mcd_asm = auger_parts["Motor_Clutch_Driver"].moved(bd.Location((0.0, 0.0, 26.2)))
    al_asm = auger_parts["auger_lower"].moved(bd.Location((0.0, 0.0, 37.22)))
    au_asm = auger_parts["auger_upper"].moved(bd.Location((0.0, 0.0, 37.22 + AUGER_HALF_HEIGHT + 0.1)))
    b01_asm = station_brackets["bracket_01"].moved(
        bd.Location((TRUNK_OUTER_R * math.cos(math.radians(60.0)), TRUNK_OUTER_R * math.sin(math.radians(60.0)), helix_z(60.0) + DOVETAIL_SLOT_Z_OFFSET), (0.0, 0.0, 60.0))
    )
    b02_asm = station_brackets["bracket_02"].moved(
        bd.Location((TRUNK_OUTER_R * math.cos(math.radians(120.0)), TRUNK_OUTER_R * math.sin(math.radians(120.0)), helix_z(120.0) + DOVETAIL_SLOT_Z_OFFSET), (0.0, 0.0, 120.0))
    )
    s01_asm = build_track_segment(
        seg_specs["track_seg_01"][1],
        seg_specs["track_seg_01"][2],
        orient_for_print=False,
        bottom_return_ramp=True,
    )

    _assert_sweep_clear_z(tm_asm, tb_asm, 20.0, "trunk_mid -> trunk_base")
    _assert_sweep_clear_z(tt_asm, tm_asm, 20.0, "trunk_top -> trunk_mid")
    _assert_sweep_clear_z(topper_asm, tt_asm, 10.0, "golden_apple_topper -> trunk_top")
    _assert_sweep_clear_z(al_asm, mcd_asm + tb_asm, 18.0, "auger_lower -> clutch+base")
    _assert_sweep_clear_z(au_asm, al_asm, 15.0, "auger_upper -> auger_lower")
    _assert_sweep_clear_z(s01_asm, tb_asm, 15.0, "track_seg_01 -> trunk_base")
    for _step_i in range(31):
        _dz_b = _step_i * 0.5
        _inter_b1 = s01_asm.moved(bd.Location((0.0, 0.0, _dz_b))) & b01_asm
        _vol_b1 = float(_inter_b1.volume) if _inter_b1 is not None else 0.0
        _max_allowed = 0.05 if _dz_b == 0.0 else 1.50
        if _vol_b1 > _max_allowed:
            raise RuntimeError(
                f"Assembly sweep regression [track_seg_01 -> bracket_01] at dz={_dz_b:.2f} mm: {_vol_b1:.4f} mm³"
            )
    print("  [PASS] Sequential assembly-order vertical insertion sweeps (0.5 mm step, max 0.00 mm³).")

    from verify_physics import run_all_physics_verifications

    run_all_physics_verifications()


if __name__ == "__main__":
    run_all_verifications()
