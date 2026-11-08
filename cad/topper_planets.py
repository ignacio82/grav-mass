"""Red Apple Topper with Green Leaf & Brown Stem, Rolling Apple Marbles & 8 Multi-Color Planet Charms
(cad/topper_planets.py).

Generates:
  1. golden_apple_topper    : Sculpted 5-lobed low-poly Red Apple Topper (Toolhead 4 Crimson Red #C41E3A)
                              with concave top calyx dimple, curved Dark Wood Brown stem (Toolhead 1 #4A2F1D),
                              sculpted 3D Emerald Green leaf with midrib (Toolhead 2 #00A86B), and
                              base `Ø 60.0 x 19.0 mm` Bambu Lab LED Lamp Kit 001 socket.
  2. apple_topper_stem_leaf : Standalone multi-color printable Brown stem (T1) & Green leaf (T2) accent.
  3. planet_mercury..neptune: All 8 multi-color low-poly Solar System planets with boolean-partitioned
                              color subparts (mapped to Snapmaker U1 Toolheads 1-4) and open-bottom
                              `Ø 5.20 x 4.00 mm` mechanical snap-peg sockets.
  4. apple_marble_01..06    : 6x `25.0 x 25.0 x 25.0 mm` Rolling "Apple" Marbles.
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    AA050_M25_TAP_DEPTH,
    AA050_M25_TAP_DIA,
    BALL_DIAMETER,
    HEMISPHERE_SNAP_CLEARANCE,
    KB003_LED_SOCKET_X,
    KB003_LED_SOCKET_Y,
    KB003_LED_SOCKET_Z,
    MAGNET_DEPTH,
    MAGNET_DIA,
    MAGNET_SKIN_THICKNESS,
    PG001_SERVO_BAY_X,
    PG001_SERVO_BAY_Y,
    PG001_SERVO_BAY_Z,
    PUCK_SOCKET_DEPTH,
    PUCK_SOCKET_DIA,
    STEEL_BALL_CAVITY_DIA,
    STEEL_BALL_DIA,
    WIRE_CONDUIT_D,
    WIRE_CONDUIT_W,
    assign_toolhead,
    make_engraved_label_solid,
)

# Centerline endpoints for the Golden Apple Topper internal ball ramp (for gauge verification)
# Oriented at -135.0 deg (225 deg = 1665 deg helix angle) to feed directly into track_seg_14_top_entry
TOPPER_CHUTE_START = bd.Vector(0.0, 0.0, 43.0)
TOPPER_CHUTE_ANGLE_DEG = -135.0
TOPPER_CHUTE_BORE_DIA = 31.0  # > 30.0 mm port specification

# Mechanical planet pedestal + Bambu Lab Single LED Magnetic Control Switch Light (Ø 7.5 x 6.0 mm)
# unified bottom-loading bore parameters:
#   - Z = 0.00 .. 3.50 mm : Engages the Ø 7.60 x 3.50 mm upward peg on the track balcony
#   - Z = 3.60 .. 9.60 mm : Houses the Ø 7.50 x 6.00 mm Bambu Magnetic LED Switch Light
#   - Z = 10.00.. 12.20 mm: 45° self-supporting conical light-diffuser roof
PLANET_PEG_SOCKET_DIA = 8.00
PLANET_PEG_SOCKET_DEPTH = 10.00
BAMBU_MAG_LED_DIA = 7.50
BAMBU_MAG_LED_HEIGHT = 6.00
BAMBU_MAG_LED_Z_OFFSET = 3.60
WAND_MAGNET_DIA = 8.00
WAND_MAGNET_HEIGHT = 2.00


def make_triangulated_antiprism_solid(
    rings: (
        list[tuple[float, float, float]]
        | list[tuple[float, float, float, float]]
        | list[tuple[float, float, float, float, float]]
    ),
    n_sides: int = 16,
) -> bd.Solid:
    """Build an exact, watertight, low-poly triangulated solid from a stack of
    (z, radius, twist_deg[, lobe_amp[, z_crown_amp]]) rings.
      - When lobe_amp > 0, applies a 5-lobed apple contour `r * (1 + lobe_amp * cos(5 * theta))`.
      - When lobe_amp < 0, applies organic vertical bark ridges `r + |lobe_amp| * bark_wave(theta, z)`.
      - When z_crown_amp > 0, applies a heart-shaped apple crown saddle + 5-carpel vertical wave
        `z + z_crown_amp * (0.65 * cos(2 * theta) + 0.35 * cos(5 * theta))`.
    """
    ring_pts: list[list[bd.Vector]] = []
    for ring in rings:
        z = ring[0]
        r = ring[1]
        twist_deg = ring[2]
        lobe_amp = ring[3] if len(ring) > 3 else 0.0
        z_crown_amp = ring[4] if len(ring) > 4 else 0.0
        pts: list[bd.Vector] = []
        for i in range(n_sides):
            ang = math.radians(twist_deg + i * (360.0 / n_sides))
            if lobe_amp >= 0.0:
                r_mod = r * (1.0 + lobe_amp * math.cos(5.0 * ang))
            else:
                bark_w = (
                    0.50 * math.sin(18.0 * ang + 0.06 * z)
                    + 0.35 * math.cos(29.0 * ang - 0.05 * z + 1.1)
                    + 0.15 * math.sin(41.0 * ang + 0.04 * z + 2.3)
                )
                r_mod = r + abs(lobe_amp) * 0.5 * (1.0 + bark_w)
            z_mod = z + z_crown_amp * (0.65 * math.cos(2.0 * ang) + 0.35 * math.cos(5.0 * ang))
            pts.append(bd.Vector(r_mod * math.cos(ang), r_mod * math.sin(ang), z_mod))
        ring_pts.append(pts)

    faces: list[bd.Face] = [bd.Face(bd.Wire.make_polygon(list(reversed(ring_pts[0]))))]
    for k in range(len(rings) - 1):
        r0 = ring_pts[k]
        r1 = ring_pts[k + 1]
        for i in range(n_sides):
            inext = (i + 1) % n_sides
            faces.append(bd.Face(bd.Wire.make_polygon([r0[i], r0[inext], r1[i]])))
            faces.append(bd.Face(bd.Wire.make_polygon([r1[i], r0[inext], r1[inext]])))
    faces.append(bd.Face(bd.Wire.make_polygon(ring_pts[-1])))
    return bd.Solid(bd.Shell(faces))


def _build_stem_and_leaf(z_offset: float = 0.0) -> tuple[bd.Solid, bd.Solid]:
    """Construct the curved woody Dark Brown apple stem (Toolhead 1) rising from the top
    stem cavity (`Z = 84.8..108.5 mm`) and a broad, realistic ovate Emerald Green apple
    leaf (Toolhead 2) branching off the woody stem clearly above the apple crown (`Z = 95.8..107.2 mm`),
    with >= 45° self-supporting undersides.
    """
    stem_w0 = bd.Pos(0.0, 0.0, 84.8 + z_offset) * bd.RegularPolygon(radius=3.1, side_count=12).wire()
    stem_w1 = (
        bd.Pos(0.6, 0.0, 89.5 + z_offset)
        * bd.Rot(0.0, 8.0, 0.0)
        * bd.RegularPolygon(radius=2.5, side_count=12).wire()
    )
    stem_w2 = (
        bd.Pos(2.2, 0.0, 96.5 + z_offset)
        * bd.Rot(0.0, 15.0, 0.0)
        * bd.RegularPolygon(radius=2.2, side_count=12).wire()
    )
    stem_w3 = (
        bd.Pos(5.4, 0.0, 108.5 + z_offset)
        * bd.Rot(0.0, 22.0, 0.0)
        * bd.RegularPolygon(radius=2.9, side_count=12).wire()
    )
    stem = bd.Solid.make_loft([stem_w0, stem_w1, stem_w2, stem_w3], ruled=True)

    # 3D sculpted ovate apple leaf lofted across 5 cambered cross-sections from petiole on the
    # woody stem (Z = 95.8 mm, clearly above the red apple crown!) out to a pointed tip
    def _leaf_section(
        x_c: float, y_c: float, z_c: float, half_w: float, thick: float, tilt_y: float
    ) -> bd.Wire:
        pts = [
            (0.0, -half_w, 0.35 * thick),
            (0.0, -0.35 * half_w, 0.85 * thick),
            (0.0, 0.0, 0.55 * thick),  # Upper central midrib V-channel
            (0.0, 0.35 * half_w, 0.85 * thick),
            (0.0, half_w, 0.35 * thick),
            (0.0, 0.0, -0.55 * thick),  # Support-free 45° lower keel
            (0.0, -half_w, 0.35 * thick),
        ]
        w = bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])
        return bd.Pos(x_c, y_c, z_c + z_offset) * bd.Rot(0.0, tilt_y, 12.0) * w

    w_l0 = _leaf_section(2.0, 0.0, 95.8, 1.7, 2.5, -30.0)
    w_l1 = _leaf_section(-4.8, -1.2, 99.6, 6.2, 3.5, -22.0)
    w_l2 = _leaf_section(-12.8, -2.4, 103.2, 7.6, 3.7, -14.0)
    w_l3 = _leaf_section(-20.5, -3.3, 105.8, 4.8, 2.7, -8.0)
    w_l4 = _leaf_section(-26.2, -4.0, 107.2, 0.9, 1.2, -4.0)
    leaf = bd.Solid.make_loft([w_l0, w_l1, w_l2, w_l3, w_l4], ruled=True)
    return stem.solid(), leaf.solid()


def topper_chute_point(u: float) -> bd.Vector:
    """Return a 3D centerline point along the Golden Apple Topper internal exit chute for u in [0, 1]."""
    rad = math.radians(TOPPER_CHUTE_ANGLE_DEG)
    r_dist = 4.0 + 26.0 * u
    z_val = 37.5 - 2.0 * u
    return bd.Vector(r_dist * math.cos(rad), r_dist * math.sin(rad), z_val)


def build_golden_apple_topper() -> bd.Solid:
    """Build the Realistic Heart-Shaped 5-Lobed Crimson Red Apple Topper (~82.5 mm wide x 108.5 mm tall):
      - Lower Z = 0.0..19.2 mm: Bark-Textured Dark Wood Brown Trunk-Crown Pedestal (Toolhead 1 #4A2F1D)
        housing the Ø 60.0 x 19.0 mm Bambu Lab LED Lamp Kit 001 socket so the base merges seamlessly
        into the bark-textured brown tree trunk (`trunk_top`).
      - Upper Z = 19.2..93.8 mm: Classic Heart-Shaped Crimson Red Apple (Toolhead 4 #C41E3A):
          * Narrow, tucked-in 5-knobbed bottom calyx base (Ø 46.0 mm at Z = 19.25 mm)
          * Long, tapered lower cheeks widening gradually up to high, broad upper shoulders
            (max Ø 82.5 mm at Z = 64..70 mm — ~72% up the apple body!)
          * Iconic Heart-Shaped 5-Crowned Top Silhouette (`z_crown_amp = 2.6 mm` saddle wave):
            high rounded left/right upper crown lobes (`Z = 93.8 mm`) dipping down in the center
            (`Z = 89.5 mm`) and rolling inward into a deep funnel-like stem basin (`Z = 74.0 mm`)
      - Tall Curved Dark Wood Brown Stem (Toolhead 1 #4A2F1D) rising out of the cleft to Z = 108.5 mm.
      - Broad Ovate Emerald Green Apple Leaf (Toolhead 2 #00A86B) branching off the woody stem at Z = 95.8 mm
        (clearly separated above the red apple crown so it never looks like a tomato sepal!).
    """
    n_sides = 60
    step = 360.0 / n_sides
    rings: list[tuple[float, float, float, float, float]] = [
        # Z = 0.0..19.2 mm: Bark-Textured Brown Trunk-Crown Lamp Housing Pedestal
        (0.0,   33.2, 0.0,        -0.75, 0.0),
        (6.0,   32.4, step * 0.5, -0.75, 0.0),
        (13.0,  31.6, 0.0,        -0.75, 0.0),
        (19.0,  31.2, step * 0.5, -0.65, 0.0),
        # Z = 19.25..28.5 mm: Tucked-in 5-Knobbed Bottom Calyx Base of the Apple (Ø 46.0 -> 61.6 mm)
        (19.25, 23.0, 0.0,         0.048, 0.0),
        (23.2,  27.2, step * 0.5,  0.046, 0.25),
        (28.0,  30.8, 0.0,         0.042, 0.35),
        # Z = 33.5..57.5 mm: Long Tapered Lower Apple Cheeks (gradual upward widening like a real apple)
        (33.5,  33.4, step * 0.5,  0.038, 0.45),
        (39.5,  35.6, 0.0,         0.035, 0.55),
        (46.0,  37.6, step * 0.5,  0.033, 0.70),
        (52.5,  39.1, 0.0,         0.032, 0.90),
        (58.5,  40.1, step * 0.5,  0.032, 1.15),
        # Z = 64.5..75.5 mm: High, Broad Upper Apple Shoulders (Max Ø 82.5 mm at ~72% height!)
        (64.5,  40.5, 0.0,         0.032, 1.45),
        (70.5,  40.1, step * 0.5,  0.032, 1.75),
        (76.0,  38.5, 0.0,         0.032, 2.05),
        # Z = 81.0..91.2 mm: Heart-Shaped Upper Crown Lobes & Central Saddle Dip
        (81.0,  35.5, step * 0.5,  0.030, 2.30),
        (85.5,  31.2, 0.0,         0.028, 2.50),
        (89.0,  25.8, step * 0.5,  0.024, 2.60),
        (91.0,  21.0, 0.0,         0.020, 2.60),
        (91.2,  18.2, step * 0.5,  0.016, 2.40),
        # Z = 90.2..86.0 mm: Sculpted Top Stem Dimple (Infundibulum) above the hollow lantern vault
        (90.2,  15.0, 0.0,         0.012, 1.80),
        (88.6,  11.6, step * 0.5,  0.008, 1.10),
        (87.2,   8.2, 0.0,         0.004, 0.50),
        (86.4,   5.2, step * 0.5,  0.000, 0.00),
        (86.0,   3.1, 0.0,         0.000, 0.00),
    ]
    apple_shell = make_triangulated_antiprism_solid(rings, n_sides=n_sides)
    stem, leaf = _build_stem_and_leaf(z_offset=0.0)

    # 1. Base cylindrical pocket (Ø 60.0 mm x 19.0 mm height) for Bambu Lab LED Lamp Kit 001
    puck_r = PUCK_SOCKET_DIA / 2.0  # 30.0 mm
    puck_socket = bd.Cylinder(
        radius=puck_r,
        height=PUCK_SOCKET_DEPTH,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    # 2. Contoured Hollow Thin-Shell Lantern Chamber (Z = 18.8..83.8 mm, reaching Z = 85.8 mm in the crown lobes):
    # Follows the outer 5-lobed apple contour with a uniform ~2.2 mm wall thickness all the way from
    # the lower calyx up through the widest shoulders and upper crown lobes (zero internal core infill!)
    lantern_cavity_rings: list[tuple[float, float, float, float, float]] = [
        (18.8,  19.8, 0.0,         0.048, 0.0),
        (23.2,  24.8, step * 0.5,  0.046, 0.25),
        (28.0,  28.6, 0.0,         0.042, 0.35),
        (33.5,  31.2, step * 0.5,  0.038, 0.45),
        (39.5,  33.4, 0.0,         0.035, 0.55),
        (46.0,  35.4, step * 0.5,  0.033, 0.70),
        (52.5,  36.9, 0.0,         0.032, 0.90),
        (58.5,  37.9, step * 0.5,  0.032, 1.15),
        (64.5,  38.3, 0.0,         0.032, 1.45),
        (70.5,  37.9, step * 0.5,  0.032, 1.75),
        (76.0,  36.3, 0.0,         0.032, 2.05),
        (80.5,  33.0, step * 0.5,  0.028, 2.10),
        (82.8,  26.5, 0.0,         0.020, 1.40),
        (83.6,  15.5, step * 0.5,  0.010, 0.40),
        (83.8,   4.2, 0.0,         0.000, 0.00),
    ]
    puck_step_cone = make_triangulated_antiprism_solid(lantern_cavity_rings, n_sides=n_sides)

    # Anti-pinch radial-to-vertical cable strain-relief channel at -X for Bambu LED Lamp Kit 001
    # USB cord exiting into trunk_top's rear wire channel
    wire_notch = bd.Pos(-puck_r, 0.0, -0.1) * bd.Box(
        14.0,
        6.5,
        PUCK_SOCKET_DEPTH + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Engrave hidden assembly number "4" on the inner ceiling of the hollow lantern vault
    # (Z = 83.8 mm — continues the vertical trunk stack 1 -> 2 -> 3 -> 4 and is 100% hidden inside!)
    topper_num_4 = bd.Pos(0.0, 0.0, 83.8) * make_engraved_label_solid(
        "4", char_h=4.2, depth=0.75
    )

    raw_body = (
        apple_shell
        - puck_socket
        - puck_step_cone
        - wire_notch
        - topper_num_4
    ).solid()

    # Partition the bottom Z = 0..19.22 mm Bark-Textured Lamp Housing Pedestal as Dark Wood Brown
    # (Toolhead 1 #4A2F1D) so the entire pedestal ledge up to Z = 19.22 mm is brown, while the
    # heart-shaped Crimson Red Apple (Z = 19.22..93.8 mm) sits cleanly on top!
    collar_cutter = bd.Cylinder(
        radius=36.0,
        height=19.30,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    base_collar_brown = (raw_body & collar_cutter).solid()

    # Boolean-partition body, collar, leaf, and stem so subparts have 0.0 mm³ internal overlap
    stem_part = stem.solid()
    leaf_part = (leaf - stem_part).solid()
    body_only = (raw_body - collar_cutter - stem_part - leaf_part).solid()
    stem_and_collar = stem_part + base_collar_brown

    body_only.color = bd.Color("#C41E3A")
    body_only.label = "apple_red_shell"
    assign_toolhead(body_only, "apple_red_shell", 4)

    leaf_part.color = bd.Color("#00A86B")
    leaf_part.label = "apple_green_leaf"
    assign_toolhead(leaf_part, "apple_green_leaf", 2)

    brown_subparts: list[bd.Solid] = []
    for idx, b_sol in enumerate(stem_and_collar.solids()):
        lbl = "apple_brown_stem" if idx == 0 else f"apple_brown_trunk_collar_{idx}"
        b_sol.color = bd.Color("#4A2F1D")
        b_sol.label = lbl
        assign_toolhead(b_sol, lbl, 1)
        brown_subparts.append(b_sol)

    combined = (body_only + stem_part + base_collar_brown + leaf_part).solid()
    assign_toolhead(combined, "golden_apple_topper", 4)
    combined.colored_subparts = [body_only, *brown_subparts, leaf_part]  # type: ignore[attr-defined]
    return combined


def build_apple_topper_stem_leaf() -> bd.Solid:
    """Build the standalone multi-color printable Apple Topper Stem (T1 Brown #4A2F1D) &
    Sculpted Leaf (T2 Emerald Green #00A86B) resting on Z = 0.
    """
    stem, leaf = _build_stem_and_leaf(z_offset=-84.8)
    base_pad = bd.Cylinder(
        radius=4.5, height=2.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    stem_full = (base_pad + stem).solid()
    leaf_only = (leaf - stem_full).solid()
    part = (stem_full + leaf_only).solid()
    bb = part.bounding_box()
    dz = -bb.min.Z
    part = part.moved(bd.Location((0.0, 0.0, dz)))
    stem_moved = stem_full.moved(bd.Location((0.0, 0.0, dz)))
    leaf_moved = leaf_only.moved(bd.Location((0.0, 0.0, dz)))

    stem_moved.color = bd.Color("#4A2F1D")
    stem_moved.label = "stem_brown"
    assign_toolhead(stem_moved, "stem_brown", 1)

    leaf_moved.color = bd.Color("#00A86B")
    leaf_moved.label = "leaf_green"
    assign_toolhead(leaf_moved, "leaf_green", 2)

    assign_toolhead(part, "apple_topper_stem_leaf", 2)
    part.colored_subparts = [leaf_moved, stem_moved]  # type: ignore[attr-defined]
    return part


PLANET_ORDER_NUM = {
    "planet_mercury": 1,
    "planet_venus": 2,
    "planet_earth": 3,
    "planet_mars": 4,
    "planet_jupiter": 5,
    "planet_saturn": 6,
    "planet_uranus": 7,
    "planet_neptune": 8,
}


def _make_planet_socket_cutter(planet_num: int | None = None) -> bd.Shape:
    """Build the unified open-bottom Ø 8.00 x 10.00 mm snap-click & LED chamber cutter:
      - Z = -0.10 .. 0.85 mm : 45° self-centering entry funnel (Ø 9.30 -> Ø 8.00 mm)
                               that eliminates first-layer elephant's foot and guides the peg
      - Z = 1.25 .. 2.85 mm  : Internal 45° ramped snap-click detent groove (Ø 8.44 mm)
                               that locks onto the track balcony peg's Ø 8.12 mm snap bead
      - Z = 0.00 .. 3.50 mm  : Mates with the Ø 7.60 x 3.50 mm upward peg on the track balcony
      - Z = 3.60 .. 9.60 mm  : Houses the Ø 7.50 x 6.00 mm Bambu Lab Single LED Magnetic Switch Light
      - Z = 10.00 .. 11.80 mm: 45° self-supporting conical light-diffuser roof + hidden planet number 1..8
    """
    r_sock = PLANET_PEG_SOCKET_DIA / 2.0  # 4.00 mm (Ø 8.00 mm)
    h_sock = PLANET_PEG_SOCKET_DEPTH      # 10.00 mm
    r_groove = r_sock + 0.22              # 4.22 mm (Ø 8.44 mm internal snap-detent groove)

    peg_socket = bd.Pos(0.0, 0.0, -0.10) * bd.Cylinder(
        radius=r_sock,
        height=h_sock + 0.10,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    entry_funnel = bd.Pos(0.0, 0.0, -0.10) * bd.Cone(
        bottom_radius=r_sock + 0.65,
        top_radius=r_sock,
        height=0.95,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    groove_lower = bd.Pos(0.0, 0.0, 1.25) * bd.Cone(
        bottom_radius=r_sock,
        top_radius=r_groove,
        height=0.25,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    groove_mid = bd.Pos(0.0, 0.0, 1.50) * bd.Cylinder(
        radius=r_groove,
        height=1.10,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    groove_upper = bd.Pos(0.0, 0.0, 2.60) * bd.Cone(
        bottom_radius=r_groove,
        top_radius=r_sock,
        height=0.25,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    socket_roof = bd.Pos(0.0, 0.0, h_sock) * bd.Cone(
        bottom_radius=r_sock,
        top_radius=2.2,
        height=1.8,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    cutter: bd.Shape = (
        peg_socket
        + entry_funnel
        + groove_lower
        + groove_mid
        + groove_upper
        + socket_roof
    )
    if planet_num is not None:
        num_c = bd.Pos(0.0, 0.0, h_sock + 1.8) * make_engraved_label_solid(
            str(planet_num), char_h=2.6, depth=0.55
        )
        cutter = cutter + num_c
    return cutter


def _cut_base_magnet_cavity(body: bd.Solid, planet_num: int | None = None) -> bd.Solid:
    """Cut the unified open-bottom Ø 8.00 mm x 10.00 mm snap-click & LED chamber."""
    return (body - _make_planet_socket_cutter(planet_num)).solid()


def _make_triangulated_planet_globe(
    sphere_radius: float,
    z_center: float,
    n_lat: int = 12,
    n_sides: int = 24,
    radial_mods: list[float] | None = None,
    cut_magnet: bool = True,
    include_pedestal: bool = True,
) -> bd.Solid:
    """Construct a high-resolution sculpted spherical planet globe with an integrated
    support-free 45° Orbital Pedestal Foot Collar at Z = 0.00..3.20 mm (Ø 13.6 mm flat bed
    contact ring that elevates the larger planet globe above the track outer wall and marbles).
    """
    step = 360.0 / n_sides
    rings: list[tuple[float, float, float]] = []
    ring_idx = 0

    if include_pedestal:
        ped_rings = [
            (0.00, 6.80),
            (1.60, 6.55),
            (3.20, 7.65),
        ]
        for z_p, r_p in ped_rings:
            twist_p = (ring_idx % 2) * (step * 0.5)
            rings.append((z_p, r_p, twist_p))
            ring_idx += 1
        lat0 = math.radians(-45.0)
    else:
        lat0 = math.asin(max(-0.98, min(0.98, -z_center / sphere_radius)))

    lat1 = math.radians(85.0)
    for i in range(n_lat + 1):
        u = i / n_lat
        lat = lat0 + (lat1 - lat0) * u
        z = max(0.0, z_center + sphere_radius * math.sin(lat))
        mod = radial_mods[i] if (radial_mods is not None and i < len(radial_mods)) else 0.0
        r = max(1.4, sphere_radius * math.cos(lat) + mod)
        twist = (ring_idx % 2) * (step * 0.5)
        rings.append((z, r, twist))
        ring_idx += 1

    globe = make_triangulated_antiprism_solid(rings, n_sides=n_sides)
    if cut_magnet:
        return _cut_base_magnet_cavity(globe)
    return globe


def _make_latitude_band_ring(
    z_bot: float,
    z_top: float,
    r_inner: float,
    r_outer_bot: float,
    r_outer_top: float,
    n_sides: int = 24,
    twist_deg: float = 0.0,
) -> bd.Solid:
    """Create a faceted latitude band ring for multi-color planetary cloud belts."""
    w_bot_out = (
        bd.Pos(0.0, 0.0, z_bot)
        * bd.Rot(0.0, 0.0, twist_deg)
        * bd.RegularPolygon(radius=r_outer_bot, side_count=n_sides, major_radius=False).wire()
    )
    w_top_out = (
        bd.Pos(0.0, 0.0, z_top)
        * bd.Rot(0.0, 0.0, twist_deg)
        * bd.RegularPolygon(radius=r_outer_top, side_count=n_sides, major_radius=False).wire()
    )
    outer = bd.Solid.make_loft([w_bot_out, w_top_out], ruled=True)
    inner = bd.Pos(0.0, 0.0, z_bot - 0.5) * bd.Cylinder(
        radius=r_inner,
        height=(z_top - z_bot) + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return (outer - inner).solid()


def _make_sculpted_crater_or_volcano(
    r_globe: float,
    z_c: float,
    lat_deg: float,
    lon_deg: float,
    rim_radius: float,
    protrusion: float = 0.75,
    n_sides: int = 10,
) -> bd.Solid:
    """Create a radially oriented 3D crater/volcano relief boss on a planet's surface."""
    lat_r = math.radians(lat_deg)
    lon_r = math.radians(lon_deg)
    r_embed = r_globe - 2.2
    cx = r_embed * math.cos(lat_r) * math.cos(lon_r)
    cy = r_embed * math.cos(lat_r) * math.sin(lon_r)
    cz = z_c + r_embed * math.sin(lat_r)
    tilt_from_z = 90.0 - lat_deg
    return (
        bd.Pos(cx, cy, cz)
        * bd.Rot(0.0, tilt_from_z, lon_deg)
        * bd.Cone(
            bottom_radius=rim_radius * 1.18,
            top_radius=rim_radius * 0.78,
            height=2.2 + protrusion,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    ).solid()


def _cut_base_socket_shape(shape: bd.Shape, planet_num: int | None = None) -> bd.Shape:
    """Subtract the open-bottom Ø 8.00 x 10.00 mm snap-click + LED socket from any Shape/Solid."""
    return shape - _make_planet_socket_cutter(planet_num)


def _finalize_multicolor_planet(
    planet_name: str,
    primary_toolhead: int,
    layers: list[tuple[bd.Shape, str, str, int]],
) -> bd.Solid:
    """Boolean-partition a multi-color planet's layers (ordered from base globe [0] to
    highest-priority surface feature [-1]) so every subpart is a disjoint manifold solid
    with 0.0 mm³ internal overlap and has the bottom Ø 8.00 x 10.00 mm snap/LED socket +
    hidden planet number (1..8) cut out.
    """
    p_num = PLANET_ORDER_NUM.get(planet_name)
    raw_union: bd.Shape = layers[0][0]
    for shape_i, _, _, _ in layers[1:]:
        raw_union = raw_union + shape_i
    combined = _cut_base_magnet_cavity(raw_union.solid(), planet_num=p_num)

    higher_shapes: list[bd.Shape] = []
    subparts_reversed: list[bd.Solid] = []

    for shape_i, label_i, hex_i, tid_i in reversed(layers):
        part_i = _cut_base_socket_shape(shape_i, planet_num=p_num)
        for h_sh in higher_shapes:
            part_i = part_i - h_sh
        higher_shapes.append(shape_i)

        solids_i = part_i.solids()
        for idx, s in enumerate(solids_i):
            sub_lbl = label_i if len(solids_i) == 1 else f"{label_i}_{idx + 1}"
            assign_toolhead(s, sub_lbl, tid_i)
            s.color = bd.Color(hex_i)
            s.hex_color = hex_i  # type: ignore[attr-defined]
            s.label = sub_lbl
            subparts_reversed.append(s)

    subparts = list(reversed(subparts_reversed))
    primary_hex = layers[0][2]
    for _sh, _lbl, hx, td in layers:
        if td == primary_toolhead:
            primary_hex = hx
            break
    assign_toolhead(combined, planet_name, primary_toolhead)
    combined.color = bd.Color(primary_hex)
    combined.hex_color = primary_hex  # type: ignore[attr-defined]
    combined.colored_subparts = subparts  # type: ignore[attr-defined]
    return combined


def build_planet_mercury() -> bd.Solid:
    """Build 4-Color Sculpted Mercury Ornament (~23.4 mm diameter, Plate 11 Warm Palette):
      - T1 (#4A2F1D) Dark Basalt Cratered Core & Orbital Pedestal Collar
      - T3 (#D4AF37) Raised Silk Gold Caloris Basin Multi-Ring Escarpment & Lobate Scarps
      - T4 (#C41E3A) Terracotta-Red Kuiper, Beethoven & Debussy Rayed Impact Craters
      - T2 (#F5EFE6) Bright Alabaster-White North Polar Water-Ice Crater Crown
    """
    r = 11.2
    z_c = 13.8
    n_sides = 24
    mercury_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Golden Caloris Basin equatorial ridge + northern/southern tectonic scarps
    caloris_belt = _make_latitude_band_ring(
        z_bot=z_c - 1.6,
        z_top=z_c + 1.6,
        r_inner=6.5,
        r_outer_bot=r + 0.45,
        r_outer_top=r + 0.45,
        n_sides=n_sides,
        twist_deg=7.5,
    )
    caloris_basin_boss = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=18.0, lon_deg=35.0, rim_radius=3.4, protrusion=0.65
    )
    gold_caloris = caloris_belt + caloris_basin_boss

    # Sculpted 3D rayed impact craters around mid-latitudes
    craters_list = [
        _make_sculpted_crater_or_volcano(r, z_c, 28.0, 145.0, 2.3, 0.70),
        _make_sculpted_crater_or_volcano(r, z_c, -22.0, -60.0, 2.5, 0.70),
        _make_sculpted_crater_or_volcano(r, z_c, 32.0, -135.0, 2.1, 0.65),
        _make_sculpted_crater_or_volcano(r, z_c, -18.0, 95.0, 2.2, 0.65),
    ]
    crimson_craters: bd.Shape = craters_list[0]
    for cr in craters_list[1:]:
        crimson_craters = crimson_craters + cr

    z_top = mercury_globe.bounding_box().max.Z
    north_ice_crown = bd.Pos(0.0, 0.0, z_top - 1.9) * bd.extrude(
        bd.RegularPolygon(radius=4.8, side_count=12), amount=2.1
    ).solid()

    return _finalize_multicolor_planet(
        "planet_mercury",
        3,
        [
            (mercury_globe, "mercury_basalt_core", "#4A2F1D", 1),
            (gold_caloris, "mercury_gold_caloris_basin", "#D4AF37", 3),
            (crimson_craters, "mercury_terracotta_craters", "#C41E3A", 4),
            (north_ice_crown, "mercury_alabaster_polar_crown", "#F5EFE6", 2),
        ],
    )


def build_planet_venus() -> bd.Solid:
    """Build 4-Color Sculpted Venus Ornament (~26.4 mm diameter, Plate 11 Warm Palette):
      - T3 (#D4AF37) Golden Sulfuric Cloud Deck Globe & Orbital Pedestal Collar
      - T2 (#F5EFE6) Creamy Alabaster High-Altitude Planetary Y-Wave Cloud Bands & Polar Hood
      - T4 (#C41E3A) Crimson-Amber Equatorial Super-Rotation Chevron Belt & Maxwell Montes
      - T1 (#4A2F1D) Dark Umber Sub-Polar Double-Eye Vortex Collars
    """
    r = 12.6
    z_c = 15.2
    n_sides = 24
    venus_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Creamy Alabaster mid-latitude Y-wave sulfuric cloud bands + bright polar dipole cap
    y_wave_north = _make_latitude_band_ring(
        z_bot=z_c + 1.8,
        z_top=z_c + 4.0,
        r_inner=7.0,
        r_outer_bot=math.sqrt(r**2 - 1.8**2) + 0.42,
        r_outer_top=math.sqrt(r**2 - 4.0**2) + 0.42,
        n_sides=n_sides,
        twist_deg=7.5,
    )
    y_wave_south = _make_latitude_band_ring(
        z_bot=z_c - 4.0,
        z_top=z_c - 1.8,
        r_inner=7.0,
        r_outer_bot=math.sqrt(r**2 - 4.0**2) + 0.42,
        r_outer_top=math.sqrt(r**2 - 1.8**2) + 0.42,
        n_sides=n_sides,
        twist_deg=7.5,
    )
    z_top = venus_globe.bounding_box().max.Z
    polar_dipole = bd.Pos(0.0, 0.0, z_top - 1.8) * bd.extrude(
        bd.RegularPolygon(radius=5.0, side_count=12), amount=2.0
    ).solid()
    alabaster_clouds = y_wave_north + y_wave_south + polar_dipole

    # Equatorial Crimson Super-Rotation Band + Ishtar Terra / Maxwell Montes highland dome
    eq_superrotation = _make_latitude_band_ring(
        z_bot=z_c - 1.5,
        z_top=z_c + 1.5,
        r_inner=7.5,
        r_outer_bot=r + 0.55,
        r_outer_top=r + 0.55,
        n_sides=n_sides,
        twist_deg=15.0,
    )
    maxwell_montes = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=26.0, lon_deg=-45.0, rim_radius=3.2, protrusion=0.75
    )
    crimson_band = eq_superrotation + maxwell_montes

    # Dark Umber Northern & Southern Cloud Vortex Collars
    vortex_north = _make_latitude_band_ring(
        z_bot=z_c + 5.2,
        z_top=z_c + 7.6,
        r_inner=5.5,
        r_outer_bot=math.sqrt(r**2 - 5.2**2) + 0.48,
        r_outer_top=math.sqrt(r**2 - 7.6**2) + 0.48,
        n_sides=n_sides,
    )
    vortex_south = _make_latitude_band_ring(
        z_bot=z_c - 6.8,
        z_top=z_c - 4.6,
        r_inner=5.5,
        r_outer_bot=math.sqrt(r**2 - 6.8**2) + 0.48,
        r_outer_top=math.sqrt(r**2 - 4.6**2) + 0.48,
        n_sides=n_sides,
    )
    bronze_vortices = vortex_north + vortex_south

    return _finalize_multicolor_planet(
        "planet_venus",
        3,
        [
            (venus_globe, "venus_gold_cloud_deck", "#D4AF37", 3),
            (alabaster_clouds, "venus_alabaster_y_waves", "#F5EFE6", 2),
            (bronze_vortices, "venus_umber_vortex_collars", "#4A2F1D", 1),
            (crimson_band, "venus_crimson_superrotation", "#C41E3A", 4),
        ],
    )


def build_planet_earth() -> bd.Solid:
    """Build 4-Color Sculpted Earth Ornament (~30.2 mm diameter, Plate 12 Ocean Palette):
      - T1 (#1E5AA8) Deep Cobalt-Azure Pacific, Atlantic & Indian Ocean Globe & Pedestal
      - T2 (#00A86B) Sculpted 3D Emerald Continents (Americas, Eurasia, Africa, Australia)
      - T4 (#D4AF37) Raised Golden-Ochre Mountain Cordilleras (Andes, Rockies, Himalayas)
      - T3 (#F0F4F8) Crisp Glacial-White Arctic Ice Cap & Trade-Wind Cyclone Swirls
    """
    r = 14.2
    z_c = 16.8
    n_sides = 24
    ocean_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )
    continent_shell = _make_triangulated_planet_globe(
        r + 0.85, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False, include_pedestal=False
    )

    # 5 Distinct Sculpted Continental Landmasses intersected with the +0.85 mm relief shell
    americas_n = (
        bd.Pos(-5.5, -4.5, z_c + 2.8)
        * bd.Rot(22.0, -28.0, 35.0)
        * bd.extrude(bd.RegularPolygon(radius=6.8, side_count=7), amount=10.5)
    )
    americas_s = (
        bd.Pos(-3.2, -6.2, z_c - 3.2)
        * bd.Rot(32.0, -12.0, 18.0)
        * bd.extrude(bd.RegularPolygon(radius=5.6, side_count=6), amount=10.5)
    )
    eurasia = (
        bd.Pos(5.4, 3.6, z_c + 2.5)
        * bd.Rot(-18.0, 28.0, -25.0)
        * bd.extrude(bd.RegularPolygon(radius=8.2, side_count=8), amount=10.5)
    )
    africa = (
        bd.Pos(3.5, 4.8, z_c - 2.2)
        * bd.Rot(-28.0, 16.0, -10.0)
        * bd.extrude(bd.RegularPolygon(radius=6.2, side_count=7), amount=10.5)
    )
    australia = (
        bd.Pos(5.2, -4.8, z_c - 4.0)
        * bd.Rot(24.0, 24.0, 15.0)
        * bd.extrude(bd.RegularPolygon(radius=4.6, side_count=6), amount=10.5)
    )
    clip_above_pedestal = bd.Pos(0.0, 0.0, 6.2) * bd.Cylinder(
        radius=20.0, height=30.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    continents = ((americas_n + americas_s + eurasia + africa + australia) & continent_shell) & clip_above_pedestal

    # Raised Golden Mountain Cordilleras (Rockies/Andes & Himalayas/Alps) at +1.25 mm relief
    mountain_shell = _make_triangulated_planet_globe(
        r + 1.25, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False, include_pedestal=False
    )
    m_cordillera = (
        bd.Pos(-5.2, -4.8, z_c + 1.8)
        * bd.Rot(22.0, -28.0, 35.0)
        * bd.extrude(bd.RegularPolygon(radius=3.4, side_count=6), amount=11.5)
    )
    m_andes = (
        bd.Pos(-3.5, -6.0, z_c - 2.8)
        * bd.Rot(32.0, -12.0, 18.0)
        * bd.extrude(bd.RegularPolygon(radius=2.8, side_count=6), amount=11.5)
    )
    m_himalayas = (
        bd.Pos(5.6, 3.8, z_c + 2.0)
        * bd.Rot(-18.0, 28.0, -25.0)
        * bd.extrude(bd.RegularPolygon(radius=3.8, side_count=6), amount=11.5)
    )
    mountains = ((m_cordillera + m_andes + m_himalayas) & mountain_shell) & clip_above_pedestal

    # Crisp Glacial-White Arctic Polar Cap + Sub-Antarctic Ice Belt
    z_top = ocean_globe.bounding_box().max.Z
    arctic_cap = (
        bd.Pos(0.0, 0.0, z_top - 2.8)
        * bd.extrude(bd.RegularPolygon(radius=6.8, side_count=16), amount=3.4)
        & continent_shell
    )
    cloud_swirl_1 = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=8.0, lon_deg=-15.0, rim_radius=2.8, protrusion=0.60
    )
    cloud_swirl_2 = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=-12.0, lon_deg=155.0, rim_radius=2.8, protrusion=0.60
    )
    polar_and_clouds = arctic_cap + cloud_swirl_1 + cloud_swirl_2

    return _finalize_multicolor_planet(
        "planet_earth",
        1,
        [
            (ocean_globe, "earth_cobalt_ocean_globe", "#1E5AA8", 1),
            (continents, "earth_emerald_continents", "#00A86B", 2),
            (mountains, "earth_gold_mountain_ranges", "#D4AF37", 4),
            (polar_and_clouds, "earth_white_polar_ice_clouds", "#F0F4F8", 3),
        ],
    )


def build_planet_mars() -> bd.Solid:
    """Build 4-Color Sculpted Mars Ornament (~25.8 mm diameter, Plate 11 Warm Palette):
      - T4 (#C41E3A) Rusty Terracotta-Crimson Planet Body & Orbital Pedestal Collar
      - T3 (#D4AF37) Ochre-Gold Tharsis Volcanic Bulge & Hellas Planitia Basin Rim
      - T1 (#4A2F1D) Dark Basalt Valles Marineris Rift Canyon + Olympus Mons & Tharsis Volcanoes
      - T2 (#F5EFE6) Crisp Alabaster-White North Polar Planum Boreum Ice Cap
    """
    r = 12.2
    z_c = 14.8
    n_sides = 24
    mars_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Ochre-Gold Tharsis bulge & southern Hellas highland belt
    hellas_belt = _make_latitude_band_ring(
        z_bot=z_c - 5.2,
        z_top=z_c - 2.6,
        r_inner=6.5,
        r_outer_bot=math.sqrt(r**2 - 5.2**2) + 0.42,
        r_outer_top=math.sqrt(r**2 - 2.6**2) + 0.42,
        n_sides=n_sides,
        twist_deg=7.5,
    )
    tharsis_plateau = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=14.0, lon_deg=-90.0, rim_radius=4.8, protrusion=0.48
    )
    ochre_highlands = hellas_belt + tharsis_plateau

    # Dark Basalt Valles Marineris canyon belt + towering Olympus Mons + 2 Tharsis shield volcanoes
    canyon_belt = _make_latitude_band_ring(
        z_bot=z_c - 1.5,
        z_top=z_c + 1.5,
        r_inner=7.0,
        r_outer_bot=r + 0.48,
        r_outer_top=r + 0.48,
        n_sides=n_sides,
        twist_deg=15.0,
    )
    olympus_mons = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=22.0, lon_deg=-90.0, rim_radius=3.1, protrusion=1.05
    )
    ascraeus_mons = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=18.0, lon_deg=-42.0, rim_radius=2.2, protrusion=0.75
    )
    pavonis_mons = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=25.0, lon_deg=110.0, rim_radius=2.4, protrusion=0.75
    )
    basalt_features = canyon_belt + olympus_mons + ascraeus_mons + pavonis_mons

    # Crisp Alabaster-White North Polar Ice Cap
    z_top = mars_globe.bounding_box().max.Z
    polar_cap = bd.Pos(0.0, 0.0, z_top - 1.9) * bd.extrude(
        bd.RegularPolygon(radius=5.0, side_count=12), amount=2.2
    ).solid()

    return _finalize_multicolor_planet(
        "planet_mars",
        4,
        [
            (mars_globe, "mars_terracotta_body", "#C41E3A", 4),
            (ochre_highlands, "mars_ochre_tharsis_hellas", "#D4AF37", 3),
            (basalt_features, "mars_basalt_canyon_olympus", "#4A2F1D", 1),
            (polar_cap, "mars_alabaster_polar_cap", "#F5EFE6", 2),
        ],
    )


