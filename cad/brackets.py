"""Cantilever Track Support Arms with Dovetails (cad/brackets.py).

Generates printable support-free cantilever ribs extending from the trunk's
60° helical female dovetail sockets to the underside of the conical helix track:
  - Inner end: Downward-tapered 45° male dovetail tenon (0.15 mm radial clearance).
  - Structural rib: Angled cantilever arm with 45° under-chamfers for support-free
    FDM printing.
  - Top interface: Cradle pad with central LED channel clearance bridge and twin
    Ø 4.0 mm alignment pegs that mate into the underside sockets of each track segment.
  - Underside feature: Small hanging eyelet (Ø 2.5 mm hole) for acoustic bells/chimes.
"""

from __future__ import annotations

import math
import build123d as bd

from common_params import (
    BRACKET_EYELET_DIA,
    BRACKET_PEG_DIA,
    BRACKET_PEG_HEIGHT,
    BRACKET_PEG_SPACING_U,
    BRACKET_STATION_COUNT,
    DOVETAIL_BASE_W_TOP,
    DOVETAIL_CLEARANCE,
    DOVETAIL_DETENT_Y_HALF,
    DOVETAIL_NECK_W_TOP,
    DOVETAIL_RADIAL_DEPTH,
    DOVETAIL_SLOT_H,
    DOVETAIL_TAPER_W,
    LED_CHANNEL_W,
    TRUNK_OUTER_R,
    assign_toolhead,
    helix_radius,
    make_engraved_label_solid,
)


def make_male_dovetail_tenon() -> bd.Solid:
    """Create the downward-tapered 45° male dovetail tenon with 0.15 mm radial clearance
    and a 45° bottom chamfer for support-free printing.
    """
    d = DOVETAIL_RADIAL_DEPTH - DOVETAIL_CLEARANCE  # 4.35 mm protrusion into 4.50 mm slot
    clr = DOVETAIL_CLEARANCE                        # 0.15 mm radial clearance per side

    half_base_top = (DOVETAIL_BASE_W_TOP / 2.0) - 2.0 * clr  # 7.70 mm at X = -4.35
    half_neck_top = (DOVETAIL_NECK_W_TOP / 2.0) - 1.5 * clr  # 3.275 mm at X = 0.0

    taper = DOVETAIL_TAPER_W / 2.0
    half_base_bot = half_base_top - taper
    half_neck_bot = half_neck_top - taper

    # Embed 1.5 mm into the bracket abutment root (X in [0, 1.5]) for a clean union
    embed_x = 1.5

    # Bottom 45° chamfer start (at Z = d + 0.35, receding to X = 0.35 at Z = 0.00)
    z_bot = 0.0
    z_chamfer = d + 0.35
    z_top = DOVETAIL_SLOT_H - 0.25
    pts_z0 = [
        (0.35, -(half_neck_bot - 0.50)),
        (0.50, -half_neck_bot),
        (embed_x, -half_neck_bot),
        (embed_x, half_neck_bot),
        (0.50, half_neck_bot),
        (0.35, half_neck_bot - 0.50),
        (0.35, -(half_neck_bot - 0.50)),
    ]
    pts_mid = [
        (-d, -half_base_bot),
        (0.0, -half_neck_bot),
        (embed_x, -half_neck_bot),
        (embed_x, half_neck_bot),
        (0.0, half_neck_bot),
        (-d, half_base_bot),
        (-d, -half_base_bot),
    ]
    pts_top = [
        (-d, -half_base_top),
        (0.0, -half_neck_top),
        (embed_x, -half_neck_top),
        (embed_x, half_neck_top),
        (0.0, half_neck_top),
        (-d, half_base_top),
        (-d, -half_base_top),
    ]

    w_z0 = bd.Pos(0.0, 0.0, z_bot) * bd.Wire(
        [bd.Edge.make_line(pts_z0[i], pts_z0[i + 1]) for i in range(6)]
    )
    w_mid = bd.Pos(0.0, 0.0, z_chamfer) * bd.Wire(
        [bd.Edge.make_line(pts_mid[i], pts_mid[i + 1]) for i in range(6)]
    )
    w_top = bd.Pos(0.0, 0.0, z_top) * bd.Wire(
        [bd.Edge.make_line(pts_top[i], pts_top[i + 1]) for i in range(6)]
    )

    lower_chamfer = bd.Solid.make_loft([w_z0, w_mid], ruled=True)
    upper_tenon = bd.Solid.make_loft([w_mid, w_top], ruled=True)
    tenon = (lower_chamfer + upper_tenon).solid()

    # Add a small 45-deg beveled anti-lift friction bump on both +/-Y neck flanks
    # (Z = 14.5..16.5 mm, Y_outer = DOVETAIL_DETENT_Y_HALF = 3.44 mm < 3.50 mm socket neck)
    # so the tenon slides cleanly in rigid PLA with zero flexing while providing light friction
    # against accidental upward slip before the helical track is locked over the pegs.
    y_bump = DOVETAIL_DETENT_Y_HALF
    for sign_y in (-1.0, 1.0):
        pts_bump = [
            (sign_y * 2.90, 14.5),
            (sign_y * y_bump, 15.1),
            (sign_y * y_bump, 15.9),
            (sign_y * 2.90, 16.5),
            (sign_y * 2.90, 14.5),
        ]
        b_wire = bd.Wire([bd.Edge.make_line(pts_bump[i], pts_bump[i + 1]) for i in range(4)])
        bump = bd.Pos(-0.20, 0.0, 0.0) * bd.extrude(bd.Plane.YZ * bd.Face(b_wire), amount=0.25, both=True)
        tenon = tenon + bump
    return tenon.solid()


