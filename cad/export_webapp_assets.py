"""Export 3D WebGL / Three.js binary mesh buffers and kinematic/assembly metadata
for the Grav-Mass Day Marble Run Tree interactive webapp (cad/export_webapp_assets.py).

Reads the generated B-Rep meshes from:
  - output/3mf/GravMass_Tree_Complete_Assembly.3mf
  - output/3mf/Plate_1..5_*.3mf
  - output/*.stl (for additional mechanical components)

Writes:
  - webapp/assets/meshes.bin    (compact Float32 positions, normals, and Uint32 indices)
  - webapp/assets/manifest.json (scene graph, assembly steps, kinematics, and plate layouts)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

import numpy as np


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
THREEMF_DIR = OUTPUT_DIR / "3mf"
WEBAPP_ASSETS_DIR = ROOT_DIR / "webapp" / "assets"


def _read_binary_stl(stl_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a binary STL file and return deduplicated (vertices_f32 [N,3], triangles_u32 [M,3])."""
    data = stl_path.read_bytes()
    num_tris = struct.unpack_from("<I", data, 80)[0]
    tri_dtype = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("v0", "<f4", (3,)),
            ("v1", "<f4", (3,)),
            ("v2", "<f4", (3,)),
            ("attr", "<u2"),
        ]
    )
    recs = np.frombuffer(data, dtype=tri_dtype, offset=84, count=num_tris)
    raw_verts = np.empty((num_tris * 3, 3), dtype=np.float32)
    raw_verts[0::3] = recs["v0"]
    raw_verts[1::3] = recs["v1"]
    raw_verts[2::3] = recs["v2"]

    # Round to 1e-3 mm to deduplicate shared vertices cleanly
    quant = np.round(raw_verts * 1000.0).astype(np.int64)
    _, unique_idx, inverse_idx = np.unique(
        quant, axis=0, return_index=True, return_inverse=True
    )
    verts = raw_verts[unique_idx].astype(np.float32)
    tris = inverse_idx.astype(np.uint32).reshape((-1, 3))
    return verts, tris


def _transform_verts(
    verts: np.ndarray,
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rot_xyz_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    center_xy: bool = False,
    drop_z0: bool = False,
) -> np.ndarray:
    """Apply optional centering, Euler rotation (X, Y, Z in degrees), and translation."""
    v = verts.copy()
    if center_xy:
        cx = 0.5 * (float(v[:, 0].min()) + float(v[:, 0].max()))
        cy = 0.5 * (float(v[:, 1].min()) + float(v[:, 1].max()))
        v[:, 0] -= cx
        v[:, 1] -= cy
    if drop_z0:
        v[:, 2] -= float(v[:, 2].min())

    rx, ry, rz = [math.radians(a) for a in rot_xyz_deg]
    if abs(rx) > 1e-9:
        c, s = math.cos(rx), math.sin(rx)
        R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float32)
        v = v @ R.T
    if abs(ry) > 1e-9:
        c, s = math.cos(ry), math.sin(ry)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)
        v = v @ R.T
    if abs(rz) > 1e-9:
        c, s = math.cos(rz), math.sin(rz)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)
        v = v @ R.T

    v[:, 0] += translate[0]
    v[:, 1] += translate[1]
    v[:, 2] += translate[2]
    return v


def _parse_3mf_meshes(threemf_path: Path, plate_centered: bool = False) -> list[dict[str, object]]:
    """Extract all mesh objects with their names and display colors from a .3mf archive.
    When `plate_centered=True`, applies the <build><item> XY translation relative to the
    plate center (135.0, 135.0) so meshes sit at their plated positions around (0, 0).
    """
    ns_core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    with zipfile.ZipFile(threemf_path, "r") as zf:
        root = ET.fromstring(zf.read("3D/3dmodel.model"))

    pid_to_color: dict[str, str] = {}
    for bg in root.findall(f".//{{{ns_core}}}basematerials"):
        bg_id = bg.attrib.get("id", "")
        bases = bg.findall(f"{{{ns_core}}}base")
        if bases:
            col = bases[0].attrib.get("displaycolor", "#D4AF37")[:7].upper()
            pid_to_color[bg_id] = col

    mesh_id_to_offset: dict[str, tuple[float, float, float]] = {}
    mesh_id_to_parent_name: dict[str, str] = {}
    if plate_centered:
        comp_to_subs: dict[str, list[str]] = {}
        obj_id_to_name: dict[str, str] = {}
        for obj_el in root.findall(f".//{{{ns_core}}}object"):
            oid = obj_el.attrib.get("id", "")
            oname = obj_el.attrib.get("partnumber") or obj_el.attrib.get("name") or ""
            obj_id_to_name[oid] = oname
            comps_el = obj_el.find(f"{{{ns_core}}}components")
            if comps_el is not None:
                comp_to_subs[oid] = [
                    c.attrib.get("objectid", "")
                    for c in comps_el.findall(f"{{{ns_core}}}component")
                ]
        for item_el in root.findall(f".//{{{ns_core}}}build/{{{ns_core}}}item"):
            item_oid = item_el.attrib.get("objectid", "")
            tf_str = item_el.attrib.get("transform", "")
            parts = [float(x) for x in tf_str.split()] if tf_str else []
            if len(parts) == 12:
                dx = parts[9] - 135.0
                dy = parts[10] - 135.0
                dz = parts[11]
            else:
                dx, dy, dz = 0.0, 0.0, 0.0
            if item_oid in comp_to_subs:
                p_name = obj_id_to_name.get(item_oid, "")
                for sub_oid in comp_to_subs[item_oid]:
                    mesh_id_to_offset[sub_oid] = (dx, dy, dz)
                    if p_name:
                        mesh_id_to_parent_name[sub_oid] = p_name
            else:
                mesh_id_to_offset[item_oid] = (dx, dy, dz)

    results: list[dict[str, object]] = []
    for obj_el in root.findall(f".//{{{ns_core}}}object"):
        mesh_el = obj_el.find(f"{{{ns_core}}}mesh")
        if mesh_el is None:
            continue
        oid = obj_el.attrib.get("id", "")
        raw_name = obj_el.attrib.get("partnumber") or obj_el.attrib.get("name") or f"obj_{oid}"
        if oid in mesh_id_to_parent_name:
            name = f"{mesh_id_to_parent_name[oid]} ({raw_name})"
        else:
            name = raw_name
        pid = obj_el.attrib.get("pid", "")
        color = pid_to_color.get(pid, "#D4AF37")

        v_els = mesh_el.findall(f"./{{{ns_core}}}vertices/{{{ns_core}}}vertex")
        t_els = mesh_el.findall(f"./{{{ns_core}}}triangles/{{{ns_core}}}triangle")

        verts = np.array(
            [(float(v.attrib["x"]), float(v.attrib["y"]), float(v.attrib["z"])) for v in v_els],
            dtype=np.float32,
        )
        if oid in mesh_id_to_offset:
            ox, oy, oz = mesh_id_to_offset[oid]
            verts[:, 0] += np.float32(ox)
            verts[:, 1] += np.float32(oy)
            verts[:, 2] += np.float32(oz)
        tris = np.array(
            [(int(t.attrib["v1"]), int(t.attrib["v2"]), int(t.attrib["v3"])) for t in t_els],
            dtype=np.uint32,
        )
        results.append(
            {
                "name": name,
                "color": color,
                "verts": verts,
                "tris": tris,
            }
        )
    return results


