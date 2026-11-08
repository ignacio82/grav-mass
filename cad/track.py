"""Conical Helix Track Sweep, 120° Segments & Scarf/Lap Joints (cad/track.py).

Generates the segmented conical helix raceway for the 25.0 mm rolling spheres:
  - Continuous conical helix geometry tapering from R = 145.0 mm (bottom)
    to R = 60.0 mm (top) over 4.5 turns at 79.0 mm vertical pitch.
  - Custom 2D swept cross-section:
      * Parabolic/circular trough floor (R = 16.0 mm) with flat shoulders
      * Inner retaining wall (12.0 mm height)
      * Outer retaining wall (18.0 mm height) with 1.0 mm inward-angled lip
  - 120° arc segments (3 per full rotation):
      * 15° angled scarf/lap joint matching the downhill roll direction
      * Twin Ø 2.0 mm alignment dowel holes on mating faces
      * Underside female mounting sockets for bracket twin alignment pegs
      * Integrated Outer-Rim Mechanical Planet Pedestal Balconies (Ø 4.8 mm snap peg,
        zero magnets, zero mid-print pauses) on 8 segments
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    AUGER_BALL_ORBIT_R,
    BRACKET_PEG_DIA,
    BRACKET_PEG_HEIGHT,
    BRACKET_PEG_SPACING_U,
    DOVETAIL_ANGULAR_STEP_DEG,
    FIT_TOLERANCE,
    HELIX_BOT_R,
    HELIX_PITCH,
    HELIX_TOP_R,
    HELIX_TOTAL_DEG,
    HELIX_TOTAL_HEIGHT,
    LED_CHANNEL_D,
    LED_CHANNEL_THROAT_W,
    LED_CHANNEL_W,
    RETURN_CHUTE_END_DEG,
    TIMING_GATE_ANGLES_DEG,
    TOP_FEEDER_START_DEG,
    TRACK_BASE_Y,
    TRACK_DOWEL_DEPTH,
    TRACK_DOWEL_DIA,
    TRACK_DOWEL_OFFSET_U,
    TRACK_DOWEL_OFFSET_V,
    TRACK_HALF_INNER_W,
    TRACK_INNER_WALL_H,
    TRACK_INNER_WALL_THICK,
    TRACK_OUTER_LIP_INSET,
    TRACK_OUTER_WALL_H,
    TRACK_OUTER_WALL_THICK,
    TRACK_SCARF_ANGLE_DEG,
    TRACK_SEGMENT_ARC_DEG,
    TRACK_SHOULDER_INNER_X,
    TRACK_TROUGH_R,
    assign_toolhead,
    closed_loop_section_plane,
    closed_loop_track_point,
    helix_arc_length_from_top,
    helix_point,
    helix_radius,
    helix_section_plane,
    helix_z,
    make_engraved_label_solid,
    theta_for_helix_arc_length,
)

# Mechanical planet pedestal mounting peg parameters (mates with Ø 8.00 x 10.00 mm bottom-load
# LED + peg bore in planets: peg occupies Z = 0..3.50 mm, holding the Ø 7.5 x 6.0 mm Bambu Magnetic
# LED Light captive at Z = 3.60..9.60 mm)
PLANET_PEG_DIA = 7.60
PLANET_PEG_HEIGHT = 3.50
TRACK_PLANET_SEGMENT_INDICES = (0, 2, 4, 5, 7, 9, 11, 13)
# Planet order 1..8 from Top (Mercury = 1 near Apple Sun) to Bottom (Neptune = 8)
SEGMENT_INDEX_TO_PLANET_NUM = {
    13: 1,  # Mercury (1590°)
    11: 2,  # Venus   (1380°)
    9: 3,   # Earth   (1140°)
    7: 4,   # Mars    (900°)
    5: 5,   # Jupiter (660°)
    4: 6,   # Saturn  (540°)
    2: 7,   # Uranus  (300°)
    0: 8,   # Neptune (60°)
}


def make_conical_helix_reference_wire() -> bd.Wire:
    """Create the continuous 4.5-turn conical Helix wire for reference/inspection."""
    cone_angle_deg = math.degrees(
        math.atan((HELIX_TOP_R - HELIX_BOT_R) / HELIX_TOTAL_HEIGHT)
    )
    helix_edge = bd.Helix(
        pitch=HELIX_PITCH,
        height=HELIX_TOTAL_HEIGHT,
        radius=HELIX_BOT_R,
        cone_angle=cone_angle_deg,
    )
    return bd.Wire([helix_edge])


def make_track_profile_wire() -> bd.Wire:
    """Construct the 2D cross-section wire of the raceway in local (u, v) coordinates.

    u (X): radial offset from helix centerline (- is inner/trunk side, + is outer side)
    v (Y): vertical offset from trough flat shoulder datum (0.0)
    """
    u_in_outer = -(TRACK_HALF_INNER_W + TRACK_INNER_WALL_THICK)  # -20.0 mm
    u_in_inner = -TRACK_HALF_INNER_W                             # -17.0 mm
    u_sh_in = -TRACK_SHOULDER_INNER_X                            # -13.0 mm
    u_sh_out = TRACK_SHOULDER_INNER_X                            # +13.0 mm
    u_out_inner = TRACK_HALF_INNER_W                             # +17.0 mm
    u_out_lip = TRACK_HALF_INNER_W - TRACK_OUTER_LIP_INSET       # +16.0 mm (1.0 mm inward lip)
    u_out_outer = TRACK_HALF_INNER_W + TRACK_OUTER_WALL_THICK    # +20.6 mm

    v_bot = TRACK_BASE_Y                                         # -12.0 mm
    v_led_roof = v_bot + LED_CHANNEL_D                           # -8.4 mm
    u_led_half = LED_CHANNEL_W / 2.0                             # 4.0 mm (internal chamber)
    u_throat_half = LED_CHANNEL_THROAT_W / 2.0                   # 2.3 mm (snap-in throat)
    v_lip_top = v_bot + 0.70                                     # -11.3 mm
    v_chamfer_top = v_lip_top + (u_led_half - u_throat_half)     # -9.6 mm (45° self-supporting flare)

    # Trough floor sagitta for R = 16.0 mm spanning [-13.0, +13.0]
    sagitta = TRACK_TROUGH_R - math.sqrt(TRACK_TROUGH_R**2 - TRACK_SHOULDER_INNER_X**2)

    pts_left = [
        (u_in_outer, -9.0),
        (u_in_outer, TRACK_INNER_WALL_H),
        (u_in_inner, TRACK_INNER_WALL_H),
        (u_in_inner, 0.0),
        (u_sh_in, 0.0),
    ]
    pts_right = [
        (u_sh_out, 0.0),
        (u_out_inner, 0.0),
        (u_out_inner, TRACK_OUTER_WALL_H - 2.0),
        (u_out_lip, TRACK_OUTER_WALL_H - 1.0),
        (u_out_lip, TRACK_OUTER_WALL_H),
        (u_out_outer, TRACK_OUTER_WALL_H),
        (u_out_outer, -9.0),
        (14.5, v_bot),
        (u_throat_half, v_bot),
        (u_throat_half, v_lip_top),
        (u_led_half, v_chamfer_top),
        (u_led_half, v_led_roof),
        (-u_led_half, v_led_roof),
        (-u_led_half, v_chamfer_top),
        (-u_throat_half, v_lip_top),
        (-u_throat_half, v_bot),
        (-14.5, v_bot),
        (u_in_outer, -9.0),
    ]

    edges = [
        bd.Edge.make_line(pts_left[i], pts_left[i + 1])
        for i in range(len(pts_left) - 1)
    ]
    edges.append(
        bd.Edge.make_three_point_arc((u_sh_in, 0.0), (0.0, -sagitta), (u_sh_out, 0.0))
    )
    edges.extend(
        [
            bd.Edge.make_line(pts_right[i], pts_right[i + 1])
            for i in range(len(pts_right) - 1)
        ]
    )
    return bd.Wire(edges)


_PROFILE_WIRE_CACHE: bd.Wire | None = None
_ENDCAP_WIRE_CACHE: bd.Wire | None = None


def _get_profile_wire() -> bd.Wire:
    global _PROFILE_WIRE_CACHE
    if _PROFILE_WIRE_CACHE is None:
        _PROFILE_WIRE_CACHE = make_track_profile_wire()
    return _PROFILE_WIRE_CACHE


def make_track_endcap_wire() -> bd.Wire:
    """Construct a solid full-height cross-section wire matching the outer boundary of
    `make_track_profile_wire()` (`u in [-20.0, +20.6]`, `v in [-12.0, +18.0]`) to form
    enclosed bumper end-caps at the top and bottom trunk transitions.
    """
    u_in_outer = -(TRACK_HALF_INNER_W + TRACK_INNER_WALL_THICK)  # -20.0 mm
    u_out_outer = TRACK_HALF_INNER_W + TRACK_OUTER_WALL_THICK    # +20.6 mm
    v_bot = TRACK_BASE_Y                                         # -12.0 mm
    v_led_roof = v_bot + LED_CHANNEL_D                           # -8.4 mm
    u_led_half = LED_CHANNEL_W / 2.0                             # 4.0 mm
    u_throat_half = LED_CHANNEL_THROAT_W / 2.0                   # 2.3 mm
    v_lip_top = v_bot + 0.70                                     # -11.3 mm
    v_chamfer_top = v_lip_top + (u_led_half - u_throat_half)     # -9.6 mm

    pts = [
        (u_in_outer, -9.0),
        (u_in_outer, TRACK_OUTER_WALL_H),
        (u_out_outer, TRACK_OUTER_WALL_H),
        (u_out_outer, -9.0),
        (14.5, v_bot),
        (u_throat_half, v_bot),
        (u_throat_half, v_lip_top),
        (u_led_half, v_chamfer_top),
        (u_led_half, v_led_roof),
        (-u_led_half, v_led_roof),
        (-u_led_half, v_chamfer_top),
        (-u_throat_half, v_lip_top),
        (-u_throat_half, v_bot),
        (-14.5, v_bot),
        (u_in_outer, -9.0),
    ]
    return bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])


def _get_endcap_wire() -> bd.Wire:
    global _ENDCAP_WIRE_CACHE
    if _ENDCAP_WIRE_CACHE is None:
        _ENDCAP_WIRE_CACHE = make_track_endcap_wire()
    return _ENDCAP_WIRE_CACHE


def make_track_male_tenon_local() -> bd.Shape:
    """Create twin under-shoulder male snap-lock tenon pegs + sidewall anti-torsion tongues
    on the uphill (`theta_end_deg`) scarf face, protruding into `w < 0` (`+t_dir`).
    """
    parts: bd.Shape | None = None
    r_peg = 1.90          # Ø 3.80 mm sturdy under-shoulder tenon peg
    r_snap = 2.04         # Ø 4.08 mm annular snap-lock retention bead
    l_protrude = 5.0      # 5.0 mm protrusion into next segment (w = 0..-5.0 mm)
    l_embed = 2.0         # 2.0 mm root embed inside current segment (w = 0..+2.0 mm)
    chamfer = 0.65
    for u_pos in (-TRACK_DOWEL_OFFSET_U, TRACK_DOWEL_OFFSET_U):
        shaft_h = (l_protrude - chamfer) + l_embed
        shaft_zc = 0.5 * (l_embed - (l_protrude - chamfer))
        shaft = bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, shaft_zc) * bd.Cylinder(
            radius=r_peg,
            height=shaft_h,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        tip = (
            bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, -(l_protrude - chamfer))
            * bd.Rot(180.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_peg,
                top_radius=r_peg - chamfer,
                height=chamfer,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        dr = r_snap - r_peg
        snap_ring = (
            bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, -2.2)
            * bd.Rot(180.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_peg,
                top_radius=r_snap,
                height=dr,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            + bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, -2.2 - dr)
            * bd.Rot(180.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=r_snap,
                height=0.6,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            + bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, -2.2 - dr - 0.6)
            * bd.Rot(180.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_snap,
                top_radius=r_peg,
                height=dr,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg = shaft + tip + snap_ring
        parts = peg if parts is None else (parts + peg)

    # Inner & Outer Sidewall Anti-Torsion Tongue Tabs (protrude 2.8 mm into w < 0, embed 1.5 mm into w > 0)
    in_tab = bd.Pos(-18.5, 4.5, -0.65) * bd.Box(
        1.15, 4.60, 4.30, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    out_tab = bd.Pos(18.8, 6.5, -0.65) * bd.Box(
        1.35, 5.60, 4.30, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    assert parts is not None
    return parts + in_tab + out_tab


def make_track_female_socket_cutter_local() -> bd.Shape:
    """Create matching female snap-lock sockets + sidewall anti-torsion slots
    on the downhill (`theta_start_deg`) scarf face, cutting into `w < 0`.
    """
    cutters: bd.Shape | None = None
    r_sock = 2.15         # Ø 4.30 mm socket (0.25 mm radial clearance around Ø 3.80 mm peg)
    r_detent = 2.30       # Ø 4.60 mm snap-detent groove (0.26 mm radial clearance around Ø 4.08 mm bead)
    l_depth = 5.6         # 5.6 mm socket depth (0.60 mm axial clearance past 5.0 mm peg)
    l_outside = 1.2       # Extend +1.2 mm into w > 0 for clean boolean entry
    for u_pos in (-TRACK_DOWEL_OFFSET_U, TRACK_DOWEL_OFFSET_U):
        bore_h = l_depth + l_outside
        bore_zc = 0.5 * (l_outside - l_depth)
        bore = bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, bore_zc) * bd.Cylinder(
            radius=r_sock,
            height=bore_h,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        detent = bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, -2.65) * bd.Cylinder(
            radius=r_detent,
            height=1.5,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        entry_flare = (
            bd.Pos(u_pos, TRACK_DOWEL_OFFSET_V, 0.2)
            * bd.Rot(180.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_sock + 0.35,
                top_radius=r_sock,
                height=0.8,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        sock = bore + detent + entry_flare
        cutters = sock if cutters is None else (cutters + sock)

    # Matching Inner & Outer Sidewall Anti-Torsion Slots (w from +1.2 to -3.4 mm)
    in_slot = bd.Pos(-18.5, 4.5, -1.1) * bd.Box(
        1.75, 5.30, 4.60, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    out_slot = bd.Pos(18.8, 6.5, -1.1) * bd.Box(
        1.95, 6.30, 4.60, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    assert cutters is not None
    return cutters + in_slot + out_slot


def build_track_joint_clip(orient_for_print: bool = True) -> bd.Solid:
    """Build a snap-on underside U-cradle splice clamp (`Track_Joint_Clip`) that bridges across
    the seam between any two track segments (retrofittable onto already-printed segments
    AND compatible with the new interlocking segments).

    Features:
      - Wraps around the bottom pads (v = -12.0 mm), 45° lower bevels, inner guard wall
        (u = -20.0 mm + top snap-hook over v = +12.0 mm), and outer guard wall (u = +20.6 mm).
      - Central 10.4 x 1.8 mm LED wire pass-through arch (u in [-5.2, +5.2 mm]) so the
        BTF-LIGHTING B0CCS11V7H WS2812B Pebble Light Wire passes straight through uninterrupted.
      - Twin Ø 4.40 mm vertical cantilever bracket peg sockets at u = ±10.6 mm on the underside.
    """
    clip_len = 16.0
    cu = 0.70
    cv = 0.85
    pts = [
        (-16.2, 10.4),
        (-16.2, 12.0 + cv),
        (-20.0 - cu, 12.0 + cv),
        (-20.0 - cu, -9.0 - cv * 0.5),
        (-14.5 - cu * 0.6, -12.0 - cv),
        (-5.2, -12.0 - cv),
        (-5.2, -13.8),
        (5.2, -13.8),
        (5.2, -12.0 - cv),
        (14.5 + cu * 0.6, -12.0 - cv),
        (20.6 + cu, -9.0 - cv * 0.5),
        (20.6 + cu, 4.2),
        (23.6, 4.2),
        (23.6, -9.8),
        (15.2, -16.8),
        (-15.2, -16.8),
        (-23.0, -9.8),
        (-23.0, 14.8),
        (-14.8, 14.8),
        (-14.8, 10.4),
        (-16.2, 10.4),
    ]
    wire = bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])
    face = bd.Plane.XY * bd.Face(wire)
    clip = bd.extrude(face, amount=clip_len / 2.0, both=True)

    # Cut twin Ø 4.40 mm underside bracket peg holes at u = ±10.6 mm so the clip can also seat on a bracket
    sock_r = (BRACKET_PEG_DIA / 2.0) + FIT_TOLERANCE
    for u_peg in (-BRACKET_PEG_SPACING_U, BRACKET_PEG_SPACING_U):
        peg_hole = (
            bd.Pos(u_peg, -14.8, 0.0)
            * bd.Rot(90.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=sock_r,
                height=5.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
            )
        )
        clip = clip - peg_hole

    clip_solid = max(clip.solids(), key=lambda s: s.volume)
    if orient_for_print:
        bb = clip_solid.bounding_box()
        clip_solid = clip_solid.moved(
            bd.Location((-(bb.min.X + bb.max.X) / 2.0, -(bb.min.Y + bb.max.Y) / 2.0, -bb.min.Z))
        )
    return assign_toolhead(clip_solid, "Track_Joint_Clip", 2)


def build_track_segment(
    theta_start_deg: float,
    theta_end_deg: float,
    orient_for_print: bool = True,
    include_planet_pedestal: bool = True,
    bottom_return_ramp: bool = False,
    top_feeder_ramp: bool = False,
    seg_number: int | None = None,
) -> bd.Solid:
    """Build a single conical helix track segment between theta_start_deg and theta_end_deg.

    Includes:
      - 15° angled scarf/lap joint on mating end faces matching roll direction
      - Twin Ø 2.0 mm alignment dowel holes on mating faces
      - Underside female bracket mounting bosses/sockets at 60° stations
      - Optional integrated Outer-Rim Mechanical Planet Pedestal Balcony (u = +30.0 mm,
        v_top = +18.0 mm) with an upward Ø 4.80 x 3.50 mm snap/press-fit mounting peg
      - Optional integrated Bottom Return Collector Chute (theta = -80°..0° into trunk_base)
      - Optional integrated Top Feeder Chute (theta = 1620°..1700° from trunk_top)
    """
    base_wire = _get_profile_wire()
    n_sections = 36 if (bottom_return_ramp or top_feeder_ramp) else 10

    # Sweep custom 2D cross-section along parametric conical helix spline with 15-deg scarf ends
    a_start = (RETURN_CHUTE_END_DEG - 18.0) if bottom_return_ramp else theta_start_deg
    a_end = (TOP_FEEDER_START_DEG + 18.0) if top_feeder_ramp else theta_end_deg
    angles = [
        a_start + (a_end - a_start) * (i / n_sections)
        for i in range(n_sections + 1)
    ]

    section_faces = [
        bd.Face(
            closed_loop_section_plane(a, scarf_tilt_deg=TRACK_SCARF_ANGLE_DEG).from_local_coords(
                base_wire
            )
        )
        for a in angles
    ]
    if bottom_return_ramp or top_feeder_ramp or (theta_end_deg - theta_start_deg) < 50.0:
        seg = bd.loft(section_faces)
    else:
        try:
            path_pts = [closed_loop_track_point(a) for a in angles]
            path_wire = bd.Wire([bd.Edge.make_spline(path_pts)])
            seg = bd.sweep(section_faces, path=path_wire, multisection=True)
        except Exception:
            seg = bd.loft(section_faces)

    # 0b. For bottom_return_ramp (track_seg_01) and top_feeder_ramp (track_seg_14_top_entry):
    #     - Add a full-height Solid End-Cap Bumper Wall strictly on the dead-end side of the
    #       -Y trunk port (X <= -13.5 mm at bottom, X >= +13.5 mm at top) bridging from the
    #       outer track wall to the Ø 68.0 mm trunk cylinder (R = 34.25 mm), with ZERO walls
    #       protruding into the downhill/incoming track trough!
    #     - Trim the inner face cleanly against the Ø 68.0 mm trunk outer cylinder (R = 34.25 mm).
    #     - Carve the sloped radial U-shaped ball channel connecting the track trough at (0, -42)
    #       directly into/out of the vertical auger flute at (0, -17.5) and sweep a Ø 27.6 mm
    #       clearance cylinder along the ramp so the rolling marble path is 100% unobstructed.
    if bottom_return_ramp:
        bot_endcap_wall = bd.Pos(-16.5, -46.5, 36.5) * bd.Box(
            6.0,
            29.0,
            30.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        pad_bot = bd.Pos(0.0, -40.0, 36.5) * bd.Box(
            16.0,
            14.0,
            4.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        seg = seg + bot_endcap_wall + pad_bot
        seg = seg - (
            bd.Pos(0.0, 0.0, 20.0)
            * bd.Cylinder(
                radius=34.25,
                height=95.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        p_out_bot = bd.Vector(0.0, -45.5, 56.3)
        p_in_bot = bd.Vector(0.0, -AUGER_BALL_ORBIT_R, 52.0)
        vec_bot = p_in_bot - p_out_bot
        pl_chute_bot = bd.Plane(origin=p_out_bot, z_dir=vec_bot.normalized())
        r_chute_bot = 13.8
        u_chute_bot = (
            (
                pl_chute_bot
                * bd.Cylinder(
                    radius=r_chute_bot,
                    height=vec_bot.length,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            + (
                pl_chute_bot
                * bd.Pos(0.0, -12.0, 0.0)
                * bd.Box(
                    2.0 * r_chute_bot,
                    24.0,
                    vec_bot.length,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            + (bd.Pos(p_in_bot.X, p_in_bot.Y, p_in_bot.Z) * bd.Sphere(radius=r_chute_bot))
        )
        keep_s01_cut = bd.Pos(0.0, -31.0, 35.0) * bd.Box(
            30.0,
            27.5,
            38.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        seg = seg - (u_chute_bot & keep_s01_cut)
        # Underside recessed Pebble-Wire Starter Feed Pocket (10.0 x 16.0 x 3.7 mm) at theta = -70°
        # Opens the snap-in throat at the bottom entry so the BTF-LIGHTING WS2812B Pebble LED Wire (B0CCS11V7H)
        # feeds smoothly into the 8.0 x 3.6 mm (4.6 mm throat) dovetail channel.
        pl_cob_pcb = closed_loop_section_plane(-70.0, scarf_tilt_deg=0.0)
        cob_pcb_pocket = bd.Pos(0.0, TRACK_BASE_Y + 1.80, 0.0) * bd.Box(
            10.0,
            3.7,
            16.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        seg = seg - pl_cob_pcb.from_local_coords(cob_pcb_pocket)

    if top_feeder_ramp:
        top_endcap_wall = bd.Pos(16.5, -47.0, 413.0) * bd.Box(
            6.0,
            29.0,
            30.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        seg = seg + top_endcap_wall
        seg = seg - (
            bd.Pos(0.0, 0.0, 380.0)
            * bd.Cylinder(
                radius=34.25,
                height=95.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        inner_wall_cyl_top = bd.Pos(0.0, 0.0, 380.0) * bd.Cylinder(
            radius=38.8,
            height=95.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        chute_slot = (
            bd.Pos(0.0, -34.0, 419.0)
            * bd.Rot(9.1, 0.0, 0.0)
            * bd.Box(
                28.0,
                28.0,
                40.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        seg = seg - (inner_wall_cyl_top & chute_slot)

    # 1. Integrated Male-to-Female Snap-Lock Track Joint + Hidden Engraved Segment Number ("1".."14"):
    #    - On the uphill face (`theta_end_deg`, when `not top_feeder_ramp`):
    #      Protrudes Twin Ø 3.80 x 5.0 mm Under-Shoulder Male Snap-Lock Tenon Pegs (with Ø 4.08 mm
    #      annular snap-detent rings and 45° nose chamfers at u = ±14.2 mm, v = -4.2 mm) PLUS
    #      Inner & Outer Sidewall Anti-Torsion Tongue Tabs (u = -18.5 mm and u = +18.8 mm).
    #    - On the downhill face (`theta_start_deg`, when `not bottom_return_ramp`):
    #      Cuts Matching Ø 4.30 x 5.6 mm Female Snap-Lock Sockets (with entry flare and Ø 4.60 mm
    #      internal snap-detent groove) PLUS Matching Sidewall Anti-Torsion Female Slots, so
    #      Segment k+1 slides and clicks directly onto Segment k with zero external hardware!
    seg_idx_zero = max(0, min(13, int(round(theta_start_deg / TRACK_SEGMENT_ARC_DEG))))
    seg_num_val = seg_number if seg_number is not None else (seg_idx_zero + 1)
    num_cutter_local = make_engraved_label_solid(
        str(seg_num_val), char_h=2.6, depth=0.65
    ).locate(bd.Location((6.2, -5.2, 0.0)))

    if not bottom_return_ramp:
        pl_start = helix_section_plane(theta_start_deg, scarf_tilt_deg=TRACK_SCARF_ANGLE_DEG)
        seg = seg - pl_start.from_local_coords(make_track_female_socket_cutter_local())
        seg = seg - pl_start.from_local_coords(num_cutter_local)

    if not top_feeder_ramp:
        pl_end = helix_section_plane(theta_end_deg, scarf_tilt_deg=TRACK_SCARF_ANGLE_DEG)
        seg = seg + pl_end.from_local_coords(make_track_male_tenon_local())
        seg = seg - pl_end.from_local_coords(num_cutter_local)

    # 2. Cut twin female bracket mounting sockets on underside at ALL 60° stations in [theta_start_deg, theta_end_deg]
    #    (both odd-60° midpoint stations AND even-60° segment seam stations 120°, 240°, ..., 1560°,
    #    or at segment midpoint if span < 60° for compact plate-grid segments)
    k_min = max(1, int(math.ceil((theta_start_deg - 0.1) / DOVETAIL_ANGULAR_STEP_DEG)))
    k_max = min(26, int(math.floor((theta_end_deg + 0.1) / DOVETAIL_ANGULAR_STEP_DEG)))
    sock_r = (BRACKET_PEG_DIA / 2.0) + FIT_TOLERANCE  # 2.20 mm radius (0.20 mm radial clearance)
    sock_depth = BRACKET_PEG_HEIGHT + 0.5             # 5.0 mm depth from v_bot = -12.0 mm

    station_angles = [k * DOVETAIL_ANGULAR_STEP_DEG for k in range(k_min, k_max + 1)]
    if not station_angles:
        station_angles = [0.5 * (theta_start_deg + theta_end_deg)]

    for st_deg in station_angles:
        pl_st = helix_section_plane(st_deg, scarf_tilt_deg=0.0)
        for u_peg in (-BRACKET_PEG_SPACING_U, BRACKET_PEG_SPACING_U):
            # Vertical socket oriented along local Y (v) from v = -12.5 up to v = -7.0 mm
            # with an internal annular snap-detent groove (R = sock_r + 0.14 mm) to lock the bracket peg
            peg_hole = (
                bd.Pos(u_peg, TRACK_BASE_Y + sock_depth / 2.0 - 0.2, 0.0)
                * bd.Rot(90.0, 0.0, 0.0)
                * bd.Cylinder(
                    radius=sock_r,
                    height=sock_depth + 0.6,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
                )
            )
            detent_groove = (
                bd.Pos(u_peg, TRACK_BASE_Y + 2.4, 0.0)
                * bd.Rot(90.0, 0.0, 0.0)
                * bd.Cylinder(
                    radius=sock_r + 0.14,
                    height=1.1,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
                )
            )
            seg = seg - pl_st.from_local_coords(peg_hole + detent_groove)

    # 3. Integrated Outer Rim Mechanical Planet Pedestal Balcony (at u = +30.0 mm, v_top = +18.0 mm)
    #    Provides a dedicated horizontal Ø 14.4 mm circular landing dock (supported by a 45°
    #    print-in-place underside gusset) with an upward Ø 7.60 x 3.50 mm self-centering snap-click
    #    mounting peg (0.85 mm conical lead-in tip + Ø 8.12 mm tactile snap-retention bead)
    #    so every solar-system planet snaps on effortlessly with zero magnets and zero overlap.
    if include_planet_pedestal and (theta_end_deg - theta_start_deg) >= 50.0:
        mid_deg = 0.5 * (theta_start_deg + theta_end_deg)
        pl_mid = helix_section_plane(mid_deg, scarf_tilt_deg=0.0)
        pad_cyl = (
            bd.Pos(30.0, 15.0, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=7.2,
                height=3.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        bridge_box = bd.Pos(24.25, 16.5, 0.0) * bd.Box(11.5, 3.0, 11.6)
        w_gus_bot = bd.Wire.make_polygon(
            [
                (18.5, 0.5, -4.8),
                (20.5, 0.5, -4.8),
                (20.5, 0.5, 4.8),
                (18.5, 0.5, 4.8),
            ],
            close=True,
        )
        w_gus_top = bd.Wire.make_polygon(
            [
                (18.5, 15.0, -4.8),
                (35.2, 15.0, -4.8),
                (35.2, 15.0, 4.8),
                (18.5, 15.0, 4.8),
            ],
            close=True,
        )
        gusset = bd.Solid.make_loft([w_gus_bot, w_gus_top], ruled=True)
        r_peg = PLANET_PEG_DIA / 2.0  # 3.80 mm (Ø 7.60 mm)
        r_bead = r_peg + 0.26         # 4.06 mm (Ø 8.12 mm snap-click bead inside Ø 8.44 mm planet groove)
        peg_cyl = (
            bd.Pos(30.0, 18.0, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=r_peg,
                height=PLANET_PEG_HEIGHT - 0.85,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_bead_lower = (
            bd.Pos(30.0, 19.65, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_peg,
                top_radius=r_bead,
                height=0.30,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_bead_mid = (
            bd.Pos(30.0, 19.95, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=r_bead,
                height=0.20,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_bead_upper = (
            bd.Pos(30.0, 20.15, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_bead,
                top_radius=r_peg,
                height=0.30,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_tip = (
            bd.Pos(30.0, 18.0 + PLANET_PEG_HEIGHT - 0.85, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_peg,
                top_radius=r_peg - 0.85,
                height=0.85,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        pedestal_local = (
            pad_cyl
            + bridge_box
            + gusset
            + peg_cyl
            + peg_bead_lower
            + peg_bead_mid
            + peg_bead_upper
            + peg_tip
        ).solid()
        # Engrave planet number ("1".."8", Mercury=1 at top to Neptune=8 at bottom) on the
        # flat top of the balcony peg (100% hidden inside the planet's bottom bore once mounted!)
        p_num = SEGMENT_INDEX_TO_PLANET_NUM.get(seg_idx_zero, 1)
        peg_num_cutter = (
            bd.Pos(30.0, 18.0 + PLANET_PEG_HEIGHT, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * make_engraved_label_solid(str(p_num), char_h=3.2, depth=0.65)
        )
        pedestal_local = (pedestal_local - peg_num_cutter).solid()
        seg = seg + pl_mid.from_local_coords(pedestal_local)

    # 3b. Galileo-Newton Gravity Chronometer Markings (Timing Gates G0..G5, Acoustic Click
    #     Micro-Ribs, and 100 mm / 500 mm True 3D Arc-Length Graduation Ticks on Outer Rail)
    if (theta_end_deg - theta_start_deg) >= 50.0:
        mid_ped_deg = 0.5 * (theta_start_deg + theta_end_deg) if include_planet_pedestal else -999.0
        # Timing Gates G0..G5:
        for g_idx, g_deg in enumerate(TIMING_GATE_ANGLES_DEG):
            if (theta_start_deg + 4.0) <= g_deg <= (theta_end_deg - 4.0):
                pl_g = helix_section_plane(g_deg, scarf_tilt_deg=0.0)
                # Top-rim sighting notch across u = 16.0..20.6 mm at v = 18.0 mm
                gate_notch = bd.Pos(18.3, 18.0, 0.0) * bd.Box(
                    5.2, 2.2, 1.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
                )
                # Engraved Gate Label ("G0".."G5") on outer vertical track wall (u = 20.6 mm)
                gate_lbl = (
                    bd.Pos(20.6, 8.2, 0.0)
                    * bd.Rot(0.0, 90.0, 0.0)
                    * make_engraved_label_solid(f"G{g_idx}", char_h=4.6, depth=0.70)
                )
                # Sub-millimeter (0.35 mm) inward acoustic click micro-rib on inner face of outer wall
                # (u = 16.65..17.40 mm, v = 3.5..8.5 mm) for smartphone audio timing (Phyphox)
                click_rib = bd.Pos(17.05, 6.0, 0.0) * bd.Box(
                    0.80, 5.0, 1.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
                )
                seg = (seg + pl_g.from_local_coords(click_rib)) - pl_g.from_local_coords(
                    gate_notch + gate_lbl
                )

        # 100 mm (10 cm) True 3D Spiral Arc-Length Graduation Ticks measured from G0 (1605°):
        s_g0 = helix_arc_length_from_top(TIMING_GATE_ANGLES_DEG[0])
        for s_dm in range(1, 29):
            s_mm = s_dm * 100.0
            t_tick = theta_for_helix_arc_length(s_g0 + s_mm)
            if (theta_start_deg + 4.0) <= t_tick <= (theta_end_deg - 4.0):
                # Skip if overlapping a Timing Gate or Planet Pedestal balcony
                if any(abs(t_tick - gd) < 4.5 for gd in TIMING_GATE_ANGLES_DEG):
                    continue
                if abs(t_tick - mid_ped_deg) < 6.5:
                    continue
                pl_t = helix_section_plane(t_tick, scarf_tilt_deg=0.0)
                is_major_500 = (s_dm % 5) == 0
                tick_h = 5.6 if is_major_500 else 3.2
                tick_w = 1.3 if is_major_500 else 0.9
                tick_box = bd.Pos(19.6, 18.0 - 0.5 * tick_h + 0.3, 0.0) * bd.Box(
                    2.6,
                    tick_h,
                    tick_w,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
                )
                if is_major_500:
                    dm_lbl = (
                        bd.Pos(20.6, 8.0, 0.0)
                        * bd.Rot(0.0, 90.0, 0.0)
                        * make_engraved_label_solid(str(s_dm), char_h=3.8, depth=0.65)
                    )
                    seg = seg - pl_t.from_local_coords(tick_box + dm_lbl)
                else:
                    seg = seg - pl_t.from_local_coords(tick_box)

    seg_solid = max(seg.solids(), key=lambda s: s.volume)

    # 4. Option A Pitch-Level Horizontal Print Orientation:
    #    Tilt each segment by its helical chord pitch angle so BOTH the downhill end and the
    #    uphill end rest on the build plate (Z = 0.0), cutting the mid-span arch height by >70%
    #    (dropping segment Z height from 55.3 mm down to ~35.0 mm) and aligning the chord with
    #    the 45° build-plate diagonal.
    if orient_for_print:
        if bottom_return_ramp:
            # 3-point plane leveling for the 210° bottom return ramp + 120° arc so all 3 ends
            # (-90° return spout, 0° outer elbow, and 120° uphill joint) sit low to Z = 0
            # and the XY footprint stays compact at 230.8 x 230.1 mm (Z = 47.8 mm).
            seg_solid = (
                seg_solid.moved(bd.Location((0.0, 0.0, 0.0), (-7.0, 0.0, 0.0)))
                .moved(bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, 82.0)))
            )
        else:
            p0_pt = closed_loop_track_point(theta_start_deg)
            p1_pt = closed_loop_track_point(1680.0 if top_feeder_ramp else theta_end_deg)
            dx = p1_pt.X - p0_pt.X
            dy = p1_pt.Y - p0_pt.Y
            dz = p1_pt.Z - p0_pt.Z
            az_deg = math.degrees(math.atan2(dy, dx))
            pitch_deg = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
            diag_deg = 45.0
            seg_solid = (
                seg_solid.moved(bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, -az_deg)))
                .moved(bd.Location((0.0, 0.0, 0.0), (0.0, pitch_deg, 0.0)))
                .moved(bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, diag_deg)))
            )
        verts = seg_solid.tessellate(0.5)[0]
        if verts:
            min_x = min(v.X for v in verts)
            max_x = max(v.X for v in verts)
            min_y = min(v.Y for v in verts)
            max_y = max(v.Y for v in verts)
            min_z = min(v.Z for v in verts)
            loc_shift = bd.Location((-(min_x + max_x) / 2.0, -(min_y + max_y) / 2.0, -min_z))
        else:
            bb = seg_solid.bounding_box()
            loc_shift = bd.Location(
                (-(bb.min.X + bb.max.X) / 2.0, -(bb.min.Y + bb.max.Y) / 2.0, -bb.min.Z)
            )
        seg_solid = seg_solid.moved(loc_shift)

    return seg_solid


def build_all_track_parts(for_plate_grid: bool = False) -> dict[str, bd.Solid]:
    """Build all 14 full-scale conical helix track segments + Track_Joint_Clip
    (Toolhead 2 - Translucent Emerald Green).

    Note: `for_plate_grid` is retained only for signature compatibility; this function
    always builds the 100% real, full-scale track segments (`track_seg_01`..`track_seg_14_top_entry`)
    so every build plate contains the exact same full-size geometry as the `.stl` and `.step` files.
    """
    _ = for_plate_grid
    parts: dict[str, bd.Solid] = {}
    num_full = int(HELIX_TOTAL_DEG // TRACK_SEGMENT_ARC_DEG)  # 13

    for i in range(num_full + 1):
        if i < num_full:
            t0 = i * TRACK_SEGMENT_ARC_DEG
            t1 = (i + 1) * TRACK_SEGMENT_ARC_DEG
            name = f"track_seg_{i + 1:02d}"
        else:
            rem_deg = HELIX_TOTAL_DEG - num_full * TRACK_SEGMENT_ARC_DEG
            if rem_deg <= 1.0:
                continue
            t0 = num_full * TRACK_SEGMENT_ARC_DEG
            t1 = HELIX_TOTAL_DEG
            name = f"track_seg_{num_full + 1:02d}_top_entry"

        has_pedestal = i in TRACK_PLANET_SEGMENT_INDICES

        seg = build_track_segment(
            t0,
            t1,
            orient_for_print=True,
            include_planet_pedestal=has_pedestal,
            bottom_return_ramp=(i == 0),
            top_feeder_ramp=(i == num_full),
            seg_number=i + 1,
        )

        parts[name] = assign_toolhead(seg, name, 2)

    parts["Track_Joint_Clip"] = build_track_joint_clip(orient_for_print=True)

    return parts


if __name__ == "__main__":
    all_segs = build_all_track_parts()
    for name, part in all_segs.items():
        bb = part.bounding_box()
        print(
            f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, "
            f"bbox=({bb.size.X:.1f}, {bb.size.Y:.1f}, {bb.size.Z:.1f})"
        )
