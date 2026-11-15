"""Printable Retrofit Keyhole Cutting Jig for Pre-Fix Trunk Base (cad/retrofit_jig.py).

Allows builders who have already printed `trunk_base` (stations 1..7 closed pockets) and
`bracket_01..24` from pre-fix files to open the 7 closed dovetail roofs into keyhole
drop-in entry windows without reprinting `trunk_base` or any brackets.

Geometry (local frame relative to socket origin at R = TRUNK_OUTER_R = 34.0 mm, Z_slot = 0):
  - Cylindrical C-saddle inner radius R_in = 34.25 mm (+0.25 mm clearance over smooth column),
    outer radius R_out = 42.25 mm (8.00 mm collar wall thickness -> total 12.85 mm depth stop
    from jig outer surface to 4.85 mm entry-window floor), spanning +/-42 deg, Z = 0.5..43.0 mm
    (resting flat on Z = 0.00 mm bed offset by -0.5 mm).
  - Self-registering registration tooth (6.0 mm wide x 3.2 mm radial inward depth at Z = 3.5..16.5 mm
    with 45-deg support-free lower ramp Z = 0.5..3.7 mm) drops directly into the existing 6.2..7.0 mm
    dovetail mouth to lock both vertical height and angular alignment.
  - Hardened guide window (16.60 mm wide x 18.80 mm tall at Z = 18.0..36.8 mm, topped by a 45-deg
    support-free arch up to Z = 42.3 mm) guides a 1/8" (3.2 mm) rotary burr / drill bit + chisel/file.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import build123d as bd

CAD_DIR = Path(__file__).resolve().parent
ROOT_DIR = CAD_DIR.parent
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))

from common_params import (
    DOVETAIL_ENTRY_DEPTH,
    DOVETAIL_ENTRY_H,
    DOVETAIL_ENTRY_W,
    DOVETAIL_SLOT_H,
    TRUNK_OUTER_R,
    assign_toolhead,
)


def build_trunk_keyhole_cutting_jig() -> bd.Solid:
    """Build the snap-on Keyhole Cutting Jig (flat on Z = 0.00 mm, support-free) with
    full 18.8 mm vertical guide window + 2.4 mm solid top arch band.

    Jig base rests at Z_slot + 1.50 mm (so it clears trunk_base's Z <= 46.5 mm root/dorsal flare
    at station k=1).
    """
    r_in = TRUNK_OUTER_R + 0.25   # 34.25 mm
    wall_t = 8.00
    r_out = r_in + wall_t         # 42.25 mm
    z_offset = 1.50               # Jig Z = 0 corresponds to Z_slot + 1.50 mm
    win_hw = (DOVETAIL_ENTRY_W + 0.40) / 2.0   # 8.30 mm (16.60 mm wide)
    win_z0 = DOVETAIL_SLOT_H - z_offset        # 16.50 mm (aligns with Z_slot + 18.0 mm)
    win_z1 = win_z0 + DOVETAIL_ENTRY_H + 0.20  # 35.30 mm (aligns with Z_slot + 36.8 mm)
    peak_hw = 2.50                             # 5.00 mm apex (< 8 mm max bridge)
    roof_dz = win_hw - peak_hw                 # 5.80 mm -> closes at Z = 41.10 mm
    z_top = win_z1 + roof_dz + 2.40            # 43.50 mm (leaves 2.40 mm solid top rim)

    arc_half_deg = 28.0
    n_arc = 28

    def _arc_ring_wire(z_val: float) -> bd.Wire:
        pts: list[tuple[float, float, float]] = []
        for i in range(n_arc + 1):
            a = math.radians(-arc_half_deg + (2.0 * arc_half_deg * i) / n_arc)
            pts.append((r_out * math.cos(a), r_out * math.sin(a), z_val))
        for i in range(n_arc, -1, -1):
            a = math.radians(-arc_half_deg + (2.0 * arc_half_deg * i) / n_arc)
            pts.append((r_in * math.cos(a), r_in * math.sin(a), z_val))
        pts.append(pts[0])
        return bd.Wire([bd.Edge.make_line(pts[j], pts[j + 1]) for j in range(len(pts) - 1)])

    saddle = bd.Solid.make_loft([_arc_ring_wire(0.0), _arc_ring_wire(z_top)], ruled=True)

    # Registration tooth inside the lower dovetail mouth (Y in [-3.0, +3.0], Z_jig = 3.5..15.5 mm
    # -> Z_slot + 5.0..17.0 mm, reaching inward to R = 30.80 mm), with 45-deg lower support-free ramp
    x_tooth_in = TRUNK_OUTER_R - 3.20   # 30.80 mm
    x_tooth_out = r_in + 1.5
    tooth_hw = 3.00                     # 6.00 mm wide
    pts_tooth = [
        (x_tooth_out, 0.3),
        (r_in, 0.3),
        (x_tooth_in, 3.75),             # 45-deg lower support-free ramp
        (x_tooth_in, 15.5),
        (x_tooth_out, 15.5),
        (x_tooth_out, 0.3),
    ]
    t_wire = bd.Wire([bd.Edge.make_line(pts_tooth[i], pts_tooth[i + 1]) for i in range(5)])
    tooth = bd.extrude(bd.Plane.XZ * bd.Face(t_wire), amount=tooth_hw, both=True)
    jig = saddle + tooth

    win_cut = bd.Pos(0.5 * (r_in - 2.0 + r_out + 2.0), 0.0, win_z0) * bd.Box(
        wall_t + 6.0,
        2.0 * win_hw,
        win_z1 - win_z0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    def _cut_wire(z_val: float, hw: float) -> bd.Wire:
        pts = [(r_in - 2.0, -hw), (r_out + 2.0, -hw), (r_out + 2.0, hw), (r_in - 2.0, hw), (r_in - 2.0, -hw)]
        return bd.Pos(0.0, 0.0, z_val) * bd.Wire([bd.Edge.make_line(pts[i], pts[i + 1]) for i in range(4)])

    win_roof = bd.Solid.make_loft([_cut_wire(win_z1, win_hw), _cut_wire(win_z1 + roof_dz, peak_hw)], ruled=True)
    jig = jig - win_cut - win_roof
    return assign_toolhead(jig.solid(), "Trunk_Keyhole_Cutting_Jig", 1)


def export_cutting_jig() -> Path:
    out_dir = ROOT_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    jig = build_trunk_keyhole_cutting_jig()
    stl_path = out_dir / "Trunk_Keyhole_Cutting_Jig.stl"
    bd.export_stl(jig, str(stl_path), tolerance=0.01, angular_tolerance=0.1)
    step_path = out_dir / "Trunk_Keyhole_Cutting_Jig.step"
    bd.export_step(jig, str(step_path))
    return stl_path


if __name__ == "__main__":
    p = export_cutting_jig()
    jig = build_trunk_keyhole_cutting_jig()
    bb = jig.bounding_box()
    print(f"Exported {p} | valid={jig.is_valid}, manifold={jig.is_manifold}, bbox={bb.size}, minZ={bb.min.Z:.3f}")
