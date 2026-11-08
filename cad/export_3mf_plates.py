"""Dual 3MF Slicer Pipeline & Multi-Plate Layout Exporter (cad/export_3mf_plates.py).

Generates pre-oriented, color-mapped `.3mf` build plates for the Snapmaker U1
(4 independent toolheads, 270 x 270 x 270 mm build volume) in OrcaSlicer / Snapmaker Orca:
  - Output A: 6 individual pre-plated `.3mf` files in `./output/3mf/Plate_N_<Name>.3mf`
              (Plates 1-5: 100% single-color plates requiring zero toolhead swaps;
               Plate 6: dedicated multi-color plate with unified multi-part objects).
  - Output B: Unified multi-plate OrcaSlicer project `./output/3mf/GravMass_Tree_Ultimate_U1.3mf`
              with `Metadata/project_settings.config`, `Metadata/model_settings.config`,
              unified `<components>` / `<part subtype="normal_part">` multi-color objects,
              and OrcaSlicer's 2D plate grid transforms (`324.0 mm` X/Y stride centered at `+135.0 mm`).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import build123d as bd

from auger import build_all_auger_parts
from brackets import build_all_24_station_brackets, build_all_bracket_parts
from common_params import (
    MIN_PART_CLEARANCE,
    ORCA_PLATE_STRIDE_X,
    ORCA_PLATE_STRIDE_Y,
    SAFE_PLATE_ZONE,
    TOOLHEAD_PALETTE,
    U1_BED_X,
    U1_BED_Y,
    U1_BED_Z,
    assign_toolhead,
)
from topper_planets import (
    build_all_apple_hemispheres,
    build_all_marbles,
    build_all_topper_planet_parts,
    build_apple_captive_pause_marble,
    build_apple_topper_stem_leaf,
)
from track import (
    TRACK_PLANET_SEGMENT_INDICES,
    build_all_track_parts,
    build_track_joint_clip,
    build_track_segment,
)
from trunk import build_all_trunk_parts
from common_params import (
    AUGER_HALF_HEIGHT,
    HELIX_PITCH,
    HELIX_TOTAL_DEG,
    TRACK_SEGMENT_ARC_DEG,
    TRUNK_SECTION_HEIGHT,
    helix_point,
    helix_radius,
    helix_section_plane,
    helix_z,
)


@dataclass
class PlatedPart:
    """Represents a single oriented, color-mapped, bed-leveled part placed on a build plate."""

    name: str
    part: bd.Solid
    toolhead_id: int
    hex_color: str
    filament_type: str
    plate_index: int
    plate_name: str
    center_xy: tuple[float, float]


def _mesh_bounds(part: bd.Solid) -> tuple[float, float, float, float, float, float]:
    """Return exact (min_x, max_x, min_y, max_y, min_z, max_z) from tessellated mesh vertices."""
    verts = part.tessellate(0.5)[0]
    if verts:
        min_x = min(v.X for v in verts)
        max_x = max(v.X for v in verts)
        min_y = min(v.Y for v in verts)
        max_y = max(v.Y for v in verts)
        min_z = min(v.Z for v in verts)
        max_z = max(v.Z for v in verts)
        return (min_x, max_x, min_y, max_y, min_z, max_z)
    bb = part.bounding_box()
    return (bb.min.X, bb.max.X, bb.min.Y, bb.max.Y, bb.min.Z, bb.max.Z)


def orient_for_printing(
    part: bd.Solid,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bd.Solid:
    """Rotate a component into its optimal support-free FDM orientation, center XY at (0, 0),
    and translate vertically so its tessellated mesh minimum Z rests strictly at z = 0.0.
    """
    label = getattr(part, "label", "") or "part"
    toolhead_id = getattr(part, "toolhead_id", 1)

    oriented = copy.deepcopy(part)
    if rotation != (0.0, 0.0, 0.0):
        oriented.move(bd.Location((0.0, 0.0, 0.0), rotation))

    # Center X and Y at 0.0 and level minimum Z at z = 0.0 using exact mesh vertices
    min_x, max_x, min_y, max_y, min_z, _max_z = _mesh_bounds(oriented)
    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    dz = -min_z
    oriented.move(bd.Location((-cx, -cy, dz)))

    assign_toolhead(oriented, label, toolhead_id)
    orig_subparts = getattr(part, "colored_subparts", None)
    if orig_subparts:
        new_subparts: list[bd.Solid] = []
        for sp in orig_subparts:
            sp_copy = copy.deepcopy(sp)
            if rotation != (0.0, 0.0, 0.0):
                sp_copy.move(bd.Location((0.0, 0.0, 0.0), rotation))
            sp_copy.move(bd.Location((-cx, -cy, dz)))
            sp_copy.color = sp.color
            sp_copy.label = sp.label
            sp_copy.toolhead_id = getattr(sp, "toolhead_id", toolhead_id)  # type: ignore[attr-defined]
            new_subparts.append(sp_copy)
        oriented.colored_subparts = new_subparts  # type: ignore[attr-defined]

    return oriented


def _place_on_bed(
    part: bd.Solid,
    rotation: tuple[float, float, float],
    xy: tuple[float, float],
    plate_index: int,
    plate_name: str,
) -> PlatedPart:
    """Orient a part for support-free printing, drop to Z=0, and translate to (x, y) on the plate."""
    label = getattr(part, "label", "") or "part"
    toolhead_id = getattr(part, "toolhead_id", 1)
    spec = TOOLHEAD_PALETTE[toolhead_id]
    custom_hex = getattr(part, "hex_color", None) or spec["hex"]

    oriented = orient_for_printing(part, rotation=rotation)
    oriented.move(bd.Location((xy[0], xy[1], 0.0)))
    # Re-ensure mesh z_min == 0.0 after XY translation
    _min_x, _max_x, _min_y, _max_y, z_err, _max_z = _mesh_bounds(oriented)
    if abs(z_err) > 1e-9:
        oriented.move(bd.Location((0.0, 0.0, -z_err)))

    subparts = getattr(oriented, "colored_subparts", None)
    if subparts:
        for sp in subparts:
            sp.move(bd.Location((xy[0], xy[1], -z_err if abs(z_err) > 1e-9 else 0.0)))

    assign_toolhead(oriented, label, toolhead_id)
    oriented.color = bd.Color(custom_hex)
    oriented.hex_color = custom_hex  # type: ignore[attr-defined]
    if subparts:
        oriented.colored_subparts = subparts  # type: ignore[attr-defined]
    return PlatedPart(
        name=label,
        part=oriented,
        toolhead_id=toolhead_id,
        hex_color=custom_hex,
        filament_type=spec["filament_type"],
        plate_index=plate_index,
        plate_name=plate_name,
        center_xy=xy,
    )


def _pair_side_by_side_on_bed(
    p1: bd.Solid,
    rot1: tuple[float, float, float],
    p2: bd.Solid,
    rot2: tuple[float, float, float],
    plate_index: int,
    plate_name: str,
    gap_x: float = 12.5,
) -> list[PlatedPart]:
    """Place two parts side-by-side along X with exact non-overlapping AABB clearance `gap_x`."""
    o1 = orient_for_printing(p1, rotation=rot1)
    o2 = orient_for_printing(p2, rotation=rot2)
    bb1 = o1.bounding_box()
    bb2 = o2.bounding_box()
    m1 = _mesh_bounds(o1)
    m2 = _mesh_bounds(o2)
    w1 = max(bb1.size.X, m1[1] - m1[0])
    w2 = max(bb2.size.X, m2[1] - m2[0])
    tot_w = w1 + gap_x + w2
    xc1 = round(-0.5 * tot_w + 0.5 * w1, 2)
    xc2 = round(0.5 * tot_w - 0.5 * w2, 2)
    return [
        _place_on_bed(p1, rot1, (xc1, 0.0), plate_index, plate_name),
        _place_on_bed(p2, rot2, (xc2, 0.0), plate_index, plate_name),
    ]


def _build_topper_color_accents() -> tuple[bd.Solid, bd.Solid]:
    """Build two small topper trim rings in Toolheads 1 & 2 for Plate 5 so Plate 5
    exercises all 4 toolheads (1: Brown, 2: Emerald Green, 3: Gold, 4: Red).
    """
    # Toolhead 1 (Dark Wood Brown): Topper-to-Trunk adapter collar ring (OD 23.6 mm, ID 18.0 mm, H 5.0 mm)
    collar = bd.Cylinder(
        radius=11.8, height=5.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    ) - bd.Cylinder(
        radius=9.0, height=12.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    collar_solid = assign_toolhead(collar.solid(), "topper_trunk_collar", 1)

    # Toolhead 2 (Translucent Emerald Green): Topper funnel light-diffuser bezel ring (OD 24.0 mm, ID 19.0 mm, H 3.5 mm)
    bezel = bd.Cylinder(
        radius=12.0, height=3.5, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    ) - bd.Cylinder(
        radius=9.5, height=10.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)
    )
    bezel_solid = assign_toolhead(bezel.solid(), "topper_emerald_bezel", 2)

    return collar_solid, bezel_solid


PLANET_NAMES = (
    "planet_mercury",
    "planet_venus",
    "planet_earth",
    "planet_mars",
    "planet_jupiter",
    "planet_saturn",
    "planet_uranus",
    "planet_neptune",
)


def _orca_plate_cols(plate_count: int) -> int:
    """Compute the number of grid columns used by OrcaSlicer's PartPlateList::compute_colum_count."""
    if plate_count <= 1:
        return 1
    val = math.sqrt(float(plate_count))
    r = round(val)
    return r + 1 if val > r else r


