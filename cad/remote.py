"""Handheld 'Newton's Apple' Wireless Remote Controller Enclosure (cad/remote.py).

Generates the two-piece ergonomic apple-shaped wireless remote shell for the
Bambu Lab CyberBrick ecosystem (ZK004 Beginner Kit / ZK003 Ultimate Kit):
  1. Remote_Bottom_Shell (Toolhead 3 - Silk Gold #D4AF37):
     - Houses the 3x1.5V AAA Battery Case (54.0 x 38.0 x 14.0 mm) in the lower grip bay
     - Houses the XA005 Transmitter Shield + XA003 Core Board (48.0 x 36.0 x 18.0 mm) in the upper bay
     - 4x M2.5 (AA050) self-tapping assembly & PCB standoffs + side XH2.54/USB-C access port
  2. Remote_Top_Faceplate (Toolhead 4 - Glossy Crimson Red #C41E3A):
     - Top cutouts and M2.5 (AA050) screw holes for the Ultimate Edition dual-stick layout:
       * 2x Dual-Axis Joysticks (XA011 — auger drive + servo gates, Ø 18.4 mm cutouts)
       * 1x Three-Position Rocker Switch (XA010 — RGB LED mode selector, 19.9 x 13.4 mm cutout)
       * 1x Momentary Button (XA008 — Servo Apple Drop trigger, Ø 12.6 mm cutout)
"""

from __future__ import annotations

import build123d as bd

from common_params import (
    AA050_M25_CBORE_DIA,
    AA050_M25_TAP_DEPTH,
    AA050_M25_TAP_DIA,
    AA050_M25_THROUGH_DIA,
    AAA_BATTERY_BOX_X,
    AAA_BATTERY_BOX_Y,
    AAA_BATTERY_BOX_Z,
    XA005_TX_BAY_X,
    XA005_TX_BAY_Y,
    XA005_TX_BAY_Z,
    XA008_BUTTON_CUTOUT_DIA,
    XA009_JOYSTICK_CUTOUT_DIA,
    XA010_ROCKER_CUTOUT_X,
    XA010_ROCKER_CUTOUT_Y,
    assign_toolhead,
)

# Ultimate Edition faceplate control layout
XA011_JOYSTICK_NOMINAL_DIA = 18.0           # XA011 dual-axis joystick gauge diameter
XA011_JOYSTICK_CUTOUT_DIA = 18.4            # +0.20 mm radial clearance
JOYSTICK_XS = (-16.0, 16.0)
JOYSTICK_Y = 8.5
BUTTON_XY = (-15.0, -13.0)                  # XA008 momentary button
ROCKER_XY = (14.0, -13.0)                   # XA010 three-position rocker


def _make_apple_remote_profile_wire(scale: float = 1.0) -> bd.Wire:
    """Create the 68.0 x 58.0 mm ergonomic low-poly Newton's Apple 2D outer profile wire."""
    pts = [
        (0.0, -27.5),
        (16.0, -29.0),
        (32.0, -23.0),
        (34.0, -12.0),
        (34.0, 12.0),
        (32.0, 23.0),
        (16.0, 29.0),
        (0.0, 27.2),
        (-16.0, 29.0),
        (-32.0, 23.0),
        (-34.0, -12.0 + 24.0),
        (-34.0, -12.0),
        (-32.0, -23.0),
        (-16.0, -29.0),
    ]
    scaled = [(x * scale, y * scale) for x, y in pts]
    return bd.Wire.make_polygon(scaled)


