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
    AUGER_BALL_ORBIT_R,
    AUGER_BORE_DIA,
    AUGER_FLUTE_R,
    BOTTOM_TRAY_OUTER_DIA,
    BOTTOM_TRAY_RABBET_DIA,
    BOTTOM_TRAY_TAB_COORDS,
    BOTTOM_TRAY_THICK,
    BRACKET_STATION_COUNT,
    CONDUIT_STRIP_LEN_BASE,
    CONDUIT_STRIP_LEN_MID,
    CONDUIT_STRIP_LEN_TOP,
    DC_BARREL_JACK_BORE_DIA,
    DC_BARREL_JACK_Z_CENTER,
    DOVETAIL_ANGULAR_STEP_DEG,
    DOVETAIL_BASE_W_TOP,
    DOVETAIL_ENTRY_DEPTH,
    DOVETAIL_ENTRY_H,
    DOVETAIL_ENTRY_PEAK_W,
    DOVETAIL_ENTRY_W,
    DOVETAIL_NECK_W_TOP,
    DOVETAIL_RADIAL_DEPTH,
    DOVETAIL_SLOT_H,
    DOVETAIL_SLOT_Z_OFFSET,
    DOVETAIL_TAPER_W,
    FIT_TOLERANCE,
    HELIX_Z_END,
    LA002_N20_POCKET_X,
    LA002_N20_POCKET_Y,
    LA002_N20_POCKET_Z,
    MOTOR_SHROUD_OD,
    ROOT_VAULT_CLEAR_R,
    TENON_HEIGHT,
    TENON_KEY_FLAT_DEPTH,
    TENON_NOMINAL_R,
    TOP_FEEDER_RISE_Z,
    TOP_FEEDER_START_R,
    TRACK_BASE_Y,
    TRUNK_BASE_FLANGE_R,
    TRUNK_OUTER_R,
    TRUNK_SECTION_HEIGHT,
    UCTRONICS_BUCK_BAY_X,
    UCTRONICS_BUCK_BAY_Y,
    WAGO_221_BAY_X,
    WAGO_221_BAY_Y,
    WIRE_CONDUIT_ANGLE_DEG,
    WIRE_CONDUIT_D,
    WIRE_CONDUIT_W,
    assign_toolhead,
    closed_loop_track_point,
    helix_z,
    make_engraved_label_solid,
)


