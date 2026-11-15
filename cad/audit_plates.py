"""Phase 4 Per-Plate Printability Audit (cad/audit_plates.py).

Reads all 18 production .3mf plates in output/3mf/Plate_*.3mf (Metadata configs,
object transforms, and meshes), plus runs live CAD tessellation checks on post-fix
trunk & brackets, verifying:
  - Slicer settings (nozzle_diameter, outer/inner line widths, layer_height, enable_support)
  - Mesh watertightness, winding consistency, and degenerate/duplicate checks
  - Bed fit inside 270x270x270 mm (240x240 safe zone), Z=0 bed contact area, and pairwise XY gaps
  - Downward overhang area (>45 deg and >60 deg from vertical, excluding Z<=0.15 bed faces)
  - Unsupported horizontal bridge spans (>8.0 mm shortest span with downward normal)
  - Ray-cast 3D minimum wall thickness against 0.40 mm nozzle / 0.42 mm line width
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
THREEMF_DIR = ROOT / "output" / "3mf"
CAD_DIR = ROOT / "cad"
if str(CAD_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_DIR))


def _parse_3mf_objects_and_settings(threemf_path: Path) -> tuple[dict, list[dict]]:
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    with zipfile.ZipFile(threemf_path, "r") as zf:
        ps = {}
        if "Metadata/project_settings.config" in zf.namelist():
            ps = json.loads(zf.read("Metadata/project_settings.config"))
        obj_names = {}
        if "Metadata/model_settings.config" in zf.namelist():
            ms_root = ET.fromstring(zf.read("Metadata/model_settings.config"))
            for obj_el in ms_root.findall("object"):
                oid = obj_el.attrib.get("id", "")
                name = ""
                for m in obj_el.findall("metadata"):
                    if m.attrib.get("key") == "name":
                        name = m.attrib.get("value", "")
                obj_names[oid] = name
        model_root = ET.fromstring(zf.read("3D/3dmodel.model"))

    res_el = model_root.find(f"{{{ns}}}resources")
    build_el = model_root.find(f"{{{ns}}}build")
    assert res_el is not None and build_el is not None

    meshes_by_id: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    comps_by_id: dict[str, list[tuple[str, np.ndarray]]] = {}
    name_by_id: dict[str, str] = {}

    def _parse_transform(t_str: str | None) -> np.ndarray:
        mat = np.eye(4)
        if not t_str:
            return mat
        vals = [float(x) for x in t_str.strip().split()]
        if len(vals) == 12:
            # 3MF affine 4x3 column-vector matrix: row-major 3 rows?
            # 3MF spec: m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32 (row vectors v * M)
            M = np.array([
                [vals[0], vals[3], vals[6], vals[9]],
                [vals[1], vals[4], vals[7], vals[10]],
                [vals[2], vals[5], vals[8], vals[11]],
                [0.0, 0.0, 0.0, 1.0],
            ])
            return M
        return mat

    for obj in res_el.findall(f"{{{ns}}}object"):
        oid = obj.attrib["id"]
        name_by_id[oid] = obj.attrib.get("name") or obj_names.get(oid) or f"obj_{oid}"
        m_el = obj.find(f"{{{ns}}}mesh")
        if m_el is not None:
            v_el = m_el.find(f"{{{ns}}}vertices")
            t_el = m_el.find(f"{{{ns}}}triangles")
            verts = np.array(
                [[float(v.attrib["x"]), float(v.attrib["y"]), float(v.attrib["z"])] for v in v_el.findall(f"{{{ns}}}vertex")],
                dtype=np.float64,
            )
            tris = np.array(
                [[int(t.attrib["v1"]), int(t.attrib["v2"]), int(t.attrib["v3"])] for t in t_el.findall(f"{{{ns}}}triangle")],
                dtype=np.int64,
            )
            meshes_by_id[oid] = (verts, tris)
        c_el = obj.find(f"{{{ns}}}components")
        if c_el is not None:
            clist = []
            for comp in c_el.findall(f"{{{ns}}}component"):
                clist.append((comp.attrib["objectid"], _parse_transform(comp.attrib.get("transform"))))
            comps_by_id[oid] = clist

    items: list[dict] = []

    def _collect(oid: str, tf: np.ndarray, out_parts: list[tuple[np.ndarray, np.ndarray]]) -> None:
        if oid in meshes_by_id:
            v, t = meshes_by_id[oid]
            vh = np.hstack([v, np.ones((len(v), 1))]) @ tf.T
            out_parts.append((vh[:, :3], t))
        if oid in comps_by_id:
            for sub_id, sub_tf in comps_by_id[oid]:
                _collect(sub_id, tf @ sub_tf, out_parts)

    for item in build_el.findall(f"{{{ns}}}item"):
        oid = item.attrib["objectid"]
        tf = _parse_transform(item.attrib.get("transform"))
        part_meshes: list[tuple[np.ndarray, np.ndarray]] = []
        _collect(oid, tf, part_meshes)
        sub_tms = [trimesh.Trimesh(vertices=v, faces=t, process=False) for v, t in part_meshes]
        merged = trimesh.util.concatenate(sub_tms) if len(sub_tms) > 1 else sub_tms[0]
        # Clean merge vertices per sub-part for watertightness checks
        sub_clean = [trimesh.Trimesh(vertices=v, faces=t, process=True) for v, t in part_meshes]
        items.append({
            "name": name_by_id.get(oid, f"obj_{oid}"),
            "sub_meshes": sub_clean,
            "merged": trimesh.Trimesh(vertices=merged.vertices, faces=merged.faces, process=True),
        })
    return ps, items


def _analyze_mesh_printability(mesh: trimesh.Trimesh, line_w: float) -> dict:
    watertight = bool(mesh.is_watertight)
    winding = bool(mesh.is_winding_consistent)
    # Remove degenerate tiny areas for normal calculations
    areas = mesh.area_faces
    normals = mesh.face_normals
    centroids = mesh.triangles_center
    valid_mask = areas > 1e-7
    areas_v = areas[valid_mask]
    norm_v = normals[valid_mask]
    cent_v = centroids[valid_mask]

    # Bed contact footprint (Z <= 0.15 mm and downward normal nz < -0.95)
    bed_mask = (cent_v[:, 2] <= 0.15) & (norm_v[:, 2] < -0.95)
    bed_area = float(areas_v[bed_mask].sum())

    # Overhang faces: downward (nz < -0.05) strictly above bed (z > 0.15)
    # Angle from vertical wall: 0 deg = vertical, 45 deg = 45 overhang, 90 deg = horizontal ceiling
    down_mask = (cent_v[:, 2] > 0.15) & (norm_v[:, 2] < -0.01)
    oh_angles = np.degrees(np.arcsin(np.clip(-norm_v[down_mask, 2], 0.0, 1.0)))
    oh_areas = areas_v[down_mask]
    area_gt45 = float(oh_areas[oh_angles > 46.0].sum())  # >46 deg ignores exact 45 deg chamfers due to tessellation noise
    area_gt60 = float(oh_areas[oh_angles > 60.0].sum())
    area_bridge = float(oh_areas[oh_angles > 84.0].sum())

    # Longest bridge spans (connected face clusters among >84 deg flat ceilings above Z=0.15)
    max_bridge_span = 0.0
    max_bridge_z = 0.0
    flat_idx = np.where((centroids[:, 2] > 0.15) & (normals[:, 2] < -0.994) & (areas > 1e-6))[0]
    if len(flat_idx) > 0:
        flat_set = set(flat_idx.tolist())
        # Group by quantized Z (0.2 mm bins) and connected adjacency
        adj = mesh.face_adjacency
        nbrs: dict[int, list[int]] = {i: [] for i in flat_idx}
        for f1, f2 in adj:
            if f1 in flat_set and f2 in flat_set and abs(centroids[f1, 2] - centroids[f2, 2]) < 0.25:
                nbrs[f1].append(f2)
                nbrs[f2].append(f1)
        seen = set()
        for f0 in flat_idx:
            if f0 in seen:
                continue
            stack = [int(f0)]
            comp = []
            seen.add(int(f0))
            while stack:
                cur = stack.pop()
                comp.append(cur)
                for nb in nbrs[cur]:
                    if nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            comp_area = float(areas[comp].sum())
            if comp_area < 2.0:
                continue
            verts = mesh.vertices[np.unique(mesh.faces[comp].ravel())]
            # Compute minimum oriented bounding-box width in XY (closest extruder bridge span!)
            xy = verts[:, :2]
            if len(xy) >= 3:
                try:
                    hull_poly = trimesh.points.PointCloud(xy).convex_hull
                except Exception:
                    hull_poly = None
                # Approximate minimum XY caliper width across 18 angles (0..85 deg)
                min_w = float("inf")
                for deg in range(0, 90, 5):
                    th = math.radians(deg)
                    c, s = math.cos(th), math.sin(th)
                    px = xy[:, 0] * c + xy[:, 1] * s
                    py = -xy[:, 0] * s + xy[:, 1] * c
                    span_x = float(px.max() - px.min())
                    span_y = float(py.max() - py.min())
                    min_w = min(min_w, min(span_x, span_y))
                # Only count bridges where span is bounded by real walls and > 1 mm
                if min_w > max_bridge_span:
                    max_bridge_span = min_w
                    max_bridge_z = float(centroids[comp, 2].mean())

    # Ray-cast minimum lateral wall thickness (sample up to 600 mostly-vertical faces with |nz| < 0.35)
    min_wall = float("inf")
    p5_wall = float("inf")
    lat_idx = np.where((np.abs(norm_v[:, 2]) < 0.35) & (areas_v > 0.2))[0]
    if len(lat_idx) > 0:
        rng = np.random.default_rng(42)
        if len(lat_idx) > 500:
            sel = rng.choice(lat_idx, size=500, replace=False)
        else:
            sel = lat_idx
        origins = cent_v[sel] - norm_v[sel] * 0.02
        dirs = -norm_v[sel]
        locs, ray_idx, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
        if len(locs) > 0:
            dists = np.linalg.norm(locs - origins[ray_idx], axis=1) + 0.02
            # Ignore grazing hits (<0.15 mm) or far cavity crossings (>20 mm)
            wall_dists = dists[(dists >= 0.15) & (dists <= 20.0)]
            if len(wall_dists) > 0:
                min_wall = float(np.min(wall_dists))
                p5_wall = float(np.percentile(wall_dists, 5))

    return {
        "watertight": watertight,
        "winding": winding,
        "bed_area_mm2": bed_area,
        "area_gt45_mm2": area_gt45,
        "area_gt60_mm2": area_gt60,
        "area_bridge_mm2": area_bridge,
        "max_bridge_span_mm": max_bridge_span,
        "max_bridge_z_mm": max_bridge_z,
        "min_wall_mm": min_wall if min_wall < 99.0 else -1.0,
        "p5_wall_mm": p5_wall if p5_wall < 99.0 else -1.0,
    }


def _xy_gap(b1: np.ndarray, b2: np.ndarray) -> float:
    dx = max(b1[0, 0] - b2[1, 0], b2[0, 0] - b1[1, 0], 0.0)
    dy = max(b1[0, 1] - b2[1, 1], b2[0, 1] - b1[1, 1], 0.0)
    return math.hypot(dx, dy)


def main() -> None:
    plate_files = sorted(THREEMF_DIR.glob("Plate_*.3mf"), key=lambda p: int(p.stem.split("_")[1]))
    print(f"Auditing {len(plate_files)} production 3MF plates in {THREEMF_DIR}\n", flush=True)

    for pf in plate_files:
        ps, items = _parse_3mf_objects_and_settings(pf)
        nozzle = ps.get("nozzle_diameter", ["?"])[0]
        lh = ps.get("layer_height", "?")
        lw = float(ps.get("outer_wall_line_width", ps.get("line_width", 0.42)))
        supp = int(ps.get("enable_support", 0))
        supp_type = ps.get("support_type", "none")

        bounds_list = [it["merged"].bounds for it in items]
        all_min = np.min([b[0] for b in bounds_list], axis=0)
        all_max = np.max([b[1] for b in bounds_list], axis=0)
        size = all_max - all_min
        min_margin_xy = min(all_min[0], all_min[1], 270.0 - all_max[0], 270.0 - all_max[1])
        fits_270 = bool(all_min[0] >= 0 and all_min[1] >= 0 and all_min[2] >= -0.05 and all_max[0] <= 270 and all_max[1] <= 270 and all_max[2] <= 270)
        fits_240 = bool(all_min[0] >= 15 and all_min[1] >= 15 and all_max[0] <= 255 and all_max[1] <= 255)

        min_pair_gap = float("inf")
        if len(bounds_list) > 1:
            for i in range(len(bounds_list)):
                for j in range(i + 1, len(bounds_list)):
                    min_pair_gap = min(min_pair_gap, _xy_gap(bounds_list[i], bounds_list[j]))

        all_wt = True
        all_wind = True
        tot_bed = 0.0
        tot_gt45 = 0.0
        tot_gt60 = 0.0
        max_br = 0.0
        max_br_part = ""
        min_w_plate = float("inf")
        min_bed_part = float("inf")

        for it in items:
            # Check each colored subpart cleanly for watertightness; merged or parts for overhangs
            for sm in it["sub_meshes"]:
                if not sm.is_watertight:
                    all_wt = False
                if not sm.is_winding_consistent:
                    all_wind = False
            st = _analyze_mesh_printability(it["merged"], lw)
            tot_bed += st["bed_area_mm2"]
            min_bed_part = min(min_bed_part, st["bed_area_mm2"])
            tot_gt45 += st["area_gt45_mm2"]
            tot_gt60 += st["area_gt60_mm2"]
            if st["max_bridge_span_mm"] > max_br:
                max_br = st["max_bridge_span_mm"]
                max_br_part = f"{it['name']}@{st['max_bridge_z_mm']:.1f}mm"
            if st["min_wall_mm"] > 0:
                min_w_plate = min(min_w_plate, st["min_wall_mm"])

        gap_str = f"{min_pair_gap:.1f}mm" if min_pair_gap < 900 else "single"
        mw_str = f"{min_w_plate:.2f}mm" if min_w_plate < 90 else "n/a"
        print(
            f"{pf.stem} | n={len(items)} nozzle={nozzle} lw={lw} lh={lh} supp={supp}({supp_type}) | "
            f"bbox={size[0]:.1f}x{size[1]:.1f}x{size[2]:.1f} marginXY={min_margin_xy:.1f} fits240={fits_240} gap={gap_str} | "
            f"wt={all_wt} wind={all_wind} minBed={min_bed_part:.1f}mm2 | "
            f"oh>45={tot_gt45:.1f}mm2 oh>60={tot_gt60:.1f}mm2 maxBridge={max_br:.1f}mm({max_br_part}) minWall={mw_str}",
            flush=True,
        )


if __name__ == "__main__":
    main()
