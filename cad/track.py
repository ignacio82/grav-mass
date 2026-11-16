"""Conical Helix Track Sweep, Stepped Half-Lap Segments & Planet Balconies (cad/track.py).

Generates the segmented conical helix raceway for the 25.0 mm rolling spheres:
  - Continuous conical helix geometry tapering from R = 145.0 mm (bottom)
    to R = 60.0 mm (top) over 4.5 turns at 79.0 mm vertical pitch.
  - Custom 2D swept cross-section (`TRACK_BASE_Y = -15.5 mm`):
      * Parabolic/circular trough floor (R = 16.0 mm) with flat shoulders
      * Inner retaining wall (12.0 mm height), outer retaining wall (18.0 mm height, 1.0 mm lip)
      * Deepened 6.2 mm underside WS2812B Pebble LED channel (45° flare + 8.4×3.6 mm pill bay)
  - 14 bracket-aligned segments (`seg_01`: -90°..60°, `seg_02..13`: 120° arcs across 60°..1500°,
    `seg_14_top_entry`: 1500°..1710°) meeting at odd-60° bracket stations:
      * 8.0° circumferential `-Z` stepped shoulder half-lap seams across `|u| >= 5.5 mm`
      * Clean vertical butt across `|u| < 5.5 mm` preserving continuous LED wire routing
      * Underside Ø 4.20 mm lead-in / Ø 4.56 mm pocket mounting sockets for bracket split-tine pegs
      * Integrated Outer-Rim Mechanical Planet Pedestal Balconies (Ø 7.60 × 3.50 mm split-tine
        pegs with Ø 8.32 mm snap lobes) on 8 segments using `PLANET_ANCHOR_DEGS`
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    AUGER_BALL_ORBIT_R,
    BRACKET_PEG_DIA,
    BRACKET_PEG_HEIGHT,
    BRACKET_PEG_SPACING_U,
    CLICK_RIB_PROTRUSION_MM,
    DOVETAIL_ANGULAR_STEP_DEG,
    HELIX_BOT_R,
    HELIX_PITCH,
    HELIX_TOP_R,
    HELIX_TOTAL_DEG,
    HELIX_TOTAL_HEIGHT,
    LED_CHANNEL_D,
    LED_CHANNEL_THROAT_W,
    LED_CHANNEL_W,
    PLANET_ANCHOR_DEGS,
    RETURN_CHUTE_END_DEG,
    TIMING_GATE_ANGLES_DEG,
    TOP_FEEDER_START_DEG,
    TOP_FEEDER_START_R,
    TRACK_BASE_Y,
    TRACK_HALF_INNER_W,
    TRACK_INNER_WALL_H,
    TRACK_INNER_WALL_THICK,
    TRACK_LAP_ARC_DEG,
    TRACK_OUTER_LIP_INSET,
    TRACK_OUTER_WALL_H,
    TRACK_OUTER_WALL_THICK,
    TRACK_SEGMENT_ARC_DEG,
    TRACK_SHOULDER_INNER_X,
    TRACK_TROUGH_R,
    assign_toolhead,
    closed_loop_section_plane,
    closed_loop_track_point,
    helix_arc_length_from_top,
    helix_radius,
    helix_section_plane,
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
    11: 2,  # Venus   (1320°)
    9: 3,   # Earth   (1080°)
    7: 4,   # Mars    (840°)
    5: 5,   # Jupiter (600°)
    4: 6,   # Saturn  (480°)
    2: 7,   # Uranus  (240°)
    0: 8,   # Neptune (-15°)
}


def get_track_segment_specs() -> list[tuple[str, float, float, bool, bool, int]]:
    """Return canonical `(name, theta_start_deg, theta_end_deg, is_bot, is_top, seg_num)` tuples
    for all 14 track segments meeting cleanly at odd-60° bracket seam stations:
      - `track_seg_01`           : 0°..60° (+ bottom return ramp -90°..0°)
      - `track_seg_02..13`       : 12 × 120° arcs across 60°..1500°
      - `track_seg_14_top_entry` : 1500°..1620° (+ top feeder catch basin 1620°..1710°)
    """
    specs: list[tuple[str, float, float, bool, bool, int]] = [
        ("track_seg_01", 0.0, 60.0, True, False, 1),
    ]
    for i in range(1, 13):
        t0 = 60.0 + (i - 1) * TRACK_SEGMENT_ARC_DEG
        t1 = t0 + TRACK_SEGMENT_ARC_DEG
        specs.append((f"track_seg_{i + 1:02d}", t0, t1, False, False, i + 1))
    specs.append(("track_seg_14_top_entry", 1500.0, HELIX_TOTAL_DEG, False, True, 14))
    return specs


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


def _append_led_channel_points(pts: list[tuple[float, float]], u_in_outer: float) -> None:
    """Append the shared deepened underside WS2812B LED channel polygon vertices from
    `u = +14.5` around the 45° snap-in flare + 8.4×3.6 mm pill bay to `(u_in_outer, -9.0)`.
    Shared by both `make_track_profile_wire()` and `make_track_endcap_wire()`.
    """
    v_bot = TRACK_BASE_Y                                     # -15.5 mm
    v_led_roof = v_bot + LED_CHANNEL_D                       # -9.3 mm
    u_led_half = LED_CHANNEL_W / 2.0                         # 4.2 mm (internal chamber)
    u_throat_half = LED_CHANNEL_THROAT_W / 2.0               # 2.3 mm (snap-in throat)
    v_lip_top = v_bot + 0.70                                 # -14.8 mm
    v_chamfer_top = v_lip_top + (u_led_half - u_throat_half) # -12.9 mm (45° self-supporting flare)
    pts.extend(
        [
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
    )


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
    ]
    _append_led_channel_points(pts_right, u_in_outer)

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
    `make_track_profile_wire()` (`u in [-20.0, +20.6]`, `v in [-15.5, +18.0]`) to form
    enclosed bumper end-caps at the top and bottom trunk transitions.
    """
    u_in_outer = -(TRACK_HALF_INNER_W + TRACK_INNER_WALL_THICK)  # -20.0 mm
    u_out_outer = TRACK_HALF_INNER_W + TRACK_OUTER_WALL_THICK    # +20.6 mm
    pts = [
        (u_in_outer, -9.0),
        (u_in_outer, TRACK_OUTER_WALL_H),
        (u_out_outer, TRACK_OUTER_WALL_H),
        (u_out_outer, -9.0),
    ]
    _append_led_channel_points(pts, u_in_outer)
    return bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])