def _tenon_keep_envelope(r_clip_150: float, x_max: float, y_min: float, r_max: float, z_h: float) -> bd.Solid:
    """Build combined XY key-flat & 150° conduit radial flat clipping prism for trunk tenon/socket."""
    xy_box = bd.Pos(0.5 * (-r_max + x_max), 0.5 * (y_min + r_max), -0.5) * bd.Box(
        x_max - (-r_max),
        r_max - y_min,
        z_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # Clip radially along WIRE_CONDUIT_ANGLE_DEG (150°) at u_150 <= r_clip_150
    w_150 = r_clip_150 - (-45.0)
    clip_150 = (
        bd.Rot(0.0, 0.0, WIRE_CONDUIT_ANGLE_DEG)
        * bd.Pos(0.5 * (-45.0 + r_clip_150), 0.0, -0.5)
        * bd.Box(w_150, 90.0, z_h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    )
    return (xy_box & clip_150).solid()


def make_keyed_male_tenon(z_base: float, height: float = TENON_HEIGHT) -> bd.Solid:
    """Create a male cylindrical tenon with 0.20 mm radial clearance, +X keyed flat,
    150° radial chord flat behind the relocated connector conduit (R <= 24.50 mm), and -Y
    flat behind the vertical ball guide flute (Y >= -14.50 mm).
    """
    r_male = TENON_NOMINAL_R - FIT_TOLERANCE  # 27.30 mm
    cyl = bd.Cylinder(
        radius=r_male,
        height=height,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    x_max = r_male - TENON_KEY_FLAT_DEPTH  # +25.30 mm
    r_clip_150 = TRUNK_OUTER_R - WIRE_CONDUIT_D - 1.00  # 24.50 mm (1.0 mm behind 25.50 mm conduit floor)
    keep_env = _tenon_keep_envelope(r_clip_150, x_max, -14.50, r_male + 2.0, height + 2.0)
    return (cyl & keep_env).locate(bd.Location((0.0, 0.0, z_base))).solid()


def make_keyed_female_socket_cutter(z_base: float = 0.0, height: float = TENON_HEIGHT) -> bd.Solid:
    """Create the female socket cutter with 0.20 mm clearance, +X/150°/-Y keyed flats, and 45-deg roof."""
    r_female = TENON_NOMINAL_R  # 27.50 mm (0.20 mm radial gap vs r_male = 27.30 mm)
    socket_h = height + FIT_TOLERANCE  # 15.20 mm axial clearance
    cyl = bd.Cylinder(
        radius=r_female,
        height=socket_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    x_max = (TENON_NOMINAL_R - FIT_TOLERANCE - TENON_KEY_FLAT_DEPTH) + FIT_TOLERANCE  # +25.50 mm
    r_clip_150 = (TRUNK_OUTER_R - WIRE_CONDUIT_D - 1.00) + FIT_TOLERANCE  # 24.70 mm
    keep_env = _tenon_keep_envelope(r_clip_150, x_max, -14.70, r_female + 2.0, socket_h + 2.0)
    keyed_cyl = cyl & keep_env

    # Self-supporting 45-degree conical roof transition from r_female to auger bore radius
    r_bore = AUGER_BORE_DIA / 2.0
    cone_h = r_female - r_bore
    roof_cone = bd.Pos(0.0, 0.0, socket_h) * bd.Cone(
        bottom_radius=r_female,
        top_radius=r_bore,
        height=cone_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    roof_keep = _tenon_keep_envelope(r_clip_150, x_max, -14.70, r_female + 2.0, socket_h + cone_h + 2.0)
    cutter = (keyed_cyl + (roof_cone & roof_keep)).locate(bd.Location((0.0, 0.0, z_base)))
    return cutter.solid()


def make_female_dovetail_slot_cutter() -> bd.Solid:
    """Build a keyhole drop-in 45-degree female dovetail socket cutter with support-free entry window.

    Geometry (local coordinates before placement at R=TRUNK_OUTER_R, theta, z_slot):
      - Lower active dovetail seat (Z = 0..DOVETAIL_SLOT_H = 18.0 mm):
          X in [-4.50, +1.50 mm], tapered downward by DOVETAIL_TAPER_W (0.80 mm),
          mouth width 7.0 -> 6.2 mm, base width 16.0 -> 15.2 mm.
      - Upper keyhole drop-in entry window (Z = 18.0..36.6 mm):
          16.20 mm wide (tenon base 15.40 + 0.80 mm) x 4.85 mm deep (tenon depth 4.35 + 0.50 mm)
          x 18.60 mm straight height (tenon height 17.75 + 0.85 mm) so brackets push radially
          inward while the trunk is already stacked and then slide down 18.2 mm into the dovetail.
      - Support-free 45-deg gable roof (Z = 36.6..43.9 mm):
          Tapers linearly at 45 deg to a 1.60 mm peak bridge (zero horizontal bridges > 8 mm).
    """
    d = DOVETAIL_RADIAL_DEPTH  # 4.5 mm
    out_ext = 1.5              # Extend past outer cylinder surface for clean boolean cut

    # Top of active dovetail slot (Z = DOVETAIL_SLOT_H)
    half_base_top = DOVETAIL_BASE_W_TOP / 2.0  # 8.0 mm at X = -d
    half_neck_top = DOVETAIL_NECK_W_TOP / 2.0  # 3.5 mm at X = 0.0

    # Bottom of active dovetail slot (Z = 0), tapered inward by DOVETAIL_TAPER_W / 2 per side
    taper = DOVETAIL_TAPER_W / 2.0
    half_base_bot = half_base_top - taper
    half_neck_bot = half_neck_top - taper

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

    w_bot = bd.Wire([bd.Edge.make_line(pts_bot[i], pts_bot[i + 1]) for i in range(6)])
    w_top = bd.Pos(0.0, 0.0, DOVETAIL_SLOT_H) * bd.Wire(
        [bd.Edge.make_line(pts_top[i], pts_top[i + 1]) for i in range(6)]
    )
    body = bd.Solid.make_loft([w_bot, w_top], ruled=True)

    # Upper keyhole entry window + 45-deg self-supporting gable roof
    win_d = DOVETAIL_ENTRY_DEPTH         # 4.85 mm
    win_hw = DOVETAIL_ENTRY_W / 2.0      # 8.10 mm
    win_z0 = DOVETAIL_SLOT_H             # 18.00 mm
    win_z1 = win_z0 + DOVETAIL_ENTRY_H   # 36.60 mm
    peak_hw = DOVETAIL_ENTRY_PEAK_W / 2.0  # 0.80 mm
    roof_dz = win_hw - peak_hw           # 7.30 mm (exact 45-deg roof slope)

    entry_win = bd.Pos(0.5 * (out_ext - win_d), 0.0, win_z0) * bd.Box(
        win_d + out_ext,
        2.0 * win_hw,
        DOVETAIL_ENTRY_H,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    def _win_wire(z_val: float, hw: float) -> bd.Wire:
        pts = [
            (-win_d, -hw),
            (out_ext, -hw),
            (out_ext, hw),
            (-win_d, hw),
            (-win_d, -hw),
        ]
        return bd.Pos(0.0, 0.0, z_val) * bd.Wire(
            [bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(4)]
        )

    roof = bd.Solid.make_loft(
        [_win_wire(win_z1, win_hw), _win_wire(win_z1 + roof_dz, peak_hw)],
        ruled=True,
    )
    return (body + entry_win + roof).solid()


def _cut_helical_dovetails_for_section(
    part: bd.Solid,
    z_section_min: float,
    z_section_max: float,
    local_z_min_safe: float,
    local_z_max_safe: float,
) -> bd.Solid:
    """Subtract female keyhole dovetail sockets at 60-degree increments along the helical slope.

    Uses the exact unclamped mathematical height `z_global = helix_z(theta_deg) + DOVETAIL_SLOT_Z_OFFSET`
    for every 60° station (`60°..1560°`, stations 1..26). Whenever a keyhole slot's vertical span
    overlaps the section `[z_section_min, z_section_max]`, it cuts cleanly at
    `z_local = z_global - z_section_min` so slots near section seams (Z = 150 mm and Z = 300 mm)
    align seamlessly across stacked trunk sections.
    """
    _ = (local_z_min_safe, local_z_max_safe)
    base_cutter = make_female_dovetail_slot_cutter()
    roof_dz = (DOVETAIL_ENTRY_W - DOVETAIL_ENTRY_PEAK_W) / 2.0
    slot_total_h = DOVETAIL_SLOT_H + DOVETAIL_ENTRY_H + roof_dz + 0.6

    for k in range(1, BRACKET_STATION_COUNT + 1):
        theta_deg = k * DOVETAIL_ANGULAR_STEP_DEG
        z_global = helix_z(theta_deg) + DOVETAIL_SLOT_Z_OFFSET
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
    """Cut the 150-degree 'Connector-Pass-Through' wiring conduit (`10.6 mm wide x 8.5 mm deep`):
      - Relocated from 180° to `WIRE_CONDUIT_ANGLE_DEG = 150.0°` (midway between the 120° and 180°
        bracket columns so brackets never bridge across the conduit or pinch the JST-SM topper cable).
      - On `trunk_base`, runs along `R = 25.5..34.0 mm` above Z = 50.0 mm (matching
        `Conduit_Cover_Strip_Base` L = 100.0 mm) and drops inside the sloped vault ceiling
        (Z = 24.0..50.0 mm) straight into the hollow root vault without piercing the outer root hub.
    """
    z_top = total_h + TENON_HEIGHT + 2.0
    conduit_loc = bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, WIRE_CONDUIT_ANGLE_DEG))
    if is_base:
        # Upper open groove for Z = 50..167 mm along outer R = 25.5..34.0 mm at 150 deg
        upper_conduit = conduit_loc * (
            bd.Pos(TRUNK_OUTER_R, 0.0, 50.0)
            * bd.Box(
                WIRE_CONDUIT_D * 2.0,
                WIRE_CONDUIT_W,
                z_top - 50.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        # Internal drop chute (Z = 28..50.5 mm) along R = 25.5..34.0 mm entering directly into raw_vault
        inner_drop = conduit_loc * (
            bd.Pos(TRUNK_OUTER_R - WIRE_CONDUIT_D * 0.5, 0.0, 28.0)
            * bd.Box(
                WIRE_CONDUIT_D,
                WIRE_CONDUIT_W,
                22.5,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        return part - upper_conduit - inner_drop

    conduit = conduit_loc * (
        bd.Pos(TRUNK_OUTER_R, 0.0, -0.5)
        * bd.Box(
            WIRE_CONDUIT_D * 2.0,
            WIRE_CONDUIT_W,
            z_top,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    return part - conduit


def _bark_furrow_depth(deg: float, z_global: float, max_depth: float = 1.45) -> float:
    """Compute organic support-free vertical & gently twisting bark furrow depth (in mm).

    Keeps the 60° bracket dovetail columns (`d60 <= 6.5°`), the 150° rear conduit strip
    (`d150 <= 10.0°`), and the 270° (-Y) ball port / viewing window strip (`d270 <= 16.0°`)
    smooth at `R = TRUNK_OUTER_R = 34.0 mm` so every bracket, track endcap, and conduit cover
    strip mates flush with 0.000 mm³ interference.
    """
    d60 = abs(((deg + 30.0) % 60.0) - 30.0)
    d150 = abs(((deg - WIRE_CONDUIT_ANGLE_DEG + 180.0) % 360.0) - 180.0)
    d270 = abs(((deg - 270.0 + 180.0) % 360.0) - 180.0)
    env60 = 0.0 if d60 <= 6.5 else min(1.0, (d60 - 6.5) / 4.5)
    env150 = 0.0 if d150 <= 10.0 else min(1.0, (d150 - 10.0) / 4.5)
    env270 = 0.0 if d270 <= 16.0 else min(1.0, (d270 - 16.0) / 5.0)
    env = min(env60, env150, env270)
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
    """Create the widened Hollow Root Vault electronics pedestal (`Z = 0..14 mm`, `R = 72.5 mm`
    housing the Ø 135.0 mm internal clear electronics vault) and support-free root-flare
    transition cone (`Z = 14..52 mm`, `R = 72.5 -> 34.0 mm`) with continuous organic bark ridges.
    Reaches `R = 34.0 mm` early in the -Y intake sector (`Z = 34 mm`), the 60° bracket_01
    column (`Z = 41.5 mm`), and the 150° conduit channel (`Z = 48.0 mm`) while preserving
    smooth wall thickness around the 45° internal vault cone.
    """
    z_rings = [
        (0.0, 72.5, 1.25),
        (9.0, 72.5, 1.25),
        (14.0, 72.5, 1.25),
        (19.0, 67.4, 1.28),
        (21.8, 64.6, 1.30),
        (28.0, 58.3, 1.35),
        (35.0, 51.2, 1.40),
        (41.5, 44.6, 1.42),
        (48.0, 38.1, 1.44),
        (50.0, 36.1, 1.44),
        (52.0, TRUNK_OUTER_R, 1.45),
    ]
    n_pts = 120
    wires: list[bd.Wire] = []
    for z_val, r_nom, depth in z_rings:
        pts: list[bd.Vector] = []
        for ip in range(n_pts):
            deg = ip * (360.0 / n_pts)
            rad = math.radians(deg)
            d180 = abs(((deg - 180.0 + 180.0) % 360.0) - 180.0)
            d150 = abs(((deg - WIRE_CONDUIT_ANGLE_DEG + 180.0) % 360.0) - 180.0)
            d30 = abs(((deg - 30.0 + 180.0) % 360.0) - 180.0)
            d60 = abs(((deg - 60.0 + 180.0) % 360.0) - 180.0)
            d270 = abs(((deg - 270.0 + 180.0) % 360.0) - 180.0)
            hub_env = 1.0
            if z_val < 28.0:
                if d180 < 16.0:
                    hub_env = min(hub_env, max(0.0, (d180 - 11.0) / 5.0))
                if d30 < 16.0:
                    hub_env = min(hub_env, max(0.0, (d30 - 11.0) / 5.0))
            if d150 < 14.5:
                hub_env = min(hub_env, max(0.0, (d150 - 10.0) / 4.5))

            r_eff = r_nom
            # Fast taper in -Y intake sector (Z = 16 -> 34 mm)
            if z_val > 16.0 and d270 < 62.0:
                w270 = 1.0 if d270 <= 46.0 else (62.0 - d270) / 16.0
                u_fast = min(1.0, (z_val - 16.0) / (34.0 - 16.0))
                r_fast = 72.5 + (TRUNK_OUTER_R - 72.5) * u_fast
                r_eff = min(r_eff, r_nom * (1.0 - w270) + r_fast * w270)
            # Clear bracket_01 (theta = 60°, Z_slot = 42.17 mm) without blocking its saddle or dovetail
            if z_val > 14.0 and d60 < 24.0:
                w60 = 1.0 if d60 <= 12.0 else (24.0 - d60) / 12.0
                u_60 = min(1.0, (z_val - 14.0) / (41.5 - 14.0))
                r_60 = 72.5 + (TRUNK_OUTER_R - 72.5) * u_60
                r_eff = min(r_eff, r_nom * (1.0 - w60) + r_60 * w60)
            # Reach R = 34.0 mm by Z = 50.0 mm at 150° conduit so the 100 mm cover strip seats at Z = 50..150
            if z_val > 14.0 and d150 < 18.0:
                w150 = 1.0 if d150 <= 10.0 else (18.0 - d150) / 8.0
                u_150 = min(1.0, (z_val - 14.0) / (50.0 - 14.0))
                r_150 = 72.5 + (TRUNK_OUTER_R - 72.5) * u_150
                r_eff = min(r_eff, r_nom * (1.0 - w150) + r_150 * w150)

            furrow = hub_env * _bark_furrow_depth(deg, z_val, max_depth=depth)

            # Clear DC-099 M11 hex nut & barrel pocket inside the rear -X (180°) wall up to Z = 20.5 mm
            if z_val > 14.0 and d180 < 20.0:
                w180 = 1.0 if d180 <= 12.0 else (20.0 - d180) / 8.0
                r_180 = 72.5 if z_val <= 20.5 else max(34.0, 72.5 - (z_val - 20.5) * (38.5 / 31.5))
                r_eff = max(r_eff, r_nom * (1.0 - w180) + r_180 * w180)
            r = r_eff - furrow
            pts.append(bd.Vector(r * math.cos(rad), r * math.sin(rad), z_val))
        wires.append(bd.Wire.make_polygon(pts))
    return bd.Solid.make_loft(wires, ruled=True)


def _make_vault_cavity_solid() -> bd.Solid:
    """Create the smooth, 45°-self-supporting Hollow Root Vault cavity (`Ø 135.0 mm` at Z = 0..12 mm,
    conical 45° dome tapering up to Z = 52.0 mm, `>= 150,000 mm³` unobstructed cable slack dome)
    with `>= 5.0 mm` radial wood margin beneath `_make_bark_textured_base_hub()` everywhere.
    """
    z_levels = [-0.1, 12.0, 16.0, 19.0, 22.2, 28.0, 31.0, 35.0, 41.5, 48.0, 50.0, 52.0]
    n_pts = 120
    wires: list[bd.Wire] = []
    for z_val in z_levels:
        pts: list[bd.Vector] = []
        for ip in range(n_pts):
            deg = ip * (360.0 / n_pts)
            rad = math.radians(deg)
            d60 = abs(((deg - 60.0 + 180.0) % 360.0) - 180.0)
            d150 = abs(((deg - WIRE_CONDUIT_ANGLE_DEG + 180.0) % 360.0) - 180.0)
            d180 = abs(((deg - 180.0 + 180.0) % 360.0) - 180.0)
            d270 = abs(((deg - 270.0 + 180.0) % 360.0) - 180.0)

            r_eff = ROOT_VAULT_CLEAR_R if z_val <= 12.0 else max(18.0, ROOT_VAULT_CLEAR_R - (z_val - 12.0))
            if z_val > 16.0 and d270 < 62.0:
                w270 = 1.0 if d270 <= 46.0 else (62.0 - d270) / 16.0
                if z_val <= 22.2:
                    rf = 63.5 + (54.5 - 63.5) * (z_val - 16.0) / (22.2 - 16.0)
                else:
                    u_fast = min(1.0, (z_val - 22.2) / (31.0 - 22.2))
                    rf = 54.5 + (22.0 - 54.5) * u_fast
                r_eff = min(r_eff, r_eff * (1.0 - w270) + rf * w270)
            if z_val > 14.0 and d60 < 24.0:
                w60 = 1.0 if d60 <= 12.0 else (24.0 - d60) / 12.0
                u_60 = min(1.0, (z_val - 14.0) / (41.5 - 14.0))
                r_60 = 65.5 + (26.5 - 65.5) * u_60
                r_eff = min(r_eff, r_eff * (1.0 - w60) + r_60 * w60)
            if z_val > 14.0 and d150 < 18.0:
                w150 = 1.0 if d150 <= 10.0 else (18.0 - d150) / 8.0
                u_150 = min(1.0, (z_val - 14.0) / (50.0 - 14.0))
                r_150 = 65.5 + (28.0 - 65.5) * u_150
                r_eff = min(r_eff, r_eff * (1.0 - w150) + r_150 * w150)
            if z_val > 12.0 and d180 < 20.0:
                w180 = 1.0 if d180 <= 12.0 else (20.0 - d180) / 8.0
                r_180 = 67.5 if z_val <= 20.5 else max(18.0, 67.5 - (z_val - 20.5) * (38.5 / 31.5))
                r_eff = max(r_eff, r_eff * (1.0 - w180) + r_180 * w180)
            pts.append(bd.Vector(r_eff * math.cos(rad), r_eff * math.sin(rad), z_val))
        wires.append(bd.Wire.make_polygon(pts))
    return bd.Solid.make_loft(wires, ruled=True)


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
    Features the simplified 'Upright Electronics Tray + Hollow Root Vault' architecture
    (`>= 150,000 mm³` unobstructed 45° dome slack zone, zero internal pocket bridges > 12 mm):
      - Flush `Ø 135.0 x 3.00 mm` vault rabbet + 4x diagonal buttress root tab pockets with
        M2.5 tap holes (`BOTTOM_TRAY_TAB_COORDS`) receiving upright `Bottom_Electronics_Lid`.
      - Isolated `Ø 28.0 mm` (`Z = 0..44 mm`) N20 motor shroud tower (Z = 1.20..26.40 mm pocket,
        -Y wire exit tunnel at Z = 3.20..11.20 mm above the tray, and Ø 19.20 mm top-drop bore
        clearing `Motor_Clutch_Driver` down to `Z = 37.20 mm` auger thrust seat).
      - Outer `-X` `Ø 16.0 mm` `45°-gabled` `DC-099` spotface leaving exact `3.80 mm` M11
        bulkhead (`X = -71.30..-67.50 mm`) + `Ø 11.40 mm` center bore.
      - `+30°` root-flare Magic Wand holster (`Ø 19.0 mm` pillar, `Ø 12.0 mm` bore).
      - `150.0°` `WIRE_CONDUIT_ANGLE_DEG` JST-SM conduit (Z = 50..165 open groove + vault drop).
    """
    flare_base = _make_five_root_flare_solid()
    elec_hub_bark = _make_bark_textured_base_hub()
    upper_col = _make_bark_textured_trunk_column(
        z_min=0.0,
        z_max=TRUNK_SECTION_HEIGHT,
        z_global_offset=0.0,
    )
    body = flare_base + elec_hub_bark + upper_col

    # Male tenon at Z = 150..165 mm with +X/-X and 150° conduit keyed flats
    tenon = make_keyed_male_tenon(z_base=TRUNK_SECTION_HEIGHT, height=TENON_HEIGHT)
    body = body + tenon

    # Hollow 45° Root Vault retaining only motor_shroud_tower (0,0) and wand_pillar (+45.03,+26.00)
    wand_x = 52.0 * math.cos(math.radians(30.0))  # +45.03 mm
    wand_y = 52.0 * math.sin(math.radians(30.0))  # +26.00 mm
    raw_vault = _make_vault_cavity_solid()

    motor_shroud_tower = (
        bd.Pos(0.0, 0.0, 0.0)
        * bd.Cylinder(
            radius=MOTOR_SHROUD_OD / 2.0,  # R = 14.0 mm (Ø 28.0 mm)
            height=36.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        + bd.Pos(0.0, 0.0, 36.0)
        * bd.Cone(
            bottom_radius=MOTOR_SHROUD_OD / 2.0,
            top_radius=26.0,
            height=12.0,  # 45° support-free flare around upper expand_cone merging into trunk column
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        + bd.Pos(0.0, 0.0, 48.0)
        * bd.Cylinder(
            radius=26.0,
            height=6.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    wand_pillar = bd.Pos(wand_x, wand_y, 0.0) * bd.Cylinder(
        radius=9.5,
        height=44.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    body = body - (raw_vault - (motor_shroud_tower + wand_pillar))

    # 4x Diagonal root-tab rabbet pockets (Z = 0..2.95 mm, 10.6 mm width <= 12 mm bridge limit)
    # + M2.5 tap holes (Ø 2.25 x 6.5 mm into Z = 2.95..9.50 mm solid diagonal root buttresses)
    for tx, ty in BOTTOM_TRAY_TAB_COORDS:
        tdeg = math.degrees(math.atan2(ty, tx))
        tab_pocket = bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, tdeg)) * (
            bd.Pos(71.5, 0.0, -0.1)
            * bd.Box(
                10.6,
                10.6,
                BOTTOM_TRAY_THICK + 0.25,  # Z = 0..2.95 mm flush seating ceiling
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        tap_hole = bd.Pos(tx, ty, BOTTOM_TRAY_THICK + 0.1) * bd.Cylinder(
            radius=AA050_M25_TAP_DIA / 2.0,
            height=AA050_M25_TAP_DEPTH,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        body = body - tab_pocket - tap_hole

    # 3. Top-drop Auger / Clamped Driver Bore & 45° Thrust Seat:
    #    - Z = 1.20..26.20 mm: N20 (12.8 x 10.8 mm) rectangular pocket + 1.20 mm solid bed floor
    #    - Z = 24.50..26.00 mm: 45° cone expanding from R = 8.1 to R = 9.60 mm (zero flat step bridge)
    #    - Z = 26.00..37.20 mm: Ø 19.20 mm (R = 9.60 mm) bore clearing Ø 18.0 mm Motor_Clutch_Driver
    #    - Z = 37.20 mm: flat 2.20 mm upward thrust shelf (R = 9.60..11.80 mm) for Ø 22.0 mm auger flange
    #    - Z = 37.20..45.90 mm: 45° expand_cone from R = 11.80 to R = 20.50 mm (parallel 3.4 mm shroud wall)
    #    - Z = 45.80..167.0 mm: full Ø 41.0 mm upper auger bore + -Y vertical ball flute
    r_driver_bore = 9.60
    r_thrust_outer = 11.80  # Ø 23.60 mm clears CLUTCH_FLANGE_OD = 22.0 mm (R = 11.0 mm) cleanly
    r_upper_bore = AUGER_BORE_DIA / 2.0  # 20.50 mm
    cone_expand_h = r_upper_bore - r_thrust_outer  # 8.70 mm (45° support-free slope)

    la002_transition = bd.Pos(0.0, 0.0, 24.50) * bd.Cone(
        bottom_radius=8.10,
        top_radius=r_driver_bore,
        height=1.50,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    driver_bore = bd.Pos(0.0, 0.0, 25.95) * bd.Cylinder(
        radius=r_driver_bore,
        height=11.25,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    expand_cone = bd.Pos(0.0, 0.0, 37.20) * bd.Cone(
        bottom_radius=r_thrust_outer,
        top_radius=r_upper_bore,
        height=cone_expand_h,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    upper_bore = bd.Pos(0.0, 0.0, 37.20 + cone_expand_h - 0.1) * bd.Cylinder(
        radius=r_upper_bore,
        height=TRUNK_SECTION_HEIGHT + TENON_HEIGHT - (37.20 + cone_expand_h) + 2.0,
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
    body = body - la002_transition - driver_bore - expand_cone - upper_bore - flute_cutter

    # N20 motor pocket (Z = 1.20..26.40 mm) + -Y side wire tunnel (Z = 3.20..11.20 mm + 45° gable roof)
    la002_pocket = bd.Pos(0.0, 0.0, 1.20) * bd.Box(
        LA002_N20_POCKET_X + 0.4,  # 12.8 mm
        LA002_N20_POCKET_Y + 0.4,  # 10.8 mm
        LA002_N20_POCKET_Z + 0.2,  # 26.2 mm height (Z = 1.20..27.40 mm, merges into transition cone)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    la002_wire_chase = bd.Pos(0.0, -7.2, 1.20) * bd.Box(
        6.5,
        5.0,
        11.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    motor_wire_pts = [
        (-4.0, 3.20),
        (4.0, 3.20),
        (4.0, 11.20),
        (0.8, 14.40),
        (-0.8, 14.40),
        (-4.0, 11.20),
        (-4.0, 3.20),
    ]
    def _motor_wire_wire(y_pos: float) -> bd.Wire:
        return bd.Wire([
            bd.Edge.make_line((motor_wire_pts[i][0], y_pos, motor_wire_pts[i][1]),
                              (motor_wire_pts[i + 1][0], y_pos, motor_wire_pts[i + 1][1]))
            for i in range(len(motor_wire_pts) - 1)
        ])

    motor_wire_tunnel = bd.Solid.make_loft(
        [_motor_wire_wire(-4.5), _motor_wire_wire(-16.0)],
        ruled=True,
    )
    body = body - la002_pocket - la002_wire_chase - motor_wire_tunnel

    # 4. Front vertical gothic-arched viewing window slot (Z = 82..136 mm along -Y)
    #    + Lower Ball Return Intake Portal along -Y
    view_slot = _make_arched_viewing_window_cutter(z_min=82.0, straight_h=47.0)
    p_in_outer = bd.Vector(0.0, -45.5, 56.3)
    p_in_inner = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 52.0)
    in_vec = p_in_inner - p_in_outer
    in_plane = bd.Plane(origin=p_in_outer, z_dir=in_vec.normalized())
    intake_chute = (
        (bd.Pos(p_in_inner.X, p_in_inner.Y, p_in_inner.Z) * bd.Sphere(radius=13.75))
        + (
            in_plane
            * bd.Cone(
                bottom_radius=16.40,
                top_radius=13.75,
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

    # 5. Rear (-X, 180°) Single-Cable 12V DC Barrel Jack Port (DC-099):
    #    - Outer Ø 16.0 mm spotface with 45° self-supporting gable roof stopping at X = -71.30 mm,
    #      leaving an exact 3.80 mm thick M11x0.75 bulkhead against the Ø 135.0 mm vault wall (X = -67.50 mm)
    #    - Center Ø 11.40 mm bore (R = 5.70 mm) along +X at Y = 0.0, Z = 10.0 mm
    r_dc_jack = DC_BARREL_JACK_BORE_DIA / 2.0  # 5.70 mm
    dc_jack_bore = (
        bd.Plane(origin=(-76.0, 0.0, DC_BARREL_JACK_Z_CENTER), z_dir=(1.0, 0.0, 0.0))
        * bd.Cylinder(
            radius=r_dc_jack,
            height=11.0,  # X = -76.0..-65.0 mm cleanly pierces X = -71.30..-67.50 bulkhead
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    r_sf = 8.00  # Ø 16.0 mm outer spotface for DC-099 bezel/washer
    sf_pts: list[tuple[float, float]] = []
    for deg_a in range(45, -226, -15):  # Lower/side circular arc from +45° clockwise to +135°
        ra = math.radians(deg_a)
        sf_pts.append((r_sf * math.cos(ra), DC_BARREL_JACK_Z_CENTER + r_sf * math.sin(ra)))
    # 45° gable roof peak above (-5.657, +15.657) to (+5.657, +15.657) with 1.6 mm flat apex
    sf_pts.append((-0.80, DC_BARREL_JACK_Z_CENTER + r_sf * math.sin(math.radians(45.0)) + 4.857))
    sf_pts.append((0.80, DC_BARREL_JACK_Z_CENTER + r_sf * math.sin(math.radians(45.0)) + 4.857))
    sf_pts.append(sf_pts[0])
    def _sf_wire(x_pos: float) -> bd.Wire:
        return bd.Wire(
            [bd.Edge.make_line((x_pos, sf_pts[i][0], sf_pts[i][1]), (x_pos, sf_pts[i + 1][0], sf_pts[i + 1][1]))
             for i in range(len(sf_pts) - 1)]
        )

    dc_spotface = bd.Solid.make_loft([_sf_wire(-75.0), _sf_wire(-71.60)], ruled=True)  # -71.60..-67.80 = 3.80 mm!
    dc_inner_nut_seat = bd.Solid.make_loft([_sf_wire(-67.80), _sf_wire(-62.50)], ruled=True)
    body = body - dc_spotface - dc_inner_nut_seat - dc_jack_bore

    # 6. Integrated Root-Flare Holster Socket for Magic_LED_Wand at theta = +30°
    wand_boss = bd.Pos(wand_x, wand_y, 0.0) * bd.Cylinder(
        radius=9.5,
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

    # 7. Cut 150° Connector-Pass-Through wire conduit along trunk wall
    body = _cut_rear_wire_conduit(body, TRUNK_SECTION_HEIGHT, is_base=True)

    # 8. Cut 60-degree helical female dovetail sockets (stations 1..26 at Z_offset = -33.5 mm)
    body = _cut_helical_dovetails_for_section(
        body,
        z_section_min=0.0,
        z_section_max=TRUNK_SECTION_HEIGHT,
        local_z_min_safe=40.0,
        local_z_max_safe=TRUNK_SECTION_HEIGHT - DOVETAIL_SLOT_H - 4.0,
    )

    # 8b. Front (-Y) vertical elevation ruler ticks alongside viewing window
    body = _cut_front_elevation_ruler_for_section(
        body, z_section_min=0.0, local_z_min=92.0, local_z_max=132.0
    )

    # 9. Engrave hidden assembly number "1" on top rim of male tenon
    num_1 = bd.Pos(0.0, 23.9, TRUNK_SECTION_HEIGHT + TENON_HEIGHT) * make_engraved_label_solid(
        "1", char_h=4.4, depth=0.85
    )
    body = body - num_1

    return body.solid()


def _make_single_conduit_cover_strip(name: str, length_mm: float) -> bd.Solid:
    """Build a section-matched snap-on brown cover strip (Toolhead 1 - Dark Wood Brown #4A2F1D)
    for the 150° `WIRE_CONDUIT_W = 10.6 mm` Connector-Pass-Through trunk wiring conduit:
      - Printed flat on the bed (Z = 0.0, 100% support-free): `11.8 mm` wide x `length_mm` long x `2.6 mm` thick
      - Outer depth-stop flange (`11.8 mm`, +0.6 mm per side) and twin retention rails
        (`10.50 mm` outer span inside the `10.60 mm` conduit channel) along the smooth 150° bark strip.
    """
    face_plate = bd.Box(
        11.8,
        length_mm,
        1.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    left_rail = bd.Pos(-4.50, 0.0, 1.2) * bd.Box(
        1.5,
        max(10.0, length_mm - 4.0),
        1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    right_rail = bd.Pos(4.50, 0.0, 1.2) * bd.Box(
        1.5,
        max(10.0, length_mm - 4.0),
        1.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    strip = face_plate + left_rail + right_rail
    return assign_toolhead(strip.solid(), name, 1)


def build_conduit_cover_strips() -> dict[str, bd.Solid]:
    """Return all 3 section-matched 150° wire conduit cover strips:
      - `Conduit_Cover_Strip_Base` (`L = 100.0 mm`, trunk_base Z = 50..150)
      - `Conduit_Cover_Strip_Mid`  (`L = 144.0 mm`, trunk_mid  Z = 3..147)
      - `Conduit_Cover_Strip_Top`  (`L = 144.0 mm`, trunk_top  Z = 3..147)
    """
    return {
        "Conduit_Cover_Strip_Base": _make_single_conduit_cover_strip("Conduit_Cover_Strip_Base", CONDUIT_STRIP_LEN_BASE),
        "Conduit_Cover_Strip_Mid": _make_single_conduit_cover_strip("Conduit_Cover_Strip_Mid", CONDUIT_STRIP_LEN_MID),
        "Conduit_Cover_Strip_Top": _make_single_conduit_cover_strip("Conduit_Cover_Strip_Top", CONDUIT_STRIP_LEN_TOP),
    }


def build_bottom_electronics_lid() -> bd.Solid:
    """Build the upright `Bottom_Electronics_Lid` tray (Toolhead 1 - Dark Wood Brown #4A2F1D):
      - `Ø 134.6 mm x 2.80 mm` (`BOTTOM_TRAY_OUTER_DIA` x `BOTTOM_TRAY_THICK`) flat circular
        base tray nesting flush inside `trunk_base`'s `Ø 135.0 mm` vault rabbet (`Z = 0.00..2.80 mm`).
      - `4x` diagonal outer flange tabs (`BOTTOM_TRAY_TAB_COORDS` at `R = 71.0 mm`, 45°/135°/225°/315°)
        with `Ø 2.75 mm` through + `Ø 5.00 mm` counterbores for `AA050` `M2.5 x 6 mm` BHCS screws.
      - Concentric cutouts clearing `motor_shroud_tower` (`Ø 28.6 mm` at center) and
        `wand_pillar` (`Ø 19.6 mm` at `(+45.03, +26.00)`), plus `14 x 14 mm` `C008` LED/button port.
      - Upward open-top `1.6 mm`-wall snap cradles (100% support-free flat bed printing):
          * `UCTRONICS` B07XXWQ49N at `(-2.0, +36.0)` with open ±X terminal/cap space & 1.2 mm standoffs
          * Unstacked `2x WAGO 221-415` at `(+46.0, -2.5)` (+5V bus) and `(-32.5, 0.0)` (GND bus)
            with open `-X` wire portals & >16 mm lever flip clearance
          * `A092+C008` at `(-2.0, -33.0)` with open `-X/+X` (+22 mm A096 / +16 mm HT3.96-4P) ends
      - Debossed `"A"`, `"12"`, `"G"` orientation glyphs via `make_engraved_label_solid()`.
    """
    t_tray = BOTTOM_TRAY_THICK
    tray = bd.Cylinder(
        radius=BOTTOM_TRAY_OUTER_DIA / 2.0,
        height=t_tray,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # 4x diagonal mounting tabs at R = 71.0 mm (45°, 135°, 225°, 315°)
    for tx, ty in BOTTOM_TRAY_TAB_COORDS:
        tdeg = math.degrees(math.atan2(ty, tx))
        tab_tip = bd.Pos(tx, ty, 0.0) * bd.Cylinder(
            radius=5.0,
            height=t_tray,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        tab_neck = bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, tdeg)) * (
            bd.Pos(68.0, 0.0, 0.0)
            * bd.Box(6.5, 10.0, t_tray, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        )
        tray = tray + tab_tip + tab_neck

    # Upward snap cradles on top surface (Z = t_tray = 2.80 mm):
    wall_t = 1.6

    # (1) UCTRONICS U6223 (63.0 x 27.0 x 12.0 mm) at (-2.0, +36.0), pocket 63.6 x 27.6 mm
    #     Long ±Y rails (length 44 mm) leave ±X screw terminals & -X 1000 uF capacitor completely open
    ux, uy = -2.0, 36.0
    for sy in (-1.0, 1.0):
        rail = bd.Pos(ux, uy + sy * (27.6 / 2.0 + wall_t / 2.0), t_tray) * bd.Box(
            44.0, wall_t, 10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        tray = tray + rail
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            standoff = bd.Pos(ux + sx * 27.5, uy + sy * 10.5, t_tray) * bd.Cylinder(
                radius=2.2, height=1.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            corner_post = bd.Pos(ux + sx * (63.6 / 2.0 + wall_t / 2.0), uy + sy * 12.0, t_tray) * bd.Box(
                wall_t, 4.0, 8.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            tray = tray + standoff + corner_post

    # (2) Unstacked 2x WAGO 221-415 cradles (18.6 x 30.0 x 8.4 mm -> pocket 19.2 x 30.6 mm)
    #     Wire entry ports face -X (left open); backstop walls + side ±Y rails hold blocks snugly
    for wx, wy in ((46.0, -2.5), (-32.5, 0.0)):
        back_wall = bd.Pos(wx + 19.2 / 2.0 + wall_t / 2.0, wy, t_tray) * bd.Box(
            wall_t, 30.6 + 2.0 * wall_t, 8.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        tray = tray + back_wall
        for sy in (-1.0, 1.0):
            side_rail = bd.Pos(wx + 1.5, wy + sy * (30.6 / 2.0 + wall_t / 2.0), t_tray) * bd.Box(
                16.2, wall_t, 8.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            front_lip = bd.Pos(wx - 19.2 / 2.0 - 0.6, wy + sy * (30.6 / 2.0 - 1.5), t_tray) * bd.Box(
                1.4, 3.0, 6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            tray = tray + side_rail + front_lip

    # (3) A092+C008 cradle (48.0 x 24.0 x 19.0 mm -> pocket 48.6 x 24.6 mm) centered at (0.0, -31.0)
    #     Seated flush on Z = 2.80 mm around the 14 x 14 mm C008 LED/button port; long ±Y rails
    #     (length 38 mm) leave -X (+22 mm A096/USB) and +X (+16 mm HT3.96-4P) plugs 100% open
    ax, ay = 0.0, -31.0
    for sy in (-1.0, 1.0):
        a_rail = bd.Pos(ax, ay + sy * (24.6 / 2.0 + wall_t / 2.0), t_tray) * bd.Box(
            38.0, wall_t, 12.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        tray = tray + a_rail

    # Concentric holes for motor_shroud_tower (0,0), wand_pillar (+45.03,+26.00), and 14x14 C008 port
    wand_x = 52.0 * math.cos(math.radians(30.0))
    wand_y = 52.0 * math.sin(math.radians(30.0))
    center_hole = bd.Pos(0.0, 0.0, -0.2) * bd.Cylinder(
        radius=MOTOR_SHROUD_OD / 2.0 + 0.30,  # Ø 28.6 mm
        height=t_tray + 0.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    wand_hole = bd.Pos(wand_x, wand_y, -0.2) * bd.Cylinder(
        radius=9.80,  # Ø 19.6 mm (0.30 mm radial clearance around R = 9.5 mm wand_pillar)
        height=t_tray + 0.4,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    c008_port = bd.Pos(ax, ay, -0.2) * bd.Box(
        14.0, 14.0, t_tray + 0.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    tray = tray - center_hole - wand_hole - c008_port

    # 4x Counterbored M2.5 mounting holes in the 4 outer diagonal tabs
    for tx, ty in BOTTOM_TRAY_TAB_COORDS:
        thru = bd.Pos(tx, ty, -0.2) * bd.Cylinder(
            radius=AA050_M25_THROUGH_DIA / 2.0,
            height=t_tray + 0.4,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        cbore = bd.Pos(tx, ty, -0.2) * bd.Cylinder(
            radius=AA050_M25_CBORE_DIA / 2.0,
            height=1.5,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        tray = tray - thru - cbore

    # Debossed "A" (A092 side), "12" (DC-099 12V -X side), "G" (WAGO_2_W GND side) labels on top deck
    glyph_a = bd.Pos(0.0, -52.5, t_tray) * make_engraved_label_solid("A", char_h=4.4, depth=0.65)
    glyph_12 = bd.Pos(-50.0, 0.0, t_tray) * make_engraved_label_solid("12", char_h=4.4, depth=0.65)
    glyph_g = bd.Pos(-32.5, -19.0, t_tray) * make_engraved_label_solid("G", char_h=4.4, depth=0.65)
    tray = tray - glyph_a - glyph_12 - glyph_g

    return assign_toolhead(tray.solid(), "Bottom_Electronics_Lid", 1)


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
      - Sloped Ø 27.6 mm Upper Ball Discharge Chute (global Z = 436.2 -> 430.83 mm) into
        curved swept-ball exit relief along `1710° -> 1650°` at `TOP_FEEDER_START_R = 47.0 mm`
      - Flat unpinned horizontal `1710°` spout cradle shelf (Z_local = 99.0..109.35 mm with 45°
        support-free underside gusset) clearing the shortened gothic viewing window (Z <= 93 mm)
      - 150° Sparkleiot topper LED wire exit slot + Ø 59.40 x 4.0 mm `crown_collar` socket tenon
    """
    body = _make_bark_textured_trunk_column(
        z_min=0.0,
        z_max=TRUNK_SECTION_HEIGHT,
        z_global_offset=2.0 * TRUNK_SECTION_HEIGHT,
    )

    # Female socket at bottom (Z = 0..15.2 mm + 45-deg roof) with 150° conduit flat
    socket_cutter = make_keyed_female_socket_cutter(z_base=-0.1, height=TENON_HEIGHT + 0.1)
    body = body - socket_cutter

    # Flat unpinned horizontal cradle shelf beneath track_seg_14's 1710° spout collar (inboard solid shoulder)
    top_feeder_local_z = (HELIX_Z_END + TOP_FEEDER_RISE_Z) - 2.0 * TRUNK_SECTION_HEIGHT  # 125.0 mm
    z_shelf_top = top_feeder_local_z + TRACK_BASE_Y - 1.15  # 108.35 mm (clears sloped -X seg_14 downhill ramp by >=0.17 mm)
    z_shelf_bot = z_shelf_top - 10.35  # 99.0 mm (45° underside gusset from Y=-33.0 out to Y=-42.5)
    shelf_pts = [
        (-33.0, z_shelf_bot),
        (-42.5, z_shelf_top),
        (-32.0, z_shelf_top),
        (-32.0, z_shelf_bot),
        (-33.0, z_shelf_bot),
    ]

    def _shelf_wire(x_pos: float) -> bd.Wire:
        return bd.Wire(
            [bd.Edge.make_line((x_pos, shelf_pts[i][0], shelf_pts[i][1]),
                               (x_pos, shelf_pts[i + 1][0], shelf_pts[i + 1][1]))
             for i in range(len(shelf_pts) - 1)]
        )

    top_spout_shelf = bd.Solid.make_loft([_shelf_wire(-8.0), _shelf_wire(8.0)], ruled=True)
    body = body + top_spout_shelf

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

    # Sloped Upper Ball Discharge Chute along -Y + curved swept-ball exit relief along 1710° -> 1650°
    p_chute_start = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 136.2)
    p_chute_mouth = bd.Vector(0.0, -TOP_FEEDER_START_R, top_feeder_local_z + 5.83)
    chute_vec = p_chute_mouth - p_chute_start
    chute_plane = bd.Plane(origin=p_chute_start, z_dir=chute_vec.normalized())
    upper_discharge_chute = (
        (bd.Pos(p_chute_start.X, p_chute_start.Y, p_chute_start.Z) * bd.Sphere(radius=13.8))
        + (
            chute_plane
            * bd.Cylinder(
                radius=13.8,
                height=chute_vec.length,
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
    swept_thetas = [1710.0 - 10.0 * idx for idx in range(7)]  # 1710° -> 1650°
    swept_pts = [
        closed_loop_track_point(th) + bd.Vector(0.0, 0.0, 5.83 - 2.0 * TRUNK_SECTION_HEIGHT)
        for th in swept_thetas
    ]
    for i in range(len(swept_pts) - 1):
        pa, pb = swept_pts[i], swept_pts[i + 1]
        seg_v = pb - pa
        seg_pl = bd.Plane(origin=pa, z_dir=seg_v.normalized())
        upper_discharge_chute = (
            upper_discharge_chute
            + (bd.Pos(pa.X, pa.Y, pa.Z) * bd.Sphere(radius=13.8))
            + (
                seg_pl
                * bd.Cylinder(
                    radius=13.8,
                    height=seg_v.length,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
        )
    upper_discharge_chute = upper_discharge_chute + (
        bd.Pos(swept_pts[-1].X, swept_pts[-1].Y, swept_pts[-1].Z) * bd.Sphere(radius=13.8)
    )
    body = body - bore - flute_cutter - flute_roof - upper_discharge_chute

    # 150° vertical 10.6 x 8.5 mm wire conduit
    body = _cut_rear_wire_conduit(body, TRUNK_SECTION_HEIGHT)

    # Lowered front vertical gothic-arched viewing window slot (Z = 28..93 mm) + ruler below spout shelf
    view_slot = _make_arched_viewing_window_cutter(z_min=28.0, straight_h=56.0)
    body = body - view_slot

    # 60-degree helical female dovetail sockets (including b25 at 1500° and b26 at 1560°)
    body = _cut_helical_dovetails_for_section(
        body,
        z_section_min=2.0 * TRUNK_SECTION_HEIGHT,
        z_section_max=3.0 * TRUNK_SECTION_HEIGHT,
        local_z_min_safe=TENON_HEIGHT + 8.0,
        local_z_max_safe=TRUNK_SECTION_HEIGHT - DOVETAIL_SLOT_H - 12.0,
    )

    body = _cut_front_elevation_ruler_for_section(
        body, z_section_min=2.0 * TRUNK_SECTION_HEIGHT, local_z_min=24.0, local_z_max=90.0
    )

    # Topper wire exit notch aligned at 150° into trunk_top's wire conduit
    topper_ring_wire_slot = bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, WIRE_CONDUIT_ANGLE_DEG)) * (
        bd.Pos(29.5, 0.0, TRUNK_SECTION_HEIGHT - 3.5)
        * bd.Box(
            14.0,
            WIRE_CONDUIT_W,
            10.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )

    # Upward Crown Centering Tenon Collar (Ø 59.40 mm OD / Ø 50.00 mm ID x 4.0 mm tall, Z = 150.0..154.0 mm)
    # Mates concentrically inside golden_apple_topper's Ø 60.00 x 4.6 mm `CROWN_SOCKET`
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

    # Engrave hidden assembly number "3" on top rim of Crown Centering Tenon Collar
    num_3 = bd.Pos(0.0, 27.1, TRUNK_SECTION_HEIGHT + 4.0) * make_engraved_label_solid(
        "3", char_h=3.6, depth=0.85
    )
    body = body - topper_ring_wire_slot - num_3

    return body.solid()


def build_all_trunk_parts() -> dict[str, bd.Solid]:
    """Return dictionary of all 3 stackable trunk sections, Bottom_Electronics_Lid,
    and 3 section-matched 150° Conduit_Cover_Strip_* parts (Toolhead 1 - Dark Wood Brown #4A2F1D).
    """
    parts: dict[str, bd.Solid] = {
        "trunk_base": assign_toolhead(build_trunk_base(), "trunk_base", 1),
        "trunk_mid": assign_toolhead(build_trunk_mid(), "trunk_mid", 1),
        "trunk_top": assign_toolhead(build_trunk_top(), "trunk_top", 1),
        "Bottom_Electronics_Lid": build_bottom_electronics_lid(),
    }
    parts.update(build_conduit_cover_strips())
    return parts


if __name__ == "__main__":
    for name, part in build_all_trunk_parts().items():
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, bbox={bb.size}")