def build_planet_jupiter() -> bd.Solid:
    """Build 4-Color Sculpted Jupiter Gas-Giant Ornament (~35.4 mm diameter, Plate 11 Warm Palette):
      - T3 (#D4AF37) Silk Gold Equatorial & Temperate Zone Globe & Orbital Pedestal Collar
      - T2 (#F5EFE6) Creamy Alabaster Tropical Cloud Zones & White Oval BA Anticyclones
      - T1 (#4A2F1D) Dark Umber North & South Equatorial/Temperate Cloud Belts
      - T4 (#C41E3A) Crimson Equatorial Festoon Belt, Raised Great Red Spot & Polar Cyclone Crown
    """
    r = 16.6
    z_c = 19.5
    n_sides = 28
    core_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=14, n_sides=n_sides, cut_magnet=False
    )

    # Creamy Alabaster North & South Tropical Zones + White Oval Storms
    zone_north = _make_latitude_band_ring(
        z_bot=z_c + 5.2,
        z_top=z_c + 7.8,
        r_inner=9.0,
        r_outer_bot=math.sqrt(r**2 - 5.2**2) + 0.50,
        r_outer_top=math.sqrt(r**2 - 7.8**2) + 0.50,
        n_sides=n_sides,
    )
    zone_south = _make_latitude_band_ring(
        z_bot=z_c - 7.8,
        z_top=z_c - 5.2,
        r_inner=9.0,
        r_outer_bot=math.sqrt(r**2 - 7.8**2) + 0.50,
        r_outer_top=math.sqrt(r**2 - 5.2**2) + 0.50,
        n_sides=n_sides,
    )
    oval_ba = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=-26.0, lon_deg=45.0, rim_radius=2.6, protrusion=0.80
    )
    alabaster_zones = zone_north + zone_south + oval_ba

    # Dark Umber North & South Equatorial Belts (NEB / SEB) + North Temperate Belt
    belt_south = _make_latitude_band_ring(
        z_bot=z_c - 5.0,
        z_top=z_c - 2.0,
        r_inner=9.5,
        r_outer_bot=math.sqrt(r**2 - 5.0**2) + 0.65,
        r_outer_top=math.sqrt(r**2 - 2.0**2) + 0.65,
        n_sides=n_sides,
    )
    belt_north = _make_latitude_band_ring(
        z_bot=z_c + 2.0,
        z_top=z_c + 5.0,
        r_inner=9.5,
        r_outer_bot=math.sqrt(r**2 - 2.0**2) + 0.65,
        r_outer_top=math.sqrt(r**2 - 5.0**2) + 0.65,
        n_sides=n_sides,
    )
    belt_ntb = _make_latitude_band_ring(
        z_bot=z_c + 8.0,
        z_top=z_c + 10.2,
        r_inner=8.0,
        r_outer_bot=math.sqrt(r**2 - 8.0**2) + 0.55,
        r_outer_top=math.sqrt(r**2 - 10.2**2) + 0.55,
        n_sides=n_sides,
    )
    brown_belts = belt_south + belt_north + belt_ntb

    # Crimson Equatorial Festoon Band + Sculpted Great Red Spot Vortex + Juno Polar Cyclone Rosette
    eq_band = _make_latitude_band_ring(
        z_bot=z_c - 1.6,
        z_top=z_c + 1.6,
        r_inner=10.5,
        r_outer_bot=r + 0.75,
        r_outer_top=r + 0.75,
        n_sides=n_sides,
        twist_deg=6.4,
    )
    great_red_spot = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=-16.0, lon_deg=-90.0, rim_radius=4.2, protrusion=1.15
    )
    z_top = core_globe.bounding_box().max.Z
    polar_crown = bd.Pos(0.0, 0.0, z_top - 2.0) * bd.extrude(
        bd.RegularPolygon(radius=6.2, side_count=8), amount=2.3
    ).solid()
    crimson_features = eq_band + great_red_spot + polar_crown

    return _finalize_multicolor_planet(
        "planet_jupiter",
        3,
        [
            (core_globe, "jupiter_gold_zones", "#D4AF37", 3),
            (alabaster_zones, "jupiter_alabaster_tropical_zones", "#F5EFE6", 2),
            (brown_belts, "jupiter_umber_temperate_belts", "#4A2F1D", 1),
            (crimson_features, "jupiter_crimson_great_red_spot", "#C41E3A", 4),
        ],
    )