def _get_endcap_wire() -> bd.Wire:
    global _ENDCAP_WIRE_CACHE
    if _ENDCAP_WIRE_CACHE is None:
        _ENDCAP_WIRE_CACHE = make_track_endcap_wire()
    return _ENDCAP_WIRE_CACHE


def _cut_loft_strips(
    seg: bd.Shape, wires: list[bd.Wire], theta_0: float, theta_1: float, n_steps: int = 4
) -> bd.Shape:
    """Loft each closed 2D `(u, v)` cutter wire along `[theta_0, theta_1]` and subtract each solid cleanly."""
    angs = [theta_0 + (theta_1 - theta_0) * (i / n_steps) for i in range(n_steps + 1)]
    for w2d in wires:
        faces = [
            bd.Face(closed_loop_section_plane(a, scarf_tilt_deg=0.0).from_local_coords(w2d))
            for a in angs
        ]
        sol = bd.loft(faces)
        for s in sol.solids():
            seg = seg - s
    return seg


def _make_stepped_lap_wires(keep_side: str) -> list[bd.Wire]:
    """Return strictly CCW 2D `(u, v)` cutter wires for the `-Z` stepped shoulder half-lap seam.

    When `keep_side == "lower"` (uphill end of `seg_k`), removes the **upper** shoulder (`v >= -9.20`
    on `5.45 <= |u| <= 16.50` and `v >= +1.00` on `16.50 <= |u| <= 22.0`).
    When `keep_side == "upper"` (downhill start of `seg_{k+1}`), removes the **lower** shoulder
    (`v <= -8.95` on `5.40 <= |u| <= 16.35` and `v <= +1.25` on `16.35 <= |u| <= 22.0`),
    providing `0.25 mm` vertical shelf clearance and `>= 0.13 mm` radial step clearance with
    zero residual seam teeth.
    """
    if keep_side == "lower":
        poly_inner = [
            (-22.00, 1.00),
            (-16.50, 1.00),
            (-16.50, -9.20),
            (-5.45, -9.20),
            (-5.45, 22.00),
            (-22.00, 22.00),
            (-22.00, 1.00),
        ]
        poly_outer = [
            (5.45, -9.20),
            (16.50, -9.20),
            (16.50, 1.00),
            (22.00, 1.00),
            (22.00, 22.00),
            (5.45, 22.00),
            (5.45, -9.20),
        ]
    else:
        poly_inner = [
            (-22.00, -18.50),
            (-5.40, -18.50),
            (-5.40, -8.95),
            (-16.35, -8.95),
            (-16.35, 1.25),
            (-22.00, 1.25),
            (-22.00, -18.50),
        ]
        poly_outer = [
            (5.40, -18.50),
            (22.00, -18.50),
            (22.00, 1.25),
            (16.35, 1.25),
            (16.35, -8.95),
            (5.40, -8.95),
            (5.40, -18.50),
        ]
    return [
        bd.Wire([bd.Edge.make_line(poly[i], poly[i + 1]) for i in range(len(poly) - 1)])
        for poly in (poly_inner, poly_outer)
    ]


