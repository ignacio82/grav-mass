"""Split-Polymer Test Coupon Plate Generator (cad/test_coupons.py).

Builds two single-polymer fast-printing Snapmaker U1 test plates (zero mixed PLA/PETG):
  - `output/3mf/Test_Coupons_PLA.3mf`  (100% Toolhead 1 Brown PLA):
      * Trunk Keyhole Socket Slice + 4x Keyhole Tenon Pull-Tabs [0.10..0.25]
      * Trunk Keyed Tenon Female Sector + 4x Male Keyed Sector Stubs [0.10..0.25]
      * 4x Split-Tine Track Bracket Plugs [0.10..0.25]
      * Bayonet Marble B Half + 4x Bayonet A Domes [0.10..0.25]
      * 4x Planet KA006 Crush-Rib + Bottom-Peg Bore Caps [0.10..0.25]
      * 1x Magic Wand Ø 8.05 x 2.20 mm Press-Fit Magnet Socket Coupon
  - `output/3mf/Test_Coupons_PETG.3mf` (100% Toolhead 2 Translucent Teal PETG):
      * Stepped Half-Lap 24-deg Track Seam Mating Pair (seg_04<->seg_05 @ 420°)
      * Track Underside Split-Tine Socket Test Block (Ø 4.20 throat / Ø 4.56 pocket)
      * Track Balcony Split-Tine Planet Peg (Ø 7.60 x 3.50 mm, Ø 8.32 lobes)

Every part sits flat at Z = 0.00 mm, packs with >= 8.8 mm XY clearance inside
240 x 240 mm safe print zone, and exports with OrcaSlicer Snapmaker U1 metadata.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import build123d as bd

CAD_DIR = Path(__file__).resolve().parent
ROOT_DIR = CAD_DIR.parent
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))

from common_params import (
    AUGER_BORE_DIA,
    BRACKET_PEG_HEIGHT,
    BRACKET_PEG_SPACING_U,
    DOVETAIL_BASE_W_TOP,
    DOVETAIL_DETENT_Y_HALF,
    DOVETAIL_NECK_W_TOP,
    DOVETAIL_RADIAL_DEPTH,
    DOVETAIL_SLOT_H,
    DOVETAIL_TAPER_W,
    TENON_HEIGHT,
    TENON_KEY_FLAT_DEPTH,
    TENON_NOMINAL_R,
    TOOLHEAD_PALETTE,
    TRUNK_OUTER_R,
    assign_toolhead,
    make_engraved_label_solid,
)
from export_3mf_plates import (
    PlatedPart,
    _add_part_meshes_to_exporter,
    _inject_orca_metadata_into_3mf,
    _mesh_bounds,
    _part_xy_gap,
)
from topper_planets import (
    BAMBU_MAG_LED_DIA,
    BAMBU_MAG_LED_HEIGHT,
    WAND_MAGNET_DIA,
    WAND_MAGNET_HEIGHT,
    _make_exact_25mm_apple_sphere_centered,
    _make_sector_wedge,
    build_apple_hemisphere_b,
)
from track import (
    PLANET_PEG_DIA,
    PLANET_PEG_HEIGHT,
    build_track_segment,
)
from trunk import make_female_dovetail_slot_cutter, make_keyed_female_socket_cutter

CLEARANCES = (0.10, 0.15, 0.20, 0.25)


def _bed_drop_center(part: bd.Solid) -> bd.Solid:
    verts = part.tessellate(0.2)[0]
    min_x = min(v.X for v in verts)
    max_x = max(v.X for v in verts)
    min_y = min(v.Y for v in verts)
    max_y = max(v.Y for v in verts)
    min_z = min(v.Z for v in verts)
    return part.moved(
        bd.Location((-0.5 * (min_x + max_x), -0.5 * (min_y + max_y), -min_z))
    )


def _label_tag(c_mm: float) -> str:
    return f"{int(round(c_mm * 100)):02d}"


# ---------------------------------------------------------------------------
# 1. Trunk Keyhole Socket Slice + 4x Keyhole Tenon Pull-Tabs (c = 0.10..0.25)
# ---------------------------------------------------------------------------
def build_trunk_keyhole_slice_coupon() -> bd.Solid:
    """54 mm tall +/-34 deg curved trunk sector centered on +X with real keyhole socket."""
    r_bore = AUGER_BORE_DIA / 2.0  # 20.5 mm
    r_out = TRUNK_OUTER_R          # 34.0 mm
    h = 54.0
    ring = bd.Cylinder(radius=r_out, height=h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) - bd.Pos(0, 0, -0.5) * bd.Cylinder(radius=r_bore, height=h + 1.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    wedge = _make_sector_wedge(40.0, -1.0, h + 1.0, -34.0, 34.0, n_arc=24)
    sector = (ring & wedge).solid()
    cutter = make_female_dovetail_slot_cutter().locate(bd.Location((r_out, 0.0, 4.0)))
    lbl = bd.Pos(r_out, 0.0, 50.5) * bd.Rot(0, 90, 0) * make_engraved_label_solid("0", char_h=3.4, depth=0.65)
    part = (sector - cutter - lbl).solid()
    return assign_toolhead(_bed_drop_center(part), "Coupon_Keyhole_Trunk_Slice", 1)


def build_keyhole_tenon_stub(c_mm: float) -> bd.Solid:
    """Flat-printed dovetail tenon pull-tab matching the new keyhole at clearance c_mm."""
    # Production dovetail has c = 0.15 radial on walls/base/neck? Wait:
    # socket top: neck_w=7.0, base_w=16.0, depth=4.5, h=18.0 (taper 0.8)
    # At clearance c_mm per side: neck_w = 7.0 - 2*c, base_w = 16.0 - 2*c, depth = 4.5 - c
    # Print flat on Z=0 along X-Y (handle extends +X, tenon extends -X, Z = thickness along Y_slot!)
    #Wait: keep local coords identical to make_male_dovetail_tenon() rotated on its side (-90° around Y?
    # Actually brackets print with Z_local = 0..8mm (slot height becomes tenon extruded flat? No, in brackets.py
    # tenon sits with X in [-4.35..0], Y_width in [-7.7..+7.7], Z in [0..17.75]! Wait: brackets rotate?
    # Wait: in brackets.py make_male_dovetail_tenon prints VERTICAL Z=0..17.75 (or flat rotated? Let's match brackets.py upright Z=0..17.75 extrusion OR flat grip!)
    d_tenon = DOVETAIL_RADIAL_DEPTH - c_mm
    taper = DOVETAIL_TAPER_W / 2.0
    hw_neck_top = DOVETAIL_NECK_W_TOP / 2.0 - c_mm
    hw_base_top = DOVETAIL_BASE_W_TOP / 2.0 - c_mm
    hw_neck_bot = hw_neck_top - taper
    hw_base_bot = hw_base_top - taper
    h = DOVETAIL_SLOT_H - 0.25  # 17.75 mm
    pts_b = [
        (0.2, -hw_neck_bot),
        (-d_tenon, -hw_base_bot),
        (-d_tenon, hw_base_bot),
        (0.2, hw_neck_bot),
        (0.2, -hw_neck_bot),
    ]
    pts_t = [
        (0.2, -hw_neck_top),
        (-d_tenon, -hw_base_top),
        (-d_tenon, hw_base_top),
        (0.2, hw_neck_top),
        (0.2, -hw_neck_top),
    ]
    tenon = bd.Solid.make_loft(
        [
            bd.Wire([bd.Edge.make_line(pts_b[i], pts_b[i + 1]) for i in range(4)]),
            bd.Pos(0, 0, h) * bd.Wire([bd.Edge.make_line(pts_t[i], pts_t[i + 1]) for i in range(4)]),
        ],
        ruled=True,
    )
    # Detent bump if clearance <= 0.15, scaled consistently with c_mm
    det_y = (DOVETAIL_NECK_W_TOP / 2.0) - max(0.03, c_mm * 0.4)
    det = bd.Pos(-0.7, det_y - 0.5, 15.5) * bd.Box(1.8, 1.0, 1.8) + bd.Pos(-0.7, -(det_y - 0.5), 15.5) * bd.Box(1.8, 1.0, 1.8)
    grip = bd.Pos(0.0, -5.0, 0.0) * bd.Box(18.0, 10.0, h, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN))
    lbl = bd.Pos(9.0, 0.0, h) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.6, depth=0.65)
    part = ((tenon + det + grip) - lbl).solid()
    return assign_toolhead(_bed_drop_center(part), f"Coupon_Keyhole_Tenon_c{_label_tag(c_mm)}", 1)


# ---------------------------------------------------------------------------
# 2. Trunk Keyed Tenon Pair Sector (Female Socket + 4x Male Stubs c=0.10..0.25)
# ---------------------------------------------------------------------------
def build_trunk_tenon_female_coupon() -> bd.Solid:
    """Compact +X keyed sector of trunk female socket (R_bore=27.5mm, +X 2mm key flat, H=24mm)."""
    h = 24.0
    cyl_out = bd.Cylinder(radius=TRUNK_OUTER_R, height=h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    wedge = _make_sector_wedge(38.0, -0.5, h + 1.0, -32.0, 32.0, n_arc=24)
    block = (cyl_out & wedge).solid()
    # Bottom bore (AUger ID) + top keyed female socket cutter (z_base=6..21.2 -> wait put socket at top z=8..24!)
    inner_hole = bd.Pos(0, 0, -0.5) * bd.Cylinder(radius=AUGER_BORE_DIA / 2.0, height=h + 1.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    fem = make_keyed_female_socket_cutter(z_base=8.8, height=TENON_HEIGHT)
    part = (block - inner_hole - fem).solid()
    return assign_toolhead(_bed_drop_center(part), "Coupon_Trunk_Socket", 1)


def build_trunk_tenon_male_coupon(c_mm: float) -> bd.Solid:
    """Matching +X keyed male sector stub (H=20mm: 6mm base flange + 14mm tenon) at clearance c_mm."""
    r_male = TENON_NOMINAL_R - c_mm
    x_max = r_male - TENON_KEY_FLAT_DEPTH
    cyl_ten = bd.Cylinder(radius=r_male, height=15.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    key_box = bd.Pos(-20.0, -40.0, -0.5) * bd.Box(20.0 + x_max, 80.0, 16.0, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN))
    wedge = _make_sector_wedge(36.0, -0.5, 22.0, -28.0, 28.0, n_arc=24)
    tenon_arc = cyl_ten & key_box & wedge
    grip_ring = (bd.Pos(0, 0, 15.0) * bd.Cylinder(radius=TRUNK_OUTER_R, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))) & wedge
    bore = bd.Pos(0, 0, -0.5) * bd.Cylinder(radius=AUGER_BORE_DIA / 2.0, height=23.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    lbl = bd.Pos(27.0, 0.0, 21.0) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.4, depth=0.65)
    # Invert so wide flange sits flat at Z=0 and tenon points +Z!
    raw = ((tenon_arc + grip_ring) - bore)
    raw = raw.moved(bd.Location((0, 0, 21.0), (180.0, 0.0, 0.0)))
    lbl_top = bd.Pos(18.0, 0.0, 21.0) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.4, depth=0.65)
    part = (raw - lbl_top).solid()
    return assign_toolhead(_bed_drop_center(part), f"Coupon_Trunk_Tenon_c{_label_tag(c_mm)}", 1)


# ---------------------------------------------------------------------------
# 3. Track Stepped Half-Lap Seam Pair (PETG) + Split-Tine Bracket Socket & Plugs
# ---------------------------------------------------------------------------
def build_track_joint_coupons() -> tuple[list[bd.Solid], list[bd.Solid]]:
    """Return (petg_parts, pla_parts) testing 420° stepped half-lap & split-tine bracket plugs."""
    s_down = build_track_segment(396.0, 420.0, orient_for_print=True, include_planet_pedestal=False, seg_number=4)
    s_up = build_track_segment(420.0, 444.0, orient_for_print=True, include_planet_pedestal=False, seg_number=5)

    def _align_x(s: bd.Solid) -> bd.Solid:
        best_s = s
        best_h = 1e9
        for ang in range(0, 180, 15):
            sr = s.moved(bd.Location((0, 0, 0), (0, 0, float(ang))))
            x0, x1, y0, y1, _, _ = _mesh_bounds(sr)
            if (y1 - y0) < best_h:
                best_h = y1 - y0
                best_s = sr
        return _bed_drop_center(best_s)

    petg_out: list[bd.Solid] = [
        assign_toolhead(_align_x(s_down), "Coupon_SteppedLap_Seg4", 2),
        assign_toolhead(_align_x(s_up), "Coupon_SteppedLap_Seg5", 2),
    ]

    # Track underside split-tine bracket socket block (Ø4.20 throat -> Ø4.56 pocket) in PETG
    fem_blk = bd.Box(38.0, 12.0, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    for u in (-BRACKET_PEG_SPACING_U / 2.0, BRACKET_PEG_SPACING_U / 2.0):
        fem_blk = fem_blk - bd.Pos(u, 0.0, 4.0) * bd.Cone(
            bottom_radius=2.35, top_radius=2.10, height=0.80,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        fem_blk = fem_blk - bd.Pos(u, 0.0, 4.8) * bd.Cylinder(
            radius=2.10, height=1.20, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        fem_blk = fem_blk - bd.Pos(u, 0.0, 6.0) * bd.Cone(
            bottom_radius=2.10, top_radius=2.28, height=0.50,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        fem_blk = fem_blk - bd.Pos(u, 0.0, 6.5) * bd.Cylinder(
            radius=2.28, height=2.20, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        fem_blk = fem_blk - bd.Pos(u, 0.0, 8.7) * bd.Cone(
            bottom_radius=2.28, top_radius=1.0, height=1.30,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    lbl_s = bd.Pos(0.0, 0.0, 10.0) * make_engraved_label_solid("0", char_h=3.4, depth=0.65)
    petg_out.append(assign_toolhead(_bed_drop_center((fem_blk - lbl_s).solid()), "Coupon_Track_Bracket_Socket", 2))

    # 4x Brown PLA twin split-tine cantilever plugs testing c = 0.10..0.25 vs Ø4.20 mm throat
    pla_out: list[bd.Solid] = []
    for c_mm in CLEARANCES:
        r_shaft = 2.10 - c_mm
        r_lobe = 2.10 - c_mm + 0.24
        base = bd.Box(36.0, 10.0, 6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        peg_h = BRACKET_PEG_HEIGHT
        for u in (-BRACKET_PEG_SPACING_U / 2.0, BRACKET_PEG_SPACING_U / 2.0):
            cyl = bd.Pos(u, 0.0, 6.0) * bd.Cylinder(
                radius=r_shaft, height=peg_h - 0.85,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            tip = bd.Pos(u, 0.0, 6.0 + peg_h - 0.85) * bd.Cone(
                bottom_radius=r_lobe, top_radius=max(0.85, r_shaft - 0.55), height=0.85,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            lobe = bd.Pos(u, 0.0, 6.0 + peg_h - 1.55) * bd.Cylinder(
                radius=r_lobe, height=0.70,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            tine_slot = bd.Pos(u, 0.0, 6.0 + 1.0) * bd.Box(
                0.85, 2.0 * r_lobe + 0.5, peg_h,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            base = base + ((cyl + lobe + tip) - tine_slot)
        lbl_p = bd.Pos(0.0, 0.0, 6.0) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.4, depth=0.65)
        pla_out.append(assign_toolhead(_bed_drop_center((base - lbl_p).solid()), f"Coupon_SplitTine_Pegs_c{_label_tag(c_mm)}", 1))
    return petg_out, pla_out


# ---------------------------------------------------------------------------
# 4. Bayonet Marble Coupons (1x Production B Half + 4x A Test Caps [0.10..0.25])
# ---------------------------------------------------------------------------
def build_bayonet_a_variant(c_mm: float) -> bd.Solid:
    """Quarter-turn bayonet upper cap with lug radial clearance = c_mm vs r_bore=10.52 / r_tunnel=11.38."""
    sph = _make_exact_25mm_apple_sphere_centered()
    r_y_led = 9.35
    r_neck = 10.52 - c_mm
    r_lug = 11.38 - c_mm
    lip_h = 2.65
    up_box = bd.Box(30.0, 30.0, 15.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    upper_dome = (sph & up_box).solid()
    ef_chamfer = bd.Pos(0.0, 0.0, -lip_h) * bd.Cone(bottom_radius=r_neck - 0.40, top_radius=r_neck, height=0.40, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    neck_cyl = bd.Pos(0.0, 0.0, -lip_h + 0.40) * bd.Cylinder(radius=r_neck, height=lip_h - 0.40 + 0.05, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    scarf_cone = bd.Pos(0.0, 0.0, -0.22) * bd.Cone(bottom_radius=r_neck, top_radius=r_neck + 0.22, height=0.22, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    scarf_top_join = bd.Cylinder(radius=r_neck + 0.22, height=0.45, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    male_collar = ef_chamfer + neck_cyl + scarf_cone + scarf_top_join

    dr_lug = r_lug - r_neck
    lug_bot = bd.Pos(0.0, 0.0, -lip_h) * bd.Cone(bottom_radius=r_neck, top_radius=r_lug, height=dr_lug, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    lug_mid = bd.Pos(0.0, 0.0, -lip_h + dr_lug) * bd.Cylinder(radius=r_lug, height=0.40, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    lug_top = bd.Pos(0.0, 0.0, -lip_h + dr_lug + 0.40) * bd.Cone(bottom_radius=r_lug, top_radius=r_neck, height=dr_lug, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    lug_ring = (lug_bot + lug_mid + lug_top).solid()
    lugs = []
    for k in range(3):
        c_deg = k * 120.0
        w = _make_sector_wedge(14.0, -lip_h - 0.2, 0.0, c_deg - 16.0, c_deg + 16.0, n_arc=24)
        lugs.append((lug_ring & w).solid())
    inner_core = bd.Pos(0.0, 0.0, -lip_h - 0.1) * bd.Cylinder(radius=r_y_led, height=lip_h + 4.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    # Add clearance digits inside cavity floor/top and flat top rim
    # Flip upside-down so flat equator rim/lugs sit Z=0? Wait: Apple_Hemisphere_A prints with lip at Z=0!
    raw = upper_dome + male_collar
    for lg in lugs:
        raw = raw + lg
    raw = raw - inner_core
    # Trim dome top flat at Z=9.0 in local coords so label reads cleanly outside
    top_flat = bd.Pos(0, 0, -lip_h) * bd.Cylinder(radius=15.0, height=lip_h + 8.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    raw = (raw & top_flat) - bd.Pos(0, 0, 8.5) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.4, depth=0.65)
    return assign_toolhead(_bed_drop_center(raw.solid()), f"Coupon_Bayonet_A_c{_label_tag(c_mm)}", 1)


# ---------------------------------------------------------------------------
# 5. Planet Peg + 4x Planet Bore Test Caps (c = 0.10..0.25)
# ---------------------------------------------------------------------------
def build_planet_peg_coupon() -> bd.Solid:
    """1x production Ø7.60 x 3.50 mm track balcony peg with Ø8.12 mm snap bead on Ø14.4 mm pad."""
    pad = bd.Cylinder(radius=7.2, height=3.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    r_peg = PLANET_PEG_DIA / 2.0  # 3.80 mm
    r_bead = r_peg + 0.26         # 4.06 mm
    peg_c = bd.Pos(0, 0, 3.5) * bd.Cylinder(radius=r_peg, height=PLANET_PEG_HEIGHT - 0.85, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    b1 = bd.Pos(0, 0, 5.15) * bd.Cone(bottom_radius=r_peg, top_radius=r_bead, height=0.30, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    b2 = bd.Pos(0, 0, 5.45) * bd.Cylinder(radius=r_bead, height=0.20, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    b3 = bd.Pos(0, 0, 5.65) * bd.Cone(bottom_radius=r_bead, top_radius=r_peg, height=0.30, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    tip = bd.Pos(0, 0, 3.5 + PLANET_PEG_HEIGHT - 0.85) * bd.Cone(bottom_radius=r_peg, top_radius=r_peg - 0.85, height=0.85, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    part = (pad + peg_c + b1 + b2 + b3 + tip).solid()
    return assign_toolhead(_bed_drop_center(part), "Coupon_Planet_Peg", 2)


def build_planet_bore_cap(c_mm: float) -> bd.Solid:
    """Ø16 x 13 mm test cap with bottom peg bore + 4x KA006 crush ribs at c_mm."""
    r_peg = PLANET_PEG_DIA / 2.0  # 3.80 mm
    r_sock = r_peg + c_mm
    cap = bd.Cylinder(radius=8.0, height=13.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    bore = bd.Pos(0, 0, -0.1) * bd.Cylinder(radius=r_sock, height=3.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    funnel = bd.Pos(0, 0, -0.1) * bd.Cone(bottom_radius=r_sock + 0.6, top_radius=r_sock, height=0.9, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    led_bay = bd.Pos(0, 0, 3.6) * bd.Cylinder(radius=BAMBU_MAG_LED_DIA / 2.0 + c_mm, height=BAMBU_MAG_LED_HEIGHT + 0.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    roof = bd.Pos(0, 0, 9.8) * bd.Cone(bottom_radius=BAMBU_MAG_LED_DIA / 2.0 + c_mm, top_radius=1.8, height=1.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    lbl = bd.Pos(0, 0, 13.5) * make_engraved_label_solid(_label_tag(c_mm), char_h=3.4, depth=0.65)
    part = cap - bore - funnel - led_bay - roof - lbl
    # 4x axial KA006 crush ribs (same 0.85 mm width protruding inward to R=3.55 mm)
    r_rib_in = BAMBU_MAG_LED_DIA / 2.0 - 0.20 + (c_mm - 0.10) * 0.5
    for ang_deg in (0.0, 90.0, 180.0, 270.0):
        rad = math.radians(ang_deg)
        rib = bd.Pos(r_rib_in * math.cos(rad), r_rib_in * math.sin(rad), 3.9) * bd.Rot(0, 0, ang_deg) * bd.Box(
            0.9, 0.85, BAMBU_MAG_LED_HEIGHT - 0.6, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.MIN)
        )
        part = part + rib
    return assign_toolhead(_bed_drop_center(part.solid()), f"Coupon_Planet_Bore_c{_label_tag(c_mm)}", 1)


def build_wand_magnet_socket_coupon() -> bd.Solid:
    """Magic Wand press-fit Ø 8.05 x 2.20 mm magnet recess coupon with Ø 3.2 mm knock-out hole."""
    blk = bd.Cylinder(radius=7.0, height=5.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    mag_pocket = bd.Pos(0, 0, 5.0 - WAND_MAGNET_HEIGHT) * bd.Cylinder(
        radius=WAND_MAGNET_DIA / 2.0,
        height=WAND_MAGNET_HEIGHT + 0.1,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    pushout = bd.Pos(0, 0, -0.1) * bd.Cylinder(
        radius=1.6, height=5.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    part = (blk - mag_pocket - pushout).solid()
    return assign_toolhead(_bed_drop_center(part), "Coupon_Wand_Magnet_Socket", 1)


def _export_coupon_plate(out_path: Path, plate_name: str, parts: list[bd.Solid]) -> tuple[Path, list[PlatedPart]]:
    gap = 8.8
    max_row_w = 230.0
    items_meta: list[tuple[bd.Solid, float, float]] = []
    for p in parts:
        assert p.is_valid and p.is_manifold, f"Invalid/non-manifold coupon: {p.label}"
        x0, x1, y0, y1, z0, _z1 = _mesh_bounds(p)
        assert abs(z0) < 0.05, f"Coupon {p.label} bottom Z={z0} not flat on Z=0"
        items_meta.append((p, x1 - x0, y1 - y0))
    items_meta.sort(key=lambda it: it[2], reverse=True)

    rows: list[list[tuple[bd.Solid, float, float]]] = []
    cur_row: list[tuple[bd.Solid, float, float]] = []
    cur_w = 0.0
    for item in items_meta:
        w = item[1]
        add_w = w if not cur_row else (gap + w)
        if cur_w + add_w > max_row_w and cur_row:
            rows.append(cur_row)
            cur_row = [item]
            cur_w = w
        else:
            cur_row.append(item)
            cur_w += add_w
    if cur_row:
        rows.append(cur_row)

    total_h = sum(max(h for _, _, h in r) for r in rows) + gap * (len(rows) - 1)
    y_cursor = -0.5 * total_h
    plated: list[PlatedPart] = []

    for row in rows:
        row_h = max(h for _, _, h in row)
        row_w = sum(w for _, w, _ in row) + gap * (len(row) - 1)
        x_cursor = -0.5 * row_w
        cy = y_cursor + 0.5 * row_h
        for p, w, _h in row:
            cx = x_cursor + 0.5 * w
            tid = int(getattr(p, "toolhead_id", 1))
            spec = TOOLHEAD_PALETTE[tid]
            placed = p.moved(bd.Location((cx, cy, 0.0)))
            plated.append(
                PlatedPart(
                    name=p.label,
                    part=placed,
                    toolhead_id=tid,
                    hex_color=spec["hex"],
                    filament_type=spec["filament_type"],
                    plate_index=0,
                    plate_name=plate_name,
                    center_xy=(cx, cy),
                )
            )
            x_cursor += w + gap
        y_cursor += row_h + gap

    all_min_x = min(_mesh_bounds(pp.part)[0] for pp in plated)
    all_max_x = max(_mesh_bounds(pp.part)[1] for pp in plated)
    all_min_y = min(_mesh_bounds(pp.part)[2] for pp in plated)
    all_max_y = max(_mesh_bounds(pp.part)[3] for pp in plated)
    all_max_z = max(_mesh_bounds(pp.part)[5] for pp in plated)
    min_gap = (
        min(
            _part_xy_gap(plated[i].part, plated[j].part)
            for i in range(len(plated))
            for j in range(i + 1, len(plated))
        )
        if len(plated) > 1
        else 99.9
    )
    span_x = all_max_x - all_min_x
    span_y = all_max_y - all_min_y
    assert span_x <= 240.0 and span_y <= 240.0 and all_max_z <= 270.0, f"Exceeds 240x240: {span_x:.1f}x{span_y:.1f}x{all_max_z:.1f}"
    assert min_gap >= 8.0, f"Part XY gap {min_gap:.2f} < 8.0 mm"

    exporter = bd.Mesher(unit=bd.Unit.MM)
    pp_sub_records: dict[str, list[tuple[str, str, int, str]]] = {}
    for pp in plated:
        pp_sub_records[pp.name] = _add_part_meshes_to_exporter(exporter, pp)
    exporter.write(str(out_path))
    _inject_orca_metadata_into_3mf(
        out_path,
        plated_parts=plated,
        pp_sub_records=pp_sub_records,
        plate_names_ordered=[plate_name],
        apply_multiplate_stride=False,
    )
    print(
        f"Exported {len(plated)} test coupons to {out_path} | "
        f"bbox={span_x:.1f}x{span_y:.1f}x{all_max_z:.1f} mm | min_gap={min_gap:.1f} mm",
        flush=True,
    )
    return out_path, plated


def generate_test_coupons() -> dict[str, tuple[Path, list[PlatedPart]]]:
    threemf_dir = ROOT_DIR / "output" / "3mf"
    threemf_dir.mkdir(parents=True, exist_ok=True)
    legacy = threemf_dir / "Test_Coupons.3mf"
    if legacy.exists():
        legacy.unlink()

    petg_track, pla_plugs = build_track_joint_coupons()
    pla_parts: list[bd.Solid] = [
        build_trunk_keyhole_slice_coupon(),
        *[build_keyhole_tenon_stub(c) for c in CLEARANCES],
        build_trunk_tenon_female_coupon(),
        *[build_trunk_tenon_male_coupon(c) for c in CLEARANCES],
        *pla_plugs,
        assign_toolhead(_bed_drop_center(build_apple_hemisphere_b("Coupon_Bayonet_B")), "Coupon_Bayonet_B", 1),
        *[build_bayonet_a_variant(c) for c in CLEARANCES],
        *[build_planet_bore_cap(c) for c in CLEARANCES],
        build_wand_magnet_socket_coupon(),
    ]
    petg_parts: list[bd.Solid] = [
        *petg_track,
        build_planet_peg_coupon(),
    ]

    return {
        "PLA": _export_coupon_plate(threemf_dir / "Test_Coupons_PLA.3mf", "Test_Coupons_PLA_SingleColor", pla_parts),
        "PETG": _export_coupon_plate(threemf_dir / "Test_Coupons_PETG.3mf", "Test_Coupons_PETG_SingleColor", petg_parts),
    }


if __name__ == "__main__":
    generate_test_coupons()
