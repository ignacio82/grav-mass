"""Segmented Trunk Core (cad/trunk.py) for the Grav-Mass Day Marble Run Tree.

Generates 3 stackable vertical trunk sections (total assembled height 450 mm):
  1. trunk_base : Ø 166 mm root-flare base, N20 motor pocket, battery cradle,
                  ON/OFF power switch mount, bottom cable exit slot, Ø 41 mm auger bore +
                  vertical ball lift flute, rear USB wire channel, 60° helical female
                  dovetail sockets, and top keyed male tenon.
  2. trunk_mid  : Bottom keyed female socket, Ø 41 mm bore + vertical ball lift flute,
                  rear USB wire channel, 60° helical female dovetail sockets, and top
                  keyed male tenon.
  3. trunk_top  : Bottom keyed female socket, Ø 41 mm bore + vertical ball lift flute,
                  rear USB wire channel, 60° helical female dovetail sockets, and sloped
                  upper ball discharge chute below the Z = 450 mm Golden Apple Topper.
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    AA050_M25_CBORE_DIA,
    AA050_M25_TAP_DEPTH,
    AA050_M25_TAP_DIA,
    AA050_M25_THROUGH_DIA,
    ATOM_LITE_CRADLE_X,
    ATOM_LITE_CRADLE_Y,
    ATOM_LITE_CRADLE_Z,
    AUGER_BALL_ORBIT_R,
    AUGER_BORE_DIA,
    AUGER_FLUTE_R,
    BALL_DIAMETER,
    BASE_BOTTOM_COVER_THICK,
    BATTERY_14500_BAY_X,
    BATTERY_14500_BAY_Y,
    BATTERY_14500_BAY_Z,
    CONDUIT_COVER_STRIP_H,
    DC_BARREL_JACK_BORE_DIA,
    DC_BARREL_JACK_Z_CENTER,
    DOVETAIL_ANGULAR_STEP_DEG,
    DOVETAIL_BASE_W_TOP,
    DOVETAIL_NECK_W_TOP,
    DOVETAIL_RADIAL_DEPTH,
    DOVETAIL_SLOT_H,
    DOVETAIL_TAPER_W,
    DUAL_MOSFET_BAY_X,
    DUAL_MOSFET_BAY_Y,
    DUAL_MOSFET_BAY_Z,
    FIT_TOLERANCE,
    HELIX_TOTAL_DEG,
    IA005_PDB_BAY_X,
    IA005_PDB_BAY_Y,
    IA005_PDB_BAY_Z,
    LA002_N20_POCKET_X,
    LA002_N20_POCKET_Y,
    LA002_N20_POCKET_Z,
    MAGNET_DEPTH,
    MAGNET_DIA,
    MOTOR_SHROUD_OD,
    PG002_SERVO_BAY_X,
    PG002_SERVO_BAY_Y,
    PG002_SERVO_BAY_Z,
    ROOT_VAULT_CLEAR_R,
    TENON_HEIGHT,
    TENON_KEY_FLAT_DEPTH,
    TENON_NOMINAL_R,
    TRUNK_BASE_FLANGE_R,
    TRUNK_FLARE_HEIGHT,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    UCTRONICS_BUCK_BAY_X,
    UCTRONICS_BUCK_BAY_Y,
    UCTRONICS_BUCK_BAY_Z,
    WAGO_221_BAY_X,
    WAGO_221_BAY_Y,
    WAGO_221_BAY_Z,
    WIRE_CONDUIT_D,
    WIRE_CONDUIT_W,
    XA007_SWITCH_BAY_X,
    XA007_SWITCH_BAY_Y,
    XA007_SWITCH_BAY_Z,
    assign_toolhead,
    helix_z,
    make_engraved_label_solid,
)


def make_keyed_male_tenon(z_base: float, height: float = TENON_HEIGHT) -> bd.Solid:
    """Create a male cylindrical tenon with 0.20 mm radial clearance, +X keyed flat,
    -X flat for the 10.0 x 8.0 mm rear wire conduit, and -Y flat behind the vertical ball
    guide flute (Y >= -14.50 mm) so the flute walls & cusps are 100% continuous across seams.
    """
    r_male = TENON_NOMINAL_R - FIT_TOLERANCE  # 27.30 mm
    cyl = bd.Cylinder(
        radius=r_male,
        height=height,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Keep X in [-24.50, r_male - TENON_KEY_FLAT_DEPTH] and Y in [-14.50, r_male + 1.0]
    x_max = r_male - TENON_KEY_FLAT_DEPTH     # +25.30 mm
    x_min = -(TRUNK_OUTER_R - WIRE_CONDUIT_D - 1.50)  # -24.50 mm
    y_min = -14.50
    y_max = r_male + 1.0
    keep_box = bd.Pos(0.5 * (x_min + x_max), 0.5 * (y_min + y_max), 0.0) * bd.Box(
        x_max - x_min,
        y_max - y_min,
        height + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    tenon = (cyl & keep_box).locate(bd.Location((0.0, 0.0, z_base)))
    return tenon


def make_keyed_female_socket_cutter(z_base: float = 0.0, height: float = TENON_HEIGHT) -> bd.Solid:
    """Create the female socket cutter with 0.20 mm clearance, +X/-X/-Y keyed flats, and 45-deg roof.
    Clips Y >= -14.70 mm so the -Y vertical ball flute (Y <= -15.70 mm) has zero recess or overhang at seams.
    """
    r_female = TENON_NOMINAL_R  # 27.50 mm (0.20 mm radial gap vs r_male = 27.30 mm)
    socket_h = height + FIT_TOLERANCE  # 15.20 mm axial clearance
    cyl = bd.Cylinder(
        radius=r_female,
        height=socket_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Keep X in [-24.70, +25.50 mm] and Y in [-14.70, r_female + 1.0]
    x_max = (TENON_NOMINAL_R - FIT_TOLERANCE - TENON_KEY_FLAT_DEPTH) + FIT_TOLERANCE  # +25.50 mm
    x_min = -(TRUNK_OUTER_R - WIRE_CONDUIT_D - 1.50) - FIT_TOLERANCE                  # -24.70 mm
    y_min = -14.70
    y_max = r_female + 1.0
    keep_box = bd.Pos(0.5 * (x_min + x_max), 0.5 * (y_min + y_max), 0.0) * bd.Box(
        x_max - x_min,
        y_max - y_min,
        socket_h + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    keyed_cyl = cyl & keep_box

    # Self-supporting 45-degree conical roof transition from r_female to auger bore radius
    r_bore = AUGER_BORE_DIA / 2.0
    cone_h = r_female - r_bore
    roof_cone = bd.Pos(0.0, 0.0, socket_h) * bd.Cone(
        bottom_radius=r_female,
        top_radius=r_bore,
        height=cone_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cutter = (keyed_cyl + (roof_cone & bd.Pos(0.5 * (x_min + x_max), 0.5 * (y_min + y_max), socket_h) * bd.Box(
        x_max - x_min,
        y_max - y_min,
        cone_h + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ))).locate(bd.Location((0.0, 0.0, z_base)))
    return cutter


def make_female_dovetail_slot_cutter() -> bd.Solid:
    """Build a downward-tapered 45-degree female dovetail socket cutter with 45-deg roof ramp.

    Local coordinates before placement at (R=TRUNK_OUTER_R, theta, z):
      X: radially outward (slot cuts from X = -DOVETAIL_RADIAL_DEPTH to X = +1.5 mm)
      Y: tangential width (45-deg dovetail sidewalls, downward tapered by DOVETAIL_TAPER_W)
      Z: vertical along trunk axis (0 to DOVETAIL_SLOT_H, plus 45-deg top lead-in ramp)
    """
    d = DOVETAIL_RADIAL_DEPTH  # 4.5 mm
    out_ext = 1.5              # Extend past outer cylinder surface for clean boolean cut

    # Top of active dovetail slot (Z = DOVETAIL_SLOT_H)
    half_base_top = DOVETAIL_BASE_W_TOP / 2.0  # 8.0 mm at X = -d
    half_neck_top = DOVETAIL_NECK_W_TOP / 2.0  # 3.5 mm at X = 0.0
    half_out_top = max(1.0, half_neck_top - out_ext)

    # Bottom of active dovetail slot (Z = 0), tapered inward by DOVETAIL_TAPER_W / 2 per side
    taper = DOVETAIL_TAPER_W / 2.0
    half_base_bot = half_base_top - taper
    half_neck_bot = half_neck_top - taper
    half_out_bot = max(1.0, half_neck_bot - out_ext)

    pts_bot = [
        (-d, -half_base_bot),
        (0.0, -half_neck_bot),
        (out_ext, -half_neck_bot),
        (out_ext, half_neck_bot),
        (0.0, half_neck_bot),
        (-d, half_base_bot),
        (-d, -half_base_bot),
    ]
    pts_top = [
        (-d, -half_base_top),
        (0.0, -half_neck_top),
        (out_ext, -half_neck_top),
        (out_ext, half_neck_top),
        (0.0, half_neck_top),
        (-d, half_base_top),
        (-d, -half_base_top),
    ]
    # 45-deg top exit ramp (Z = DOVETAIL_SLOT_H + d + 0.2) so top overhang is <= 45 deg
    pts_ramp = [
        (0.2, -half_neck_top),
        (0.3, -half_neck_top),
        (out_ext, -half_neck_top),
        (out_ext, half_neck_top),
        (0.3, half_neck_top),
        (0.2, half_neck_top),
        (0.2, -half_neck_top),
    ]

    w_bot = bd.Wire([bd.Edge.make_line(pts_bot[i], pts_bot[i + 1]) for i in range(6)])
    w_top = bd.Pos(0.0, 0.0, DOVETAIL_SLOT_H) * bd.Wire(
        [bd.Edge.make_line(pts_top[i], pts_top[i + 1]) for i in range(6)]
    )
    w_ramp = bd.Pos(0.0, 0.0, DOVETAIL_SLOT_H + d + 0.2) * bd.Wire(
        [bd.Edge.make_line(pts_ramp[i], pts_ramp[i + 1]) for i in range(6)]
    )

    body = bd.Solid.make_loft([w_bot, w_top], ruled=True)
    ramp = bd.Solid.make_loft([w_top, w_ramp], ruled=True)
    return body + ramp


def _cut_helical_dovetails_for_section(
    part: bd.Solid,
    z_section_min: float,
    z_section_max: float,
    local_z_min_safe: float,
    local_z_max_safe: float,
) -> bd.Solid:
    """Subtract female dovetail sockets at 60-degree increments along the helical slope.

    Uses the exact unclamped mathematical height `z_global = helix_z(theta_deg) - 30.0`
    for every 60° station (60°..1560°). Whenever a slot's vertical span overlaps the
    section `[z_section_min, z_section_max]`, it cuts cleanly at `z_local = z_global - z_section_min`
    so slots near section seams (Z = 150 mm and Z = 300 mm) align 100% seamlessly across
    stacked trunk sections with 0.000 mm vertical error.
    """
    _ = (local_z_min_safe, local_z_max_safe)
    base_cutter = make_female_dovetail_slot_cutter()
    slot_total_h = DOVETAIL_SLOT_H + DOVETAIL_RADIAL_DEPTH + 1.0
    num_steps = int(round(HELIX_TOTAL_DEG / DOVETAIL_ANGULAR_STEP_DEG))

    for k in range(1, num_steps):
        theta_deg = k * DOVETAIL_ANGULAR_STEP_DEG
        # Bracket engages trunk at Z = helix_z(theta_deg) + TRACK_BASE_Y (-12.0) - DOVETAIL_SLOT_H (18.0)
        z_global = helix_z(theta_deg) - 30.0
        if (z_global + slot_total_h) >= z_section_min and z_global <= z_section_max:
            z_local = z_global - z_section_min
            rad = math.radians(theta_deg)
            loc = bd.Location(
                (TRUNK_OUTER_R * math.cos(rad), TRUNK_OUTER_R * math.sin(rad), z_local),
                (0.0, 0.0, theta_deg),
            )
            part = part - base_cutter.moved(loc)
    return part


def _cut_rear_wire_conduit(part: bd.Solid, total_h: float, is_base: bool = False) -> bd.Solid:
    """Cut the oversized vertical rear (-X) 'Connector-Pass-Through' wiring conduit:
      - 10.0 mm wide (Y in [-5.0, +5.0 mm]) x 8.0 mm deep (X in [-34.0, -26.0 mm])
      - Allows pre-terminated JST-SM (SM2.54-3P), SH1.0, PH2.0, or Dupont plugs (and inline
        switches) to be threaded straight through Trunk_Base, Trunk_Middle, and Trunk_Top
        without cutting or de-pinning wires, then concealed behind Conduit_Cover_Strip.
    """
    z_top = total_h + TENON_HEIGHT + 2.0
    if is_base:
        # From Z = 0..38 mm inside the widened base hub, keep X in [-34.2, -26.0 mm] so the
        # XA007 switch pocket at X = -46.0 mm (X in [-57.0, -35.0 mm]) retains its inner wall,
        # while above Z = 38 mm the conduit opens cleanly through the R = 34.0 mm bark surface.
        lower_conduit = bd.Pos(-30.1, 0.0, -0.5) * bd.Box(
            8.2,
            WIRE_CONDUIT_W,
            40.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        upper_conduit = bd.Pos(-TRUNK_OUTER_R, 0.0, 38.0) * bd.Box(
            WIRE_CONDUIT_D * 2.0,
            WIRE_CONDUIT_W,
            z_top - 38.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        return part - lower_conduit - upper_conduit

    conduit = bd.Pos(-TRUNK_OUTER_R, 0.0, -0.5) * bd.Box(
        WIRE_CONDUIT_D * 2.0,
        WIRE_CONDUIT_W,
        z_top,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return part - conduit


def _bark_furrow_depth(deg: float, z_global: float, max_depth: float = 1.45) -> float:
    """Compute organic support-free vertical & gently twisting bark furrow depth (in mm).

    Keeps the 60° bracket dovetail columns (`d60 <= 6.5°`) and the 270° (-Y) ball port /
    viewing window strip (`d270 <= 16.0°`) smooth at `R = TRUNK_OUTER_R = 34.0 mm` so every
    cantilever bracket and track endcap mates flush with 0.000 mm³ interference, while
    sculpting deep gnarled wood-bark ridges and crevices across all inter-bracket panels.
    Because `z_global` is continuous across `trunk_base` (0..150), `trunk_mid` (150..300),
    and `trunk_top` (300..450), the bark ridges align 100% seamlessly across section joints
    and never exceed a 3° vertical overhang angle (100% support-free).
    """
    d60 = abs(((deg + 30.0) % 60.0) - 30.0)
    d270 = abs(((deg - 270.0 + 180.0) % 360.0) - 180.0)
    env60 = 0.0 if d60 <= 6.5 else min(1.0, (d60 - 6.5) / 4.5)
    env270 = 0.0 if d270 <= 16.0 else min(1.0, (d270 - 16.0) / 5.0)
    env = min(env60, env270)
    if env <= 1e-6:
        return 0.0

    wave1 = 0.55 * (1.0 - math.cos(math.radians(30.0 * deg + 18.0 * math.sin(z_global * 0.045))))
    wave2 = 0.30 * (
        1.0 - math.cos(math.radians(18.0 * deg - z_global * 0.35 + 25.0 * math.cos(z_global * 0.03)))
    )
    wave3 = 0.15 * (1.0 - math.cos(math.radians(48.0 * deg + z_global * 0.55)))
    return max_depth * env * (wave1 + wave2 + wave3) / 2.0


def _make_bark_textured_trunk_column(
    z_min: float,
    z_max: float,
    z_global_offset: float,
    r_outer: float = TRUNK_OUTER_R,
    n_pts: int = 120,
    n_z: int = 13,
) -> bd.Solid:
    """Create a support-free organic bark-textured trunk cylinder column for `z in [z_min, z_max]`."""
    wires: list[bd.Wire] = []
    for iz in range(n_z):
        u = iz / (n_z - 1)
        z_local = z_min + u * (z_max - z_min)
        zg = z_global_offset + z_local
        pts: list[bd.Vector] = []
        for ip in range(n_pts):
            deg = ip * (360.0 / n_pts)
            rad = math.radians(deg)
            r = r_outer - _bark_furrow_depth(deg, zg, max_depth=1.45)
            pts.append(bd.Vector(r * math.cos(rad), r * math.sin(rad), z_local))
        wires.append(bd.Wire.make_polygon(pts))
    return bd.Solid.make_loft(wires, ruled=True)


def _make_bark_textured_base_hub() -> bd.Solid:
    """Create the widened Hollow Root Vault electronics pedestal (`Z = 0..18 mm`, `R = 72.5 mm`
    housing the Ø 135.0 mm internal clear electronics vault) and support-free root-flare
    transition cone (`Z = 18..45 mm`, `R = 72.5 -> 34.0 mm`) with continuous organic bark ridges.
    Includes a -Y intake terrace so `track_seg_01`'s return ramp (Z >= 38 mm) has 0.0 mm³ interference.
    """
    z_rings = [
        (0.0, 72.5, 1.25),
        (9.0, 72.5, 1.25),
        (17.5, 72.5, 1.25),
        (24.0, 63.0, 1.30),
        (30.0, 53.5, 1.35),
        (35.0, 46.0, 1.40),
        (40.0, 39.5, 1.42),
        (45.0, TRUNK_OUTER_R, 1.45),
    ]
    n_pts = 120
    wires: list[bd.Wire] = []
    for z_val, r_nom, depth in z_rings:
        pts: list[bd.Vector] = []
        for ip in range(n_pts):
            deg = ip * (360.0 / n_pts)
            rad = math.radians(deg)
            d180 = abs(((deg - 180.0 + 180.0) % 360.0) - 180.0)
            d30 = abs(((deg - 30.0 + 180.0) % 360.0) - 180.0)
            d270 = abs(((deg - 270.0 + 180.0) % 360.0) - 180.0)
            hub_env = 1.0
            if z_val < 28.0:
                if d180 < 16.0:
                    hub_env = min(hub_env, max(0.0, (d180 - 11.0) / 5.0))
                if d30 < 16.0:
                    hub_env = min(hub_env, max(0.0, (d30 - 11.0) / 5.0))
            # In the -Y ball intake sector (d270 <= 62°), taper inward faster above Z = 17.5 mm
            # so the front wall is already at R = TRUNK_OUTER_R (34.0 mm) by Z = 34.0 mm
            r_eff = r_nom
            if z_val > 17.5 and d270 < 62.0:
                w270 = 1.0 if d270 <= 46.0 else (62.0 - d270) / 16.0
                u_fast = min(1.0, (z_val - 17.5) / (34.0 - 17.5))
                r_fast = 72.5 + (TRUNK_OUTER_R - 72.5) * u_fast
                r_eff = r_nom * (1.0 - w270) + r_fast * w270
            furrow = hub_env * _bark_furrow_depth(deg, z_val, max_depth=depth)
            r = r_eff - furrow
            pts.append(bd.Vector(r * math.cos(rad), r * math.sin(rad), z_val))
        wires.append(bd.Wire.make_polygon(pts))
    hub = bd.Solid.make_loft(wires, ruled=True)
    # Add rear +Y dorsal root-arch dome (Z = 30..53.5 mm) so the internal clear electronics
    # vault reaches a full 50.0 mm tall beneath the bulkhead with >= 3.2 mm wall thickness
    dorsal_dome = bd.Pos(0.0, 20.0, 28.0) * bd.Cone(
        bottom_radius=26.0,
        top_radius=9.5,
        height=26.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return hub + dorsal_dome


def _make_five_root_flare_solid() -> bd.Solid:
    """Create the spreading tree-root base flare with 4 diagonal buttress roots (45°, 135°,
    225°, 315°) reaching R = 92.5 mm (Ø 185.0 mm tip-to-tip outer root footprint!) while
    keeping the X/Y Axis-Aligned Bounding Box within 145.0 x 145.0 mm for single-plate printing.
    """
    n_roots = 4

    def _ring_wire(z: float, r_tip: float, r_sh: float, r_bay: float, ridge_amp: float) -> bd.Wire:
        pts: list[bd.Vector] = []
        for k in range(n_roots):
            base_deg = 45.0 + k * (360.0 / n_roots)
            sector = [
                (base_deg - 45.0, r_bay),
                (base_deg - 32.0, 0.5 * (r_bay + r_sh) - ridge_amp),
                (base_deg - 22.0, r_sh),
                (base_deg - 14.0, 0.5 * (r_sh + r_tip) - ridge_amp * 0.9),
                (base_deg - 7.0, r_tip - 1.5),
                (base_deg - 2.5, r_tip - ridge_amp * 0.6),
                (base_deg, r_tip),
                (base_deg + 2.5, r_tip - ridge_amp * 0.6),
                (base_deg + 7.0, r_tip - 1.5),
                (base_deg + 14.0, 0.5 * (r_sh + r_tip) - ridge_amp * 0.9),
                (base_deg + 22.0, r_sh),
                (base_deg + 32.0, 0.5 * (r_bay + r_sh) - ridge_amp),
            ]
            for deg, r in sector:
                rad = math.radians(deg)
                pts.append(bd.Vector(r * math.cos(rad), r * math.sin(rad), z))
        return bd.Wire.make_polygon(pts)

    w0 = _ring_wire(0.0, TRUNK_BASE_FLANGE_R, 76.0, 71.5, 1.2)
    w1 = _ring_wire(5.0, TRUNK_BASE_FLANGE_R - 2.0, 74.0, 71.0, 1.1)
    w2 = _ring_wire(13.0, 77.0, 70.0, 68.0, 0.9)
    w3 = _ring_wire(21.0, 62.0, 58.0, 56.0, 0.6)
    w4 = _ring_wire(30.0, TRUNK_OUTER_R - 0.5, TRUNK_OUTER_R - 0.5, TRUNK_OUTER_R - 0.5, 0.0)
    return bd.Solid.make_loft([w0, w1, w2, w3, w4], ruled=True)


def _make_vertical_ball_flute_cutter(z_min: float, height: float) -> bd.Solid:
    """Create the vertical ball-guide flute cutter (R = AUGER_FLUTE_R = 13.3 mm centered at
    X = 0.0, Y = -AUGER_BALL_ORBIT_R = -17.5 mm) that cradles the outer half of the Ø 25.0 mm
    rolling Apple marble and prevents it from spinning around the Z-axis with the auger screw.
    """
    return bd.Pos(0.0, -AUGER_BALL_ORBIT_R, z_min) * bd.Cylinder(
        radius=AUGER_FLUTE_R,
        height=height,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )


def _make_arched_viewing_window_cutter(
    z_min: float,
    straight_h: float,
    width_inner: float = 14.0,
    width_outer: float = 18.0,
) -> bd.Solid:
    """Build a support-free gothic-arched front viewing window cutter along -Y (X = 0, Y = -36..-22 mm):
      - Inner width 14.0 mm (< 25.0 mm marble diameter so rising marbles stay 100% captive)
      - Flared 45° outer bark bevel (18.0 mm wide at outer surface) for wide-angle viewing of the
        silk-gold Archimedes screw and rising red marbles
      - 45° pointed gable roof and bottom sill so the window prints with zero horizontal bridges.
    """
    y_in = -22.0
    y_out = -36.5
    hw_in = width_inner / 2.0
    hw_out = width_outer / 2.0
    peak_in = hw_in
    peak_out = hw_out

    def _window_wire(y_pos: float, hw: float, peak: float) -> bd.Wire:
        pts = [
            (0.0, y_pos, z_min),
            (-hw, y_pos, z_min + peak),
            (-hw, y_pos, z_min + straight_h),
            (0.0, y_pos, z_min + straight_h + peak),
            (hw, y_pos, z_min + straight_h),
            (hw, y_pos, z_min + peak),
            (0.0, y_pos, z_min),
        ]
        return bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])

    w_in = _window_wire(y_in, hw_in, peak_in)
    w_out = _window_wire(y_out, hw_out, peak_out)
    return bd.Solid.make_loft([w_in, w_out], ruled=True)


def _cut_front_elevation_ruler_for_section(
    part: bd.Solid,
    z_section_min: float,
    local_z_min: float,
    local_z_max: float,
) -> bd.Solid:
    """Cut a vertical elevation / drop ruler (25 mm ticks + 100 mm decimeter marks) alongside
    the gothic-arched front (-Y) viewing windows so users can measure both the vertical drop
    (Δh) of falling marbles and the vertical lift speed (mm/s) of rising marbles in the auger.
    """
    cutters: bd.Shape | None = None
    for z_global in range(75, 430, 25):
        z_local = float(z_global) - z_section_min
        if local_z_min <= z_local <= local_z_max:
            is_dm = (z_global % 100) == 0
            is_50 = (z_global % 50) == 0
            tick_w = 4.2 if is_dm else (3.4 if is_50 else 2.4)
            tick_h = 1.3 if is_50 else 0.95
            for sign_x in (-1.0, 1.0):
                cx = sign_x * (9.2 + 0.5 * tick_w)
                t_box = bd.Pos(cx, -32.6, z_local) * bd.Box(
                    tick_w,
                    2.4,
                    tick_h,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
                )
                cutters = t_box if cutters is None else (cutters + t_box)
    if cutters is not None:
        part = part - cutters
    return part




def build_trunk_base() -> bd.Solid:
    """Build Section 1 (trunk_base): Z = 0..150 mm + 15 mm male tenon (total H = 165 mm).
    Features the 'Zero-Fuss Cable Management' Hollow Root Vault (Ø 185.0 mm diagonal root footprint,
    Ø 135.0 x 50.0 mm internal clear electronics vault with > 200,000 mm³ unobstructed Cable Slack
    Dump Zone):
      - Isolated Ø 28.0 mm Motor & Magnetic Safety Clutch Shroud Tower (Z = 0..42.0 mm) with bottom wire notch
      - Dedicated +Y Snap-In Cradle at (-4.0, +36.5) for the UCTRONICS B07XXWQ49N (U6223,
        63.0 x 27.0 x 10.0 mm) 12V->5V 5A Screw-Terminal Buck Converter (64.2 x 28.2 x 12.0 mm pocket
        with open -X/+X screw-terminal wire portals)
      - Dedicated +X Snap-In Organizer Cradle at (+44.5, -12.0) for the WAGO 221-415 (30.0 x 18.6 x 8.4 mm)
        5-Port Lever-Nut Bus Blocks (19.8 x 31.2 x 18.0 mm dual-stack pocket with open -X wire portal)
      - Stepped -Y ESPHome / Battery Cradle (0.0, -33.0) for M5Stack Atomic H-Driver (A092 + C008,
        48.0 x 24.0 x 18.0 mm) or 14500 pack, with inner +Y Grove/terminal wire portal into the vault
      - Oversized 10.0 x 8.0 mm Rear (-X) Connector-Pass-Through Trunk Wiring Conduit
    """
    # 1. 4-diagonal-root spreading flare (Ø 185.0 mm span) + widened bark-textured vault drum (R=72.5 mm)
    #    + support-free bark-textured upper trunk column (Z=0..150 mm)
    flare_base = _make_five_root_flare_solid()
    elec_hub_bark = _make_bark_textured_base_hub()
    upper_col = _make_bark_textured_trunk_column(
        z_min=0.0,
        z_max=TRUNK_SECTION_HEIGHT,
        z_global_offset=0.0,
    )
    body = flare_base + elec_hub_bark + upper_col

    # 2. Add top interlocking male tenon (Z = 150..165 mm) with +X/-X keyed flats
    tenon = make_keyed_male_tenon(z_base=TRUNK_SECTION_HEIGHT, height=TENON_HEIGHT)
    body = body + tenon

    # 2b. Excavate the cavernous Hollow Root Vault (Ø 135.0 mm = R 67.5 mm internal diameter,
    #     50.0 mm tall beneath bulkhead) while preserving the internal structural towers & cradle frames:
    wand_x = 52.0 * math.cos(math.radians(30.0))  # +45.03 mm
    wand_y = 52.0 * math.sin(math.radians(30.0))  # +26.00 mm

    vault_cyl = bd.Pos(0.0, 0.0, -0.1) * bd.Cylinder(
        radius=ROOT_VAULT_CLEAR_R,  # 67.5 mm (Ø 135.0 mm)
        height=16.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    vault_cone = bd.Pos(0.0, 0.0, 16.4) * bd.Cone(
        bottom_radius=ROOT_VAULT_CLEAR_R,
        top_radius=28.0,
        height=21.6,                # Z = 16.4..38.0 mm support-free conical vault ceiling
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Clip vault_cone in the -Y intake sector above Z = 29.0 mm so the Z = 34.0 mm intake terrace has a thick floor
    intake_floor_keep = bd.Pos(0.0, -52.0, 29.0) * bd.Box(
        90.0,
        64.0,
        25.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    vault_upper_dome = bd.Pos(0.0, 20.0, 34.0) * bd.Cone(
        bottom_radius=19.0,
        top_radius=5.0,
        height=16.0,                # Reaches Z = 50.0 mm tall beneath bulkhead!
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    raw_vault = (vault_cyl + (vault_cone - intake_floor_keep)) + vault_upper_dome

    # Internal structures preserved inside the Hollow Root Vault (extend Z = -0.2..42.0 mm so every
    # cradle column merges 100% into the vault roof above, guaranteeing a single manifold solid!):
    # (i) Isolated Ø 28.0 mm (R = 14.0 mm) Motor & Magnetic Safety Clutch Shroud Tower at (0, 0)
    motor_shroud_tower = bd.Pos(0.0, 0.0, -0.2) * bd.Cylinder(
        radius=MOTOR_SHROUD_OD / 2.0,  # R = 14.0 mm (Ø 28.0 mm)
        height=44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # (ii) Front -Y Stepped ESPHome / Battery Cradle Frame at (0.0, -33.0)
    front_cradle_frame = bd.Pos(0.0, -33.0, -0.2) * bd.Box(
        65.0,
        36.0,
        44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # (iii) Rear -X XA007 Switch Housing Boss at (-47.0, 0.0)
    xa007_boss = bd.Pos(-47.0, 0.0, -0.2) * bd.Box(
        26.0,
        22.0,
        44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # (iv) +30° Magic Wand Holster Internal Pillar at (+45.03, +26.00)
    wand_pillar = bd.Pos(wand_x, wand_y, -0.2) * bd.Cylinder(
        radius=9.5,
        height=44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # (v) North (+Y) Dedicated UCTRONICS B07XXWQ49N (U6223, 63.0 x 27.0 x 10.0 mm) 5V 5A Buck Cradle at (-4.0, +36.5)
    buck_cradle_frame = bd.Pos(-4.0, 36.5, -0.2) * bd.Box(
        UCTRONICS_BUCK_BAY_X + 3.6,  # 67.8 mm
        UCTRONICS_BUCK_BAY_Y + 3.6,  # 31.8 mm
        44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # (vi) East (+X) Dedicated WAGO 221-415 (30.0 x 18.6 x 8.4 mm) Dual-Stack Lever-Nut Cradle at (+44.5, -12.0)
    wago_cradle_frame = bd.Pos(44.5, -12.0, -0.2) * bd.Box(
        WAGO_221_BAY_X + 3.6,        # 23.4 mm
        WAGO_221_BAY_Y + 3.6,        # 34.8 mm
        44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    internal_structures = (
        motor_shroud_tower
        + front_cradle_frame
        + xa007_boss
        + wand_pillar
        + buck_cradle_frame
        + wago_cradle_frame
    )
    body = body - (raw_vault - internal_structures)

    # Cut the internal pockets of the UCTRONICS 5V 5A Buck Cradle & WAGO 221-415 Lever-Nut Cradle:
    buck_pocket = bd.Pos(-4.0, 36.5, -0.1) * bd.Box(
        UCTRONICS_BUCK_BAY_X,        # 64.2 mm (fits 63.0 mm UCTRONICS B07XXWQ49N PCB)
        UCTRONICS_BUCK_BAY_Y,        # 28.2 mm (fits 27.0 mm UCTRONICS B07XXWQ49N PCB)
        UCTRONICS_BUCK_BAY_Z + 0.1,  # 12.1 mm clear height (fits 10.0 mm tall module)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    buck_terminal_wire_slots = bd.Pos(-4.0, 36.5, -0.1) * bd.Box(
        UCTRONICS_BUCK_BAY_X + 8.0,  # 72.2 mm — opens both -X (VIN) and +X (5V OUT) end walls for 18 AWG wires
        20.0,                        # 20.0 mm wide wire pass-through centered on the screw terminals
        UCTRONICS_BUCK_BAY_Z + 0.1,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    buck_sight_vent = bd.Pos(-4.0, 36.5, -0.1) * bd.Cylinder(
        radius=3.5,
        height=18.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wago_pocket = bd.Pos(44.5, -12.0, -0.1) * bd.Box(
        WAGO_221_BAY_X,              # 19.8 mm (fits 18.6 mm deep WAGO 221-415 / 221-413 blocks)
        WAGO_221_BAY_Y,              # 31.2 mm (fits 30.0 mm wide 5-port WAGO 221-415 blocks)
        WAGO_221_BAY_Z + 0.1,        # 18.1 mm clear height (fits 2x 8.4 mm = 16.8 mm stacked blocks)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wago_wire_open = bd.Pos(34.0, -12.0, -0.1) * bd.Box(
        6.0,                         # Opens -X inner vault wall of wago_cradle_frame for all 5 lever-nut wire ports
        26.0,                        # Leaves 2.6 mm retention corner lips at ±Y to hold WAGO blocks captive
        WAGO_221_BAY_Z + 0.1,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = (
        body
        - buck_pocket
        - buck_terminal_wire_slots
        - buck_sight_vent
        - wago_pocket
        - wago_wire_open
    )

    # 3. Cut lower Ø 24.0 mm clutch/collar bore (Z = -0.5..42.0 mm), 45° support-free expansion cone
    #    (Z = 42.0..50.5 mm, R = 12.0 -> 20.5 mm), full Ø 41.0 mm upper auger bore (Z = 50.5..166.5 mm),
    #    and the -Y vertical ball guide flute (Z = 38.0..166.5 mm) with 45° self-supporting floor cone.
    r_clutch_bore = 12.00
    r_upper_bore = AUGER_BORE_DIA / 2.0  # 20.50 mm
    cone_expand_h = r_upper_bore - r_clutch_bore  # 8.50 mm (45° support-free slope)

    lower_bore = bd.Pos(0.0, 0.0, -0.5) * bd.Cylinder(
        radius=r_clutch_bore,
        height=42.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    expand_cone = bd.Pos(0.0, 0.0, 42.0) * bd.Cone(
        bottom_radius=r_clutch_bore,
        top_radius=r_upper_bore,
        height=cone_expand_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    upper_bore = bd.Pos(0.0, 0.0, 42.0 + cone_expand_h - 0.1) * bd.Cylinder(
        radius=r_upper_bore,
        height=TRUNK_SECTION_HEIGHT + TENON_HEIGHT - (42.0 + cone_expand_h) + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    flute_cutter = _make_vertical_ball_flute_cutter(
        z_min=44.0,
        height=TRUNK_SECTION_HEIGHT + TENON_HEIGHT - 44.0 + 2.0,
    ) + (
        bd.Pos(0.0, -AUGER_BALL_ORBIT_R, 38.0)
        * bd.Cone(
            bottom_radius=AUGER_FLUTE_R - 6.0,
            top_radius=AUGER_FLUTE_R,
            height=6.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    body = body - lower_bore - expand_cone - upper_bore - flute_cutter

    # 3b. Add internal horizontal thrust ledge / collar at Z = 37.20 mm (R_inner = 8.50 mm -> R_outer = 12.00 mm)
    #     with a support-free 45° underside taper (Z = 33.70..37.20 mm) to support the outer 1.50 mm rim
    #     of the Ø 20.0 mm Auger_Bottom flange with a 1.00 mm axial air gap above Motor_Clutch_Driver (Z = 26.2..36.2 mm)
    r_ledge_inner = 8.50           # Supports R = 8.50..10.00 mm (1.50 mm outer rim of Ø 20.0 mm flange)
    ledge_h = r_clutch_bore - r_ledge_inner  # 3.50 mm (Z = 33.70..37.20 mm)
    thrust_collar_outer = bd.Pos(0.0, 0.0, 37.20 - ledge_h) * bd.Cylinder(
        radius=r_clutch_bore + 0.5,
        height=ledge_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    thrust_collar_bore = bd.Pos(0.0, 0.0, 37.20 - ledge_h) * bd.Cone(
        bottom_radius=r_clutch_bore,
        top_radius=r_ledge_inner,
        height=ledge_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body + (thrust_collar_outer - thrust_collar_bore)

    # 4. Cut front vertical gothic-arched viewing window slot (Z = 82..136 mm along -Y, 14.0 mm inner width < 25.0 mm ball)
    #    PLUS Lower Ball Return Intake Portal along -Y (X = 0.0, Y = -34.0..-17.5 mm, Z = 41.5..71.5 mm
    #    with 45° self-supporting roof) connecting track_seg_01's enclosed -90° catch basin
    #    (X = 0.0, Y = -42.0 mm, Z_marble = 56.8 mm) directly into the -Y vertical ball guide flute
    #    at (X = 0.0, Y = -17.5 mm, Z_marble = 54.5 mm)!
    view_slot = _make_arched_viewing_window_cutter(z_min=82.0, straight_h=47.0)
    p_in_outer = bd.Vector(0.0, -45.5, 56.3)
    p_in_inner = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 52.0)
    in_vec = p_in_inner - p_in_outer
    in_plane = bd.Plane(origin=p_in_outer, z_dir=in_vec.normalized())
    intake_chute = (
        (bd.Pos(p_in_inner.X, p_in_inner.Y, p_in_inner.Z) * bd.Sphere(radius=13.8))
        + (
            in_plane
            * bd.Cylinder(
                radius=13.8,
                height=in_vec.length,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        + (
            bd.Pos(0.0, -27.5, 67.5)
            * bd.Cone(
                bottom_radius=6.5,
                top_radius=1.5,
                height=5.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
    )
    body = body - view_slot - intake_chute

    # 5a. Dual-Compatible Auger Lift Motor Bay at (0, 0) inside the Ø 28.0 mm Shroud Tower:
    la002_pocket = bd.Pos(0.0, 0.0, -0.1) * bd.Box(
        LA002_N20_POCKET_X + 0.4,  # 12.8 mm
        LA002_N20_POCKET_Y + 0.4,  # 10.8 mm
        LA002_N20_POCKET_Z + 0.3,  # 26.3 mm (Z = 0..26.2 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    pg002_bay = bd.Pos(0.0, 0.0, -0.1) * bd.Box(
        PG002_SERVO_BAY_X + 0.4,   # 23.6 mm
        PG002_SERVO_BAY_Y + 0.4,   # 12.9 mm
        PG002_SERVO_BAY_Z + 0.3,   # 24.3 mm (Z = 0..24.2 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body - la002_pocket - pg002_bay

    # 5b. Stepped Bottom Electronics Bay at (X = 0.0, Y = -33.0):
    batt_bay = bd.Pos(0.0, -33.0, -0.1) * bd.Box(
        BATTERY_14500_BAY_X + 0.6,  # 54.6 mm
        BATTERY_14500_BAY_Y + 0.6,  # 31.6 mm
        BATTERY_14500_BAY_Z + 0.4,  # 16.9 mm (Z = 0.0..16.8 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    m5_atom_hdriver_bay = bd.Pos(0.0, -33.0, -0.1) * bd.Box(
        49.2,                       # 48.0 mm M5Stack Atomic H-Driver + 1.2 mm clearance
        25.2,                       # 24.0 mm M5Stack Atomic H-Driver + 1.2 mm clearance
        20.4,                       # Z = 0.0..20.3 mm (18.9 mm clear above Z = 1.4 mm cover lip)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body - batt_bay - m5_atom_hdriver_bay
    for bx in (-30.0, 30.0):
        batt_m25 = bd.Pos(bx, -33.0, -0.1) * bd.Cylinder(
            radius=AA050_M25_TAP_DIA / 2.0,
            height=AA050_M25_TAP_DEPTH + 0.1,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        body = body - batt_m25

    # 5c. Rear (-X) Single-Cable 12V DC Barrel Jack Port (Ø 11.40 mm M11 DC-099 5.5x2.1mm Panel Mount)
    #     & Dual-Compatible Power Switch / Entry Bay at (X = -46.0, Y = 0.0, Z = 4.0..16.0 mm):
    xa007_bay = bd.Pos(-46.0, 0.0, 3.8) * bd.Box(
        XA007_SWITCH_BAY_X + 0.6,  # 22.6 mm
        XA007_SWITCH_BAY_Y + 0.6,  # 14.6 mm
        XA007_SWITCH_BAY_Z + 0.6,  # 12.6 mm (Z = 3.8..16.4 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    xa007_toggle_slot = bd.Pos(-68.0, 0.0, 6.0) * bd.Box(
        24.0,
        10.0,
        8.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Horizontal Ø 11.40 mm (R = 5.70 mm) panel-mount DC barrel jack bore along -X (Y = 0, Z = 10.0 mm)
    # with internal +Y/-Y pigtail routing portals straight into the Ø 135 mm Hollow Root Vault
    r_dc_jack = DC_BARREL_JACK_BORE_DIA / 2.0  # 5.70 mm (fits Ø 11.0-11.2 mm M11x0.75 DC-099 barrel jack)
    dc_jack_bore = (
        bd.Plane(origin=(-75.0, 0.0, DC_BARREL_JACK_Z_CENTER), z_dir=(1.0, 0.0, 0.0))
        * bd.Cylinder(
            radius=r_dc_jack,
            height=19.0,  # X = -75.0 .. -56.0 mm (opens into rear nut-seat chamber)
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    dc_jack_vault_portal = bd.Pos(-46.0, 0.0, 4.5) * bd.Box(
        12.0,
        24.0,  # Opens +Y and -Y sides of xa007_boss into the Hollow Root Vault for 18 AWG pigtails
        9.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body - xa007_bay - xa007_toggle_slot - dc_jack_bore - dc_jack_vault_portal
    for sw_y in (-9.5, 9.5):
        sw_m25 = bd.Pos(-46.0, sw_y, 4.0) * bd.Cylinder(
            radius=AA050_M25_TAP_DIA / 2.0,
            height=AA050_M25_TAP_DEPTH,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        body = body - sw_m25

    # 6. Cut bottom cable exit slot & internal wire-routing pass-through notches
    #    (including the bottom wire exit notch in the Ø 28.0 mm central motor shroud tower)
    cable_slot = bd.Pos(-TRUNK_BASE_FLANGE_R / 2.0, 0.0, -0.1) * bd.Box(
        TRUNK_BASE_FLANGE_R + 10.0,
        6.0,
        5.1,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    motor_to_pdb_tunnel = bd.Pos(0.0, -11.5, -0.1) * bd.Box(
        6.5,
        14.0,
        7.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cob_wire_entry_port = bd.Pos(16.5, -31.5, 35.0) * bd.Box(
        7.5,
        12.0,
        6.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cob_wire_conduit = bd.Pos(16.5, -27.5, 6.0) * bd.Box(
        7.5,
        7.0,
        35.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cob_wire_conduit_roof = bd.Pos(16.5, -29.5, 41.5) * bd.Cone(
        bottom_radius=5.0,
        top_radius=0.6,
        height=4.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = (
        body
        - cable_slot
        - motor_to_pdb_tunnel
        - cob_wire_entry_port
        - cob_wire_conduit
        - cob_wire_conduit_roof
    )

    # 6c. Integrated Root-Flare Holster Socket for the Magic_LED_Wand at theta = +30°
    #     (R = 52.0 mm -> X = +45.03 mm, Y = +26.00 mm)
    wand_boss = bd.Pos(wand_x, wand_y, 0.0) * bd.Cylinder(
        radius=9.0,
        height=27.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wand_bore = bd.Pos(wand_x, wand_y, 5.5) * bd.Cylinder(
        radius=6.0,
        height=22.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wand_bore_floor = bd.Pos(wand_x, wand_y, 1.5) * bd.Cone(
        bottom_radius=2.0,
        top_radius=6.0,
        height=4.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wand_bore_chamfer = bd.Pos(wand_x, wand_y, 25.8) * bd.Cone(
        bottom_radius=6.0,
        top_radius=7.4,
        height=1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = (body + wand_boss) - wand_bore - wand_bore_floor - wand_bore_chamfer

    # 7. Cut oversized 10.0 x 8.0 mm rear (-X) Connector-Pass-Through wire conduit along trunk wall
    body = _cut_rear_wire_conduit(body, TRUNK_SECTION_HEIGHT, is_base=True)

    # 8. Cut 60-degree helical female dovetail sockets (above electronics hub cone)
    body = _cut_helical_dovetails_for_section(
        body,
        z_section_min=0.0,
        z_section_max=TRUNK_SECTION_HEIGHT,
        local_z_min_safe=46.0,
        local_z_max_safe=TRUNK_SECTION_HEIGHT - DOVETAIL_SLOT_H - 4.0,
    )

    # 8b. Cut front (-Y) vertical elevation ruler ticks alongside viewing window (Z = 95..125 mm)
    body = _cut_front_elevation_ruler_for_section(
        body, z_section_min=0.0, local_z_min=92.0, local_z_max=132.0
    )

    # 9. Engrave hidden assembly number "1" on the flat top annular rim of the male tenon
    #    (Z = 165.0 mm, Y = +23.9 mm — 100% hidden inside trunk_mid's bottom socket once stacked!)
    num_1 = bd.Pos(0.0, 23.9, TRUNK_SECTION_HEIGHT + TENON_HEIGHT) * make_engraved_label_solid(
        "1", char_h=4.4, depth=0.85
    )
    body = body - num_1

    return body.solid()


def build_base_bottom_cover() -> bd.Solid:
    """Build the removable Twist-Lock / Magnetic Bottom Service Lid (`Base_Bottom_Cover`,
    Toolhead 1 - Dark Wood Brown #4A2F1D):
      - Flat, 100% support-free 3.0 mm thick circular service lid (Ø 45.0 mm disk + 4x quarter-turn
        bayonet / captive-magnet tabs = Ø 52.0 mm diagonal span, 45.0 x 45.0 mm cardinal AABB)
        that closes the central access port of the Hollow Root Vault in Trunk_Base
      - 4x ventilation louvers for thermal convection
      - 4x captive CA001 magnet sockets (Ø 4.25 x 2.20 mm) on the 4 bayonet tabs
      - Central & rear sight/access ports for the M5Stack status RGB LED & programmable button
    """
    disk = bd.Cylinder(
        radius=22.5,
        height=BASE_BOTTOM_COVER_THICK,  # 3.0 mm thick
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # 4x quarter-turn bayonet / magnet tabs at 45°, 135°, 225°, 315°
    for deg in (45.0, 135.0, 225.0, 315.0):
        rad = math.radians(deg)
        tx = 21.5 * math.cos(rad)
        ty = 21.5 * math.sin(rad)
        tab = bd.Pos(tx, ty, 0.0) * bd.Cylinder(
            radius=4.5,
            height=BASE_BOTTOM_COVER_THICK,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        disk = disk + tab

    # Cut 4x captive magnet pockets (Ø 4.25 x 2.20 mm) on the top face (Z = 0.80..3.10 mm) of the 4 tabs
    for deg in (45.0, 135.0, 225.0, 315.0):
        rad = math.radians(deg)
        tx = 21.5 * math.cos(rad)
        ty = 21.5 * math.sin(rad)
        mag_pocket = bd.Pos(tx, ty, BASE_BOTTOM_COVER_THICK - MAGNET_DEPTH) * bd.Cylinder(
            radius=MAGNET_DIA / 2.0,
            height=MAGNET_DEPTH + 0.1,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        disk = disk - mag_pocket

    # Cut 4x ventilation louvers (16.0 x 2.4 mm through-slots)
    for ly in (-11.0, -4.5, 4.5, 11.0):
        louver = bd.Pos(0.0, ly, -0.1) * bd.Box(
            16.0 if abs(ly) > 6.0 else 12.0,
            2.4,
            BASE_BOTTOM_COVER_THICK + 0.2,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        disk = disk - louver

    # Central Ø 5.0 mm button/LED access port + rear cable notch
    center_port = bd.Pos(0.0, 0.0, -0.1) * bd.Cylinder(
        radius=2.5,
        height=BASE_BOTTOM_COVER_THICK + 0.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    rear_notch = bd.Pos(-21.5, 0.0, -0.1) * bd.Box(
        6.0,
        6.0,
        BASE_BOTTOM_COVER_THICK + 0.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Upward Snap-In Hollow Retaining Collar (Ø 23.60 mm OD / Ø 19.60 mm ID x 2.8 mm tall, Z = 3.0..5.8 mm)
    # Snaps concentrically inside Trunk_Base's central Ø 24.00 mm (R = 12.00 mm) motor shroud bore
    # with 0.20 mm radial clearance so Base_Bottom_Cover locks in place even without magnets!
    snap_collar_outer = (
        bd.Pos(0.0, 0.0, BASE_BOTTOM_COVER_THICK)
        * bd.Cylinder(
            radius=11.80,
            height=2.2,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        + bd.Pos(0.0, 0.0, BASE_BOTTOM_COVER_THICK + 2.2)
        * bd.Cone(
            bottom_radius=11.80,
            top_radius=11.20,
            height=0.6,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    snap_collar_inner = bd.Pos(0.0, 0.0, BASE_BOTTOM_COVER_THICK - 0.1) * bd.Cylinder(
        radius=9.80,
        height=3.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    snap_collar_slots = (
        bd.Pos(-11.0, 0.0, BASE_BOTTOM_COVER_THICK - 0.1)
        * bd.Box(8.0, 7.0, 3.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        + bd.Pos(0.0, -11.0, BASE_BOTTOM_COVER_THICK - 0.1)
        * bd.Box(7.5, 8.0, 3.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    snap_collar = snap_collar_outer - snap_collar_inner - snap_collar_slots
    cover = (disk - center_port - rear_notch) + snap_collar
    return assign_toolhead(cover.solid(), "Base_Bottom_Cover", 1)


def build_conduit_cover_strip() -> bd.Solid:
    """Build the snap-on brown cover strip (`Conduit_Cover_Strip`, Toolhead 1 - Dark Wood Brown #4A2F1D)
    for the oversized 10.0 mm wide x 8.0 mm deep rear Connector-Pass-Through trunk wiring conduit:
      - Printed flat on the bed (Z = 0.0, 100% support-free): 68.0 mm long x 11.2 mm wide x 2.6 mm thick
      - Features a 11.2 mm wide outer depth-stop flange (+0.6 mm per side over the 10.0 mm conduit)
        and twin snap-fit retention rails (9.80 mm across outer ribs with 6.8 mm central flex gap)
        that press-fit snugly into the 10.0 mm wide rear trunk channel after threading pre-terminated plugs.
    """
    face_plate = bd.Box(
        11.2,
        CONDUIT_COVER_STRIP_H,      # 68.0 mm
        1.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    left_rail = bd.Pos(-4.15, 0.0, 1.2) * bd.Box(
        1.5,
        CONDUIT_COVER_STRIP_H - 4.0,
        1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    right_rail = bd.Pos(4.15, 0.0, 1.2) * bd.Box(
        1.5,
        CONDUIT_COVER_STRIP_H - 4.0,
        1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    strip = face_plate + left_rail + right_rail
    return assign_toolhead(strip.solid(), "Conduit_Cover_Strip", 1)


def build_battery_cover() -> bd.Solid:
    """Build the printable Battery_Cover latch plate (Toolhead 1 - Dark Wood Brown #4A2F1D)
    for the bottom electronics bay in Trunk_Base (fits Bambu IA005 Power Hub, M5Stack Atomic
    H-Driver ESP32 K050, or 14500 Battery Pack), with 2x M2.5 (AA050) counterbored through-holes
    at X = ±30.0 mm and a central Ø 5.0 mm status-LED / button access port.
    """
    plate = bd.Box(
        66.0,
        34.0,
        2.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    lip = bd.Pos(0.0, 0.0, 2.6) * bd.Box(
        53.6,
        30.6,
        1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cover = plate + lip
    status_port = bd.Pos(0.0, 0.0, -0.1) * bd.Cylinder(
        radius=2.5,
        height=5.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cover = cover - status_port
    for bx in (-30.0, 30.0):
        thru = bd.Pos(bx, 0.0, -0.1) * bd.Cylinder(
            radius=AA050_M25_THROUGH_DIA / 2.0,
            height=5.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        cbore = bd.Pos(bx, 0.0, -0.1) * bd.Cylinder(
            radius=AA050_M25_CBORE_DIA / 2.0,
            height=1.3,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        cover = cover - thru - cbore
    return assign_toolhead(cover.solid(), "Battery_Cover", 1)


def build_trunk_mid() -> bd.Solid:
    """Build Section 2 (trunk_mid): local Z = 0..150 mm + 15 mm tenon (global Z = 150..300 mm)."""
    body = _make_bark_textured_trunk_column(
        z_min=0.0,
        z_max=TRUNK_SECTION_HEIGHT,
        z_global_offset=TRUNK_SECTION_HEIGHT,
    )
    tenon = make_keyed_male_tenon(z_base=TRUNK_SECTION_HEIGHT, height=TENON_HEIGHT)
    body = body + tenon

    # Female socket at bottom (Z = 0..15.2 mm + 45-deg roof)
    socket_cutter = make_keyed_female_socket_cutter(z_base=-0.1, height=TENON_HEIGHT + 0.1)
    body = body - socket_cutter

    # Continuous Ø 41.0 mm vertical through-bore + Ø 26.6 mm (-Y) vertical ball guide flute
    bore = bd.Cylinder(
        radius=AUGER_BORE_DIA / 2.0,
        height=TRUNK_SECTION_HEIGHT + TENON_HEIGHT + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ).locate(bd.Location((0.0, 0.0, -0.5)))
    flute_cutter = _make_vertical_ball_flute_cutter(
        z_min=-0.5,
        height=TRUNK_SECTION_HEIGHT + TENON_HEIGHT + 2.0,
    )
    body = body - bore - flute_cutter

    # Rear vertical 4.0 x 3.0 mm wire conduit for Bambu LED Lamp Kit 001 USB cable
    body = _cut_rear_wire_conduit(body, TRUNK_SECTION_HEIGHT)

    # Front vertical gothic-arched auger viewing window slot (Z = 28..122 mm along -Y, 14.0 mm inner width < 25.0 mm ball)
    view_slot = _make_arched_viewing_window_cutter(z_min=28.0, straight_h=87.0)
    body = body - view_slot

    # 60-degree helical female dovetail sockets for global Z in [150, 300)
    body = _cut_helical_dovetails_for_section(
        body,
        z_section_min=TRUNK_SECTION_HEIGHT,
        z_section_max=2.0 * TRUNK_SECTION_HEIGHT,
        local_z_min_safe=TENON_HEIGHT + 8.0,
        local_z_max_safe=TRUNK_SECTION_HEIGHT - DOVETAIL_SLOT_H - 8.0,
    )

    # Cut front (-Y) vertical elevation ruler ticks alongside viewing window (global Z = 175..275 mm)
    body = _cut_front_elevation_ruler_for_section(
        body, z_section_min=TRUNK_SECTION_HEIGHT, local_z_min=24.0, local_z_max=126.0
    )

    # Engrave hidden assembly number "2" on the flat top annular rim of the male tenon
    # (Z = 165.0 mm, Y = +23.9 mm — 100% hidden inside trunk_top's bottom socket once stacked!)
    num_2 = bd.Pos(0.0, 23.9, TRUNK_SECTION_HEIGHT + TENON_HEIGHT) * make_engraved_label_solid(
        "2", char_h=4.4, depth=0.85
    )
    body = body - num_2

    return body.solid()


def build_trunk_top() -> bd.Solid:
    """Build Section 3 (trunk_top): local Z = 0..150 mm (global Z = 300..450 mm).
    Features:
      - Ø 41.0 mm auger bore + Ø 26.6 mm (-Y) vertical ball guide flute
      - Sloped Ø 28.0 mm Upper Ball Discharge Chute at local Z = 134.5 -> 131.5 mm
        (global Z = 434.5 -> 431.5 mm, completely underneath the Z = 450.0 mm Bambu LED Lamp Puck!)
        that discharges rising marbles directly onto track_seg_14_top_entry at 1665° (-135°).
    """
    body = _make_bark_textured_trunk_column(
        z_min=0.0,
        z_max=TRUNK_SECTION_HEIGHT,
        z_global_offset=2.0 * TRUNK_SECTION_HEIGHT,
    )

    # Female socket at bottom (Z = 0..15.2 mm + 45-deg roof)
    socket_cutter = make_keyed_female_socket_cutter(z_base=-0.1, height=TENON_HEIGHT + 0.1)
    body = body - socket_cutter

    # Continuous Ø 41.0 mm vertical through-bore + Ø 26.6 mm (-Y) vertical ball guide flute
    bore = bd.Cylinder(
        radius=AUGER_BORE_DIA / 2.0,
        height=TRUNK_SECTION_HEIGHT + 2.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ).locate(bd.Location((0.0, 0.0, -0.5)))
    flute_cutter = _make_vertical_ball_flute_cutter(
        z_min=-0.5,
        height=136.0,
    )
    flute_roof = bd.Pos(0.0, -AUGER_BALL_ORBIT_R, 135.0) * bd.Cone(
        bottom_radius=AUGER_FLUTE_R,
        top_radius=1.5,
        height=12.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Sloped Upper Ball Discharge Chute along -Y (global Z = 436.2 -> 432.2 mm, below Z = 450 mm Lamp Puck!)
    # Discharges rising marbles straight along -Y into track_seg_14_top_entry's enclosed catch basin at 1710° (0, -42.5)
    p_chute_start = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 136.2)
    p_chute_end = bd.Vector(0.0, -42.5, 132.2)
    chute_vec = p_chute_end - p_chute_start
    chute_plane = bd.Plane(origin=p_chute_start, z_dir=chute_vec.normalized())
    upper_discharge_chute = (
        (bd.Pos(p_chute_start.X, p_chute_start.Y, p_chute_start.Z) * bd.Sphere(radius=13.8))
        + (
            chute_plane
            * bd.Cylinder(
                radius=13.8,
                height=chute_vec.length + 4.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        + (
            bd.Pos(0.0, -26.0, 146.0)
            * bd.Cone(
                bottom_radius=13.5,
                top_radius=1.5,
                height=3.5,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
    )
    body = body - bore - flute_cutter - flute_roof - upper_discharge_chute

    # Rear vertical 4.0 x 3.0 mm wire conduit
    body = _cut_rear_wire_conduit(body, TRUNK_SECTION_HEIGHT)

    # Front vertical gothic-arched auger viewing window slot (Z = 28..116 mm along -Y, 14.0 mm inner width < 25.0 mm ball)
    view_slot = _make_arched_viewing_window_cutter(z_min=28.0, straight_h=81.0)
    body = body - view_slot

    # 60-degree helical female dovetail sockets for global Z in [300, 450]
    body = _cut_helical_dovetails_for_section(
        body,
        z_section_min=2.0 * TRUNK_SECTION_HEIGHT,
        z_section_max=3.0 * TRUNK_SECTION_HEIGHT,
        local_z_min_safe=TENON_HEIGHT + 8.0,
        local_z_max_safe=TRUNK_SECTION_HEIGHT - DOVETAIL_SLOT_H - 12.0,
    )

    # Cut front (-Y) vertical elevation ruler ticks alongside viewing window (global Z = 325..400 mm)
    body = _cut_front_elevation_ruler_for_section(
        body, z_section_min=2.0 * TRUNK_SECTION_HEIGHT, local_z_min=24.0, local_z_max=118.0
    )

    # Recessed Ø 46.2 x 2.5 mm Topper LED Ring Seat on top rim (Z = 147.5..150.0 mm, R = 20.5..23.1 mm)
    # Cradles the Ø 45.0 mm Sparkleiot 16-Bit WS2812 RGB LED Ring (B09YTMNGTD) flat and centered
    # 12 mm above the auger, with a 6.5 mm wide rear (-X) wire exit channel into the rear trunk conduit
    topper_ring_seat = bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT - 2.5) * bd.Cylinder(
        radius=23.1,
        height=3.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    topper_ring_wire_slot = bd.Pos(-29.0, 0.0, TRUNK_SECTION_HEIGHT - 3.2) * bd.Box(
        18.0,
        WIRE_CONDUIT_W,
        8.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Upward Crown Centering Tenon Collar (Ø 59.40 mm OD / Ø 50.00 mm ID x 4.0 mm tall, Z = 150.0..154.0 mm)
    # Mates concentrically inside golden_apple_topper's Ø 60.00 mm (R = 30.00 mm) bottom socket with
    # 0.30 mm radial clearance so the Apple Topper locks positively onto trunk_top and cannot slide off!
    crown_collar_outer = (
        bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT - 0.2)
        * bd.Cylinder(
            radius=29.70,
            height=3.4,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        + bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT + 3.2)
        * bd.Cone(
            bottom_radius=29.70,
            top_radius=28.90,
            height=0.8,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    crown_collar_inner = bd.Pos(0.0, 0.0, TRUNK_SECTION_HEIGHT - 0.5) * bd.Cylinder(
        radius=25.00,
        height=5.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    crown_collar = crown_collar_outer - crown_collar_inner
    body = body + crown_collar

    # Engrave hidden assembly number "3" on the flat top annular rim of the Crown Centering Tenon Collar
    # (Z = 154.0 mm, Y = +27.1 mm — 100% covered underneath golden_apple_topper once assembled!)
    num_3 = bd.Pos(0.0, 27.1, TRUNK_SECTION_HEIGHT + 4.0) * make_engraved_label_solid(
        "3", char_h=3.6, depth=0.85
    )
    body = body - topper_ring_seat - topper_ring_wire_slot - num_3

    return body.solid()


def build_all_trunk_parts() -> dict[str, bd.Solid]:
    """Return dictionary of all 3 stackable trunk sections, Base_Bottom_Cover,
    Conduit_Cover_Strip, and Battery_Cover (Toolhead 1 - Dark Wood Brown #4A2F1D).
    """
    return {
        "trunk_base": assign_toolhead(build_trunk_base(), "trunk_base", 1),
        "trunk_mid": assign_toolhead(build_trunk_mid(), "trunk_mid", 1),
        "trunk_top": assign_toolhead(build_trunk_top(), "trunk_top", 1),
        "Base_Bottom_Cover": build_base_bottom_cover(),
        "Conduit_Cover_Strip": build_conduit_cover_strip(),
        "Battery_Cover": build_battery_cover(),
    }


if __name__ == "__main__":
    for name, part in build_all_trunk_parts().items():
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, bbox={bb.size}")
