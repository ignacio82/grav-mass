"""Master Runner: Builds, Validates, and Exports All STEP/STL Files (cad/generate_all.py).

Usage:
    uv run --with build123d python3 cad/generate_all.py

Iterates over all generated modular parts for the Grav-Mass Day 'Falling Apple Cascade'
marble run tree:
  1. Verifies B-Rep validity (`part.is_valid is True`) and closed manifold topology.
  2. Confirms non-zero volume (`part.volume > 0`).
  3. Verifies compliance with the Snapmaker U1 build envelope (260 x 260 x 280 mm).
  4. Exports `output/<part_name>.step` and high-resolution `output/<part_name>.stl`
     (linear deflection tolerance = 0.01 mm).
  5. Prints a formatted engineering summary table.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure local cad/ directory is importable regardless of current working directory
CAD_DIR = Path(__file__).resolve().parent
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))

import build123d as bd

from auger import build_all_auger_parts
from brackets import build_all_24_station_brackets, build_all_bracket_parts
from common_params import MAX_BUILD_X, MAX_BUILD_Y, MAX_BUILD_Z
from export_3mf_plates import export_all_3mf_plates, verify_3mf_exports
from topper_planets import build_all_topper_planet_parts
from track import build_all_track_parts
from trunk import build_all_trunk_parts


def is_manifold_solid(part: bd.Shape) -> bool:
    """Verify that the shape is a valid, watertight manifold B-Rep solid."""
    if not part.is_valid or not part.is_manifold or part.volume <= 0.0:
        return False
    return len(part.solids()) == 1


def generate_and_export_all(output_dir: Path | None = None) -> list[dict[str, object]]:
    """Build, validate, and export all parts to STEP and high-tessellation STL."""
    if output_dir is None:
        output_dir = CAD_DIR.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    all_parts: dict[str, bd.Solid] = {}
    all_parts.update(build_all_trunk_parts())
    all_parts.update(build_all_auger_parts())
    all_parts.update(build_all_track_parts())
    all_parts.update(build_all_24_station_brackets())
    all_parts.update(build_all_topper_planet_parts())

    # Remove stale files for obsolete/unplated parts if present
    obsolete_parts = (
        "Hand_Crank_Handle",
        "Topper_Gate_Arm",
        "Track_Diverter_Flipper",
        "Track_Seg_07_Diverter",
        "Remote_Bottom_Shell",
        "Remote_Top_Faceplate",
        "apple_topper_stem_leaf",
        "Apple_Captive_Pause_Marble",
        "Track_Joint_Clip",
        "bracket_tier1_top",
        "bracket_tier2_upper_mid",
        "bracket_tier3_lower_mid",
        "bracket_tier4_bottom",
    )
    for obs in obsolete_parts:
        all_parts.pop(obs, None)
        for ext in (".step", ".stl"):
            obs_path = output_dir / f"{obs}{ext}"
            if obs_path.exists():
                obs_path.unlink()

    summary_rows: list[dict[str, object]] = []

    for part_name, part in all_parts.items():
        # 1. Verify B-Rep validity & non-zero volume
        if not part.is_valid:
            raise RuntimeError(f"Part '{part_name}' failed B-Rep validity check (is_valid=False).")
        if part.volume <= 0.0:
            raise RuntimeError(f"Part '{part_name}' has non-positive volume ({part.volume}).")

        manifold_ok = is_manifold_solid(part)
        if not manifold_ok:
            raise RuntimeError(f"Part '{part_name}' is not a single closed manifold solid.")

        # 2. Check bounding box against Snapmaker U1 build envelope (260 x 260 x 280 mm)
        bbox = part.bounding_box()
        dx, dy, dz = bbox.size.X, bbox.size.Y, bbox.size.Z
        fits_envelope = (
            dx <= MAX_BUILD_X + 1e-3
            and dy <= MAX_BUILD_Y + 1e-3
            and dz <= MAX_BUILD_Z + 1e-3
        )
        if not fits_envelope:
            raise RuntimeError(
                f"Part '{part_name}' exceeds Snapmaker U1 envelope "
                f"({dx:.2f} x {dy:.2f} x {dz:.2f} mm > {MAX_BUILD_X} x {MAX_BUILD_Y} x {MAX_BUILD_Z} mm)."
            )

        # 3. Export STEP (with multi-color sub-solids if present) and high-resolution STL (0.01 mm)
        step_path = output_dir / f"{part_name}.step"
        stl_path = output_dir / f"{part_name}.stl"

        subparts = getattr(part, "colored_subparts", None)
        if subparts:
            step_comp = bd.Compound(children=subparts)
            step_comp.label = part_name
            bd.export_step(step_comp, str(step_path))
        else:
            bd.export_step(part, str(step_path))
        bd.export_stl(part, str(stl_path), tolerance=0.01)

        if not step_path.exists() or step_path.stat().st_size == 0:
            raise RuntimeError(f"STEP export failed for '{part_name}'.")
        if not stl_path.exists() or stl_path.stat().st_size == 0:
            raise RuntimeError(f"STL export failed for '{part_name}'.")

        summary_rows.append(
            {
                "name": part_name,
                "dx": dx,
                "dy": dy,
                "dz": dz,
                "volume_cm3": part.volume / 1000.0,
                "is_valid": part.is_valid,
                "manifold": "MANIFOLD (OK)" if manifold_ok else "INVALID",
                "envelope": "PASS" if fits_envelope else "FAIL",
            }
        )

    elapsed = time.time() - t_start

    # 4. Print clean engineering summary table
    header = (
        f"{'Part Name':<26} | {'X (mm)':>8} | {'Y (mm)':>8} | {'Z (mm)':>8} | "
        f"{'Vol (cm³)':>10} | {'B-Rep Valid':>11} | {'Manifold Status':<15}"
    )
    sep = "-" * len(header)
    print("\n" + "=" * len(header))
    print(" GRAV-MASS DAY 'FALLING APPLE CASCADE' MARBLE RUN TREE — CAD BUILD SUMMARY")
    print("=" * len(header))
    print(header)
    print(sep)
    for r in summary_rows:
        print(
            f"{str(r['name']):<26} | "
            f"{float(r['dx']):>8.2f} | "
            f"{float(r['dy']):>8.2f} | "
            f"{float(r['dz']):>8.2f} | "
            f"{float(r['volume_cm3']):>10.2f} | "
            f"{str(r['is_valid']):>11} | "
            f"{str(r['manifold']):<15}"
        )
    print(sep)
    print(
        f"Total Parts Exported: {len(summary_rows)} (.step + .stl @ 0.01 mm deflection) "
        f"in {elapsed:.2f}s -> {output_dir}"
    )
    print("=" * len(header) + "\n")

    # 5. Export and verify Snapmaker U1 4-Toolhead 3MF build plates & unified project
    individual_paths, master_path, built_plates = export_all_3mf_plates(
        output_dir, prebuilt_parts=all_parts
    )
    verify_3mf_exports(individual_paths, master_path, built_plates)

    return summary_rows


if __name__ == "__main__":
    generate_and_export_all()
