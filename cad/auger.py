"""Central Archimedes Screw Lift & Direct Hex Coupling (cad/auger.py).

Generates the two-piece 3D-printable Archimedes screw and direct mechanical drive
coupler designed to run inside the Ø 41.0 mm trunk bore:
  1. auger_lower         : Ø 9.0 mm central shaft, 2.4 mm thick spiral blade extending
                           to Ø 38.0 mm (pitch 46.0 mm), base Ø 20.0 mm thrust flange with
                           female 5.0 mm hex drive socket, and top 5.0 mm male hex peg.
  2. auger_upper         : Ø 9.0 mm central shaft, 2.4 mm thick spiral blade extending
                           to Ø 38.0 mm (pitch 46.0 mm), and bottom 5.0 mm female hex
                           coupling socket with self-supporting conical roof.
  3. Motor_Clutch_Driver : Direct mechanical N20 D-shaft to 5.0 mm male hex drive coupler.
  4. Servo_Or_030_Adapter: Snap-in motor sleeve for the LA002 N20 gear motor.
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    AUGER_FLIGHT_THICKNESS,
    AUGER_HALF_HEIGHT,
    AUGER_HEX_ACROSS_FLATS,
    AUGER_HEX_HEIGHT,
    AUGER_OD,
    AUGER_PITCH,
    AUGER_SHAFT_DIA,
    FIT_TOLERANCE,
    HEX_COUPLE_CLEARANCE,
    N20_DSHAFT_DIA,
    N20_DSHAFT_FLAT,
    assign_toolhead,
    make_engraved_label_solid,
)

CLUTCH_FLANGE_OD = 20.0
CLUTCH_AIR_GAP = 1.00


def build_motor_clutch_driver() -> bd.Solid:
    """Build the direct mechanical Motor_Clutch_Driver coupler (Toolhead 3 - Silk Gold #D4AF37):
      - Lower motor boss: Ø 11.0 mm stem (Z = 0.00..3.50 mm) expanding at 45° (Z = 3.50..6.00 mm)
        to a Ø 16.0 mm coupling flange (Z = 6.00..10.00 mm).
      - Bottom N20 D-shaft bore: Ø 3.15 mm with 2.65 mm D-flat, 6.50 mm deep (Z = 0.00..6.50 mm)
        with a 45° self-supporting conical roof.
      - Upper male hex drive peg: 4.85 mm across-flats x 4.50 mm tall (Z = 10.00..14.50 mm)
        that engages the female hex socket in the base of auger_lower without magnets.
    """
    stem = bd.Cylinder(
        radius=5.5,
        height=3.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    taper = bd.Pos(0.0, 0.0, 3.5) * bd.Cone(
        bottom_radius=5.5,
        top_radius=8.0,
        height=2.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    collar = bd.Pos(0.0, 0.0, 6.0) * bd.Cylinder(
        radius=8.0,
        height=4.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    apothem_peg = (AUGER_HEX_ACROSS_FLATS / 2.0) - (HEX_COUPLE_CLEARANCE / 2.0)  # 2.425 mm
    hex_poly = bd.RegularPolygon(radius=apothem_peg, side_count=6, major_radius=False)
    hex_peg = bd.Pos(0.0, 0.0, 10.0) * bd.extrude(hex_poly, 4.5)

    # Vertical N20 D-shaft bore (Ø 3.15 mm with 2.65 mm D-flat, Z = 0.00..6.50 mm + 45° conical roof)
    r_d = 3.15 / 2.0  # 1.575 mm
    d_cyl = bd.Pos(0.0, 0.0, -0.1) * bd.Cylinder(
        radius=r_d,
        height=6.60,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    flat_x = 2.65 - r_d  # 1.075 mm
    keep_box = bd.Pos(flat_x - r_d, 0.0, -0.2) * bd.Box(
        2.0 * r_d,
        4.0 * r_d,
        7.00,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    d_bore = d_cyl & keep_box
    d_roof = bd.Pos(0.0, 0.0, 6.50) * bd.Cone(
        bottom_radius=r_d,
        top_radius=0.2,
        height=1.40,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    driver = (stem + taper + collar + hex_peg - d_bore - d_roof).solid()
    return assign_toolhead(driver, "Motor_Clutch_Driver", 3)


def _build_auger_core(
    height: float,
    start_angle_deg: float = 0.0,
    is_upper: bool = False,
) -> bd.Solid:
    """Build one half of the Archimedes screw (central Ø 9.0 mm rod + Ø 38.0 mm helical blade
    with 45° self-supporting bottom entry taper on the lower half so it prints upright without
    supports and clears the Trunk_Base bevel-crank collar, while the upper half starts flush at
    z = 0.0 mm so the helical flight is 100% continuous across the Z = 235.2 mm hex joint).
    """
    r_shaft = AUGER_SHAFT_DIA / 2.0   # 4.5 mm
    r_outer = AUGER_OD / 2.0          # 19.0 mm (1.5 mm radial clearance inside Ø 41.0 mm bore)

    shaft = bd.Cylinder(
        radius=r_shaft,
        height=height,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Embed inner edge of blade 0.8 mm inside the central shaft for a robust boolean union
    r_inner_embed = r_shaft - 0.8
    blade_radial_w = (r_outer + 0.6) - r_inner_embed
    r_mid = r_inner_embed + blade_radial_w / 2.0
    z_margin = 0.0 if is_upper else 5.5
    z_top_margin = 3.0 if is_upper else 0.0
    helix_h = height - z_margin - z_top_margin

    # For a circular cylinder helix, the Frenet principal normal is strictly horizontal & radial
    # toward the Z-axis everywhere, so is_frenet=True keeps the blade strictly horizontal radially
    # at full r_outer from bottom to top!
    helix_path = bd.Wire(
        [
            bd.Helix(
                pitch=AUGER_PITCH,
                height=helix_h,
                radius=r_mid,
                center=(0.0, 0.0, z_margin),
            )
        ]
    )
    blade_profile = (
        bd.Plane.XZ
        * bd.Pos(r_mid, z_margin)
        * bd.Rectangle(blade_radial_w, AUGER_FLIGHT_THICKNESS)
    )
    blade = bd.sweep(
        blade_profile,
        path=helix_path,
        is_frenet=True,
    )
    if abs(start_angle_deg) > 1e-6:
        blade = bd.Rot(0.0, 0.0, start_angle_deg) * blade

    if is_upper:
        # Clip cleanly to [0.0, height] cylinder so leading edge sits flat on Z=0 build plate
        # and meets auger_lower's top blade edge with zero missing-blade gap
        bound_cyl = bd.Cylinder(
            radius=r_outer,
            height=height,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        blade_trimmed = blade & bound_cyl
    else:
        # Trim lower blade OD to r_outer with a 45° self-supporting bottom entry cone starting
        # from the Ø 20.0 mm (R = 10.0 mm) base flange at Z = 4.5..13.5 mm (R = 10.0..19.0 mm)
        taper_h = r_outer - 10.0  # 9.0 mm
        lower_cone = bd.Pos(0.0, 0.0, 4.5) * bd.Cone(
            bottom_radius=10.0,
            top_radius=r_outer,
            height=taper_h,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        upper_cyl = bd.Pos(0.0, 0.0, 4.5 + taper_h) * bd.Cylinder(
            radius=r_outer,
            height=height - (4.5 + taper_h),
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        blade_trimmed = blade & (lower_cone + upper_cyl)

    core = (shaft + blade_trimmed).solid()
    return core


def build_auger_lower() -> bd.Solid:
    """Build lower half of the Archimedes screw (auger_lower) with:
      - Base Ø 20.0 mm x 4.5 mm thrust collar flange resting on the trunk_base Z = 37.20 mm ledge
      - Bottom 5.0 mm female hex socket (0.15 mm radial clearance, 45° self-supporting roof)
        that mates directly with the top male hex peg on Motor_Clutch_Driver (zero magnets)
      - Top 5.0 mm male hex coupling peg (0.15 mm radial clearance)
    """
    part = _build_auger_core(AUGER_HALF_HEIGHT)

    # 1. Top 5.0 mm male hex peg with 0.15 mm radial clearance
    apothem_peg = (AUGER_HEX_ACROSS_FLATS / 2.0) - (HEX_COUPLE_CLEARANCE / 2.0)
    hex_poly = bd.RegularPolygon(radius=apothem_peg, side_count=6, major_radius=False)
    hex_peg = bd.Pos(0.0, 0.0, AUGER_HALF_HEIGHT) * bd.extrude(hex_poly, AUGER_HEX_HEIGHT)
    part = part + hex_peg

    # 2. Base Ø 20.0 mm x 4.5 mm thrust flange + 45° transition cone to shaft
    r_flange = CLUTCH_FLANGE_OD / 2.0  # 10.0 mm
    r_shaft = AUGER_SHAFT_DIA / 2.0    # 4.5 mm
    flange = bd.Cylinder(
        radius=r_flange,
        height=4.50,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    flange_taper = bd.Pos(0.0, 0.0, 4.50) * bd.Cone(
        bottom_radius=r_flange,
        top_radius=r_shaft,
        height=r_flange - r_shaft,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    part = part + flange + flange_taper

    # 3. Bottom 5.0 mm female hex socket (5.15 mm across-flats, 4.50 mm deep + 45° conical roof)
    apothem_sock = (AUGER_HEX_ACROSS_FLATS / 2.0) + (HEX_COUPLE_CLEARANCE / 2.0)
    sock_depth = 4.50
    hex_sock_poly = bd.RegularPolygon(radius=apothem_sock, side_count=6, major_radius=False)
    hex_sock_prism = bd.Pos(0.0, 0.0, -0.1) * bd.extrude(hex_sock_poly, sock_depth + 0.1)
    circum_r = apothem_sock / math.cos(math.radians(30.0))
    roof_cone = bd.Pos(0.0, 0.0, sock_depth) * bd.Cone(
        bottom_radius=circum_r,
        top_radius=0.2,
        height=circum_r,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    part = part - (hex_sock_prism + roof_cone)

    # 4. Engrave hidden assembly number "1" on the flat top of the male hex peg
    #    (Z = 208.0 mm — 100% hidden inside auger_upper's bottom socket once coupled!)
    num_1 = bd.Pos(0.0, 0.0, AUGER_HALF_HEIGHT + AUGER_HEX_HEIGHT) * make_engraved_label_solid(
        "1", char_h=3.2, depth=0.80
    )
    part = part - num_1

    return part.solid()


def build_servo_or_030_adapter() -> bd.Solid:
    """Build the snap-in Servo_Or_030_Adapter sleeve (Toolhead 1 - Dark Wood Brown #4A2F1D):
    Allows the Trunk_Base dual-compatible motor bay to snugly sleeve the LA002
    N20 Reduction Gear Motor (12.4 x 10.4 x 26.0 mm).
    """
    outer_box = bd.Box(
        23.2,
        12.5,
        24.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    inner_n20_bore = bd.Pos(0.0, 0.0, -0.1) * bd.Box(
        12.6,
        10.6,
        24.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    m25_left = bd.Pos(-9.0, 0.0, -0.1) * bd.Cylinder(
        radius=2.25 / 2.0,
        height=6.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    m25_right = bd.Pos(9.0, 0.0, -0.1) * bd.Cylinder(
        radius=2.25 / 2.0,
        height=6.6,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    adapter = (outer_box - inner_n20_bore - m25_left - m25_right).solid()
    return assign_toolhead(adapter, "Servo_Or_030_Adapter", 1)


def build_auger_upper() -> bd.Solid:
    """Build upper half of the Archimedes screw with bottom 5.0 mm female hex socket,
    phase-matched to auger_lower so the helical flight is continuous across the joint.
    """
    phase_deg = (((AUGER_HALF_HEIGHT + 0.1 - 5.5) / AUGER_PITCH) * 360.0) % 360.0
    part = _build_auger_core(AUGER_HALF_HEIGHT, start_angle_deg=phase_deg, is_upper=True)

    # Bottom 5.0 mm female hex socket with 0.15 mm radial clearance vs male hex peg
    apothem_sock = (AUGER_HEX_ACROSS_FLATS / 2.0) + (HEX_COUPLE_CLEARANCE / 2.0)
    sock_depth = AUGER_HEX_HEIGHT + 0.5
    hex_poly = bd.RegularPolygon(radius=apothem_sock, side_count=6, major_radius=False)
    hex_prism = bd.Pos(0.0, 0.0, -0.1) * bd.extrude(hex_poly, sock_depth + 0.1)

    # Self-supporting 45-degree conical roof above hex socket
    circum_r = apothem_sock / math.cos(math.radians(30.0))
    roof_cone = bd.Pos(0.0, 0.0, sock_depth) * bd.Cone(
        bottom_radius=circum_r,
        top_radius=0.2,
        height=circum_r,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    part = part - (hex_prism + roof_cone)

    # Engrave hidden assembly number "2" on the flat top of the central shaft
    # (Z = 198.0 mm — 100% hidden inside the top of trunk_top below the Apple Topper!)
    num_2 = bd.Pos(0.0, 0.0, AUGER_HALF_HEIGHT) * make_engraved_label_solid(
        "2", char_h=4.6, depth=0.80
    )
    part = part - num_2

    return part.solid()


def build_all_auger_parts() -> dict[str, bd.Solid]:
    """Return dictionary of both printable Archimedes screw halves, the direct mechanical
    Motor_Clutch_Driver coupler, and the Servo_Or_030_Adapter sleeve.
    """
    return {
        "auger_lower": assign_toolhead(build_auger_lower(), "auger_lower", 3),
        "auger_upper": assign_toolhead(build_auger_upper(), "auger_upper", 3),
        "Motor_Clutch_Driver": build_motor_clutch_driver(),
        "Servo_Or_030_Adapter": build_servo_or_030_adapter(),
    }


if __name__ == "__main__":
    for name, part in build_all_auger_parts().items():
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, bbox={bb.size}")