def build_track_segment(
    theta_start_deg: float,
    theta_end_deg: float,
    orient_for_print: bool = True,
    include_planet_pedestal: bool = True,
    bottom_return_ramp: bool = False,
    top_feeder_ramp: bool = False,
    seg_number: int | None = None,
) -> bd.Solid:
    """Build a single conical helix track segment between `theta_start_deg` and `theta_end_deg`.

    Includes:
      - Bracket-aligned `-Z` stepped shoulder half-lap seams (`TRACK_LAP_ARC_DEG = 8.0°`,
        `>= 3.2 mm` vertical shoulder flanges across `|u| >= 5.5 mm`, vertical butt across
        `|u| < 5.5 mm` preserving continuous LED wire routing)
      - Underside female split-tine bracket sockets (`Ø 4.20 mm` throat, `Ø 4.56 mm` pocket)
      - Optional integrated Outer-Rim Mechanical Planet Pedestal Balcony (`u = +30.0 mm`,
        `v_top = +18.0 mm`) with a split-tine `Ø 7.60 × 3.50 mm` peg (`Ø 8.32 mm` snap lobes)
        anchored at `PLANET_ANCHOR_DEGS`
      - Optional Bottom Return Collector Chute (`theta = -90°..0°` into `trunk_base`)
      - Optional Top Feeder Chute (`theta = 1620°..1710°` from `trunk_top`, `TOP_FEEDER_START_R = 47.0`)
    """
    base_wire = _get_profile_wire()
    lap_half = TRACK_LAP_ARC_DEG / 2.0  # 4.0 deg
    n_sections = 40 if (bottom_return_ramp or top_feeder_ramp) else 14

    # Sweep extends across ±lap_half on stepped-lap seam ends (with 0.15 deg end-stop clearance)
    a_start = (
        (RETURN_CHUTE_END_DEG - 18.0)
        if bottom_return_ramp
        else (theta_start_deg - lap_half + 0.15)
    )
    a_end = (
        (TOP_FEEDER_START_DEG + 18.0)
        if top_feeder_ramp
        else (theta_end_deg + lap_half - 0.15)
    )
    angles = [
        a_start + (a_end - a_start) * (i / n_sections)
        for i in range(n_sections + 1)
    ]

    section_faces = [
        bd.Face(
            closed_loop_section_plane(a, scarf_tilt_deg=0.0).from_local_coords(base_wire)
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
    if bottom_return_ramp:
        bot_endcap_wall = bd.Pos(-16.5, -46.5, 33.05) * bd.Box(
            6.0,
            29.0,
            33.45,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        pad_bot = bd.Pos(0.0, -40.0, 33.20) * bd.Box(
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
            + bd.Pos(0.0, 0.0, 30.0)
            * bd.Cone(
                bottom_radius=47.2,
                top_radius=45.8,
                height=2.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            + bd.Pos(0.0, 0.0, 32.0)
            * bd.Cone(
                bottom_radius=45.8,
                top_radius=38.2,
                height=16.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            + bd.Pos(0.0, 0.0, 48.0)
            * bd.Cone(
                bottom_radius=38.2,
                top_radius=35.8,
                height=5.0,
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
        keep_s01_cut = bd.Pos(0.0, -31.0, 31.5) * bd.Box(
            30.0,
            27.5,
            41.5,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        seg = seg - (u_chute_bot & keep_s01_cut)
        pl_cob_pcb = closed_loop_section_plane(-70.0, scarf_tilt_deg=0.0)
        cob_pcb_pocket = bd.Pos(0.0, TRACK_BASE_Y + 1.85, 0.0) * bd.Box(
            10.0,
            3.8,
            16.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        seg = seg - pl_cob_pcb.from_local_coords(cob_pcb_pocket)

    if top_feeder_ramp:
        top_endcap_wall = bd.Pos(16.5, -51.5, 409.55) * bd.Box(
            6.0,
            34.0,
            33.45,
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
            radius=max(41.5, TOP_FEEDER_START_R - 5.5),
            height=95.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        chute_slot = (
            bd.Pos(0.0, -34.0, 418.0)
            * bd.Rot(9.1, 0.0, 0.0)
            * bd.Box(
                28.0,
                32.0,
                40.0,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        seg = seg - (inner_wall_cyl_top & chute_slot)

    # 1. Bracket-Aligned -Z Stepped Shoulder Half-Lap Seams + Underside Segment Number:
    pts_center_cut_end = [
        (-5.55, -18.50),
        (5.55, -18.50),
        (5.55, 22.00),
        (-5.55, 22.00),
        (-5.55, -18.50),
    ]
    w_center_cut_end = bd.Wire(
        [bd.Edge.make_line(pts_center_cut_end[i], pts_center_cut_end[i + 1]) for i in range(4)]
    )
    pts_center_cut_start = [
        (-5.58, -18.50),
        (5.58, -18.50),
        (5.58, 22.00),
        (-5.58, 22.00),
        (-5.58, -18.50),
    ]
    w_center_cut_start = bd.Wire(
        [bd.Edge.make_line(pts_center_cut_start[i], pts_center_cut_start[i + 1]) for i in range(4)]
    )

    if not bottom_return_ramp and (theta_end_deg - theta_start_deg) >= 40.0:
        seg = _cut_loft_strips(
            seg,
            _make_stepped_lap_wires("upper"),
            theta_start_deg - lap_half - 0.8,
            theta_start_deg + lap_half,
            n_steps=4,
        )
        seg = _cut_loft_strips(
            seg,
            [w_center_cut_start],
            theta_start_deg - lap_half - 0.8,
            theta_start_deg + 0.14,
            n_steps=2,
        )

    if not top_feeder_ramp and (theta_end_deg - theta_start_deg) >= 40.0:
        seg = _cut_loft_strips(
            seg,
            _make_stepped_lap_wires("lower"),
            theta_end_deg - lap_half,
            theta_end_deg + lap_half + 0.8,
            n_steps=4,
        )
        seg = _cut_loft_strips(
            seg,
            [w_center_cut_end],
            theta_end_deg - 0.14,
            theta_end_deg + lap_half + 0.8,
            n_steps=2,
        )

    seg_num_val = seg_number if seg_number is not None else max(
        1, min(14, int(round((theta_start_deg + 60.0) / TRACK_SEGMENT_ARC_DEG)))
    )
    seg_idx_zero = seg_num_val - 1

    # Engrave segment number ("1".."14") flush on underside beside the first midspan cradle
    lbl_deg = 0.5 * (theta_start_deg + theta_end_deg)
    pl_lbl = helix_section_plane(lbl_deg, scarf_tilt_deg=0.0)
    num_cutter_world = pl_lbl.from_local_coords(
        bd.Pos(-BRACKET_PEG_SPACING_U, TRACK_BASE_Y, 10.5)
        * bd.Rot(90.0, 0.0, 0.0)
        * make_engraved_label_solid(str(seg_num_val), char_h=3.2, depth=0.65)
    )
    seg = seg - num_cutter_world

    # 2. Cut twin female split-tine bracket mounting sockets on underside:
    #    - Midspan stations (strictly inside segment, including 60° on bottom seg_01)
    #    - Seam station ONLY on uphill lower half-lap end (`theta_end_deg` when not top_feeder_ramp)
    #    So upper segment (`seg_{k+1}`) drops -Z onto exposed lower flange (`seg_k`) with zero deadlock.
    k_min_offs = 0.0 if bottom_return_ramp else 5.0
    k_max_offs = 0.0 if top_feeder_ramp else 0.5
    k_min = max(1, int(math.ceil((theta_start_deg + k_min_offs) / DOVETAIL_ANGULAR_STEP_DEG)))
    k_max = min(26, int(math.floor((theta_end_deg + k_max_offs) / DOVETAIL_ANGULAR_STEP_DEG)))
    if top_feeder_ramp:
        k_max = min(26, int(math.floor((TOP_FEEDER_START_DEG - 140.0) / DOVETAIL_ANGULAR_STEP_DEG)))

    r_throat = 2.10   # Ø 4.20 mm lead-in throat (0.10 mm clearance over Ø 4.0 mm bracket peg)
    r_pocket = 2.28   # Ø 4.56 mm internal snap pocket (0.09 mm resting clearance over Ø 4.38 mm lobes)
    cham_h = 0.60     # 45° bottom mouth chamfer (R = 2.70 -> 2.10 mm clears 0.50 mm peg fillet)

    station_angles = [k * DOVETAIL_ANGULAR_STEP_DEG for k in range(k_min, k_max + 1)]
    if not station_angles:
        station_angles = [0.5 * (theta_start_deg + theta_end_deg)]

    for st_deg in station_angles:
        pl_st = helix_section_plane(st_deg, scarf_tilt_deg=0.0)
        for u_peg in (-BRACKET_PEG_SPACING_U, BRACKET_PEG_SPACING_U):
            sock_lead = (
                bd.Pos(u_peg, TRACK_BASE_Y - 0.85, 0.0)
                * bd.Rot(-90.0, 0.0, 0.0)
                * bd.Cone(
                    bottom_radius=r_throat + cham_h + 0.85,
                    top_radius=r_throat,
                    height=cham_h + 0.85,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            sock_throat = (
                bd.Pos(u_peg, TRACK_BASE_Y + cham_h, 0.0)
                * bd.Rot(-90.0, 0.0, 0.0)
                * bd.Cylinder(
                    radius=r_throat,
                    height=1.90,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            sock_expand = (
                bd.Pos(u_peg, TRACK_BASE_Y + 2.50, 0.0)
                * bd.Rot(-90.0, 0.0, 0.0)
                * bd.Cone(
                    bottom_radius=r_throat,
                    top_radius=r_pocket,
                    height=0.18,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            sock_pocket = (
                bd.Pos(u_peg, TRACK_BASE_Y + 2.68, 0.0)
                * bd.Rot(-90.0, 0.0, 0.0)
                * bd.Cylinder(
                    radius=r_pocket,
                    height=1.42,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            sock_roof = (
                bd.Pos(u_peg, TRACK_BASE_Y + 4.10, 0.0)
                * bd.Rot(-90.0, 0.0, 0.0)
                * bd.Cone(
                    bottom_radius=r_pocket,
                    top_radius=1.40,
                    height=0.88,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )
            seg = seg - pl_st.from_local_coords(
                sock_lead + sock_throat + sock_expand + sock_pocket + sock_roof
            )

    # 3. Integrated Outer Rim Mechanical Planet Pedestal Balcony (at u = +30.0 mm, v_top = +18.0 mm)
    #    Anchored explicitly at `PLANET_ANCHOR_DEGS` (clear of seams & timing gates) with
    #    split-tine flex slots (0.85 × 2.40 mm) and Ø 8.32 mm snap lobes on Ø 7.60 × 3.50 mm pegs.
    if include_planet_pedestal and seg_idx_zero in SEGMENT_INDEX_TO_PLANET_NUM:
        p_num = SEGMENT_INDEX_TO_PLANET_NUM[seg_idx_zero]
        ped_deg = PLANET_ANCHOR_DEGS[p_num - 1]
        pl_mid = closed_loop_section_plane(ped_deg, scarf_tilt_deg=0.0)
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
        r_bead = 4.16                 # Ø 8.32 mm snap lobes inside Ø 8.46 mm planet groove
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
                height=0.36,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_bead_mid = (
            bd.Pos(30.0, 20.01, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cylinder(
                radius=r_bead,
                height=0.22,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
        )
        peg_bead_upper = (
            bd.Pos(30.0, 20.23, 0.0)
            * bd.Rot(-90.0, 0.0, 0.0)
            * bd.Cone(
                bottom_radius=r_bead,
                top_radius=r_peg,
                height=0.36,
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
        split_slot = bd.Pos(30.0, 18.0 + PLANET_PEG_HEIGHT - 2.40 + 1.50, 0.0) * bd.Box(
            10.0,
            3.00,
            0.85,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
        split_peg = (peg_cyl + peg_bead_lower + peg_bead_mid + peg_bead_upper + peg_tip) - split_slot
        pedestal_local = (pad_cyl + bridge_box + gusset + split_peg).solid()
        # Engrave planet number ("1".."8") on flat balcony deck beside split-tine peg
        peg_num_cutter = (
            bd.Pos(30.0, 18.0, 5.4)
            * bd.Rot(-90.0, 0.0, 0.0)
            * make_engraved_label_solid(str(p_num), char_h=2.4, depth=0.65)
        )
        pedestal_local = (pedestal_local - peg_num_cutter).solid()
        seg = seg + pl_mid.from_local_coords(pedestal_local)

    # 3b. Galileo-Newton Gravity Chronometer Markings (Timing Gates G0..G5, Acoustic Click
    #     Micro-Ribs = CLICK_RIB_PROTRUSION_MM = 0.50 mm, and 100 mm / 500 mm Ticks)
    if (theta_end_deg - theta_start_deg) >= 50.0:
        ped_deg_excl = (
            PLANET_ANCHOR_DEGS[SEGMENT_INDEX_TO_PLANET_NUM[seg_idx_zero] - 1]
            if (include_planet_pedestal and seg_idx_zero in SEGMENT_INDEX_TO_PLANET_NUM)
            else -999.0
        )
        # Timing Gates G0..G5:
        for g_idx, g_deg in enumerate(TIMING_GATE_ANGLES_DEG):
            if (theta_start_deg + 4.5) <= g_deg <= (theta_end_deg - 4.5):
                pl_g = closed_loop_section_plane(g_deg, scarf_tilt_deg=0.0)
                gate_notch = bd.Pos(18.3, 18.0, 0.0) * bd.Box(
                    5.2, 2.2, 1.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
                )
                gate_lbl = (
                    bd.Pos(20.6, 8.2, 0.0)
                    * bd.Rot(0.0, 90.0, 0.0)
                    * make_engraved_label_solid(f"G{g_idx}", char_h=4.6, depth=0.70)
                )
                # 0.50 mm inward acoustic click micro-rib on inner face of outer wall (u = 16.50..17.50)
                click_rib = bd.Pos(17.0 - CLICK_RIB_PROTRUSION_MM + 0.50, 6.0, 0.0) * bd.Box(
                    1.00, 5.0, 1.2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
                )
                seg = (seg + pl_g.from_local_coords(click_rib)) - pl_g.from_local_coords(
                    gate_notch + gate_lbl
                )

        # 100 mm (10 cm) True 3D Spiral Arc-Length Graduation Ticks measured from G0 (1605°):
        s_g0 = helix_arc_length_from_top(TIMING_GATE_ANGLES_DEG[0])
        for s_dm in range(1, 29):
            s_mm = s_dm * 100.0
            t_tick = theta_for_helix_arc_length(s_g0 + s_mm)
            if (theta_start_deg + 4.5) <= t_tick <= (theta_end_deg - 4.5):
                if any(abs(t_tick - gd) < 4.5 for gd in TIMING_GATE_ANGLES_DEG):
                    continue
                if abs(t_tick - ped_deg_excl) < 6.5:
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

    # 4. Pitch-Level Horizontal Print Orientation + Explicit Datum Lands (`seg_01`, `seg_14`):
    if orient_for_print:
        if bottom_return_ramp:
            seg_solid = (
                seg_solid.moved(bd.Location((0.0, 0.0, 0.0), (0.0, -5.5, 0.0)))
                .moved(bd.Location((0.0, 0.0, 0.0), (-5.0, 0.0, 0.0)))
                .moved(bd.Location((0.0, 0.0, 0.0), (0.0, 0.0, 55.0)))
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

        # Ensure crisp >= 25 mm^2 coplanar datum land at Z = 0.00 mm (slice lowest heel)
        skim_z = 0.90 if bottom_return_ramp else (0.55 if top_feeder_ramp else 0.45)
        bb_z = seg_solid.bounding_box()
        trim_box = bd.Pos(
            0.5 * (bb_z.min.X + bb_z.max.X),
            0.5 * (bb_z.min.Y + bb_z.max.Y),
            -2.0,
        ) * bd.Box(
            bb_z.size.X + 20.0,
            bb_z.size.Y + 20.0,
            2.0 + skim_z,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        seg_solid = (seg_solid - trim_box).moved(bd.Location((0.0, 0.0, -skim_z))).solid()

    return seg_solid


def build_all_track_parts(for_plate_grid: bool = False) -> dict[str, bd.Solid]:
    """Build all 14 full-scale conical helix track segments
    (Toolhead 2 - Translucent Teal PETG).
    """
    _ = for_plate_grid
    parts: dict[str, bd.Solid] = {}
    for idx, (name, t0, t1, is_bot, is_top, seg_num) in enumerate(get_track_segment_specs()):
        has_pedestal = idx in TRACK_PLANET_SEGMENT_INDICES
        seg = build_track_segment(
            t0,
            t1,
            orient_for_print=True,
            include_planet_pedestal=has_pedestal,
            bottom_return_ramp=is_bot,
            top_feeder_ramp=is_top,
            seg_number=seg_num,
        )
        parts[name] = assign_toolhead(seg, name, 2)

    return parts


if __name__ == "__main__":
    all_segs = build_all_track_parts()
    for name, part in all_segs.items():
        bb = part.bounding_box()
        print(
            f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, "
            f"bbox=({bb.size.X:.1f}, {bb.size.Y:.1f}, {bb.size.Z:.1f})"
        )