def build_remote_bottom_shell() -> bd.Solid:
    """Build Remote_Bottom_Shell (Toolhead 3 - Silk Gold #D4AF37, 68.0 x 58.0 x 35.0 mm):
      - Lower compartment (Z = 1.8..16.3 mm): 54.0 x 38.0 x 14.0 mm 3x1.5V AAA Battery Case
      - Support-free 45° transition ledge (Z = 16.2..19.2 mm)
      - Upper compartment (Z = 16.5..35.0 mm): 48.0 x 36.0 x 18.0 mm XA005 Transmitter + XA003 Core
      - 4x corner M2.5 (AA050) self-tapping assembly boss holes at (±27.5, ±20.5)
    """
    outer_wire = _make_apple_remote_profile_wire(1.0)
    shell = bd.extrude(bd.Face(outer_wire), amount=35.0)

    # 1. Lower tier bay for 3x1.5V AAA Battery Case (54.0 x 38.0 x 14.0 mm gauge at Z = 2.0..16.0 mm)
    aaa_bay = bd.Pos(0.0, 0.0, 1.8) * bd.Box(
        AAA_BATTERY_BOX_X + 0.6,  # 54.6 mm
        AAA_BATTERY_BOX_Y + 0.6,  # 38.6 mm
        AAA_BATTERY_BOX_Z + 0.5,  # 14.5 mm (Z = 1.8..16.3 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # 2. Support-free 45° transition loft from (54.6, 38.6) at Z = 16.2 mm to (48.6, 36.6) at Z = 19.2 mm
    w_bot = bd.Pos(0.0, 0.0, 16.2) * bd.Rectangle(54.6, 38.6).wire()
    w_top = bd.Pos(0.0, 0.0, 19.2) * bd.Rectangle(48.6, 36.6).wire()
    transition_loft = bd.Solid.make_loft([w_bot, w_top], ruled=True)

    # 3. Upper tier bay for XA005 Transmitter Shield + XA003 Core Board (48.0 x 36.0 x 18.0 mm gauge at Z = 16.5..34.5 mm)
    xa005_bay = bd.Pos(0.0, 0.0, 16.2) * bd.Box(
        XA005_TX_BAY_X + 0.6,  # 48.6 mm
        XA005_TX_BAY_Y + 0.6,  # 36.6 mm
        XA005_TX_BAY_Z + 1.0,  # 19.0 mm (Z = 16.2..35.2 mm)
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # 4. USB-C / XH2.54 side programming & power switch access port at Y = +27.5 mm, Z = 20.0..28.0 mm
    usb_port = bd.Pos(0.0, 27.0, 20.0) * bd.Box(
        14.0,
        10.0,
        8.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    shell = shell - aaa_bay - transition_loft - xa005_bay - usb_port

    # 5. Four corner M2.5 (AA050) self-tapping screw holes (Ø 2.25 x 6.5 mm) at (±27.5, ±20.5)
    for sx in (-27.5, 27.5):
        for sy in (-20.5, 20.5):
            m25_hole = bd.Pos(sx, sy, 35.0 - AA050_M25_TAP_DEPTH) * bd.Cylinder(
                radius=AA050_M25_TAP_DIA / 2.0,
                height=AA050_M25_TAP_DEPTH + 0.2,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            shell = shell - m25_hole

    return assign_toolhead(shell.solid(), "Remote_Bottom_Shell", 3)


def build_remote_top_faceplate() -> bd.Solid:
    """Build Remote_Top_Faceplate (Toolhead 4 - Glossy Crimson Red #C41E3A, 68.0 x 58.0 x 8.0 mm):
      - Printed flat at Z = 0.00 mm
      - Decorative top Newton's Apple stem/leaf relief crest
      - Ultimate Edition dual-joystick control layout (cutouts + M2.5 screw holes):
        * 2x XA011 Dual-Axis Joysticks (Ø 18.4 mm cutouts at X = ±16.0, Y = +8.5 mm)
          - Left stick : auger speed / direction (N20 clutch drive)
          - Right stick: topper gate servo (PG001) + track diverter servo (PG002)
        * 1x XA008 Momentary Button (Ø 12.6 mm cutout at X = -15.0, Y = -13.0 mm) - Apple drop
        * 1x XA010 Three-Position Rocker Switch (19.9 x 13.4 mm cutout at X = +14.0, Y = -13.0 mm)
          - RGB lighting mode selector (Lamp Puck / WS2812 / COB strip)
    """
    outer_wire = _make_apple_remote_profile_wire(1.0)
    plate = bd.extrude(bd.Face(outer_wire), amount=6.5)

    # Decorative low-poly apple leaf/stem crest at top of faceplate (Y = +23.5 mm, Z = 6.5..8.0 mm)
    crest = bd.Pos(0.0, 23.5, 6.5) * bd.Box(
        14.0,
        5.0,
        1.5,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    plate = plate + crest

    # 1. 2x XA011 Dual-Axis Joystick cutouts (Ø 18.4 mm clears Ø 18.0 mm gauge) + M2.5 holes
    for jx in JOYSTICK_XS:
        joy_cut = bd.Pos(jx, JOYSTICK_Y, -0.2) * bd.Cylinder(
            radius=XA011_JOYSTICK_CUTOUT_DIA / 2.0,
            height=9.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        plate = plate - joy_cut
        # Two M2.5 tap holes on the outboard diagonal of each stick (clear of the crest and centre)
        sgn = 1.0 if jx > 0 else -1.0
        for hx, hy in ((jx + sgn * 11.5, JOYSTICK_Y + 7.5), (jx + sgn * 11.5, JOYSTICK_Y - 7.5)):
            jm25 = bd.Pos(hx, hy, -0.1) * bd.Cylinder(
                radius=AA050_M25_TAP_DIA / 2.0,
                height=5.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            plate = plate - jm25

    # 2. XA010 Three-Position Rocker Switch cutout (19.9 x 13.4 mm at X = +14.0, Y = -13.0 mm)
    rocker_cut = bd.Pos(ROCKER_XY[0], ROCKER_XY[1], -0.2) * bd.Box(
        XA010_ROCKER_CUTOUT_X + 0.4,  # 19.9 mm
        XA010_ROCKER_CUTOUT_Y + 0.4,  # 13.4 mm
        9.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    plate = plate - rocker_cut

    # 3. XA008 Momentary Button cutout (Ø 12.6 mm at X = -15.0, Y = -13.0 mm)
    btn_cut = bd.Pos(BUTTON_XY[0], BUTTON_XY[1], -0.2) * bd.Cylinder(
        radius=(XA008_BUTTON_CUTOUT_DIA + 0.4) / 2.0,  # R = 6.3 mm (clears Ø 12.2 mm gauge)
        height=9.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    plate = plate - btn_cut

    # 4. Four corner M2.5 (AA050) counterbored assembly through-holes at (±27.5, ±20.5)
    for sx in (-27.5, 27.5):
        for sy in (-20.5, 20.5):
            thru = bd.Pos(sx, sy, -0.2) * bd.Cylinder(
                radius=AA050_M25_THROUGH_DIA / 2.0,
                height=9.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            cbore = bd.Pos(sx, sy, 4.5) * bd.Cylinder(
                radius=AA050_M25_CBORE_DIA / 2.0,
                height=3.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            plate = plate - thru - cbore

    return assign_toolhead(plate.solid(), "Remote_Top_Faceplate", 4)


def build_all_remote_parts() -> dict[str, bd.Solid]:
    """Return dictionary of both printable Newton's Apple Wireless Remote enclosure halves."""
    return {
        "Remote_Bottom_Shell": build_remote_bottom_shell(),
        "Remote_Top_Faceplate": build_remote_top_faceplate(),
    }


if __name__ == "__main__":
    for name, part in build_all_remote_parts().items():
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid}, manifold={part.is_manifold}, bbox={bb.size}")