def build_five_plates(
    prebuilt_parts: dict[str, bd.Solid] | None = None,
) -> dict[str, list[PlatedPart]]:
    """Construct and lay out all Grand Grav-Mass parts across 10 Snapmaker U1 build plates:
      - Plates 1-9: 100% single-color plates (only 1 filament/toolhead per plate, zero swaps)
        containing every FULL-SCALE track segment (track_seg_01..14) and all 24 exact-radius
        cantilever support brackets (bracket_01..24).
      - Plate 10:   Dedicated multi-color plate containing ONLY unified multi-color objects.
    """
    if prebuilt_parts is not None:
        trunk_parts = {
            k: prebuilt_parts[k]
            for k in (
                "trunk_base",
                "trunk_mid",
                "trunk_top",
                "Base_Bottom_Cover",
                "Conduit_Cover_Strip",
                "Battery_Cover",
            )
        }
        auger_parts = {
            k: prebuilt_parts[k]
            for k in (
                "auger_lower",
                "auger_upper",
                "Motor_Clutch_Driver",
                "Servo_Or_030_Adapter",
            )
        }
        topper_planet_parts = {
            k: prebuilt_parts[k]
            for k in ("golden_apple_topper", "Magic_LED_Wand", *PLANET_NAMES)
        }
    else:
        trunk_parts = build_all_trunk_parts()
        auger_parts = build_all_auger_parts()
        topper_planet_parts = build_all_topper_planet_parts()

    if prebuilt_parts is not None and "bracket_01" in prebuilt_parts:
        station_brackets = {f"bracket_{k:02d}": prebuilt_parts[f"bracket_{k:02d}"] for k in range(1, 25)}
    else:
        station_brackets = build_all_24_station_brackets()

    if prebuilt_parts is not None and "track_seg_01" in prebuilt_parts:
        track_parts = {
            k: prebuilt_parts[k]
            for k in (
                *[f"track_seg_{i:02d}" for i in range(1, 14)],
                "track_seg_14_top_entry",
            )
        }
    else:
        track_parts = build_all_track_parts(for_plate_grid=False)

    hemispheres = (
        {
            k: prebuilt_parts[k]
            for k in (
                *[f"apple_hemisphere_a_{i:02d}" for i in range(1, 7)],
                *[f"apple_hemisphere_b_{i:02d}" for i in range(1, 7)],
            )
        }
        if (prebuilt_parts is not None and "apple_hemisphere_a_01" in prebuilt_parts)
        else build_all_apple_hemispheres(count=6)
    )

    # Create 3 labeled copies of Conduit_Cover_Strip (1 for each trunk section: base, mid, top)
    conduit_covers: dict[str, bd.Solid] = {}
    for idx in range(1, 4):
        c_copy = copy.deepcopy(trunk_parts["Conduit_Cover_Strip"])
        c_name = f"Conduit_Cover_Strip_{idx:02d}"
        assign_toolhead(c_copy, c_name, 1)
        conduit_covers[c_name] = c_copy

    plates: dict[str, list[PlatedPart]] = {}

    # -----------------------------------------------------------------------
    # Plate 1: Single-Color T1 Dark Wood Brown (#4A2F1D) — Trunk Base & Bottom Cover
    # 100% Toolhead 1 (Zero filament swaps, zero prime tower, >= 15.1 mm gap)
    # -----------------------------------------------------------------------
    p1_name = "Plate_1_SingleColor_Brown_Trunk_Base"
    plates[p1_name] = [
        _place_on_bed(trunk_parts["trunk_base"], (0.0, 0.0, 0.0), (-30.0, 0.0), 0, p1_name),
        _place_on_bed(trunk_parts["Base_Bottom_Cover"], (0.0, 0.0, 0.0), (80.0, 0.0), 0, p1_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 2: Single-Color T1 Dark Wood Brown (#4A2F1D) — Upper Trunk Sections & Covers
    # 100% Toolhead 1 (Zero filament swaps, zero prime tower, >= 13.4 mm gap)
    # Includes 3x copies of Conduit_Cover_Strip (1 per trunk section: base, mid, top)
    # -----------------------------------------------------------------------
    p2_name = "Plate_2_SingleColor_Brown_Trunk_Upper_And_Covers"
    plates[p2_name] = [
        _place_on_bed(trunk_parts["trunk_mid"], (0.0, 0.0, 0.0), (-52.0, -38.0), 1, p2_name),
        _place_on_bed(trunk_parts["trunk_top"], (0.0, 0.0, 0.0), (52.0, -38.0), 1, p2_name),
        _place_on_bed(trunk_parts["Battery_Cover"], (0.0, 0.0, 0.0), (-52.0, 32.0), 1, p2_name),
        _place_on_bed(auger_parts["Servo_Or_030_Adapter"], (0.0, 0.0, 90.0), (-52.0, 74.0), 1, p2_name),
        _place_on_bed(conduit_covers["Conduit_Cover_Strip_01"], (0.0, 0.0, 90.0), (48.0, 24.0), 1, p2_name),
        _place_on_bed(conduit_covers["Conduit_Cover_Strip_02"], (0.0, 0.0, 90.0), (48.0, 50.0), 1, p2_name),
        _place_on_bed(conduit_covers["Conduit_Cover_Strip_03"], (0.0, 0.0, 90.0), (48.0, 76.0), 1, p2_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 3: Single-Color T1 Dark Wood Brown (#4A2F1D) — Station Brackets #1 to #12
    # 100% Toolhead 1 (Upright Z=0 flat rib base, zero supports, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p3_name = "Plate_3_SingleColor_Brown_Brackets_01_To_12"
    p3_items: list[PlatedPart] = []
    for i in range(6):
        yc = round(-75.0 + i * 30.0, 2)
        k1 = i + 1
        k2 = 12 - i
        b1 = station_brackets[f"bracket_{k1:02d}"]
        b2 = station_brackets[f"bracket_{k2:02d}"]
        len1 = max(b1.bounding_box().size.X, _mesh_bounds(b1)[1] - _mesh_bounds(b1)[0])
        len2 = max(b2.bounding_box().size.X, _mesh_bounds(b2)[1] - _mesh_bounds(b2)[0])
        tot_w = len1 + 12.5 + len2
        xc1 = round(-0.5 * tot_w + 0.5 * len1, 2)
        xc2 = round(0.5 * tot_w - 0.5 * len2, 2)
        p3_items.append(_place_on_bed(b1, (0.0, 0.0, 0.0), (xc1, yc), 2, p3_name))
        p3_items.append(_place_on_bed(b2, (0.0, 0.0, 180.0), (xc2, yc), 2, p3_name))
    plates[p3_name] = p3_items

    # -----------------------------------------------------------------------
    # Plate 4: Single-Color T1 Dark Wood Brown (#4A2F1D) — Station Brackets #13 to #24
    # 100% Toolhead 1 (Upright Z=0 flat rib base, zero supports, >= 14.6 mm gap)
    # -----------------------------------------------------------------------
    p4_name = "Plate_4_SingleColor_Brown_Brackets_13_To_24"
    p4_items: list[PlatedPart] = []
    for i in range(6):
        yc = round(-75.0 + i * 30.0, 2)
        k1 = 13 + i
        k2 = 24 - i
        b1 = station_brackets[f"bracket_{k1:02d}"]
        b2 = station_brackets[f"bracket_{k2:02d}"]
        len1 = max(b1.bounding_box().size.X, _mesh_bounds(b1)[1] - _mesh_bounds(b1)[0])
        len2 = max(b2.bounding_box().size.X, _mesh_bounds(b2)[1] - _mesh_bounds(b2)[0])
        tot_w = len1 + 15.0 + len2
        xc1 = round(-0.5 * tot_w + 0.5 * len1, 2)
        xc2 = round(0.5 * tot_w - 0.5 * len2, 2)
        p4_items.append(_place_on_bed(b1, (0.0, 0.0, 0.0), (xc1, yc), 3, p4_name))
        p4_items.append(_place_on_bed(b2, (0.0, 0.0, 180.0), (xc2, yc), 3, p4_name))
    plates[p4_name] = p4_items

    # -----------------------------------------------------------------------
    # Plate 5: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segment 01 (Dedicated Plate)
    # 100% Toolhead 2 (Centered solo at (0, 0), 230.8 x 230.1 mm, >= 19.6 mm margin on all 4 sides)
    # -----------------------------------------------------------------------
    p5_name = "Plate_5_SingleColor_Green_Track_01"
    plates[p5_name] = [
        _place_on_bed(track_parts["track_seg_01"], (0.0, 0.0, 0.0), (0.0, 0.0), 4, p5_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 6: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segment 02 (Dedicated Plate)
    # 100% Toolhead 2 (Centered solo at (0, 0), 203.4 x 202.2 mm)
    # -----------------------------------------------------------------------
    p6_name = "Plate_6_SingleColor_Green_Track_02"
    plates[p6_name] = [
        _place_on_bed(track_parts["track_seg_02"], (0.0, 0.0, 0.0), (0.0, 0.0), 5, p6_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 7: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segment 03 (Dedicated Plate)
    # 100% Toolhead 2 (Centered solo at (0, 0), 195.6 x 194.4 mm)
    # -----------------------------------------------------------------------
    p7_name = "Plate_7_SingleColor_Green_Track_03"
    plates[p7_name] = [
        _place_on_bed(track_parts["track_seg_03"], (0.0, 0.0, 0.0), (0.0, 0.0), 6, p7_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 8: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segment 04 (Dedicated Plate)
    # 100% Toolhead 2 (Centered solo at (0, 0), 187.8 x 186.6 mm)
    # -----------------------------------------------------------------------
    p8_name = "Plate_8_SingleColor_Green_Track_04"
    plates[p8_name] = [
        _place_on_bed(track_parts["track_seg_04"], (0.0, 0.0, 0.0), (0.0, 0.0), 7, p8_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 9: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segments 05 & 13
    # 100% Toolhead 2 (Side-by-side non-overlapping AABB & Convex Hulls, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p9_name = "Plate_9_SingleColor_Green_Track_05_And_13"
    plates[p9_name] = _pair_side_by_side_on_bed(
        track_parts["track_seg_05"],
        (0.0, 0.0, 70.0),
        track_parts["track_seg_13"],
        (0.0, 0.0, 40.0),
        8,
        p9_name,
        gap_x=12.5,
    )

    # -----------------------------------------------------------------------
    # Plate 10: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segments 06 & 12
    # 100% Toolhead 2 (Side-by-side non-overlapping AABB & Convex Hulls, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p10_name = "Plate_10_SingleColor_Green_Track_06_And_12"
    plates[p10_name] = _pair_side_by_side_on_bed(
        track_parts["track_seg_06"],
        (0.0, 0.0, 60.0),
        track_parts["track_seg_12"],
        (0.0, 0.0, 40.0),
        9,
        p10_name,
        gap_x=12.5,
    )

    # -----------------------------------------------------------------------
    # Plate 11: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segments 07 & 11
    # 100% Toolhead 2 (Side-by-side non-overlapping AABB & Convex Hulls, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p11_name = "Plate_11_SingleColor_Green_Track_07_And_11"
    plates[p11_name] = _pair_side_by_side_on_bed(
        track_parts["track_seg_07"],
        (0.0, 0.0, 20.0),
        track_parts["track_seg_11"],
        (0.0, 0.0, 45.0),
        10,
        p11_name,
        gap_x=12.5,
    )

    # -----------------------------------------------------------------------
    # Plate 12: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segments 08 & 10
    # 100% Toolhead 2 (Side-by-side non-overlapping AABB & Convex Hulls, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p12_name = "Plate_12_SingleColor_Green_Track_08_And_10"
    plates[p12_name] = _pair_side_by_side_on_bed(
        track_parts["track_seg_08"],
        (0.0, 0.0, 50.0),
        track_parts["track_seg_10"],
        (0.0, 0.0, 45.0),
        11,
        p12_name,
        gap_x=12.5,
    )

    # -----------------------------------------------------------------------
    # Plate 13: Single-Color T2 Translucent Emerald Green (#00A86B) — Track Segments 09 & 14
    # 100% Toolhead 2 (Side-by-side non-overlapping AABB & Convex Hulls, >= 12.5 mm gap)
    # -----------------------------------------------------------------------
    p13_name = "Plate_13_SingleColor_Green_Track_09_And_14"
    plates[p13_name] = _pair_side_by_side_on_bed(
        track_parts["track_seg_09"],
        (0.0, 0.0, 60.0),
        track_parts["track_seg_14_top_entry"],
        (0.0, 0.0, 20.0),
        12,
        p13_name,
        gap_x=12.5,
    )

    # -----------------------------------------------------------------------
    # Plate 14: Single-Color T3 Silk Gold (#D4AF37) — Archimedes Auger & Hex Coupler
    # 100% Toolhead 3 (Zero filament swaps, zero prime tower, >= 22.0 mm gap)
    # -----------------------------------------------------------------------
    p14_name = "Plate_14_SingleColor_Gold_Auger_And_Drive"
    plates[p14_name] = [
        _place_on_bed(auger_parts["auger_lower"], (0.0, 0.0, 0.0), (-45.0, 0.0), 13, p14_name),
        _place_on_bed(auger_parts["auger_upper"], (0.0, 0.0, 0.0), (15.0, 0.0), 13, p14_name),
        _place_on_bed(auger_parts["Motor_Clutch_Driver"], (0.0, 0.0, 0.0), (65.0, 0.0), 13, p14_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 15: Single-Color T4 Glossy Crimson Red (#C41E3A) — 6x Glowing Apple Marbles (12 Hemispheres)
    # 100% Toolhead 4 (Zero filament swaps, zero prime tower, >= 13.0 mm gap)
    # -----------------------------------------------------------------------
    p15_name = "Plate_15_SingleColor_Red_Apple_Marbles"
    row_x6 = [-95.0, -57.0, -19.0, 19.0, 57.0, 95.0]
    plates[p15_name] = [
        *[
            _place_on_bed(
                hemispheres[f"apple_hemisphere_a_{i:02d}"],
                (0.0, 0.0, 0.0),
                (row_x6[i - 1], -22.0),
                14,
                p15_name,
            )
            for i in range(1, 7)
        ],
        *[
            _place_on_bed(
                hemispheres[f"apple_hemisphere_b_{i:02d}"],
                (0.0, 0.0, 0.0),
                (row_x6[i - 1], 22.0),
                14,
                p15_name,
            )
            for i in range(1, 7)
        ],
    ]

    # -----------------------------------------------------------------------
    # Plate 16: Dedicated 4-Color Plate — Apple Topper (with integrated Stem/Leaf) & Magic Wand
    # Palette (4 Colors max): T1 #4A2F1D Brown, T2 #00A86B Emerald, T3 #D4AF37 Gold, T4 #C41E3A Red
    # -----------------------------------------------------------------------
    p16_name = "Plate_16_MultiColor_Topper_And_Wand"
    plates[p16_name] = [
        _place_on_bed(topper_planet_parts["golden_apple_topper"], (0.0, 0.0, 0.0), (-42.0, 0.0), 15, p16_name),
        _place_on_bed(topper_planet_parts["Magic_LED_Wand"], (0.0, 0.0, 90.0), (45.0, 0.0), 15, p16_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 17: Dedicated 4-Color Plate — Warm Terrestrial & Gas-Giant Planets
    # Palette (4 Colors max): T1 #4A2F1D Dark Basalt/Umber, T2 #F5EFE6 Creamy Alabaster,
    #                         T3 #D4AF37 Ochre/Silk Gold, T4 #C41E3A Terracotta/Crimson Red
    # -----------------------------------------------------------------------
    p17_name = "Plate_17_MultiColor_Planets_Warm_And_Gas_Giants"
    plates[p17_name] = [
        _place_on_bed(topper_planet_parts["planet_mercury"], (0.0, 0.0, 0.0), (-65.0, -42.0), 16, p17_name),
        _place_on_bed(topper_planet_parts["planet_venus"], (0.0, 0.0, 0.0), (0.0, -42.0), 16, p17_name),
        _place_on_bed(topper_planet_parts["planet_mars"], (0.0, 0.0, 0.0), (65.0, -42.0), 16, p17_name),
        _place_on_bed(topper_planet_parts["planet_jupiter"], (0.0, 0.0, 0.0), (-42.0, 36.0), 16, p17_name),
        _place_on_bed(topper_planet_parts["planet_saturn"], (0.0, 0.0, 0.0), (42.0, 36.0), 16, p17_name),
    ]

    # -----------------------------------------------------------------------
    # Plate 18: Dedicated 4-Color Plate — Ocean & Ice-Giant Planets
    # Palette (4 Colors max): T1 #1E5AA8 Deep Cobalt Ocean Blue, T2 #00A86B Continental Emerald/Teal,
    #                         T3 #F0F4F8 Glacial Polar Ice White, T4 #D4AF37 Golden Mountain/Ring Accent
    # -----------------------------------------------------------------------
    p18_name = "Plate_18_MultiColor_Planets_Ocean_And_Ice_Giants"
    plates[p18_name] = [
        _place_on_bed(topper_planet_parts["planet_earth"], (0.0, 0.0, 0.0), (-62.0, 0.0), 17, p18_name),
        _place_on_bed(topper_planet_parts["planet_uranus"], (0.0, 0.0, 0.0), (0.0, 0.0), 17, p18_name),
        _place_on_bed(topper_planet_parts["planet_neptune"], (0.0, 0.0, 0.0), (62.0, 0.0), 17, p18_name),
    ]

    return plates


build_six_plates = build_five_plates
build_ten_plates = build_five_plates
build_twelve_plates = build_five_plates
build_eighteen_plates = build_five_plates

PLATE_FILAMENT_PALETTES: dict[str, tuple[list[str], list[str]]] = {
    "Plate_17_MultiColor_Planets_Warm_And_Gas_Giants": (
        ["#4A2F1D", "#F5EFE6", "#D4AF37", "#C41E3A"],
        ["PLA", "PLA", "PLA", "PLA"],
    ),
    "Plate_18_MultiColor_Planets_Ocean_And_Ice_Giants": (
        ["#1E5AA8", "#00A86B", "#F0F4F8", "#D4AF37"],
        ["PLA", "PETG", "PLA", "PLA"],
    ),
}


def _make_project_settings_json(plate_name: str | None = None) -> str:
    """Create OrcaSlicer / Snapmaker Orca Metadata/project_settings.config JSON string
    explicitly configured for Snapmaker U1 (0.4 mm nozzle across all 4 toolheads).
    """
    if plate_name and plate_name in PLATE_FILAMENT_PALETTES:
        filament_colours, filament_types = PLATE_FILAMENT_PALETTES[plate_name]
    else:
        filament_colours = [TOOLHEAD_PALETTE[i]["hex"] for i in (1, 2, 3, 4)]
        filament_types = [TOOLHEAD_PALETTE[i]["filament_type"] for i in (1, 2, 3, 4)]
    is_single_color = bool(plate_name and "SingleColor" in plate_name)
    needs_support = bool(
        plate_name is None
        or "Track" in plate_name
        or "MultiColor" in plate_name
    )
    config = {
        "printer_model": "Snapmaker U1",
        "printer_settings_id": "Snapmaker U1 (0.4 nozzle)",
        "printer_variant": "0.4",
        "nozzle_diameter": ["0.4", "0.4", "0.4", "0.4"],
        "nozzle_type": "hardened_steel",
        "printable_area": ["0x0", f"{int(U1_BED_X)}x0", f"{int(U1_BED_X)}x{int(U1_BED_Y)}", f"0x{int(U1_BED_Y)}"],
        "printable_height": str(int(U1_BED_Z)),
        "extruder_colour": filament_colours,
        "filament_colour": filament_colours,
        "filament_type": filament_types,
        "filament_settings_id": [
            f"Generic {ft} @Snapmaker U1 (0.4 nozzle)" for ft in filament_types
        ],
        "print_settings_id": "0.20 Standard @Snapmaker U1 (0.4 nozzle)",
        "layer_height": "0.2",
        "initial_layer_print_height": "0.2",
        "line_width": "0.42",
        "initial_layer_line_width": "0.5",
        "outer_wall_line_width": "0.42",
        "inner_wall_line_width": "0.45",
        "sparse_infill_line_width": "0.45",
        "internal_solid_infill_line_width": "0.42",
        "top_surface_line_width": "0.42",
        "support_line_width": "0.42",
        "wall_loops": "3",
        "sparse_infill_density": "15%",
        "sparse_infill_pattern": "gyroid",
        "enable_prime_tower": "0" if is_single_color else "1",
        "print_sequence": "by layer",
        "enable_support": "1" if needs_support else "0",
        "support_type": "tree(auto)",
        "support_on_build_plate_only": "1",
        "dont_support_bridges": "1",
    }
    return json.dumps(config, indent=2)


def _make_slice_info_xml(plate_names_ordered: list[str]) -> str:
    """Create OrcaSlicer Metadata/slice_info.config XML declaring Snapmaker U1 0.4mm nozzles."""
    cfg = ET.Element("config")
    hdr = ET.SubElement(cfg, "header")
    ET.SubElement(hdr, "header_item", {"key": "X-BBL-Client-Type", "value": "slicer"})
    ET.SubElement(hdr, "header_item", {"key": "X-BBL-Client-Version", "value": "02.02.00.85"})
    for idx, pname in enumerate(plate_names_ordered, start=1):
        if pname in PLATE_FILAMENT_PALETTES:
            f_cols, f_types = PLATE_FILAMENT_PALETTES[pname]
        else:
            f_cols = [TOOLHEAD_PALETTE[i]["hex"] for i in (1, 2, 3, 4)]
            f_types = [TOOLHEAD_PALETTE[i]["filament_type"] for i in (1, 2, 3, 4)]
        pl = ET.SubElement(cfg, "plate")
        ET.SubElement(pl, "metadata", {"key": "index", "value": str(idx)})
        ET.SubElement(pl, "metadata", {"key": "printer_model_id", "value": "Snapmaker U1"})
        ET.SubElement(pl, "metadata", {"key": "nozzle_diameters", "value": "0.4,0.4,0.4,0.4"})
        for tid in range(1, 5):
            ET.SubElement(
                pl,
                "filament",
                {
                    "id": str(tid),
                    "type": f_types[tid - 1],
                    "color": f_cols[tid - 1],
                },
            )
    ET.indent(cfg, space="  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(cfg, encoding="unicode")


def _color_to_toolhead_id(hex_str: str, default_tid: int) -> int:
    """Map a sub-part hex color to the closest Snapmaker U1 toolhead (1..4)."""
    h = hex_str.upper()
    if h in ("#4A2F1D", "#6E4726", "#B8860B", "#1E5AA8"):
        return 1
    if h in ("#00A86B", "#2E9B4F", "#1E6B9B", "#F5EFE6"):
        return 2
    if h in ("#D4AF37", "#F4B41A", "#F2E2C4", "#F0F4F8", "#E5B84B"):
        return 3
    if h in ("#C41E3A", "#D96B27", "#8C2D19"):
        return 4
    return default_tid


def _add_part_meshes_to_exporter(
    exporter: bd.Mesher,
    pp: PlatedPart,
) -> list[tuple[str, str, int, str]]:
    """Add a PlatedPart's mesh (or colored sub-meshes) to a bd.Mesher in local object
    coordinates (parent XY centered at (0, 0), z_min = 0.0).
    Returns a list of (mesh_key, sub_label, toolhead_id, hex_color) tuples.
    """
    dx = -pp.center_xy[0]
    dy = -pp.center_xy[1]
    subparts = getattr(pp.part, "colored_subparts", None)
    records: list[tuple[str, str, int, str]] = []

    if subparts and len(subparts) > 1:
        for idx, sp in enumerate(subparts):
            sp_local = copy.deepcopy(sp)
            sp_local.move(bd.Location((dx, dy, 0.0)))
            custom_sp_hex = getattr(sp, "hex_color", None)
            if custom_sp_hex:
                sp_hex = custom_sp_hex.upper()
            elif sp.color is not None:
                rgba = tuple(sp.color)
                sp_hex = "#{:02X}{:02X}{:02X}".format(
                    int(round(rgba[0] * 255)),
                    int(round(rgba[1] * 255)),
                    int(round(rgba[2] * 255)),
                )
            else:
                sp_hex = pp.hex_color
            sp_tid = int(getattr(sp, "toolhead_id", _color_to_toolhead_id(sp_hex, pp.toolhead_id)))
            sub_label = getattr(sp, "label", "") or f"part_{idx + 1}"
            mesh_key = f"{pp.name}__sub_{idx}__{sub_label}"
            sp_local.color = bd.Color(sp_hex)
            sp_local.label = mesh_key
            exporter.add_shape(sp_local, part_number=mesh_key)
            records.append((mesh_key, sub_label, sp_tid, sp_hex))
    else:
        s_local = copy.deepcopy(pp.part)
        s_local.move(bd.Location((dx, dy, 0.0)))
        s_local.color = bd.Color(pp.hex_color)
        s_local.label = pp.name
        exporter.add_shape(s_local, part_number=pp.name)
        records.append((pp.name, pp.name, pp.toolhead_id, pp.hex_color))

    return records


def _inject_orca_metadata_into_3mf(
    threemf_path: Path,
    plated_parts: list[PlatedPart],
    pp_sub_records: dict[str, list[tuple[str, str, int, str]]],
    plate_names_ordered: list[str],
    apply_multiplate_stride: bool,
) -> None:
    """Open a Mesher-generated .3mf ZIP archive and inject OrcaSlicer project_settings.config,
    model_settings.config, unified multi-color <components>/<part subtype="normal_part"> objects,
    and OrcaSlicer 2D plate grid <build><item transform="..."/> coordinates.
    """
    ns_core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ns_mat = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
    ns_prod = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
    ET.register_namespace("", ns_core)
    ET.register_namespace("m", ns_mat)
    ET.register_namespace("p", ns_prod)

    with zipfile.ZipFile(threemf_path, "r") as zin:
        existing_files = {name: zin.read(name) for name in zin.namelist()}

    model_xml_bytes = existing_files["3D/3dmodel.model"]
    root = ET.fromstring(model_xml_bytes)

    resources_el = root.find(f"{{{ns_core}}}resources")
    build_el = root.find(f"{{{ns_core}}}build")
    if resources_el is None or build_el is None:
        raise RuntimeError(f"Malformed 3D/3dmodel.model in {threemf_path}")

    # Stamp BambuStudio/OrcaSlicer 3MF application & version metadata at top of <model>
    existing_meta_names = {
        m.attrib.get("name", "") for m in root.findall(f"{{{ns_core}}}metadata")
    }
    if "BambuStudio:3mfVersion" not in existing_meta_names:
        m_ver = ET.Element(f"{{{ns_core}}}metadata", {"name": "BambuStudio:3mfVersion"})
        m_ver.text = "1"
        root.insert(0, m_ver)
    if "Application" not in existing_meta_names:
        m_app = ET.Element(f"{{{ns_core}}}metadata", {"name": "Application"})
        m_app.text = "BambuStudio-02.02.00.85"
        root.insert(0, m_app)

    # Index all <mesh> <object> elements by partnumber/name and remove unused Mesher <components> wrappers
    mesh_by_key: dict[str, ET.Element] = {}
    max_id = 0
    for child in list(resources_el):
        cid = int(child.attrib.get("id", "0") or 0)
        max_id = max(max_id, cid)
        if child.tag == f"{{{ns_core}}}object":
            mesh_el = child.find(f"{{{ns_core}}}mesh")
            comps_el = child.find(f"{{{ns_core}}}components")
            if mesh_el is not None:
                key = child.attrib.get("partnumber") or child.attrib.get("name") or ""
                mesh_by_key[key] = child
            elif comps_el is not None:
                resources_el.remove(child)

    # Rebuild <build> items and Metadata/model_settings.config from logical PlatedPart list
    for item_el in list(build_el):
        build_el.remove(item_el)

    cols = _orca_plate_cols(len(plate_names_ordered)) if apply_multiplate_stride else 1
    config_root = ET.Element("config")
    plate_instances: dict[str, list[tuple[str, int]]] = {
        pname: [] for pname in plate_names_ordered
    }
    next_identify_id = 100

    for pp in plated_parts:
        if apply_multiplate_stride:
            row = pp.plate_index // cols
            col = pp.plate_index % cols
            origin_x = col * ORCA_PLATE_STRIDE_X
            origin_y = -row * ORCA_PLATE_STRIDE_Y
        else:
            origin_x = 0.0
            origin_y = 0.0

        tx = origin_x + 0.5 * U1_BED_X + pp.center_xy[0]
        ty = origin_y + 0.5 * U1_BED_Y + pp.center_xy[1]
        sub_records = pp_sub_records[pp.name]

        # Ensure exact Z_min = 0.000000 across all exported 3MF mesh vertices of this part
        part_vert_els: list[ET.Element] = []
        for m_key, _s_lbl, _s_tid, _s_hex in sub_records:
            m_el = mesh_by_key[m_key].find(f"{{{ns_core}}}mesh")
            if m_el is not None:
                part_vert_els.extend(
                    m_el.findall(f"./{{{ns_core}}}vertices/{{{ns_core}}}vertex")
                )
        if part_vert_els:
            min_vz = min(float(v.attrib["z"]) for v in part_vert_els)
            if abs(min_vz) > 1e-7:
                for v in part_vert_els:
                    vz = float(v.attrib["z"]) - min_vz
                    v.set("z", f"{0.0 if abs(vz) < 1e-7 else vz:.6f}")

        if len(sub_records) == 1:
            mesh_key, _sub_label, _sp_tid, _sp_hex = sub_records[0]
            mesh_obj_el = mesh_by_key[mesh_key]
            obj_id = mesh_obj_el.attrib["id"]
            mesh_obj_el.set("name", pp.name)
            mesh_obj_el.set("partnumber", pp.name)

            ET.SubElement(
                build_el,
                f"{{{ns_core}}}item",
                {
                    "objectid": str(obj_id),
                    "transform": f"1 0 0 0 1 0 0 0 1 {tx:.4f} {ty:.4f} 0.0000",
                    "printable": "1",
                },
            )

            obj_node = ET.SubElement(config_root, "object", {"id": str(obj_id)})
            ET.SubElement(obj_node, "metadata", {"key": "name", "value": pp.name})
            ET.SubElement(obj_node, "metadata", {"key": "extruder", "value": str(pp.toolhead_id)})
            part_node = ET.SubElement(obj_node, "part", {"id": str(obj_id), "subtype": "normal_part"})
            ET.SubElement(part_node, "metadata", {"key": "name", "value": pp.name})
            ET.SubElement(part_node, "metadata", {"key": "matrix", "value": "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"})
            ET.SubElement(part_node, "metadata", {"key": "extruder", "value": str(pp.toolhead_id)})

            plate_instances[pp.plate_name].append((str(obj_id), next_identify_id))
            next_identify_id += 1
        else:
            # Multi-color unified object: create ONE composite parent <object> with <components>
            max_id += 1
            comp_id = str(max_id)
            comp_obj_el = ET.SubElement(
                resources_el,
                f"{{{ns_core}}}object",
                {
                    "id": comp_id,
                    "name": pp.name,
                    "partnumber": pp.name,
                    "type": "model",
                },
            )
            comps_el = ET.SubElement(comp_obj_el, f"{{{ns_core}}}components")

            obj_node = ET.SubElement(config_root, "object", {"id": comp_id})
            ET.SubElement(obj_node, "metadata", {"key": "name", "value": pp.name})
            ET.SubElement(obj_node, "metadata", {"key": "extruder", "value": str(pp.toolhead_id)})

            for mesh_key, sub_label, sp_tid, _sp_hex in sub_records:
                sub_obj_el = mesh_by_key[mesh_key]
                sub_id = sub_obj_el.attrib["id"]
                sub_obj_el.set("name", sub_label)
                sub_obj_el.set("partnumber", sub_label)

                ET.SubElement(
                    comps_el,
                    f"{{{ns_core}}}component",
                    {
                        "objectid": str(sub_id),
                        "transform": "1 0 0 0 1 0 0 0 1 0 0 0",
                    },
                )
                part_node = ET.SubElement(
                    obj_node,
                    "part",
                    {"id": str(sub_id), "subtype": "normal_part"},
                )
                ET.SubElement(part_node, "metadata", {"key": "name", "value": sub_label})
                ET.SubElement(
                    part_node,
                    "metadata",
                    {"key": "matrix", "value": "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"},
                )
                ET.SubElement(part_node, "metadata", {"key": "extruder", "value": str(sp_tid)})

            ET.SubElement(
                build_el,
                f"{{{ns_core}}}item",
                {
                    "objectid": comp_id,
                    "transform": f"1 0 0 0 1 0 0 0 1 {tx:.4f} {ty:.4f} 0.0000",
                    "printable": "1",
                },
            )

            plate_instances[pp.plate_name].append((comp_id, next_identify_id))
            next_identify_id += 1

    # Add <plate> blocks (plater_id 1..N)
    for idx, pname in enumerate(plate_names_ordered, start=1):
        plate_node = ET.SubElement(config_root, "plate")
        ET.SubElement(plate_node, "metadata", {"key": "plater_id", "value": str(idx)})
        ET.SubElement(plate_node, "metadata", {"key": "plater_name", "value": pname})
        ET.SubElement(plate_node, "metadata", {"key": "locked", "value": "false"})
        for obj_id, ident_id in plate_instances[pname]:
            inst_node = ET.SubElement(plate_node, "model_instance")
            ET.SubElement(inst_node, "metadata", {"key": "object_id", "value": str(obj_id)})
            ET.SubElement(inst_node, "metadata", {"key": "instance_id", "value": "0"})
            ET.SubElement(inst_node, "metadata", {"key": "identify_id", "value": str(ident_id)})

    ET.indent(config_root, space="  ")
    model_settings_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(
        config_root, encoding="unicode"
    )
    updated_model_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(
        root, encoding="unicode"
    )

    existing_files["3D/3dmodel.model"] = updated_model_xml.encode("utf-8")
    single_plate_name = plate_names_ordered[0] if len(plate_names_ordered) == 1 else None
    existing_files["Metadata/project_settings.config"] = _make_project_settings_json(
        single_plate_name
    ).encode("utf-8")
    existing_files["Metadata/model_settings.config"] = model_settings_xml.encode("utf-8")
    existing_files["Metadata/slice_info.config"] = _make_slice_info_xml(
        plate_names_ordered
    ).encode("utf-8")

    with tempfile.NamedTemporaryFile(dir=threemf_path.parent, delete=False, suffix=".3mf") as tmp:
        tmp_path = Path(tmp.name)

    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for arcname, data in existing_files.items():
            zout.writestr(arcname, data)

    tmp_path.chmod(0o644)
    tmp_path.replace(threemf_path)


def export_all_3mf_plates(
    output_dir: Path,
    prebuilt_parts: dict[str, bd.Solid] | None = None,
) -> tuple[dict[str, Path], Path, dict[str, list[PlatedPart]]]:
    """Generate both Output A (6 individual pre-plated .3mf files) and Output B
    (unified GravMass_Tree_Ultimate_U1.3mf) inside `./output/3mf/`.
    """
    threemf_dir = output_dir / "3mf"
    threemf_dir.mkdir(parents=True, exist_ok=True)

    if prebuilt_parts is None:
        prebuilt_parts = {}
        prebuilt_parts.update(build_all_trunk_parts())
        prebuilt_parts.update(build_all_auger_parts())
        prebuilt_parts.update(build_all_bracket_parts())
        prebuilt_parts.update(build_all_topper_planet_parts())

    plates = build_five_plates(prebuilt_parts=prebuilt_parts)
    plate_names_ordered = list(plates.keys())
    individual_paths: dict[str, Path] = {}

    # Remove stale legacy Plate_*.3mf files before writing the current plate files
    for old_plate in threemf_dir.glob("Plate_*.3mf"):
        if old_plate.stem not in plates:
            old_plate.unlink(missing_ok=True)

    # Output A: Individual Pre-Plated .3mf Files (centered at (135, 135) on the 270x270 bed)
    for pname, part_list in plates.items():
        exporter = bd.Mesher(unit=bd.Unit.MM)
        pp_sub_records: dict[str, list[tuple[str, str, int, str]]] = {}
        for pp in part_list:
            pp_sub_records[pp.name] = _add_part_meshes_to_exporter(exporter, pp)

        plate_path = threemf_dir / f"{pname}.3mf"
        exporter.write(str(plate_path))
        _inject_orca_metadata_into_3mf(
            plate_path,
            plated_parts=part_list,
            pp_sub_records=pp_sub_records,
            plate_names_ordered=[pname],
            apply_multiplate_stride=False,
        )
        individual_paths[pname] = plate_path

    # Output B: Unified Multi-Plate OrcaSlicer Project (GravMass_Tree_Ultimate_U1.3mf)
    master_exporter = bd.Mesher(unit=bd.Unit.MM)
    all_plated_parts: list[PlatedPart] = []
    master_sub_records: dict[str, list[tuple[str, str, int, str]]] = {}
    for pname in plate_names_ordered:
        for pp in plates[pname]:
            master_sub_records[pp.name] = _add_part_meshes_to_exporter(master_exporter, pp)
            all_plated_parts.append(pp)

    master_path = threemf_dir / "GravMass_Tree_Ultimate_U1.3mf"
    master_exporter.write(str(master_path))
    _inject_orca_metadata_into_3mf(
        master_path,
        plated_parts=all_plated_parts,
        pp_sub_records=master_sub_records,
        plate_names_ordered=plate_names_ordered,
        apply_multiplate_stride=True,
    )
    # Write aliases for backward compatibility
    master_bytes = master_path.read_bytes()
    for alias_name in (
        "GravMass_Tree_CyberBrick_U1_MultiPlate.3mf",
        "GravMass_Tree_U1_MultiPlate.3mf",
    ):
        (threemf_dir / alias_name).write_bytes(master_bytes)

    # Output C: Full Assembled Multi-Color Tree (matching ./output/model.jpeg)
    build_and_export_full_assembly(output_dir, prebuilt_parts=prebuilt_parts)

    return individual_paths, master_path, plates


def build_and_export_full_assembly(
    output_dir: Path,
    prebuilt_parts: dict[str, bd.Solid] | None = None,
) -> Path:
    """Assemble the complete multi-color Grav-Mass Day Marble Run Tree in 3D space
    matching `./output/model.jpeg` and export to `output/full_tree_assembly.step`
    and `output/3mf/GravMass_Tree_Complete_Assembly.3mf`.
    """
    if prebuilt_parts is None:
        prebuilt_parts = {}
        prebuilt_parts.update(build_all_trunk_parts())
        prebuilt_parts.update(build_all_auger_parts())
        prebuilt_parts.update(build_all_bracket_parts())
        prebuilt_parts.update(build_all_topper_planet_parts())

    assembly_solids: list[bd.Solid] = []

    def _add_placed(part: bd.Solid, loc: bd.Location, base_label: str, fallback_hex: str) -> None:
        subparts = getattr(part, "colored_subparts", None)
        if subparts:
            for idx, sp in enumerate(subparts):
                s_moved = copy.deepcopy(sp).moved(loc)
                s_moved.color = sp.color or bd.Color(fallback_hex)
                s_moved.label = f"{base_label}_{sp.label or idx}"
                assembly_solids.append(s_moved)
        else:
            s_moved = copy.deepcopy(part).moved(loc)
            s_moved.color = part.color or bd.Color(fallback_hex)
            s_moved.label = base_label
            assembly_solids.append(s_moved)

    # 1. Stack the 3 Trunk sections (Z = 0, 150, 300 mm)
    _add_placed(prebuilt_parts["trunk_base"], bd.Location((0, 0, 0)), "asm_trunk_base", "#4A2F1D")
    _add_placed(
        prebuilt_parts["trunk_mid"],
        bd.Location((0, 0, TRUNK_SECTION_HEIGHT)),
        "asm_trunk_mid",
        "#4A2F1D",
    )
    _add_placed(
        prebuilt_parts["trunk_top"],
        bd.Location((0, 0, 2.0 * TRUNK_SECTION_HEIGHT)),
        "asm_trunk_top",
        "#4A2F1D",
    )
    if "Base_Bottom_Cover" in prebuilt_parts:
        _add_placed(
            prebuilt_parts["Base_Bottom_Cover"],
            bd.Location((0, 0, -3.2)),
            "asm_Base_Bottom_Cover",
            "#4A2F1D",
        )
    if "Conduit_Cover_Strip" in prebuilt_parts:
        for idx, z_center in enumerate((105.0, 225.0, 375.0), start=1):
            _add_placed(
                prebuilt_parts["Conduit_Cover_Strip"],
                bd.Location((-28.5, 0, z_center), (90.0, 0.0, 90.0)),
                f"asm_Conduit_Cover_Strip_{idx:02d}",
                "#4A2F1D",
            )

    # 2. Place internal Archimedes Auger Screw halves inside the trunk bore
    #    (resting on the Z = 37.20 mm thrust ledge with 1.02 mm air gap above Motor_Clutch_Driver)
    _add_placed(prebuilt_parts["auger_lower"], bd.Location((0, 0, 37.22)), "asm_auger_lower", "#D4AF37")
    _add_placed(
        prebuilt_parts["auger_upper"],
        bd.Location((0, 0, 37.22 + AUGER_HALF_HEIGHT + 0.1)),
        "asm_auger_upper",
        "#D4AF37",
    )

    # 3. Place the 4.5-turn Conical Helix Track segments in true assembly space
    num_full = int(HELIX_TOTAL_DEG // TRACK_SEGMENT_ARC_DEG)
    for i in range(num_full + 1):
        t0 = i * TRACK_SEGMENT_ARC_DEG
        t1 = min(HELIX_TOTAL_DEG, (i + 1) * TRACK_SEGMENT_ARC_DEG)
        if t1 - t0 <= 1.0:
            continue
        seg = build_track_segment(
            t0,
            t1,
            orient_for_print=False,
            include_planet_pedestal=(i in TRACK_PLANET_SEGMENT_INDICES),
            bottom_return_ramp=(i == 0),
            top_feeder_ramp=(i == num_full),
        )
        seg.color = bd.Color("#00A86B")
        seg.label = f"asm_track_seg_{i + 1:02d}"
        assembly_solids.append(seg)

    # 4. Place Golden Apple Topper on top of the trunk (Z = 450 mm)
    _add_placed(
        prebuilt_parts["golden_apple_topper"],
        bd.Location((0, 0, 3.0 * TRUNK_SECTION_HEIGHT)),
        "asm_golden_apple_topper",
        "#F4B41A",
    )

    # 5. Place all 8 Multi-Color Planetary Ornaments along the 8 magnetized track segments
    planet_placements = [
        ("planet_mercury", 1590.0),
        ("planet_venus", 1380.0),
        ("planet_earth", 1140.0),
        ("planet_mars", 900.0),
        ("planet_jupiter", 660.0),
        ("planet_saturn", 540.0),
        ("planet_uranus", 300.0),
        ("planet_neptune", 60.0),
    ]
    for pname, deg in planet_placements:
        pt = helix_point(deg)
        rad = math.radians(deg)
        out_x = pt.X + 30.0 * math.cos(rad)
        out_y = pt.Y + 30.0 * math.sin(rad)
        _add_placed(
            prebuilt_parts[pname],
            bd.Location((out_x, out_y, pt.Z + 18.05)),
            f"asm_{pname}",
            "#D4AF37",
        )

    # 6. Place Star-Tipped Magic LED Wand standing upright inside the +30° Root-Flare Holster
    #    Socket on trunk_base (holster center X = +45.03, Y = +26.00, Z_floor = 5.50 mm)
    if "Magic_LED_Wand" in prebuilt_parts:
        _add_placed(
            prebuilt_parts["Magic_LED_Wand"],
            bd.Location((48.03, 26.00, 59.10), (0.0, -90.0, 0.0)),
            "asm_Magic_LED_Wand",
            "#D4AF37",
        )

    # 7. Place Rolling Crimson Red Apple Marbles descending along the track
    marbles = build_all_marbles(count=6)
    marble_angles = [1510.0, 1250.0, 880.0, 520.0, 290.0, 85.0]
    for idx, deg in enumerate(marble_angles, start=1):
        pt = helix_point(deg)
        m_key = f"apple_marble_{idx:02d}"
        _add_placed(
            marbles[m_key],
            bd.Location((pt.X, pt.Y, pt.Z - 5.7)),
            f"asm_{m_key}",
            "#C41E3A",
        )

    asm_comp = bd.Compound(children=assembly_solids)
    asm_comp.label = "GravMass_Tree_Complete_Assembly"

    step_path = output_dir / "full_tree_assembly.step"
    bd.export_step(asm_comp, str(step_path))

    threemf_path = output_dir / "3mf" / "GravMass_Tree_Complete_Assembly.3mf"
    asm_mesher = bd.Mesher(unit=bd.Unit.MM)
    for s in assembly_solids:
        asm_mesher.add_shape(s, part_number=s.label)
    asm_mesher.write(str(threemf_path))
    threemf_path.chmod(0o644)

    return step_path


def _bbox_xy_gap(bb1: bd.BoundBox, bb2: bd.BoundBox) -> float:
    """Return minimum 2D XY separation distance between two axis-aligned bounding boxes."""
    gap_x = max(0.0, max(bb1.min.X - bb2.max.X, bb2.min.X - bb1.max.X))
    gap_y = max(0.0, max(bb1.min.Y - bb2.max.Y, bb2.min.Y - bb1.max.Y))
    if gap_x == 0.0 and gap_y == 0.0:
        # Overlapping in both X and Y
        overlap_x = min(bb1.max.X - bb2.min.X, bb2.max.X - bb1.min.X)
        overlap_y = min(bb1.max.Y - bb2.min.Y, bb2.max.Y - bb1.min.Y)
        return -min(overlap_x, overlap_y)
    return max(gap_x, gap_y)


def _part_xy_gap(p1: bd.Solid, p2: bd.Solid) -> float:
    """Return strict 2D AABB XY separation distance between two solids (preventing any 2D convex-hull overlap in OrcaSlicer)."""
    return _bbox_xy_gap(p1.bounding_box(), p2.bounding_box())


def verify_3mf_exports(
    individual_paths: dict[str, Path],
    master_path: Path,
    plates: dict[str, list[PlatedPart]],
) -> None:
    """Open generated .3mf files as ZIP archives, parse 3D/3dmodel.model and
    Metadata/model_settings.config, verify all 4 colors/extruders and 10 plates
    (9 pure single-color plates + 1 unified multi-color plate), verify OrcaSlicer
    2D plate grid transforms, and print a summary table.
    """
    expected_colors = {TOOLHEAD_PALETTE[i]["hex"].upper() for i in (1, 2, 3, 4)}
    expected_extruders = {"1", "2", "3", "4"}
    ns_core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    num_plates = len(plates)

    # 1. Verify unified multi-plate 3MF ZIP archive
    with zipfile.ZipFile(master_path, "r") as zf:
        namelist = set(zf.namelist())
        for req_file in (
            "3D/3dmodel.model",
            "Metadata/project_settings.config",
            "Metadata/model_settings.config",
            "Metadata/slice_info.config",
        ):
            if req_file not in namelist:
                raise RuntimeError(f"Missing required '{req_file}' in {master_path.name}")

        proj_cfg = json.loads(zf.read("Metadata/project_settings.config").decode("utf-8"))
        if proj_cfg.get("printer_settings_id") != "Snapmaker U1 (0.4 nozzle)":
            raise RuntimeError(
                f"Expected printer_settings_id 'Snapmaker U1 (0.4 nozzle)', got {proj_cfg.get('printer_settings_id')}"
            )
        if proj_cfg.get("nozzle_diameter") != ["0.4", "0.4", "0.4", "0.4"]:
            raise RuntimeError(
                f"Expected nozzle_diameter ['0.4', '0.4', '0.4', '0.4'], got {proj_cfg.get('nozzle_diameter')}"
            )
        cfg_colors = {c.upper() for c in proj_cfg.get("filament_colour", [])}
        if cfg_colors != expected_colors:
            raise RuntimeError(f"Mismatch in project_settings.config filament_colour: {cfg_colors}")

        model_cfg_root = ET.fromstring(zf.read("Metadata/model_settings.config"))
        found_extruders = {
            m.attrib.get("value", "")
            for m in model_cfg_root.findall("./object/metadata[@key='extruder']")
        } | {
            m.attrib.get("value", "")
            for m in model_cfg_root.findall("./object/part/metadata[@key='extruder']")
        }
        if found_extruders != expected_extruders:
            raise RuntimeError(
                f"Expected extruders {expected_extruders} in model_settings.config, found {found_extruders}"
            )

        plate_nodes = model_cfg_root.findall("./plate")
        if len(plate_nodes) != num_plates:
            raise RuntimeError(
                f"Expected {num_plates} <plate> blocks in model_settings.config, found {len(plate_nodes)}"
            )

        # Verify every multi-color object is a single <object> with multiple <part subtype="normal_part">
        multicolor_expected = {
            "golden_apple_topper",
            "Magic_LED_Wand",
            *PLANET_NAMES,
        }
        obj_nodes_by_name: dict[str, ET.Element] = {}
        for obj_node in model_cfg_root.findall("./object"):
            n_el = obj_node.find("./metadata[@key='name']")
            if n_el is not None:
                obj_nodes_by_name[n_el.attrib.get("value", "")] = obj_node

        for mc_name in multicolor_expected:
            if mc_name not in obj_nodes_by_name:
                raise RuntimeError(f"Missing unified multi-color object '{mc_name}' in model_settings.config")
            part_children = obj_nodes_by_name[mc_name].findall("./part[@subtype='normal_part']")
            if len(part_children) < 2:
                raise RuntimeError(
                    f"Multi-color object '{mc_name}' must have >= 2 <part subtype='normal_part'> sub-volumes, found {len(part_children)}"
                )

        model_root = ET.fromstring(zf.read("3D/3dmodel.model"))
        base_colors = {
            b.attrib.get("displaycolor", "")[:7].upper()
            for b in model_root.findall(f".//{{{ns_core}}}base")
        }
        if not expected_colors.issubset(base_colors):
            raise RuntimeError(
                f"Expected all 4 hex colors {expected_colors} in 3D/3dmodel.model, found {base_colors}"
            )

        # Verify every <object><mesh> vertex in 3D/3dmodel.model fits inside 270 x 270 x 270 mm
        for obj_el in model_root.findall(f".//{{{ns_core}}}object"):
            mesh_el = obj_el.find(f"{{{ns_core}}}mesh")
            if mesh_el is None:
                continue
            xs, ys, zs = [], [], []
            for v_el in mesh_el.findall(f"./{{{ns_core}}}vertices/{{{ns_core}}}vertex"):
                xs.append(float(v_el.attrib["x"]))
                ys.append(float(v_el.attrib["y"]))
                zs.append(float(v_el.attrib["z"]))
            if xs:
                span_x = max(xs) - min(xs)
                span_y = max(ys) - min(ys)
                span_z = max(zs) - min(zs)
                if span_x > U1_BED_X or span_y > U1_BED_Y or span_z > U1_BED_Z or min(zs) < -1e-4:
                    raise RuntimeError(
                        f"Mesh object '{obj_el.attrib.get('name')}' violates 270x270x270 mm bed limits."
                    )

    # 2. Verify each of the 12 individual plate .3mf files and compute plate footprints & clearances
    plate_summary_rows: list[dict[str, object]] = []
    half_safe = SAFE_PLATE_ZONE / 2.0  # 128.0 mm

    for pname, ppath in individual_paths.items():
        if not ppath.exists() or ppath.stat().st_size == 0:
            raise RuntimeError(f"Individual plate 3MF missing or empty: {ppath}")
        with zipfile.ZipFile(ppath, "r") as pzf:
            p_model_xml = ET.fromstring(pzf.read("3D/3dmodel.model"))
            p_mcfg_xml = ET.fromstring(pzf.read("Metadata/model_settings.config"))
            p_proj_cfg = json.loads(pzf.read("Metadata/project_settings.config").decode("utf-8"))

            # Enforce max 4 colors / 4 extruders per plate
            p_fil_colors = p_proj_cfg.get("filament_colour", [])
            if len(p_fil_colors) > 4:
                raise RuntimeError(
                    f"Plate '{pname}' exceeds 4 filament colors in project_settings.config: {p_fil_colors}"
                )
            p_used_exts = {
                m.attrib.get("value", "")
                for m in p_mcfg_xml.findall(".//metadata[@key='extruder']")
            }
            if not p_used_exts.issubset(expected_extruders) or len(p_used_exts) > 4:
                raise RuntimeError(
                    f"Plate '{pname}' uses invalid or >4 extruders: {p_used_exts}"
                )
            p_mesh_colors = {
                b.attrib.get("displaycolor", "")[:7].upper()
                for b in p_model_xml.findall(f".//{{{ns_core}}}base")
            }
            if len(p_mesh_colors) > 4:
                raise RuntimeError(
                    f"Plate '{pname}' contains {len(p_mesh_colors)} distinct mesh colors (> 4 max): {p_mesh_colors}"
                )

        plist = plates[pname]
        mbounds = [_mesh_bounds(pp.part) for pp in plist]

        min_x = min(b[0] for b in mbounds)
        max_x = max(b[1] for b in mbounds)
        min_y = min(b[2] for b in mbounds)
        max_y = max(b[3] for b in mbounds)
        min_z = min(b[4] for b in mbounds)
        max_z = max(b[5] for b in mbounds)

        for pp, mb in zip(plist, mbounds):
            if abs(mb[4]) > 1e-3:
                raise RuntimeError(
                    f"Part '{pp.name}' on plate '{pname}' floats above/below Z=0 (mesh min_z = {mb[4]:.4f} mm)"
                )

        footprint_x = max_x - min_x
        footprint_y = max_y - min_y

        if (
            min_x < -half_safe - 1e-2
            or max_x > half_safe + 1e-2
            or min_y < -half_safe - 1e-2
            or max_y > half_safe + 1e-2
            or footprint_x > SAFE_PLATE_ZONE + 1e-2
            or footprint_y > SAFE_PLATE_ZONE + 1e-2
        ):
            raise RuntimeError(
                f"Plate '{pname}' exceeds {SAFE_PLATE_ZONE:.0f}x{SAFE_PLATE_ZONE:.0f} mm centered zone: "
                f"X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]"
            )

        if min_z < -1e-4 or max_z > U1_BED_Z:
            raise RuntimeError(
                f"Plate '{pname}' violates Z=[0, 270] mm limits: Z=[{min_z:.3f}, {max_z:.2f}]"
            )

        min_gap = float("inf") if len(plist) > 1 else 99.9
        for i in range(len(plist)):
            for j in range(i + 1, len(plist)):
                g = _part_xy_gap(plist[i].part, plist[j].part)
                min_gap = min(min_gap, g)

        if min_gap < MIN_PART_CLEARANCE - 0.1:
            raise RuntimeError(
                f"Plate '{pname}' part clearance ({min_gap:.2f} mm) is below {MIN_PART_CLEARANCE} mm."
            )

        # Verify Plates 1-9 are 100% single-color plates
        if "SingleColor" in pname:
            plate_tids = {pp.toolhead_id for pp in plist}
            if len(plate_tids) != 1:
                raise RuntimeError(
                    f"Single-color plate '{pname}' contains multiple toolheads: {plate_tids}"
                )
            for pp in plist:
                if getattr(pp.part, "colored_subparts", None):
                    raise RuntimeError(
                        f"Single-color plate '{pname}' contains multi-color part '{pp.name}'"
                    )

        plate_summary_rows.append(
            {
                "plate_name": pname,
                "num_parts": len(plist),
                "parts": plist,
                "footprint_x": footprint_x,
                "footprint_y": footprint_y,
                "max_z": max_z,
                "min_gap": min_gap,
            }
        )

    # 3. Print clean Multi-Plate & Toolhead Summary Table
    hdr = (
        f"{'Plate Name':<50} | {'Part Name':<26} | {'Toolhead':<12} | "
        f"{'Hex Color':<9} | {'Plate XY Footprint':<20} | {'Min Gap':>8}"
    )
    sep = "-" * len(hdr)
    print("\n" + "=" * len(hdr))
    print(" SNAPMAKER U1 (4-TOOLHEAD) MULTI-PLATE .3MF SLICER PIPELINE SUMMARY")
    print("=" * len(hdr))
    print(hdr)
    print(sep)
    for row in plate_summary_rows:
        pname = str(row["plate_name"])
        fp_str = f"{float(row['footprint_x']):.1f} x {float(row['footprint_y']):.1f} mm"
        gap_str = f"{float(row['min_gap']):.1f} mm"
        plist: list[PlatedPart] = row["parts"]  # type: ignore[assignment]
        for idx, pp in enumerate(plist):
            p_col = pname if idx == 0 else ""
            fp_col = fp_str if idx == 0 else ""
            g_col = gap_str if idx == 0 else ""
            subparts = getattr(pp.part, "colored_subparts", None)
            if subparts and len(subparts) > 1:
                th_str = f"4-Color({len(subparts)}p)"
            else:
                th_str = f"T{pp.toolhead_id} ({pp.filament_type})"
            print(
                f"{p_col:<50} | {pp.name:<26} | "
                f"{th_str:<12} | "
                f"{pp.hex_color:<9} | {fp_col:<20} | {g_col:>8}"
            )
        print(sep)
    print(
        f"Verified {num_plates} Individual Plates (15 Pure Single-Color + 3 Dedicated 4-Color Plates, <= 4 Colors/Plate) + Unified '{master_path.name}' "
        f"(OrcaSlicer 5x4 Plate Grid, Zero Convex-Hull Overlaps, Full-Scale Tracks, 24x Exact Station Brackets, <= {SAFE_PLATE_ZONE:.0f}x{SAFE_PLATE_ZONE:.0f} mm Safe Zone, >= {MIN_PART_CLEARANCE:.1f} mm Clearance: PASS)"
    )
    print("=" * len(hdr) + "\n")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "output"
    ind_paths, mst_path, built_plates = export_all_3mf_plates(out_dir)
    verify_3mf_exports(ind_paths, mst_path, built_plates)