def build_planet_saturn() -> bd.Solid:
    """Build 4-Color Sculpted Saturn Ornament (~44.0 mm ring span, Plate 11 Warm Palette):
      - T3 (#D4AF37) Silk Gold Gas-Giant Globe, Orbital Pedestal & Main A/B Ring System
      - T2 (#F5EFE6) Creamy Alabaster Inner B-Ring Crest & Bright Equatorial Ammonia Band
      - T1 (#4A2F1D) Dark Umber Cassini Ring Division Band & Southern Temperate Belt
      - T4 (#C41E3A) Crimson Northern Storm Belt & Famous 6-Sided North Polar Hexagon
    """
    r = 13.6
    z_c = 16.6
    n_sides = 24
    saturn_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Multi-tiered planetary ring disc (Ø 44.0 mm outer span at Z = z_c + 1.0 = 17.6 mm)
    n_ring = 28
    w_r0 = bd.Pos(0.0, 0.0, z_c - 0.5) * bd.RegularPolygon(radius=19.8, side_count=n_ring).wire()
    w_r1 = bd.Pos(0.0, 0.0, z_c + 1.0) * bd.RegularPolygon(radius=22.0, side_count=n_ring).wire()
    w_r2 = bd.Pos(0.0, 0.0, z_c + 2.5) * bd.RegularPolygon(radius=19.8, side_count=n_ring).wire()
    ring_outer = bd.Solid.make_loft([w_r0, w_r1, w_r2], ruled=True)
    ring_bore = bd.Pos(0.0, 0.0, z_c - 3.0) * bd.Cylinder(
        radius=10.5, height=8.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    main_ring = (ring_outer - ring_bore).solid()
    gold_body_and_ring = (saturn_globe + main_ring).solid()

    # Creamy Alabaster bright inner B-ring crest (R = 14.5..16.8 mm) + sub-equatorial cloud band
    w_b0 = bd.Pos(0.0, 0.0, z_c - 0.7) * bd.RegularPolygon(radius=16.8, side_count=n_ring).wire()
    w_b1 = bd.Pos(0.0, 0.0, z_c + 2.7) * bd.RegularPolygon(radius=16.8, side_count=n_ring).wire()
    b_ring_outer = bd.Solid.make_loft([w_b0, w_b1], ruled=True)
    b_ring_inner = bd.Pos(0.0, 0.0, z_c - 3.0) * bd.Cylinder(
        radius=14.6, height=8.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    b_ring_crest = (b_ring_outer - b_ring_inner).solid()
    ammonia_band = _make_latitude_band_ring(
        z_bot=z_c - 5.2,
        z_top=z_c - 2.6,
        r_inner=7.5,
        r_outer_bot=math.sqrt(r**2 - 5.2**2) + 0.45,
        r_outer_top=math.sqrt(r**2 - 2.6**2) + 0.45,
        n_sides=n_sides,
    )
    alabaster_features = b_ring_crest + ammonia_band

    # Dark Umber Cassini Division ring band (R = 17.5..19.2 mm)
    w_c0 = bd.Pos(0.0, 0.0, z_c - 0.8) * bd.RegularPolygon(radius=19.2, side_count=n_ring).wire()
    w_c1 = bd.Pos(0.0, 0.0, z_c + 2.8) * bd.RegularPolygon(radius=19.2, side_count=n_ring).wire()
    cassini_outer = bd.Solid.make_loft([w_c0, w_c1], ruled=True)
    cassini_inner = bd.Pos(0.0, 0.0, z_c - 3.0) * bd.Cylinder(
        radius=17.4, height=8.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    cassini_band = (cassini_outer - cassini_inner).solid()

    # Crimson Northern Dragon Storm Belt + Famous 6-Sided North Polar Hexagon
    crimson_belt = _make_latitude_band_ring(
        z_bot=z_c + 3.4,
        z_top=z_c + 6.0,
        r_inner=7.5,
        r_outer_bot=math.sqrt(r**2 - 3.4**2) + 0.50,
        r_outer_top=math.sqrt(r**2 - 6.0**2) + 0.50,
        n_sides=n_sides,
    )
    z_top = saturn_globe.bounding_box().max.Z
    polar_hexagon = bd.Pos(0.0, 0.0, z_top - 1.9) * bd.extrude(
        bd.RegularPolygon(radius=5.8, side_count=6), amount=2.2
    ).solid()
    crimson_features = crimson_belt + polar_hexagon

    return _finalize_multicolor_planet(
        "planet_saturn",
        3,
        [
            (gold_body_and_ring, "saturn_gold_globe_and_ring", "#D4AF37", 3),
            (alabaster_features, "saturn_alabaster_inner_ring", "#F5EFE6", 2),
            (cassini_band, "saturn_umber_cassini_division", "#4A2F1D", 1),
            (crimson_features, "saturn_crimson_polar_hexagon", "#C41E3A", 4),
        ],
    )


def build_planet_uranus() -> bd.Solid:
    """Build 4-Color Sculpted Uranus Ice-Giant Ornament (~36.4 mm ring span, Plate 12 Ice Palette):
      - T2 (#00A86B) Cyan-Emerald Ice-Giant Atmosphere Globe & Orbital Pedestal Collar
      - T1 (#1E5AA8) Deep Cobalt-Azure Tropospheric Latitude Bands
      - T4 (#D4AF37) Sculpted 16° Tilted Golden Epsilon & Alpha Ring System
      - T3 (#F0F4F8) Crisp Glacial-White North Polar Cloud Hood & Methane Storm Plumes
    """
    r = 12.8
    z_c = 15.6
    n_sides = 24
    uranus_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Deep Cobalt-Azure Northern & Southern Tropospheric Cloud Bands
    cobalt_north = _make_latitude_band_ring(
        z_bot=z_c + 2.8,
        z_top=z_c + 5.6,
        r_inner=7.0,
        r_outer_bot=math.sqrt(r**2 - 2.8**2) + 0.45,
        r_outer_top=math.sqrt(r**2 - 5.6**2) + 0.45,
        n_sides=n_sides,
    )
    cobalt_south = _make_latitude_band_ring(
        z_bot=z_c - 5.4,
        z_top=z_c - 2.6,
        r_inner=7.0,
        r_outer_bot=math.sqrt(r**2 - 5.4**2) + 0.45,
        r_outer_top=math.sqrt(r**2 - 2.6**2) + 0.45,
        n_sides=n_sides,
    )
    cobalt_bands = cobalt_north + cobalt_south

    # Tilted 16° Golden Epsilon Ring around Uranus (centered at Z = z_c + 1.0 = 16.6 mm)
    n_ring = 24
    ring_prism = bd.extrude(
        bd.RegularPolygon(radius=18.2, side_count=n_ring), amount=1.8, both=True
    )
    ring_hole = bd.Cylinder(
        radius=9.8, height=10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    tilted_ring = (
        bd.Pos(0.0, 0.0, z_c + 1.0)
        * bd.Rot(16.0, 0.0, 0.0)
        * (ring_prism - ring_hole)
    ).solid()

    # Crisp Glacial-White Polar Hood + Methane Ice Cloud Plumes
    z_top = uranus_globe.bounding_box().max.Z
    polar_hood = bd.Pos(0.0, 0.0, z_top - 2.0) * bd.extrude(
        bd.RegularPolygon(radius=5.4, side_count=14), amount=2.3
    ).solid()
    methane_plume = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=34.0, lon_deg=90.0, rim_radius=2.2, protrusion=0.65
    )
    white_polar_features = polar_hood + methane_plume

    return _finalize_multicolor_planet(
        "planet_uranus",
        2,
        [
            (uranus_globe, "uranus_cyan_ice_globe", "#00A86B", 2),
            (cobalt_bands, "uranus_cobalt_latitude_bands", "#1E5AA8", 1),
            (tilted_ring, "uranus_gold_epsilon_ring", "#D4AF37", 4),
            (white_polar_features, "uranus_white_polar_hood", "#F0F4F8", 3),
        ],
    )


def build_planet_neptune() -> bd.Solid:
    """Build 4-Color Sculpted Neptune Ice-Giant Ornament (~28.4 mm diameter, Plate 12 Ice Palette):
      - T1 (#1E5AA8) Deep Cobalt-Azure Ice-Giant Atmosphere Globe & Orbital Pedestal Collar
      - T2 (#00A86B) Cyan-Teal Supersonic Zonal Wind Belts & Southern Collar
      - T4 (#D4AF37) Golden-Ochre Raised Great Dark Spot Vortex Rim & Equatorial Ring Arc
      - T3 (#F0F4F8) Crisp Glacial-White Methane Cirrus Cloud Streaks, 'Scooter' Storm & Polar Cap
    """
    r = 13.5
    z_c = 16.2
    n_sides = 24
    neptune_globe = _make_triangulated_planet_globe(
        r, z_c, n_lat=12, n_sides=n_sides, cut_magnet=False
    )

    # Cyan-Teal Supersonic Zonal Wind Belts
    teal_north = _make_latitude_band_ring(
        z_bot=z_c + 2.4,
        z_top=z_c + 5.2,
        r_inner=7.5,
        r_outer_bot=math.sqrt(r**2 - 2.4**2) + 0.45,
        r_outer_top=math.sqrt(r**2 - 5.2**2) + 0.45,
        n_sides=n_sides,
    )
    teal_south = _make_latitude_band_ring(
        z_bot=z_c - 5.4,
        z_top=z_c - 2.6,
        r_inner=7.5,
        r_outer_bot=math.sqrt(r**2 - 5.4**2) + 0.45,
        r_outer_top=math.sqrt(r**2 - 2.6**2) + 0.45,
        n_sides=n_sides,
    )
    teal_belts = teal_north + teal_south

    # Golden Adams Ring Arc (equatorial) + Great Dark Spot outer collar
    eq_ring_arc = _make_latitude_band_ring(
        z_bot=z_c - 1.4,
        z_top=z_c + 1.4,
        r_inner=8.0,
        r_outer_bot=r + 0.52,
        r_outer_top=r + 0.52,
        n_sides=n_sides,
        twist_deg=7.5,
    )
    gds_outer = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=-18.0, lon_deg=-90.0, rim_radius=3.6, protrusion=0.80
    )
    gold_features = eq_ring_arc + gds_outer

    # Crisp Glacial-White High-Altitude Cirrus Companion Cloud on GDS + 'Scooter' Storm + Polar Vortex
    gds_companion = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=-18.0, lon_deg=-90.0, rim_radius=2.1, protrusion=1.15
    )
    scooter_storm = _make_sculpted_crater_or_volcano(
        r, z_c, lat_deg=24.0, lon_deg=60.0, rim_radius=2.3, protrusion=0.85
    )
    z_top = neptune_globe.bounding_box().max.Z
    polar_cap = bd.Pos(0.0, 0.0, z_top - 1.9) * bd.extrude(
        bd.RegularPolygon(radius=5.2, side_count=14), amount=2.2
    ).solid()
    white_cirrus = gds_companion + scooter_storm + polar_cap

    return _finalize_multicolor_planet(
        "planet_neptune",
        1,
        [
            (neptune_globe, "neptune_cobalt_ice_globe", "#1E5AA8", 1),
            (teal_belts, "neptune_teal_wind_belts", "#00A86B", 2),
            (gold_features, "neptune_gold_dark_spot_ring", "#D4AF37", 4),
            (white_cirrus, "neptune_white_cirrus_scooter", "#F0F4F8", 3),
        ],
    )


_SPHERE_25MM_CACHE: bd.Solid | None = None


def _make_exact_25mm_apple_sphere_centered() -> bd.Solid:
    """Create a cached exact 25.00 x 25.00 x 25.00 mm faceted sphere centered at (0, 0, 0)."""
    global _SPHERE_25MM_CACHE
    if _SPHERE_25MM_CACHE is None:
        r = BALL_DIAMETER / 2.0  # 12.50 mm
        n_sides = 24
        lat_angles_deg = [-82.0, -65.0, -45.0, -22.5, 0.0, 22.5, 45.0, 65.0, 82.0]
        rings: list[tuple[float, float, float]] = []
        for lat_deg in lat_angles_deg:
            lat_rad = math.radians(lat_deg)
            if abs(lat_deg - (-82.0)) < 1e-6:
                z = -r
            elif abs(lat_deg - 82.0) < 1e-6:
                z = r
            else:
                z = r * math.sin(lat_rad)
            rad = r * math.cos(lat_rad)
            rings.append((z, rad, 0.0))
        _SPHERE_25MM_CACHE = make_triangulated_antiprism_solid(rings, n_sides=n_sides)
    return _SPHERE_25MM_CACHE


def _make_sector_wedge(
    r_max: float, z_min: float, z_max: float, deg_start: float, deg_end: float, n_arc: int = 16
) -> bd.Solid:
    """Create a cylindrical sector prism spanning [deg_start, deg_end] and [z_min, z_max]."""
    pts = [(0.0, 0.0)]
    for i in range(n_arc + 1):
        ang = math.radians(deg_start + (deg_end - deg_start) * (i / n_arc))
        pts.append((r_max * math.cos(ang), r_max * math.sin(ang)))
    pts.append((0.0, 0.0))
    wire = bd.Wire.make_polygon([bd.Vector(x, y, z_min) for x, y in pts])
    face = bd.Face(wire)
    return bd.extrude(face, amount=z_max - z_min)


def build_apple_hemisphere_a(label: str = "Apple_Hemisphere_A") -> bd.Solid:
    """Build Apple_Hemisphere_A (Upper Half with Quarter-Turn 3-Lug Bayonet Twist-Lock Collar,
    wide Ø 18.70 x 7.30 mm equatorial chamber for the Bambu Lab Y-Shape LED Light with Magnetic
    Control Switch KC012/KC013 [Ø 18.0 x 6.5 mm] as well as M8 hex nut / Ø 12.7 mm steel ball /
    Ø 7.5 mm Single LED, R_neck = 10.42 mm, 3 radial lugs R_lug = 11.02 mm with 45° elephant's-foot
    relief & 45° top locking cam ramp, and ~1.9 mm hollow lantern dome), oriented flat at Z = 0.00 mm.
    """
    sph = _make_exact_25mm_apple_sphere_centered()
    r_y_led = 9.35      # Ø 18.70 mm bore (+0.70 mm clearance for Ø 18.0 x 6.5 mm Bambu Y-Shape LED KC012/KC013!)
    r_neck = 10.30      # Smooth cylindrical male bayonet neck (0.95 mm solid wall, Ø 20.60 mm)
    r_lug = 11.15       # 3 protruding bayonet lugs (+0.85 mm radial / +1.70 mm diametrical lock!)
    lip_h = 2.65

    up_box = bd.Box(30.0, 30.0, 15.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    upper_dome = (sph & up_box).solid()

    # 1. Smooth axisymmetric male bayonet neck + 0.40 mm bottom elephant's-foot chamfer + 0.22 mm top root fillet
    ef_chamfer = bd.Pos(0.0, 0.0, -lip_h) * bd.Cone(
        bottom_radius=9.90,
        top_radius=r_neck,
        height=0.40,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    neck_cyl = bd.Pos(0.0, 0.0, -lip_h + 0.40) * bd.Cylinder(
        radius=r_neck,
        height=lip_h - 0.40 + 0.05,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    scarf_cone = bd.Pos(0.0, 0.0, -0.22) * bd.Cone(
        bottom_radius=r_neck,
        top_radius=r_neck + 0.22,
        height=0.22,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    scarf_top_join = bd.Cylinder(
        radius=r_neck + 0.22,
        height=0.45,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    male_collar_base = ef_chamfer + neck_cyl + scarf_cone + scarf_top_join

    # 2. 3 Male Bayonet Lugs (32° wide each at 0°, 120°, 240°) with 45° bottom lead-in & 45° top locking ramp:
    # - z = -2.65..-1.80 mm (Z_print = 0.00..0.85 mm): 45° bottom lead-in & elephant's-foot relief (10.30 -> 11.15 mm)
    # - z = -1.80..-1.40 mm (Z_print = 0.85..1.25 mm): Cylindrical lug land at R_lug = 11.15 mm
    # - z = -1.40..-0.55 mm (Z_print = 1.25..2.10 mm): 45° top locking cam ramp (11.15 -> 10.30 mm)
    lug_bot_cone = bd.Pos(0.0, 0.0, -lip_h) * bd.Cone(
        bottom_radius=r_neck,
        top_radius=r_lug,
        height=r_lug - r_neck,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    lug_mid_cyl = bd.Pos(0.0, 0.0, -1.80) * bd.Cylinder(
        radius=r_lug,
        height=0.40,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    lug_top_cone = bd.Pos(0.0, 0.0, -1.40) * bd.Cone(
        bottom_radius=r_lug,
        top_radius=r_neck,
        height=r_lug - r_neck,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    lug_ring_full = (lug_bot_cone + lug_mid_cyl + lug_top_cone).solid()

    lugs_list = []
    for k in range(3):
        c_deg = k * 120.0
        wedge = _make_sector_wedge(14.0, -lip_h - 0.2, 0.0, c_deg - 16.0, c_deg + 16.0, n_arc=24)
        lugs_list.append((lug_ring_full & wedge).solid())

    # 3. Wide Ø 18.70 mm (R = 9.35 mm) Y-Shape LED & Universal Core Chamber (z = -2.55..+3.65 mm)
    inner_core_a = bd.Pos(0.0, 0.0, -lip_h - 0.10) * bd.Cylinder(
        radius=r_y_led,
        height=lip_h + 3.65 + 0.15,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # 4. Contoured Thin-Shell Hollow Lantern Dome (Z = 3.60..10.65 mm):
    # Seamlessly continues from the Ø 18.70 mm (R = 9.35 mm) Y-Shape LED chamber up to the pole!
    lantern_dome_a = make_triangulated_antiprism_solid(
        [
            (3.60,  r_y_led, 0.0),
            (5.70,  8.90,    7.5),
            (7.20,  8.15,    0.0),
            (9.00,  6.75,    7.5),
            (10.20, 4.60,    0.0),
            (10.65, 2.25,    7.5),
        ],
        n_sides=24,
    )
    mark_a = bd.Pos(0.0, 0.0, 10.65) * make_engraved_label_solid(
        "A", char_h=2.5, depth=0.45
    )

    hemi_a_raw = upper_dome + male_collar_base
    for lg in lugs_list:
        hemi_a_raw = hemi_a_raw + lg
    hemi_a_raw = (
        hemi_a_raw
        - inner_core_a
        - lantern_dome_a
        - mark_a
    ).solid()
    hemi_a = hemi_a_raw.moved(bd.Location((0.0, 0.0, lip_h)))
    return assign_toolhead(hemi_a, label, 4)


def build_apple_hemisphere_b(label: str = "Apple_Hemisphere_B") -> bd.Solid:
    """Build Apple_Hemisphere_B (Lower Half with Quarter-Turn 3-Lug Female Bayonet Socket:
    R_bore = 10.64 mm (+0.44 mm diametrical clearance around R_neck = 10.42 mm), 3 vertical entry
    keyway slots (40° wide, R = 11.26 mm), 3 clockwise undercut locking tunnels (R = 11.24 mm
    with 45° self-supporting cam ceiling & floor), wide Ø 18.70 x 7.30 mm chamber for the
    Bambu Lab Y-Shape LED Light KC012/KC013 [Ø 18.0 x 6.5 mm], and ~1.9 mm hollow lantern dome),
    oriented flat at Z = 0.00 mm.
    """
    sph = _make_exact_25mm_apple_sphere_centered()
    r_y_led = 9.35      # Ø 18.70 mm bore (+0.70 mm clearance for Ø 18.0 x 6.5 mm Bambu Y-Shape LED KC012/KC013!)
    r_bore = 10.52      # +0.22 mm radial (+0.44 mm diametrical) clearance around R_neck = 10.30 mm
    r_tunnel = 11.38    # +0.23 mm radial (+0.46 mm diametrical) clearance around R_lug = 11.15 mm
    r_seat_top = 10.76  # 0.24 mm top entry chamfer leaving a wide 1.74 mm flat bed ring AND full retaining roof!

    low_box = bd.Box(30.0, 30.0, 15.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX))
    lower_dome = (sph & low_box).solid()

    # 1. Axisymmetric Female Entry Chamfer + Central Throat Bore (R_bore = 10.52 mm)
    #    + 45° self-supporting transition to the Ø 18.70 mm (R = 9.35 mm) Y-Shape LED chamber:
    seat_top_cyl = bd.Pos(0.0, 0.0, -0.05) * bd.Cylinder(
        radius=r_seat_top,
        height=0.25,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    seat_cone = bd.Pos(0.0, 0.0, -0.24) * bd.Cone(
        bottom_radius=r_bore,
        top_radius=r_seat_top,
        height=0.24,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    throat_cyl = bd.Pos(0.0, 0.0, -2.75) * bd.Cylinder(
        radius=r_bore,
        height=2.55,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    throat_roof_cone = bd.Pos(0.0, 0.0, -2.75 - (r_bore - r_y_led)) * bd.Cone(
        bottom_radius=r_y_led,
        top_radius=r_bore,
        height=r_bore - r_y_led,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    fem_bore_base = seat_top_cyl + seat_cone + throat_cyl + throat_roof_cone

    # 2. 3 Vertical Entry Keyway Slots (42° wide at 0°, 120°, 240°, R = 11.40 mm):
    kw_cyl = bd.Pos(0.0, 0.0, -1.95) * bd.Cylinder(
        radius=r_tunnel + 0.02,
        height=2.15,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    kw_floor_cone = bd.Pos(0.0, 0.0, -1.95 - (r_tunnel + 0.02 - r_bore)) * bd.Cone(
        bottom_radius=r_bore,
        top_radius=r_tunnel + 0.02,
        height=r_tunnel + 0.02 - r_bore,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    kw_ring_full = (kw_cyl + kw_floor_cone).solid()

    # 3. 3 Two-Stage Helical Cam Undercut Twist-Lock Tunnels (spanning -64° to +21° around 0°, 120°, 240°):
    # - Stage 1 Entry Ramp (-28° to +21°): ceiling starts higher (z = -0.34 -> -1.20 mm) for effortless lead-in
    # - Stage 2 Locked Seat (-64° to -24°): ceiling steps down (z = -0.46 -> -1.32 mm) to cinch the 45° lug ramp
    #   underneath a thick solid PLA retaining ceiling once twisted -45° clockwise!
    tun_entry_ceil = bd.Pos(0.0, 0.0, -1.20) * bd.Cone(
        bottom_radius=r_tunnel,
        top_radius=r_bore,
        height=r_tunnel - r_bore,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    tun_lock_ceil = bd.Pos(0.0, 0.0, -1.32) * bd.Cone(
        bottom_radius=r_tunnel,
        top_radius=r_bore,
        height=r_tunnel - r_bore,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    tun_mid_cyl = bd.Pos(0.0, 0.0, -1.95) * bd.Cylinder(
        radius=r_tunnel,
        height=0.75,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    tun_floor_cone = bd.Pos(0.0, 0.0, -1.95 - (r_tunnel - r_bore)) * bd.Cone(
        bottom_radius=r_bore,
        top_radius=r_tunnel,
        height=r_tunnel - r_bore,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    tun_entry_ring = (tun_entry_ceil + tun_mid_cyl + tun_floor_cone).solid()
    tun_lock_ring = (tun_lock_ceil + tun_mid_cyl + tun_floor_cone).solid()

    bayonet_cutters = []
    for k in range(3):
        c_deg = k * 120.0
        kw_wedge = _make_sector_wedge(14.0, -3.5, 0.5, c_deg - 21.0, c_deg + 21.0, n_arc=24)
        bayonet_cutters.append((kw_ring_full & kw_wedge).solid())
        entry_wedge = _make_sector_wedge(14.0, -3.5, 0.0, c_deg - 28.0, c_deg + 21.0, n_arc=24)
        bayonet_cutters.append((tun_entry_ring & entry_wedge).solid())
        lock_wedge = _make_sector_wedge(14.0, -3.5, 0.0, c_deg - 64.0, c_deg - 24.0, n_arc=24)
        bayonet_cutters.append((tun_lock_ring & lock_wedge).solid())

    # 4. Wide Ø 18.70 mm (R = 9.35 mm) Y-Shape LED Chamber (z = -3.65..0.00 mm)
    inner_core_b = bd.Pos(0.0, 0.0, -3.65) * bd.Cylinder(
        radius=r_y_led,
        height=3.75,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    lantern_dome_b = make_triangulated_antiprism_solid(
        [
            (-10.65, 2.25,    7.5),
            (-10.20, 4.60,    0.0),
            (-9.00,  6.75,    7.5),
            (-7.20,  8.15,    0.0),
            (-5.70,  8.90,    7.5),
            (-3.60,  r_y_led, 0.0),
        ],
        n_sides=24,
    )
    mark_b = bd.Pos(0.0, 0.0, -10.65) * make_engraved_label_solid(
        "B", char_h=2.5, depth=0.45
    )

    hemi_b_raw = (
        lower_dome
        - fem_bore_base
        - inner_core_b
        - lantern_dome_b
        - mark_b
    )
    for bc in bayonet_cutters:
        hemi_b_raw = hemi_b_raw - bc
    hemi_b = hemi_b_raw.solid().moved(bd.Location((0.0, 0.0, 0.0), (180.0, 0.0, 0.0)))
    return assign_toolhead(hemi_b, label, 4)


def build_assembled_apple_marble(
    label: str = "assembled_apple_marble",
) -> tuple[bd.Solid, bd.Solid, bd.Solid]:
    """Reconstruct the complete assembled 25.00 x 25.00 x 25.00 mm Rolling Apple Marble
    from Apple_Hemisphere_A and Apple_Hemisphere_B in 3D assembly coordinates (center at Z = 12.50 mm),
    with Apple_Hemisphere_A rotated -45.0° clockwise into its locked bayonet position!
    Returns (assembled_solid, hemi_a_placed, hemi_b_placed).
    """
    r_half = BALL_DIAMETER / 2.0  # 12.50 mm
    lip_h = 2.65
    hemi_a_print = build_apple_hemisphere_a()
    hemi_b_print = build_apple_hemisphere_b()

    # Place B at bottom (Z = 0.00..12.50 mm) and A on top rotated -45° into the locked bayonet tunnel
    hemi_b_placed = hemi_b_print.moved(bd.Location((0.0, 0.0, r_half), (180.0, 0.0, 0.0)))
    hemi_a_placed = hemi_a_print.moved(bd.Location((0.0, 0.0, r_half - lip_h), (0.0, 0.0, -45.0)))

    assembled_solid = (hemi_a_placed + hemi_b_placed).solid()
    return assign_toolhead(assembled_solid, label, 4), hemi_a_placed, hemi_b_placed


def build_apple_captive_pause_marble(label: str = "Apple_Captive_Pause_Marble") -> bd.Solid:
    """Build the One-Piece 25.00 x 25.00 x 25.00 mm Rolling 'Apple' Marble
    with an internal Ø 13.10 mm void centered at Z = 12.50 mm and a built-in breakaway 0.20 mm
    sacrificial foot collar at Z = 0.00 mm for bed stability.
    """
    r = BALL_DIAMETER / 2.0  # 12.50 mm
    r_core = STEEL_BALL_CAVITY_DIA / 2.0  # 6.55 mm (Ø 13.10 mm)
    sph_z0 = _make_exact_25mm_apple_sphere_centered().moved(bd.Location((0.0, 0.0, r)))

    # Built-in 0.20 mm breakaway sacrificial foot collar at Z = 0.00..0.20 mm for bed stability
    foot_collar = bd.Cylinder(
        radius=7.50,
        height=0.20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    # Internal Ø 13.10 mm cylindrical bearing void from Z = 5.80 mm to Z = 19.00 mm (centered at Z = 12.40..12.50 mm)
    bearing_void = bd.Pos(0.0, 0.0, 5.80) * bd.Cylinder(
        radius=r_core,
        height=13.20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    marble = (sph_z0 + foot_collar - bearing_void).solid()
    return assign_toolhead(marble, label, 4)


def build_rolling_apple_marble(label: str = "apple_marble_01") -> bd.Solid:
    """Return a weighted 25.00 x 25.00 x 25.00 mm Rolling 'Apple' Marble with Ø 13.10 mm steel bearing core."""
    return build_apple_captive_pause_marble(label)


def build_all_apple_hemispheres(count: int = 6) -> dict[str, bd.Solid]:
    """Build all 12 flat-bottomed split hemispheres (6x Apple_Hemisphere_A + 6x Apple_Hemisphere_B)
    for support-free printing at Z = 0.00 mm on Plate_5_Topper_Marbles_And_Planets.
    """
    base_a = build_apple_hemisphere_a("Apple_Hemisphere_A")
    base_b = build_apple_hemisphere_b("Apple_Hemisphere_B")
    hemis: dict[str, bd.Solid] = {}
    for i in range(1, count + 1):
        name_a = f"apple_hemisphere_a_{i:02d}"
        copy_a = bd.Solid(base_a.wrapped)
        hemis[name_a] = assign_toolhead(copy_a, name_a, 4)
    for i in range(1, count + 1):
        name_b = f"apple_hemisphere_b_{i:02d}"
        copy_b = bd.Solid(base_b.wrapped)
        hemis[name_b] = assign_toolhead(copy_b, name_b, 4)
    return hemis


def build_all_marbles(count: int = 6) -> dict[str, bd.Solid]:
    """Build 6x assembled Ø 25.00 mm Weighted Rolling Apple Marbles."""
    assembled_base, _, _ = build_assembled_apple_marble("apple_marble_01")
    marbles: dict[str, bd.Solid] = {}
    for i in range(1, count + 1):
        name = f"apple_marble_{i:02d}"
        m_copy = bd.Solid(assembled_base.wrapped)
        marbles[name] = assign_toolhead(m_copy, name, 4)
    return marbles


def build_magic_led_wand() -> bd.Solid:
    """Build the 3-Color Star-Tipped Magic Wand (`Magic_LED_Wand`, ~107 x 26 x 7.0 mm) resting flat
    on Z = 0.00 mm for support-free printing on the Snapmaker U1:
      - Woody Wand Handle (`wand_brown_shaft` — Toolhead 1 Dark Wood Brown #4A2F1D)
      - 6-Pointed Star Head & Pommel (`wand_gold_star` — Toolhead 3 Silk Gold #D4AF37)
      - Raised Star Bezel Ring (`wand_crimson_bezel` — Toolhead 4 Glossy Crimson Red #C41E3A)
      - Press-fit Ø 8.30 x 2.20 mm socket at (42.0, 0.0, Z = 4.80..7.00 mm) for the Bambu Lab
        Ø 8.0 x 2.0 mm Magnetic Control Switch trigger magnet + Ø 3.2 mm push-out hole.
    """
    # 1. Woody Handle Shaft (X = -48.0 .. +33.0 mm, flat bottom at Z = 0.0 mm)
    shaft_body = bd.Pos(-7.5, 0.0, 0.0) * bd.Box(
        81.0,
        7.6,
        5.2,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    shaft_ridge = bd.Pos(-7.5, 0.0, 5.2) * bd.Box(
        79.0,
        5.2,
        0.8,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    grip_ring_1 = bd.Pos(-28.0, 0.0, 0.0) * bd.Box(
        4.0, 9.6, 5.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    grip_ring_2 = bd.Pos(-12.0, 0.0, 0.0) * bd.Box(
        4.0, 9.2, 5.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    raw_shaft = (shaft_body + shaft_ridge + grip_ring_1 + grip_ring_2).solid()

    # 2. 6-Pointed Golden Star Head at X = +42.0 mm + Golden Pommel at X = -48.0 mm
    tri_a = bd.Pos(42.0, 0.0, 0.0) * bd.extrude(
        bd.RegularPolygon(radius=13.5, side_count=3), amount=6.4
    )
    tri_b = (
        bd.Pos(42.0, 0.0, 0.0)
        * bd.Rot(0.0, 0.0, 60.0)
        * bd.extrude(bd.RegularPolygon(radius=13.5, side_count=3), amount=6.4)
    )
    pommel_gold = bd.Pos(-48.0, 0.0, 0.0) * bd.Cylinder(
        radius=5.6, height=6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    raw_star_gold = tri_a + tri_b + pommel_gold

    # 3. Crimson Star Gem Bezel Ring around the magnet pocket at (42.0, 0.0, Z = 5.0..7.0 mm)
    bezel_outer = bd.Pos(42.0, 0.0, 5.0) * bd.extrude(
        bd.RegularPolygon(radius=6.8, side_count=12), amount=2.0
    )
    bezel_inner = bd.Pos(42.0, 0.0, 4.5) * bd.Cylinder(
        radius=4.15, height=3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    raw_bezel_crimson = (bezel_outer - bezel_inner).solid()

    # 4. Cut Ø 8.30 x 2.20 mm magnet press-fit socket (Z = 4.80..7.00 mm) + Ø 3.2 mm push-out hole
    mag_pocket = bd.Pos(42.0, 0.0, 4.80) * bd.Cylinder(
        radius=8.30 / 2.0,  # 4.15 mm (0.15 mm radial clearance for Ø 8.00 mm magnet)
        height=2.50,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    push_hole = bd.Pos(42.0, 0.0, -0.1) * bd.Cylinder(
        radius=1.60,
        height=5.20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    bezel_part = (raw_bezel_crimson - mag_pocket - push_hole).solid()
    star_shapes = (raw_star_gold - bezel_part - mag_pocket - push_hole).solids()
    shaft_part = (raw_shaft - raw_star_gold - bezel_part - mag_pocket - push_hole).solid()

    assign_toolhead(shaft_part, "wand_brown_shaft", 1)
    shaft_part.color = bd.Color("#4A2F1D")
    shaft_part.label = "wand_brown_shaft"

    star_subparts: list[bd.Solid] = []
    for idx, s_gold in enumerate(star_shapes):
        lbl = "wand_gold_star" if idx == 0 else f"wand_gold_pommel_{idx}"
        assign_toolhead(s_gold, lbl, 3)
        s_gold.color = bd.Color("#D4AF37")
        s_gold.label = lbl
        star_subparts.append(s_gold)

    assign_toolhead(bezel_part, "wand_crimson_bezel", 4)
    bezel_part.color = bd.Color("#C41E3A")
    bezel_part.label = "wand_crimson_bezel"

    combined = (
        (raw_shaft + raw_star_gold + raw_bezel_crimson) - mag_pocket - push_hole
    ).solid()
    assign_toolhead(combined, "Magic_LED_Wand", 3)
    combined.colored_subparts = [*star_subparts, shaft_part, bezel_part]  # type: ignore[attr-defined]
    return combined


def build_all_topper_planet_parts() -> dict[str, bd.Solid]:
    """Return dictionary of the Red Apple Topper, all 8 Multi-Color Solar System Planetary
    Ornaments (with unified Ø 8.00 mm Bambu Magnetic LED Light + balcony peg bore), the
    Star-Tipped Magic LED Wand, and the Apple Marble variants.
    """
    return {
        "golden_apple_topper": build_golden_apple_topper(),
        "planet_mercury": build_planet_mercury(),
        "planet_venus": build_planet_venus(),
        "planet_earth": build_planet_earth(),
        "planet_mars": build_planet_mars(),
        "planet_jupiter": build_planet_jupiter(),
        "planet_saturn": build_planet_saturn(),
        "planet_uranus": build_planet_uranus(),
        "planet_neptune": build_planet_neptune(),
        "Magic_LED_Wand": build_magic_led_wand(),
        "Apple_Hemisphere_A": build_apple_hemisphere_a("Apple_Hemisphere_A"),
        "Apple_Hemisphere_B": build_apple_hemisphere_b("Apple_Hemisphere_B"),
        "Apple_Captive_Pause_Marble": build_apple_captive_pause_marble("Apple_Captive_Pause_Marble"),
    }


if __name__ == "__main__":
    for name, part in build_all_topper_planet_parts().items():
        bb = part.bounding_box()
        print(
            f"{name}: valid={part.is_valid}, manifold={part.is_manifold}, "
            f"bbox=({bb.size.X:.2f}, {bb.size.Y:.2f}, {bb.size.Z:.2f})"
        )