def _classify_assembly_part(name: str, default_color: str) -> dict[str, object]:
    """Assign subsystem group, assembly step (1-12), sub_delay, insert_offset, explode vector, toolhead, and kinematic role."""
    n = name.lower()
    # Default metadata
    meta: dict[str, object] = {
        "subsystem": "misc",
        "step": 1,
        "sub_delay": 0.0,
        "anim_dur": 0.65,
        "insert_offset": [0.0, 0.0, 45.0],
        "explode": [0.0, 0.0, 0.0],
        "toolhead": 1,
        "color": default_color,
        "kinematic_group": "static",
        "opacity": 1.0,
    }

    if "trunk_base" in n:
        meta.update(
            {
                "subsystem": "trunk_base",
                "label": "Trunk Base #1 (Ø185mm Root Footprint, Ø135×50mm Hollow Root Vault, Ø28mm Motor Shroud & Snap-In Cradles)",
                "step": 1,
                "sub_delay": 0.0,
                "anim_dur": 0.65,
                "insert_offset": [0.0, 0.0, 55.0],
                "explode": [0.0, 0.0, -90.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "cutaway_candidate": True,
            }
        )
    elif "bottom_electronics_lid" in n:
        meta.update(
            {
                "subsystem": "trunk_base",
                "label": "Bottom_Electronics_Lid (Flush Ø134.6×2.8 mm Vault Tray + 4× M2.5×6 mm Screws, Clears All Wiring Bays)",
                "step": 2,
                "sub_delay": 1.45,
                "anim_dur": 0.65,
                "insert_offset": [0.0, 0.0, -65.0],
                "explode": [0.0, 0.0, -145.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "kinematic_group": "static",
            }
        )
    elif "conduit_cover_strip" in n:
        meta.update(
            {
                "subsystem": "trunk_mid",
                "label": "Conduit_Cover_Strip (Section-Matched Snap-On Brown Cover for 10.6×8.5mm 150° Connector Conduit)",
                "step": 9,
                "sub_delay": 0.30,
                "anim_dur": 0.65,
                "insert_offset": [-47.63, 27.5, 0.0],
                "explode": [-82.27, 47.5, 0.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "kinematic_group": "static",
            }
        )
    elif "trunk_mid" in n:
        meta.update(
            {
                "subsystem": "trunk_mid",
                "label": "Trunk Middle #2 (Stack onto Trunk Base #1 Tenon — Aligns Ball Flute & 10×8mm Rear Connector Conduit)",
                "step": 5,
                "sub_delay": 0.0,
                "anim_dur": 0.80,
                "insert_offset": [0.0, 0.0, 115.0],
                "explode": [0.0, 0.0, 0.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "cutaway_candidate": True,
            }
        )
    elif "trunk_top" in n:
        meta.update(
            {
                "subsystem": "trunk_top",
                "label": "Trunk Top #3 (Stack onto Trunk Middle #2 Tenon — Houses Upper -Y Chute & 10×8mm Rear Conduit)",
                "step": 5,
                "sub_delay": 0.85,
                "anim_dur": 0.80,
                "insert_offset": [0.0, 0.0, 115.0],
                "explode": [0.0, 0.0, 75.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "cutaway_candidate": True,
            }
        )
    elif "auger_lower" in n:
        meta.update(
            {
                "subsystem": "auger_lower",
                "label": "Archimedes Auger Lower #1 (Female Hex Socket Seats onto Motor_Clutch_Driver; Top Hex Peg Engraved '1')",
                "step": 4,
                "sub_delay": 0.0,
                "anim_dur": 0.80,
                "insert_offset": [0.0, 0.0, 95.0],
                "explode": [-110.0, 0.0, -20.0],
                "toolhead": 3,
                "color": "#D4AF37",
                "kinematic_group": "auger_driven",
            }
        )
    elif "auger_upper" in n:
        meta.update(
            {
                "subsystem": "auger_upper",
                "label": "Archimedes Auger Upper #2 (Couples onto Auger Lower #1's Hex Peg; Top Shaft Engraved '2')",
                "step": 4,
                "sub_delay": 0.85,
                "anim_dur": 0.80,
                "insert_offset": [0.0, 0.0, 110.0],
                "explode": [-110.0, 0.0, 50.0],
                "toolhead": 3,
                "color": "#D4AF37",
                "kinematic_group": "auger_driven",
            }
        )
    elif "track_seg" in n:
        # Extract segment index 1..14
        digits = "".join(ch for ch in n if ch.isdigit())
        seg_idx = int(digits[:2]) if digits else 1
        mid_deg = (seg_idx - 0.5) * 120.0
        rad = math.radians(mid_deg)
        meta.update(
            {
                "subsystem": "track",
                "label": f"Helical Track Segment {seg_idx:02d} (8.0° Stepped Shoulder Half-Laps & Split-Tine Bracket Snap Sockets — Drops Vertically -Z)",
                "step": 7,
                "sub_delay": round((seg_idx - 1) * 0.24, 3),
                "anim_dur": 0.55,
                "insert_offset": [
                    round(28.0 * math.cos(rad), 2),
                    round(28.0 * math.sin(rad), 2),
                    36.0,
                ],
                "explode": [115.0 * math.cos(rad), 115.0 * math.sin(rad), (seg_idx - 7) * 10.0],
                "toolhead": 2,
                "color": "#00A86B",
                "opacity": 0.90,
            }
        )
    elif "golden_apple_topper" in n or "apple_green_leaf" in n:
        is_collar = "collar" in n
        is_stem = "stem" in n
        is_leaf = "leaf" in n
        if is_collar:
            tid_top, lbl_top = 1, "Upper Trunk Crown Collar (Wood Brown PLA — Seats onto Trunk Top #3)"
            s_delay = 0.55
            ins_off = [0.0, 0.0, 65.0]
        elif is_stem:
            tid_top, lbl_top = 1, "Apple Topper Woody Stem (Toolhead 1 Brown PLA — Sockets into Topper Crown)"
            s_delay = 1.35
            ins_off = [0.0, 0.0, 85.0]
        elif is_leaf:
            tid_top, lbl_top = 2, "Apple Topper 3D Sculpted Leaf (Translucent Green PETG on Plate 13 — Snaps into Stem Socket)"
            s_delay = 1.50
            ins_off = [14.0, 0.0, 40.0]
        else:
            tid_top, lbl_top = 4, "Sculpted Heart-Shaped Crimson Apple Topper (#4 PLA — Contoured ~2.2 mm Thin-Walled Hollow Lantern Shell)"
            s_delay = 1.35
            ins_off = [0.0, 0.0, 80.0]
        meta.update(
            {
                "subsystem": "topper",
                "label": lbl_top,
                "step": 9,
                "sub_delay": s_delay,
                "anim_dur": 0.75,
                "insert_offset": ins_off,
                "explode": [0.0, 0.0, 175.0 if not (is_stem or is_leaf) else 210.0],
                "toolhead": tid_top,
                "color": default_color,
                "cutaway_candidate": not (is_stem or is_leaf),
            }
        )
    elif "planet_" in n:
        # Determine planet name
        parts = n.replace("asm_", "").split("_")
        p_key = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else "planet"
        planet_angles = {
            "planet_neptune": (-15.0, 0, 8),
            "planet_uranus": (240.0, 1, 7),
            "planet_saturn": (480.0, 2, 6),
            "planet_jupiter": (600.0, 3, 5),
            "planet_mars": (840.0, 4, 4),
            "planet_earth": (1080.0, 5, 3),
            "planet_venus": (1320.0, 6, 2),
            "planet_mercury": (1590.0, 7, 1),
        }
        deg, p_order, p_num = planet_angles.get(p_key, (900.0, 4, 4))
        rad = math.radians(deg)
        col_u = default_color.upper()
        if col_u in ("#4A2F1D", "#6E4726", "#B8860B", "#1E5AA8"):
            tid = 1
        elif col_u in ("#00A86B", "#1E6B9B", "#2E9B4F", "#F5EFE6"):
            tid = 2
        elif col_u in ("#D4AF37", "#F2E2C4", "#F0F4F8", "#F4B41A"):
            tid = 3
        else:
            tid = 4
        meta.update(
            {
                "subsystem": "planets",
                "planet_id": p_key,
                "label": f"{p_key.replace('_', ' ').title()} (#{p_num} — Larger 4-Color Sculpted Planet with Self-Centering Snap-Click Socket & Magnetic Switch LED)",
                "step": 10,
                "sub_delay": round(p_order * 0.25 + 0.08, 3),
                "anim_dur": 0.50,
                "insert_offset": [
                    round(36.0 * math.cos(rad), 2),
                    round(36.0 * math.sin(rad), 2),
                    36.0,
                ],
                "explode": [185.0 * math.cos(rad), 185.0 * math.sin(rad), 25.0],
                "toolhead": tid,
                "color": default_color,
                "kinematic_group": "planet_ornament",
            }
        )
    elif "magic_led_wand" in n:
        col_u = default_color.upper()
        tid = 1 if col_u == "#4A2F1D" else (4 if col_u == "#C41E3A" else 3)
        meta.update(
            {
                "subsystem": "planets",
                "label": "Magic_LED_Wand (Ø8×2 mm Magnet in Star Tip — Docks Upright in +30° Root-Flare Holster)",
                "step": 11,
                "sub_delay": 0.0,
                "anim_dur": 0.80,
                "insert_offset": [22.0, 13.0, 80.0],
                "explode": [0.0, 0.0, 95.0],
                "toolhead": tid,
                "color": default_color,
                "kinematic_group": "magic_wand",
            }
        )
    elif "apple_marble" in n:
        meta.update(
            {
                "subsystem": "marbles",
                "label": "Glowing 25 mm Rolling Apple Marble (Quarter-Turn Twist-Lock Hemispheres A+B + Bambu KC012/KC013 Y-Shape 3-LED)",
                "step": 12,
                "sub_delay": 0.0,
                "anim_dur": 0.55,
                "insert_offset": [0.0, 0.0, 55.0],
                "explode": [0.0, -140.0, 120.0],
                "toolhead": 4,
                "color": "#C41E3A",
                "kinematic_group": "dynamic_marble",
            }
        )
    return meta


def export_webapp_bundle() -> None:
    WEBAPP_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    binary_chunks: list[bytes] = []
    byte_offset = 0

    def _pack_mesh(verts: np.ndarray, tris: np.ndarray) -> dict[str, int]:
        nonlocal byte_offset
        v_bytes = np.ascontiguousarray(verts, dtype=np.float32).tobytes()
        t_bytes = np.ascontiguousarray(tris, dtype=np.uint32).tobytes()
        v_off = byte_offset
        binary_chunks.append(v_bytes)
        byte_offset += len(v_bytes)
        t_off = byte_offset
        binary_chunks.append(t_bytes)
        byte_offset += len(t_bytes)
        return {
            "v_offset": v_off,
            "v_count": int(verts.shape[0]),
            "t_offset": t_off,
            "t_count": int(tris.shape[0]),
        }

    # 1. Parse main assembled tree from GravMass_Tree_Complete_Assembly.3mf
    asm_3mf_path = THREEMF_DIR / "GravMass_Tree_Complete_Assembly.3mf"
    raw_asm_meshes = _parse_3mf_meshes(asm_3mf_path)

    assembled_entries: list[dict[str, object]] = []
    marble_template_saved = False

    for m in raw_asm_meshes:
        name = str(m["name"])
        # Only keep one marble mesh template for dynamic instancing (we animate 6 marbles in JS)
        if "apple_marble_" in name:
            if marble_template_saved:
                continue
            marble_template_saved = True
            name = "asm_apple_marble_template"
            # Center the marble template at (0, 0, 0) so JS can position it directly on the helix/auger
            verts = m["verts"]  # type: ignore[assignment]
            center = 0.5 * (verts.min(axis=0) + verts.max(axis=0))
            m["verts"] = verts - center

        meta = _classify_assembly_part(name, str(m["color"]))
        buf_info = _pack_mesh(m["verts"], m["tris"])  # type: ignore[arg-type]
        assembled_entries.append(
            {
                "name": name,
                **meta,
                **buf_info,
            }
        )

    # 2. Add the additional mechanical parts into the 3D assembly scene
    # 2a. Motor_Clutch_Driver (placed upright at Z = 26.20 mm so top hex peg engages auger_lower at Z = 37.22..40.70 mm)
    v_mcd, t_mcd = _read_binary_stl(OUTPUT_DIR / "Motor_Clutch_Driver.stl")
    v_mcd_asm = _transform_verts(v_mcd, translate=(0.0, 0.0, 26.20), rot_xyz_deg=(0.0, 0.0, 0.0))
    assembled_entries.append(
        {
            "name": "asm_Motor_Clutch_Driver",
            "label": "Motor_Clutch_Driver (D-Shaft Clamp Coupler w/ 1× M2.5×6 mm Pinch Screw + Hex Drive)",
            "subsystem": "clutch",
            "step": 3,
            "sub_delay": 0.0,
            "anim_dur": 0.85,
            "insert_offset": [0.0, 0.0, 68.0],
            "explode": [0.0, -110.0, -60.0],
            "toolhead": 1,
            "color": "#4A2F1D",
            "kinematic_group": "motor_driver",
            "pivot": [0.0, 0.0, 31.20],
            **_pack_mesh(v_mcd_asm, t_mcd),
        }
    )

    # 2b. All 26 Exact-Radius Cantilever Brackets (bracket_01..26, placed every 60° from 60° to 1560° around the trunk)
    for k_idx in range(26):
        b_num = k_idx + 1
        b_deg = b_num * 60.0  # 60° .. 1560°
        t_num = max(1, 4 - (k_idx // 6))
        t_lbl = {
            4: "Tier 4 Bottom",
            3: "Tier 3 Lower-Mid",
            2: "Tier 2 Upper-Mid",
            1: "Tier 1 Top",
        }[t_num]

        vb_station, tb_base = _read_binary_stl(OUTPUT_DIR / f"bracket_{b_num:02d}.stl")
        rad_b = math.radians(b_deg)
        z_slot = (62.5 + 79.0 * (b_deg / 360.0)) - 33.5
        vb_asm = _transform_verts(
            vb_station,
            translate=(34.0 * math.cos(rad_b), 34.0 * math.sin(rad_b), z_slot),
            rot_xyz_deg=(0.0, 0.0, b_deg),
        )
        assembled_entries.append(
            {
                "name": f"asm_bracket_{b_num:02d}_tier{t_num}",
                "label": f"Cantilever Bracket #{b_num:02d} (Engraved '{b_num}') @ {int(b_deg)}° — {t_lbl} (Push Radially into Keyhole Window, Then Drop into Dovetail)",
                "subsystem": "brackets",
                "step": 6,
                "sub_delay": round(k_idx * 0.11, 3),
                "anim_dur": 0.45,
                "insert_offset": [
                    round(52.0 * math.cos(rad_b), 2),
                    round(52.0 * math.sin(rad_b), 2),
                    24.0,
                ],
                "explode": [85.0 * math.cos(rad_b), 85.0 * math.sin(rad_b), 0.0],
                "toolhead": 1,
                "color": "#4A2F1D",
                "kinematic_group": "static",
                **_pack_mesh(vb_asm, tb_base),
            }
        )

    # 3. Export all 18 Snapmaker U1 Build Plates (15 Single-Color + 3 Dedicated 4-Color Plates) for the 3D Plate & Layer Inspector
    plate_files = [
        ("Plate_1_SingleColor_Brown_Trunk_Base", "Plate 1 (Single-Color T1 Brown PLA) — Trunk Base #1"),
        ("Plate_2_SingleColor_Brown_Trunk_Upper_And_Covers", "Plate 2 (Single-Color T1 Brown PLA) — Trunk Mid #2, Top #3, Bottom Electronics Lid, 3× Conduit Covers & Motor Clamp Coupler"),
        ("Plate_3_SingleColor_Brown_Brackets_01_To_12", "Plate 3 (Single-Color T1 Brown PLA) — 12× Exact-Radius Station Brackets (#1 to #12)"),
        ("Plate_4_SingleColor_Brown_Brackets_13_To_26", "Plate 4 (Single-Color T1 Brown PLA) — 14× Exact-Radius Station Brackets (#13 to #26)"),
        ("Plate_5_SingleColor_Green_Track_01", "Plate 5 (Single-Color T2 PETG) — Track Segment 01 (Bottom Return Ramp & Root-Flare Relief)"),
        ("Plate_6_SingleColor_Green_Track_02", "Plate 6 (Single-Color T2 PETG) — Track Segment 02"),
        ("Plate_7_SingleColor_Green_Track_03", "Plate 7 (Single-Color T2 PETG) — Track Segment 03"),
        ("Plate_8_SingleColor_Green_Track_04", "Plate 8 (Single-Color T2 PETG) — Track Segment 04"),
        ("Plate_9_SingleColor_Green_Track_05_And_13", "Plate 9 (Single-Color T2 PETG) — Track Segments 05 & 13"),
        ("Plate_10_SingleColor_Green_Track_06_And_12", "Plate 10 (Single-Color T2 PETG) — Track Segments 06 & 12"),
        ("Plate_11_SingleColor_Green_Track_07_And_11", "Plate 11 (Single-Color T2 PETG) — Track Segments 07 & 11"),
        ("Plate_12_SingleColor_Green_Track_08_And_10", "Plate 12 (Single-Color T2 PETG) — Track Segments 08 & 10"),
        ("Plate_13_SingleColor_Green_Track_09_And_14", "Plate 13 (Single-Color T2 PETG) — Track Segments 09, 14 (Top Entry) & Apple Green Leaf"),
        ("Plate_14_SingleColor_Gold_Auger_And_Drive", "Plate 14 (Single-Color T3 Silk Gold PLA) — Archimedes Auger Lower #1 & Upper #2"),
        ("Plate_15_SingleColor_Red_Apple_Marbles", "Plate 15 (Single-Color T4 Red PLA) — 12× Glowing Apple Hemispheres A/B (6× Marbles)"),
        ("Plate_16_MultiColor_Topper_And_Wand", "Plate 16 (3-Color PLA Tree Palette) — Apple Topper Shell + Stem/Collar & Magic LED Wand"),
        ("Plate_17_MultiColor_Planets_Warm_And_Gas_Giants", "Plate 17 (4-Color Warm PLA Palette) — Mercury, Venus, Mars, Jupiter & Saturn"),
        ("Plate_18_MultiColor_Planets_Ocean_And_Ice_Giants", "Plate 18 (3-Color Ocean/Ice PLA Palette) — Earth, Uranus & Neptune"),
    ]
    plates_manifest: list[dict[str, object]] = []
    for p_key, p_title in plate_files:
        p_meshes = _parse_3mf_meshes(THREEMF_DIR / f"{p_key}.3mf", plate_centered=True)
        p_items: list[dict[str, object]] = []
        for pm in p_meshes:
            buf_info = _pack_mesh(pm["verts"], pm["tris"])  # type: ignore[arg-type]
            p_items.append(
                {
                    "name": pm["name"],
                    "color": pm["color"],
                    **buf_info,
                }
            )
        plates_manifest.append(
            {
                "id": p_key,
                "title": p_title,
                "file_url": f"/output/3mf/{p_key}.3mf",
                "meshes": p_items,
            }
        )

    # 4. Define the 12 Step-by-Step Interactive Assembly Stages (Pieces Appear Only as Connected)
    assembly_steps = [
        {
            "step": 1,
            "title": "Step 1 — Place Trunk Base (#1), Mount Rear 12V DC Barrel Jack (J1) & Insert N20 Motor Into Shroud Tower",
            "subtitle": "1a) Mount 5.5×2.1mm DC Barrel Jack (J1) in rear -X Ø11.40mm port → 1b) Slide 12V 150RPM N20 Motor straight up into 12.8×10.8×26.2 mm Shroud Pocket",
            "camera_target": [0, 0, 42],
            "camera_pos": [195, -205, 110],
            "hardware": [
                "1a. Place Bark-Textured Trunk_Base (#1, Ø185mm diagonal root footprint, Ø135×50mm Hollow Root Vault) flat on build surface and thread the 5.5×2.1mm DC Barrel Jack (J1, DC-099) through the 6.8 mm stepped rear -X Ø11.40 mm port (Z = 11.5 mm)",
                "1b. Slide the 12V 150rpm N20 Gear Motor directly up into the central Ø28.0 mm Isolated Motor Shroud Tower's direct-fit 12.8×10.8×26.2 mm rectangular pocket (D-shaft pointing up through Z=27.2 mm roof bore — zero printed sleeve adapter needed!)",
                "1c. Route the 2-wire motor lead out the bottom -Y shroud wire exit notch (6.5×7.6 mm) so loose cables in the vault can never rub against the spinning clutch or auger",
            ],
            "clearance_note": "The central Ø28.0 mm Isolated Motor & Clutch Shroud Tower holds the N20 gearbox directly (anti-rotation rectangular walls) and isolates the spinning D-shaft from the >150 cm³ Cable Slack Dump Zone.",
        },
        {
            "step": 2,
            "title": "Step 2 — Install 12V→5V Buck Converter, WAGO 221 Lever Nuts, M5Stack (A092+C008) & Bottom_Electronics_Lid",
            "subtitle": "2a) Seat A092+C008 & 12V→5V 5A Buck in vault cradles → 2b) Wire WAGO-1..4 (cap Grove Red +5V!) → 2c) Secure Bottom_Electronics_Lid w/ 4× M2.5×6 mm screws",
            "camera_target": [0, -20, 22],
            "camera_pos": [175, -195, 78],
            "hardware": [
                "2a. Seat M5Stack ATOM Lite (C008) + Atomic H-Driver Base (A092) into the -Y cradle (powered from WAGO-1 +12V_BUS via 2A fuse F1 into VIN/GND) and seat the 12V→5.0V 5A Buck Converter into the 64.2×28.2 mm bay (fed via 3A fuse F2)",
                "2b. Clamp the 12V 150RPM N20 Motor leads into A092 M1/M2, plug the A096 Grove2Dupont cable into C008 (leave A096 Red +5V wire CAPPED in an empty WAGO port to prevent 5V backfeeding!), and connect the 5V Buck output (+ 1000µF cap) to WAGO-3 (+5V_LED) & WAGO-4 (GND_LED)",
                "2c. Seat the flush upright Bottom_Electronics_Lid (Ø134.6×2.8 mm) into the bottom vault rabbet and fasten with 4× M2.5 × 6 mm BHCS screws (100% flush with Z=0 root pads)",
            ],
            "clearance_note": "With >150 cm³ of unobstructed perimeter volume inside the Ø135×50 mm Hollow Root Vault and the single flush Bottom_Electronics_Lid, all WAGO 221 blocks and bays fit cleanly with zero soldering.",
        },
        {
            "step": 3,
            "title": "Step 3 — Clamp Motor_Clutch_Driver Onto N20 Motor D-Shaft (1× M2.5×6 mm Pinch Screw)",
            "subtitle": "Lower Motor_Clutch_Driver (Brown PLA) onto the N20 D-shaft at Z = 26.2 mm and tighten 1× M2.5×6 mm side pinch screw",
            "camera_target": [0, 0, 36],
            "camera_pos": [155, -160, 95],
            "hardware": [
                "3a. Align the flat inside Motor_Clutch_Driver's split clamp D-bore with the flat on the LA002 N20 motor shaft",
                "3b. Press down until seated at Z = 26.2 mm and tighten 1× M2.5 × 6 mm BHCS radial pinch screw into the split clamp ear for zero-slip positive lock",
            ],
            "clearance_note": "The M2.5 pinch-screw clamp eliminates D-shaft slippage while keeping its hex peg ready for top-down auger insertion.",
        },
        {
            "step": 4,
            "title": "Step 4 — Couple Two-Piece Archimedes Auger (#1 Lower + #2 Upper)",
            "subtitle": "4a) Lower auger_lower (#1) onto the Gold Hex Coupler → 4b) Press auger_upper (#2) onto auger_lower's top hex peg (engraved '1')",
            "camera_target": [0, 0, 220],
            "camera_pos": [265, -265, 255],
            "hardware": [
                "4a. Lower auger_lower (#1) into Trunk_Base so its bottom 5.15 mm AF female hex socket slides over Motor_Clutch_Driver's hex peg",
                "4b. Align auger_upper (#2, engraved '2' on top shaft) with auger_lower's top male hex peg (engraved '1') and press together (hiding '1')",
            ],
            "clearance_note": "The phase-matched helical flight is continuous across the Z = 222.7 mm hex joint with 1.50 mm radial clearance inside the trunk bore.",
        },
        {
            "step": 5,
            "title": "Step 5 — Stack Bark-Textured Trunk Middle (#2) & Trunk Top (#3)",
            "subtitle": "5a) Lower trunk_mid (#2) over the auger onto trunk_base (#1) → 5b) Lower trunk_top (#3) onto trunk_mid (#2)",
            "camera_target": [0, 0, 265],
            "camera_pos": [-255, -265, 305],
            "hardware": [
                "5a. Slide trunk_mid (#2) down over the auger and seat onto trunk_base's keyed tenon (engraved '1' at Z = 150 mm becomes 100% hidden)",
                "5b. Slide trunk_top (#3, with its upward Ø59.4×4.0 mm Crown Centering Tenon Collar) down onto trunk_mid's keyed tenon (engraved '2' at Z = 300 mm becomes 100% hidden)",
            ],
            "clearance_note": "The keyed tenon flats automatically align the internal Ø 26.6 mm (-Y) vertical ball flute, gothic viewing windows, and the oversized 10.0×8.0 mm rear (-X) Connector-Pass-Through wiring conduit.",
        },
        {
            "step": 6,
            "title": "Step 6 — Drop In All 26 Keyhole Cantilever Brackets (#1 at 60° → #26 at 1560°)",
            "subtitle": "Push each bracket tenon radially inward into its keyhole entry window (+16.0 mm Z), then slide straight down -Z into the 45° dovetail wedge",
            "camera_target": [0, 0, 225],
            "camera_pos": [310, -295, 260],
            "hardware": [
                "6a. Push tenon radially inward into the upper keyhole entry window (0.000 mm³ collision), then drop vertically -16.0 mm into the 45° dovetail over the ±Y neck detent bumps",
                "6b. Install brackets #1–#26 in order (60°..1560°): #25 (1500°) and #26 (1560°) support the upper Seg 13/14 feeder curve",
                "6c. With the conduit relocated to 150° (midway between 120° and 180° brackets), all 26 brackets clear the wiring channel completely!",
            ],
            "clearance_note": "All 26 sockets have upper drop-in keyhole windows (16.2×4.85×18.6 mm, 45° gable roof) giving a verified 0.0000 mm³ L-path while stacked.",
        },
        {
            "step": 7,
            "title": "Step 7 — Drop Helical Track Segments 01 → 14 (-Z Onto Stepped Half-Laps & Split-Tine Bracket Pegs)",
            "subtitle": "Drop Seg 01 into Trunk_Base & brackets #1/#2, then drop Seg 02 → 14 vertically -Z onto each downhill 8.0° stepped shoulder half-lap & split-tine bracket pegs!",
            "camera_target": [0, 0, 220],
            "camera_pos": [370, -350, 275],
            "hardware": [
                "7a. Lower track_seg_01 (-Z) into Trunk_Base's -Y intake port (Z = 48.5 mm) and press onto the Tier #4 bracket pegs at 60° and 120°",
                "7b. Lower track_seg_02 → track_seg_13 vertically (-Z) in ascending order: each downhill 8.0° stepped shoulder half-lap drops flush onto the previous uphill shoulder directly above its 60° cantilever bracket while both underside sockets snap-lock onto the bracket's split-tine pegs!",
                "7c. Lower track_seg_14_top_entry vertically onto Seg 13 at 1560°, Bracket #26 (1560°), and Trunk_Top's -Y discharge chute (Z = 431.8 mm).",
            ],
            "clearance_note": "Single vertical -Z assembly eliminates the old orthogonal deadlock: the marble rides a continuous zero-snag top groove while the stepped half-lap overlaps directly onto the bracket saddle below.",
        },
        {
            "step": 8,
            "title": "Step 8 — Snap In BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Wire (B0CCS11V7H) & Connect to Grove GPIO26 + WAGO-3/4",
            "subtitle": "8a) Seat B0CCS11V7H starter pocket under track_seg_01 → 8b) Snap 50-LED Pebble wire into 8.4×6.2 mm dovetail chamber → 8c) Connect Data to GPIO26 & Power to WAGO-3/4",
            "camera_target": [0, -15, 195],
            "camera_pos": [340, -340, 210],
            "hardware": [
                "8a. Seat the starter end of the BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Flexible Wire (B0CCS11V7H) into the 10.0×16.0 mm starter pocket underneath track_seg_01 (theta = -70°)",
                "8b. Press the 360°-flexible 3-wire cord and 6.2×3.2 mm oval Pebble LEDs edge-on through the 4.6 mm snap-in throat into the deep 8.4×6.2 mm (3.6 mm flat bay) internal dovetail chamber up to Segment 14 — completely flush above bracket saddles!",
                "8c. Route the pre-terminated 3-pin JST-SM input plug through Trunk_Base's cob_wire_conduit into the Hollow Root Vault: White Data to Grove GPIO26 and Red (+5V) / Black (GND) into WAGO-3 (+5V_LED) & WAGO-4 (GND_LED)",
            ],
            "clearance_note": "The deepened 8.4×6.2 mm dovetail channel (3.6 mm full-width bay above the 4.6 mm throat) recesses all 6.2×3.2 mm LED pills cleanly above bracket saddles.",
        },
        {
            "step": 9,
            "title": "Step 9 — Route Topper Cable Through 150° Conduit, Snap Covers, Seat Topper & Snap Green PETG Leaf",
            "subtitle": "9a) Drop JST-SM plug through 150° conduit & snap 3 full-length covers → 9b) Seat Sparkleiot Ring → 9c) Place Apple Topper (#4) + snap Green PETG Leaf (Plate 13)",
            "camera_target": [0, 0, 465],
            "camera_pos": [225, -225, 525],
            "hardware": [
                "9a. Route the 1m 3-Pin JST-SM Extension Cable (B0CT827QQC) straight through the unobstructed 10.6×8.5 mm 150° conduit to GPIO32 & WAGO-3/4, then snap Conduit_Cover_Strip_Base (100 mm), Mid (144 mm), and Top (144 mm) flush",
                "9b. Seat the Ø45.0 mm Sparkleiot 16-Bit WS2812 RGB LED Ring (B09YTMNGTD) flat into the Ø46.2×2.5 mm recessed ring seat on Trunk_Top at Z = 447.5 mm",
                "9c. Lower the 3-color PLA Apple Topper (#4 + Brown Stem) onto Trunk_Top's Ø59.40×4.0 mm Crown Centering Collar, then press the standalone Translucent Emerald Green PETG apple_green_leaf (Plate 13) into the upper stem socket!",
            ],
            "clearance_note": "Keeping apple_green_leaf as a dedicated snap-in PETG print (Plate 13) gives every multi-color Plate 16–18 print pure 100% single-polymer PLA adhesion with zero PETG/PLA contamination!",
        },
        {
            "step": 10,
            "title": "Step 10 — Insert 8 Magnetic Switch LEDs Into Upgraded 4-Color Planets #8 → #1 & Snap-Click Onto Balconies",
            "subtitle": "For each 4-color PLA planet (#8 Neptune at -15° to #1 Mercury at 1590°): press wireless KA006 LED into 4× crush ribs & snap onto Balcony Peg #8 → #1",
            "camera_target": [0, 0, 235],
            "camera_pos": [395, -380, 290],
            "hardware": [
                "10a. Press 1× wireless Bambu Single LED Magnetic Control Switch Light (Ø7.5×6.0 mm) past the 4× internal 0.85 mm crush ribs inside each Planet (#8 Neptune → #1 Mercury)",
                "10b. Match the hidden number inside each planet's bottom bore (8..1) with the number on each Track Balcony Peg (8..1) and press down until the internal Ø8.46 mm groove clicks onto the peg's Ø8.36 mm snap bead",
            ],
            "clearance_note": "Planets print 100% single-polymer PLA (Plates 17 & 18) with 4× internal crush ribs clamping the KA006 LEDs and 0.18 mm radial snap interference on the balcony pegs.",
        },
        {
            "step": 11,
            "title": "Step 11 — Assemble Magic_LED_Wand & Dock in +30° Root-Flare Holster",
            "subtitle": "Press the Ø8×2 mm trigger magnet into the Magic_LED_Wand star tip and stand the wand upright in the +30° Root-Flare Holster",
            "camera_target": [35, 20, 55],
            "camera_pos": [210, -165, 125],
            "hardware": [
                "11a. Press the included Ø8×2 mm neodymium trigger magnet into the star tip of the 3-color Magic_LED_Wand",
                "11b. Dock the wand upright in the integrated +30° Root-Flare Holster socket (X = +45.0, Y = +26.0 mm) on Trunk_Base",
            ],
            "clearance_note": "Touching any planet with the Magic_LED_Wand star tip toggles its internal magnetic reed switch through ON -> Breathe -> Flash -> OFF.",
        },
        {
            "step": 12,
            "title": "Step 12 — Twist-Lock the 6 Glowing Apple Marbles (A + Bambu Y-Shape or Single LED + B) & Run!",
            "subtitle": "Drop a Bambu Y-Shape LED Light (Ø18×6.5 mm KC012/KC013) or Single LED + M8 nut into Apple_Hemisphere_B, align & drop Apple_Hemisphere_A into the 3 keyways, twist 45° clockwise to lock, and tap ON with the Magic Wand!",
            "camera_target": [0, 0, 225],
            "camera_pos": [410, -395, 310],
            "hardware": [
                "12a. Drop 1× wireless Bambu Y-Shape LED Light with Magnetic Control Switch (Ø18.0×6.5 mm KC012/KC013, CR1632 battery) OR 1× Single LED (Ø7.5×6.0 mm KA006) + M8 Hex Nut into the Ø18.70 mm chamber of Apple_Hemisphere_B (marked 'B')",
                "12b. Align the 3 male bayonet lugs on Apple_Hemisphere_A (marked 'A') with the 3 vertical entry keyway slots on Apple_Hemisphere_B—the two halves drop flush together with zero force",
                "12c. Twist Apple_Hemisphere_A 45° clockwise ('righty-tighty') to lock the 3 lugs under the solid bayonet ceiling, tap each marble ON with the Magic_LED_Wand, and load onto the track!",
            ],
            "clearance_note": "The Quarter-Turn 3-Lug Bayonet Twist-Lock requires zero PLA bending to insert (+0.44 mm clearance) and locks under solid PLA ceilings so the halves never separate during rolling or drops!",
        },
    ]

    # Write binary buffer and JSON manifest
    bin_path = WEBAPP_ASSETS_DIR / "meshes.bin"
    bin_path.write_bytes(b"".join(binary_chunks))

    manifest = {
        "title": "Grav-Mass Day Marble Run Tree — Interactive 3D CAD, Simulator & Assembly Studio",
        "binary_file": "assets/meshes.bin",
        "binary_size_bytes": byte_offset,
        "toolheads": {
            "1": {"name": "Dark Wood Brown", "hex": "#4A2F1D", "type": "PLA"},
            "2": {"name": "Translucent Emerald Green", "hex": "#00A86B", "type": "PETG"},
            "3": {"name": "Silk Gold / Brass", "hex": "#D4AF37", "type": "PLA"},
            "4": {"name": "Glossy Crimson Red", "hex": "#C41E3A", "type": "PLA"},
        },
        "kinematics": {
            "helix_bot_r": 145.0,
            "helix_top_r": 60.0,
            "helix_pitch": 79.0,
            "helix_turns": 4.5,
            "helix_total_deg": 1620.0,
            "helix_z_start": 62.5,
            "helix_z_end": 418.0,
            "return_chute_end_deg": -90.0,
            "return_chute_end_r": 42.0,
            "top_feeder_start_deg": 1710.0,
            "top_feeder_start_r": 47.0,
            "top_feeder_rise_z": 7.0,
            "auger_pitch": 46.0,
            "auger_ball_orbit_r": 17.5,
            "auger_z_start": 37.22,
            "auger_z_end": 433.32,
        },
        "assembled_meshes": assembled_entries,
        "assembly_steps": assembly_steps,
        "plates": plates_manifest,
    }
    manifest_path = WEBAPP_ASSETS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(
        f"Exported {len(assembled_entries)} assembled meshes + {len(plates_manifest)} plates "
        f"({byte_offset / (1024 * 1024):.2f} MB binary) -> {WEBAPP_ASSETS_DIR}"
    )


if __name__ == "__main__":
    export_webapp_bundle()