def build_cantilever_bracket(
    track_center_radius: float,
    tier_num: int = 1,
    label_text: str | None = None,
) -> bd.Solid:
    """Build a support-free upright-printable cantilever bracket for a given helix centerline radius.

    Local coordinates:
      X: Radial outreach from trunk outer surface (X = 0 corresponds to R = TRUNK_OUTER_R)
      Y: Tangential width (centered at Y = 0)
      Z: Vertical height (Z = 0.00 is the full-length flat bottom of the structural rib resting
         on the build plate; Z = DOVETAIL_SLOT_H - 0.25 = 17.75 mm is the top cradle mating with
         the underside of the track).
    """
    reach_x = track_center_radius - TRUNK_OUTER_R
    cradle_inner_x = max(6.0, reach_x - 14.5)
    cradle_outer_x = reach_x + 14.5
    top_z = DOVETAIL_SLOT_H - 0.25  # 17.75 mm nominal peg datum (0.25 mm below track centerline)
    pad_shoulder_z = top_z - 1.85   # 15.90 mm outer shoulder clears steep inner-turn helix slope
    pad_top_z = top_z - 0.35        # 17.40 mm crowned central bearing ridge beneath split-tine pegs

    rib_w = 8.0
    tenon = make_male_dovetail_tenon()

    # Main structural cantilever rib profile in XZ plane:
    # Rests 100% flat on Z = 0.00 mm from X = 0.35 mm out to bot_flat_end_x, then bevels up at a
    # self-supporting 45° angle to (cradle_outer_x, top_z - 5.0) for upright support-free printing.
    eyelet_x = 0.55 * reach_x
    eyelet_center_z = 4.5
    tip_bevel = top_z - 5.0  # 12.75 mm (exact 45° outer tip chamfer)
    bot_flat_end_x = max(12.0, cradle_outer_x - tip_bevel)

    pts_rib = [
        (0.35, 0.0),
        (bot_flat_end_x, 0.0),
        (cradle_outer_x, top_z - 5.0),
        (cradle_outer_x, pad_shoulder_z),
        (0.35, pad_shoulder_z),
        (0.35, 0.0),
    ]
    rib_wire = bd.Wire(
        [bd.Edge.make_line(pts_rib[i], pts_rib[i + 1]) for i in range(len(pts_rib) - 1)]
    )
    rib_face = bd.Plane.XZ * bd.Face(rib_wire)
    rib_body = bd.extrude(rib_face, amount=rib_w / 2.0, both=True)

    # Top wider track support pad (11.0 mm wide shoulder, 45° under-chamfer, crowned to 4.2 mm ridge)
    # so even the steepest 1560° inner track turn clears the downhill pad shoulder cleanly.
    pad_w = 11.0
    crown_w = 4.2
    pad_h = 4.5
    chamfer_d = (pad_w - rib_w) / 2.0  # 1.5 mm 45-deg under-chamfer
    pad_len = cradle_outer_x - cradle_inner_x
    pad_center_x = 0.5 * (cradle_inner_x + cradle_outer_x)

    w_pad_bot = (
        bd.Pos(pad_center_x, 0.0, top_z - pad_h)
        * bd.Rectangle(pad_len, rib_w).wire()
    )
    w_pad_mid1 = (
        bd.Pos(pad_center_x, 0.0, top_z - pad_h + chamfer_d)
        * bd.Rectangle(pad_len, pad_w).wire()
    )
    w_pad_mid2 = (
        bd.Pos(pad_center_x, 0.0, pad_shoulder_z)
        * bd.Rectangle(pad_len, pad_w).wire()
    )
    w_pad_top = (
        bd.Pos(pad_center_x, 0.0, pad_top_z)
        * bd.Rectangle(pad_len, crown_w).wire()
    )
    pad_solid = (
        bd.Solid.make_loft([w_pad_bot, w_pad_mid1], ruled=True)
        + bd.Solid.make_loft([w_pad_mid1, w_pad_mid2], ruled=True)
        + bd.Solid.make_loft([w_pad_mid2, w_pad_top], ruled=True)
    )

    arm = tenon + rib_body + pad_solid

    # Cut Ø 2.5 mm acoustic chime hanging eyelet through-hole inside the solid lower rib web
    eyelet_hole = (
        bd.Pos(eyelet_x, 0.0, eyelet_center_z)
        * bd.Rot(90.0, 0.0, 0.0)
        * bd.Cylinder(
            radius=BRACKET_EYELET_DIA / 2.0,
            height=rib_w + 4.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
        )
    )
    arm = arm - eyelet_hole

    # Cut central LED wire/strip clearance notch on top cradle pad at X = reach_x
    led_notch = bd.Pos(reach_x, 0.0, pad_top_z - 1.5) * bd.Box(
        LED_CHANNEL_W + 0.8,
        pad_w + 2.0,
        3.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    arm = arm - led_notch

    # Add twin Ø 4.0 mm root-filleted split-tine cantilever alignment pegs with tangential
    # ±Y through-slots (0.85 mm wide × 2.80 mm deep from peg tip) and symmetric 0.90 mm-tall
    # (axial Z) × Ø 4.38 mm radial snap lobes (<= 0.09 mm radial flex per tine through
    # the Ø 4.20 mm PETG throat into the Ø 4.56 mm internal track socket pocket).
    peg_r = BRACKET_PEG_DIA / 2.0  # 2.00 mm nominal (mates with Ø 4.20 mm socket throat)
    lobe_r = 2.19                  # Ø 4.38 mm radial snap lobes
    dr_lobe = lobe_r - peg_r       # 0.19 mm radial protrusion (<= 0.09 mm flex past R=2.10 throat)
    chamfer_top = 0.60
    root_fillet_r = 0.40
    slot_w = 0.85
    slot_depth = 2.80
    slot_z0 = top_z + BRACKET_PEG_HEIGHT - slot_depth  # top_z + 1.70 mm
    lobe_z0 = top_z + 3.00         # 0.90 mm tall lobe sits at z_peg = 3.00..3.90 (sock 2.75..3.65)
    lobe_land = 0.90 - 2.0 * dr_lobe  # 0.52 mm crest
    for u_offset in (-BRACKET_PEG_SPACING_U, BRACKET_PEG_SPACING_U):
        peg_x = reach_x + u_offset
        peg_fillet = bd.Pos(peg_x, 0.0, pad_top_z) * bd.Cone(
            bottom_radius=peg_r + root_fillet_r,
            top_radius=peg_r,
            height=root_fillet_r,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        peg_cyl = bd.Pos(peg_x, 0.0, pad_top_z) * bd.Cylinder(
            radius=peg_r,
            height=(top_z + BRACKET_PEG_HEIGHT - chamfer_top) - pad_top_z,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        peg_tip = bd.Pos(peg_x, 0.0, top_z + BRACKET_PEG_HEIGHT - chamfer_top) * bd.Cone(
            bottom_radius=peg_r,
            top_radius=peg_r - chamfer_top,
            height=chamfer_top,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        lobe_bot = bd.Pos(peg_x, 0.0, lobe_z0) * bd.Cone(
            bottom_radius=peg_r,
            top_radius=lobe_r,
            height=dr_lobe,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        lobe_mid = bd.Pos(peg_x, 0.0, lobe_z0 + dr_lobe) * bd.Cylinder(
            radius=lobe_r,
            height=lobe_land,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        lobe_top = bd.Pos(peg_x, 0.0, lobe_z0 + dr_lobe + lobe_land) * bd.Cone(
            bottom_radius=lobe_r,
            top_radius=peg_r,
            height=dr_lobe,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        peg_solid = peg_fillet + peg_cyl + peg_tip + lobe_bot + lobe_mid + lobe_top
        tine_slot = bd.Pos(peg_x, 0.0, slot_z0) * bd.Box(
            slot_w,
            2.0 * lobe_r + 2.0,
            slot_depth + 1.0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        peg_split = peg_solid - tine_slot
        arm = arm + peg_split

    # Deboss 1..4 support-free 45° V-notch tier identification bars on the hidden back face
    # (X = -4.35 mm) of the male dovetail tenon so builders can sort Tiers 1–4 at a glance
    d_tenon = DOVETAIL_RADIAL_DEPTH - DOVETAIL_CLEARANCE  # 4.35 mm
    notch_depth = 0.70
    for idx in range(max(1, min(4, tier_num))):
        z_n = 6.2 + idx * 2.5
        pts_v = [
            (-d_tenon - 0.3, z_n - notch_depth - 0.3),
            (-d_tenon + notch_depth, z_n),
            (-d_tenon - 0.3, z_n + notch_depth + 0.3),
            (-d_tenon - 0.3, z_n - notch_depth - 0.3),
        ]
        v_wire = bd.Wire([bd.Edge.make_line(pts_v[i], pts_v[i + 1]) for i in range(3)])
        v_prism = bd.extrude(bd.Plane.XZ * bd.Face(v_wire), amount=5.0, both=True)
        arm = arm - v_prism

    # Engrave the station or tier number into the recessed top saddle floor
    # at (X = reach_x, Y = 0.0, Z = top_z - 1.5 mm) between the twin Ø 4.0 mm pegs (100% covered
    # underneath the track segment once assembled!)
    lbl_str = label_text if label_text is not None else str(max(1, min(4, tier_num)))
    char_h = 3.5 if len(lbl_str) >= 2 else 4.5
    tier_digit = bd.Pos(reach_x, 0.0, top_z - 1.5) * make_engraved_label_solid(
        lbl_str, char_h=char_h, depth=0.80
    )
    arm = arm - tier_digit

    return arm.solid()


def build_all_bracket_parts() -> dict[str, bd.Solid]:
    """Generate the 4 tier cantilever support brackets (Toolhead 1 - Dark Wood Brown)."""
    # Representative stations for the 4 conical tiers (Top, Upper-Mid, Lower-Mid, Bottom)
    tier_specs = [
        ("bracket_tier1_top", helix_radius(1440.0), 1),       # Top tier (~70 mm radius)
        ("bracket_tier2_upper_mid", helix_radius(1080.0), 2), # Upper-mid tier (~88 mm radius)
        ("bracket_tier3_lower_mid", helix_radius(540.0), 3),  # Lower-mid tier (~117 mm radius)
        ("bracket_tier4_bottom", helix_radius(120.0), 4),     # Bottom tier (~139 mm radius)
    ]
    return {
        name: assign_toolhead(build_cantilever_bracket(r, tier_num=t_num), name, 1)
        for name, r, t_num in tier_specs
    }


def build_all_station_brackets() -> dict[str, bd.Solid]:
    """Generate all 26 exact-radius station cantilever brackets (`bracket_01`..`bracket_26`,
    for stations 60°..1560° from bottom to top, Toolhead 1 - Dark Wood Brown #4A2F1D) with
    their exact station number ('1'..'26') engraved face-up on the top saddle floor.
    """
    parts: dict[str, bd.Solid] = {}
    for k in range(1, BRACKET_STATION_COUNT + 1):
        deg = k * 60.0
        r = helix_radius(deg)
        tier_num = max(1, 4 - (k - 1) // 6)
        name = f"bracket_{k:02d}"
        part = build_cantilever_bracket(r, tier_num=tier_num, label_text=str(k))
        parts[name] = assign_toolhead(part, name, 1)
    return parts


if __name__ == "__main__":
    for name, part in build_all_bracket_parts().items():
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid}, vol={part.volume:.1f}, bbox={bb.size}")
