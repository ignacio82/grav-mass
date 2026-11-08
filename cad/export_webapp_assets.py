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
    elif "base_bottom_cover" in n:
        meta.update(
            {
                "subsystem": "trunk_base",
                "label": "Base_Bottom_Cover (Twist-Lock / 4× Captive Magnet Service Lid with Ventilation Louvers)",
                "step": 2,
                "sub_delay": 1.75,
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
                "label": "Conduit_Cover_Strip (Snap-On Brown Cover Strip for 10×8mm Rear Connector-Pass-Through Conduit)",
                "step": 9,
                "sub_delay": 0.30,
                "anim_dur": 0.65,
                "insert_offset": [-55.0, 0.0, 0.0],
                "explode": [-95.0, 0.0, 0.0],
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
    elif "track_joint_clip" in n:
        rad_120 = math.radians(120.0)
        meta.update(
            {
                "subsystem": "track",
                "label": "Track_Joint_Clip (Snap-On Underside U-Cradle Splice Clamp — Bridges Across Track Seams & Retrofits Older Prints)",
                "step": 7,
                "sub_delay": 0.36,
                "anim_dur": 0.55,
                "insert_offset": [
                    round(48.0 * math.cos(rad_120), 2),
                    round(48.0 * math.sin(rad_120), 2),
                    -28.0,
                ],
                "explode": [125.0 * math.cos(rad_120), 125.0 * math.sin(rad_120), -45.0],
                "toolhead": 2,
                "color": "#00A86B",
                "opacity": 0.95,
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
                "label": f"Helical Track Segment {seg_idx:02d} (Clicks into Seg {seg_idx - 1:02d}'s Twin Ø3.8mm Male Snap-Tenons + Sidewall Tongues & Bracket Pegs)",
                "step": 7,
                "sub_delay": round((seg_idx - 1) * 0.24, 3),
                "anim_dur": 0.55,
                "insert_offset": [
                    round(48.0 * math.cos(rad), 2),
                    round(48.0 * math.sin(rad), 2),
                    28.0,
                ],
                "explode": [115.0 * math.cos(rad), 115.0 * math.sin(rad), (seg_idx - 7) * 10.0],
                "toolhead": 2,
                "color": "#00A86B",
                "opacity": 0.90,
            }
        )
    elif "golden_apple_topper" in n:
        is_collar = "collar" in n
        is_stem = "stem" in n
        is_leaf = "leaf" in n
        if is_collar:
            tid_top, lbl_top = 1, "Upper Trunk Crown Collar (Wood Brown — Seats onto Trunk Top #3)"
            s_delay = 0.55
            ins_off = [0.0, 0.0, 65.0]
        elif is_stem:
            tid_top, lbl_top = 1, "Apple Topper Woody Stem (Toolhead 1 Brown — Branches into Sculpted Leaf)"
            s_delay = 1.35
            ins_off = [0.0, 0.0, 85.0]
        elif is_leaf:
            tid_top, lbl_top = 2, "Apple Topper 3D Sculpted Leaf (Toolhead 2 Emerald Green)"
            s_delay = 1.35
            ins_off = [0.0, 0.0, 85.0]
        else:
            tid_top, lbl_top = 4, "Sculpted Heart-Shaped Crimson Apple Topper (#4 — Contoured ~2.2 mm Thin-Walled Hollow Lantern Shell)"
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
            "planet_neptune": (60.0, 0, 8),
            "planet_uranus": (300.0, 1, 7),
            "planet_saturn": (540.0, 2, 6),
            "planet_jupiter": (660.0, 3, 5),
            "planet_mars": (900.0, 4, 4),
            "planet_earth": (1140.0, 5, 3),
            "planet_venus": (1380.0, 6, 2),
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
            "label": "Motor_Clutch_Driver (Direct Mechanical Hex Motor Coupler — Presses onto N20 D-Shaft)",
            "subsystem": "clutch",
            "step": 3,
            "sub_delay": 0.0,
            "anim_dur": 0.85,
            "insert_offset": [0.0, 0.0, 68.0],
            "explode": [0.0, -110.0, -60.0],
            "toolhead": 3,
            "color": "#D4AF37",
            "kinematic_group": "motor_driver",
            "pivot": [0.0, 0.0, 31.20],
            **_pack_mesh(v_mcd_asm, t_mcd),
        }
    )

    # 2b. Battery_Cover & Servo_Or_030_Adapter at base of trunk_base
    v_bc, t_bc = _read_binary_stl(OUTPUT_DIR / "Battery_Cover.stl")
    v_bc_asm = _transform_verts(v_bc, translate=(0.0, -33.0, -2.5), center_xy=True, drop_z0=True)
    assembled_entries.append(
        {
            "name": "asm_Battery_Cover",
            "label": "Battery_Cover (Bottom M5Stack ESPHome Bay Cover + Ø5.0 mm Button/LED Port + 2× M2.5 Screws)",
            "subsystem": "trunk_base",
            "step": 2,
            "sub_delay": 1.45,
            "anim_dur": 0.65,
            "insert_offset": [0.0, -15.0, -55.0],
            "explode": [0.0, -85.0, -135.0],
            "toolhead": 1,
            "color": "#4A2F1D",
            "kinematic_group": "static",
            **_pack_mesh(v_bc_asm, t_bc),
        }
    )

    v_adp, t_adp = _read_binary_stl(OUTPUT_DIR / "Servo_Or_030_Adapter.stl")
    v_adp_asm = _transform_verts(v_adp, translate=(0.0, 0.0, 0.2), center_xy=True, drop_z0=True)
    assembled_entries.append(
        {
            "name": "asm_Servo_Or_030_Adapter",
            "label": "Servo_Or_030_Adapter (N20 Gear Motor Mounting Sleeve)",
            "subsystem": "trunk_base",
            "step": 1,
            "sub_delay": 0.70,
            "anim_dur": 0.70,
            "insert_offset": [0.0, 0.0, -60.0],
            "explode": [0.0, 0.0, -125.0],
            "toolhead": 1,
            "color": "#4A2F1D",
            "kinematic_group": "static",
            **_pack_mesh(v_adp_asm, t_adp),
        }
    )

    # 2c. All 24 Exact-Radius Cantilever Brackets (bracket_01..24, placed every 60° from 60° to 1440° around the trunk)
    for k_idx in range(24):
        b_num = k_idx + 1
        b_deg = b_num * 60.0  # 60° .. 1440°
        if k_idx < 6:
            t_num, t_lbl = 4, "Tier 4 Bottom"
        elif k_idx < 12:
            t_num, t_lbl = 3, "Tier 3 Lower-Mid"
        elif k_idx < 18:
            t_num, t_lbl = 2, "Tier 2 Upper-Mid"
        else:
            t_num, t_lbl = 1, "Tier 1 Top"

        vb_station, tb_base = _read_binary_stl(OUTPUT_DIR / f"bracket_{b_num:02d}.stl")
        rad_b = math.radians(b_deg)
        z_slot = (62.5 + 79.0 * (b_deg / 360.0)) - 30.0
        vb_asm = _transform_verts(
            vb_station,
            translate=(34.0 * math.cos(rad_b), 34.0 * math.sin(rad_b), z_slot),
            rot_xyz_deg=(0.0, 0.0, b_deg),
        )
        assembled_entries.append(
            {
                "name": f"asm_bracket_{b_num:02d}_tier{t_num}",
                "label": f"Cantilever Bracket #{b_num:02d} (Engraved '{b_num}') @ {int(b_deg)}° — {t_lbl} (Exact Station Radius, Slides into Trunk Dovetail & Supports Track)",
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
        ("Plate_1_SingleColor_Brown_Trunk_Base", "Plate 1 (Single-Color T1 Brown) — Trunk Base #1 & Bottom Service Cover"),
        ("Plate_2_SingleColor_Brown_Trunk_Upper_And_Covers", "Plate 2 (Single-Color T1 Brown) — Trunk Mid #2, Trunk Top #3, Battery Cover, 3× Conduit Covers & Motor Adapter"),
        ("Plate_3_SingleColor_Brown_Brackets_01_To_12", "Plate 3 (Single-Color T1 Brown) — 12× Exact-Radius Station Brackets (#1 to #12)"),
        ("Plate_4_SingleColor_Brown_Brackets_13_To_24", "Plate 4 (Single-Color T1 Brown) — 12× Exact-Radius Station Brackets (#13 to #24)"),
        ("Plate_5_SingleColor_Green_Track_01", "Plate 5 (Single-Color T2 Green) — Dedicated Full-Scale Track Segment 01 (Return Ramp, 230.8×230.1 mm)"),
        ("Plate_6_SingleColor_Green_Track_02", "Plate 6 (Single-Color T2 Green) — Dedicated Full-Scale Track Segment 02"),
        ("Plate_7_SingleColor_Green_Track_03", "Plate 7 (Single-Color T2 Green) — Dedicated Full-Scale Track Segment 03"),
        ("Plate_8_SingleColor_Green_Track_04", "Plate 8 (Single-Color T2 Green) — Dedicated Full-Scale Track Segment 04"),
        ("Plate_9_SingleColor_Green_Track_05_And_13", "Plate 9 (Single-Color T2 Green) — Full-Scale Track Segments 05 & 13 (Side-by-Side)"),
        ("Plate_10_SingleColor_Green_Track_06_And_12", "Plate 10 (Single-Color T2 Green) — Full-Scale Track Segments 06 & 12 (Side-by-Side)"),
        ("Plate_11_SingleColor_Green_Track_07_And_11", "Plate 11 (Single-Color T2 Green) — Full-Scale Track Segments 07 & 11 (Side-by-Side)"),
        ("Plate_12_SingleColor_Green_Track_08_And_10", "Plate 12 (Single-Color T2 Green) — Full-Scale Track Segments 08 & 10 (Side-by-Side)"),
        ("Plate_13_SingleColor_Green_Track_09_And_14", "Plate 13 (Single-Color T2 Green) — Full-Scale Track Segments 09 & 14 (Top Entry, Side-by-Side)"),
        ("Plate_14_SingleColor_Gold_Auger_And_Drive", "Plate 14 (Single-Color T3 Gold) — Archimedes Auger Halves & Hex Coupler"),
        ("Plate_15_SingleColor_Red_Apple_Marbles", "Plate 15 (Single-Color T4 Red) — 12× Glowing Apple Hemispheres A/B (6× Complete Marbles)"),
        ("Plate_16_MultiColor_Topper_And_Wand", "Plate 16 (4-Color Tree Palette) — Unified Apple Topper (with Stem & Leaf) & Magic LED Wand"),
        ("Plate_17_MultiColor_Planets_Warm_And_Gas_Giants", "Plate 17 (4-Color Warm Palette: Umber/Alabaster/Gold/Crimson) — Mercury, Venus, Mars, Jupiter & Saturn"),
        ("Plate_18_MultiColor_Planets_Ocean_And_Ice_Giants", "Plate 18 (4-Color Ocean/Ice Palette: Cobalt/Emerald/Ice White/Gold) — Earth, Uranus & Neptune"),
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
            "subtitle": "1a) Mount 5.5×2.1mm DC Barrel Jack (J1) in rear -X Ø11.40mm port → 1b) Slide 12V 150RPM N20 Motor (Option B) or 6V LA002 (Option A) up into Ø28.0 mm Shroud Tower",
            "camera_target": [0, 0, 42],
            "camera_pos": [195, -205, 110],
            "hardware": [
                "1a. Place Bark-Textured Trunk_Base (#1, Ø185mm diagonal root footprint, Ø135×50mm Hollow Root Vault) flat on build surface and thread the 5.5×2.1mm DC Barrel Jack (J1, DC-099) into the rear -X Ø11.40 mm port (Z = 10.0 mm)",
                "1b. Slide the 12V 150rpm N20 Gear Motor (Option B primary drop-in, or 6V LA002 for Option A) + Servo_Or_030_Adapter up into the central Ø28.0 mm Isolated Motor Shroud Tower (D-shaft pointing up through Z=27.2 mm roof bore)",
                "1c. Route the 2-wire motor lead out the bottom -Y shroud wire exit notch (6.5×7.6 mm) so loose cables in the vault can never rub against the spinning clutch or auger",
            ],
            "clearance_note": "The central Ø28.0 mm Isolated Motor & Clutch Shroud Tower physically walls off the spinning N20 motor and coupler from the >150 cm³ open Cable Slack Dump Zone.",
        },
        {
            "step": 2,
            "title": "Step 2 — Install 12V→5V Buck Converter, WAGO 221 Lever Nuts & M5Stack (A092 + C008) in Root Vault",
            "subtitle": "2a) Seat A092+C008 & 12V→5V 5A Buck in vault cradles → 2b) Wire WAGO-1..4 with inline fuses (cap Grove Red +5V!) → 2c) Close Battery_Cover & Base_Bottom_Cover",
            "camera_target": [0, -20, 22],
            "camera_pos": [175, -195, 78],
            "hardware": [
                "2a. Seat M5Stack ATOM Lite (C008) + Atomic H-Driver Base (A092) into the -Y cradle (powered from WAGO-1 +12V_BUS via 2A fuse F1 into VIN/GND; A092's internal buck powers C008 with zero USB cable needed) and seat the 12V→5.0V 5A screw-terminal Buck Converter into the +X cradle (fed via 3A fuse F2)",
                "2b. Clamp the 12V 150RPM N20 Motor leads into A092 M1/M2 (or wire Option A 12V→6V buck + H-bridge for 6V LA002), plug the A096 Grove2Dupont cable into C008 (leave A096 Red +5V wire CAPPED in an empty WAGO port to prevent 5V backfeeding!), and connect the 5V Buck output (+ 1000µF cap) to WAGO-3 (+5V_LED) & WAGO-4 (GND_LED)",
                "2c. Secure Battery_Cover and snap on Base_Bottom_Cover (3.0 mm thick with ventilation louvers, 4× captive-magnet tabs, and an upward Ø23.60×2.8 mm Snap-In Hollow Retaining Ring that clicks concentrically into Trunk_Base's central Ø24.00 mm shroud bore with zero screws needed!)",
            ],
            "clearance_note": "With >150 cm³ of unobstructed perimeter volume inside the Ø135×50 mm Hollow Root Vault and >= 18 mm finger gap around every cradle, WAGO 221 lever nuts and inline fuse holders fit cleanly with zero soldering.",
        },
        {
            "step": 3,
            "title": "Step 3 — Press Gold Hex Coupler (Motor_Clutch_Driver) Onto N20 Motor D-Shaft",
            "subtitle": "Lower Motor_Clutch_Driver straight down through the Trunk_Base bore onto the N20 motor's D-shaft at Z = 26.2 mm",
            "camera_target": [0, 0, 36],
            "camera_pos": [155, -160, 95],
            "hardware": [
                "3a. Align the flat inside Motor_Clutch_Driver's bottom D-bore with the flat on the LA002 N20 motor shaft",
                "3b. Press down firmly until seated at Z = 26.2 mm with its 4.85 mm AF male hex peg pointing straight up",
            ],
            "clearance_note": "Direct positive hex drive eliminates magnet slippage while allowing the auger to lift straight out from above.",
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
            "title": "Step 6 — Slide In All 24 Exact-Radius Cantilever Brackets (#1 at 60° → #24 at 1440°)",
            "subtitle": "Sort Plates 3 & 4's 24 brackets by their engraved top-saddle number (1 to 24) and slide each dovetail tenon down into its 60° trunk socket",
            "camera_target": [0, 0, 215],
            "camera_pos": [310, -295, 250],
            "hardware": [
                "6a. Lower 6 Stations (#1–#6 on Plate 3, engraved '1'..'6' on the top saddle floor): slide into the lowest 6 trunk dovetail sockets (60°–360°, radii 141.9 mm down to 126.1 mm)",
                "6b. Middle 12 Stations (#7–#12 on Plate 3 & #13–#18 on Plate 4, engraved '7'..'18'): slide in ascending spiral order into the middle trunk sockets (420°–1080°, radii 123.0 mm down to 88.3 mm, including the precision cross-seam dovetails at Z = 150 mm and Z = 300 mm)",
                "6c. Upper 6 Stations (#19–#24 on Plate 4, engraved '19'..'24'): slide into the highest 6 trunk sockets (1140°–1440°, radii 85.2 mm down to 69.4 mm)",
            ],
            "clearance_note": "Every single bracket (#1–#12 on Plate 3, #13–#24 on Plate 4) is custom-sized to the exact conical helix radius at its 60° station and prints upright on Z=0 with a flat bottom rib (zero supports!).",
        },
        {
            "step": 7,
            "title": "Step 7 — Snap Together Helical Track Segments 01 → 14 (Built-In Male/Female Tenons + Seam Brackets)",
            "subtitle": "Slide each segment's downhill Female Sockets onto the previous segment's Twin Ø3.8mm Male Snap-Lock Tenon Pegs + Sidewall Tongues and click onto the 24 Bracket Pegs",
            "camera_target": [0, 0, 220],
            "camera_pos": [370, -350, 275],
            "hardware": [
                "7a. Dock track_seg_01's bottom return ramp into Trunk_Base's -Y intake port (Z = 50 mm) and click its underside sockets onto the Tier #4 bracket pegs at 60° and 120°",
                "7b. Snap track_seg_02 → track_seg_13 together in ascending order: each segment's uphill end has Twin Ø3.80×5.0 mm Under-Shoulder Male Snap-Lock Tenon Pegs (u = ±14.2 mm, v = -4.2 mm, with Ø4.08 mm detent rings) + Inner/Outer Sidewall Anti-Torsion Tongues that click directly into the next segment's Ø4.30×5.6 mm Female Sockets, while the even-60° cantilever brackets lock into the underside seam sockets!",
                "7c. Dock track_seg_14_top_entry into Trunk_Top's -Y discharge chute (Z = 431.4 mm) and snap its downhill socket onto track_seg_13's male tenon pegs at 1560°.",
            ],
            "clearance_note": "Every track seam locks in 3D via Twin Ø3.8mm Under-Shoulder Snap-Tenons + Sidewall Anti-Torsion Tongues (0.000 mm³ collision, 84.1 mm³ shear lock) and Even-60° Underside Seam Bracket Sockets!",
        },
        {
            "step": 8,
            "title": "Step 8 — Snap In BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Wire (B0CCS11V7H) & Connect to Grove GPIO26 + WAGO-3/4",
            "subtitle": "8a) Seat B0CCS11V7H starter pocket under track_seg_01 → 8b) Snap 50-LED Pebble wire into 4.6mm dovetail throat up Seg 01→14 → 8c) Connect Data to GPIO26 & Power to 5V Buck (WAGO-3/4)",
            "camera_target": [0, -15, 195],
            "camera_pos": [340, -340, 210],
            "hardware": [
                "8a. Seat the starter end of the BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Flexible Wire (B0CCS11V7H) into the 10.0×16.0 mm starter pocket underneath track_seg_01 (theta = -70°)",
                "8b. Press the 360°-flexible 3-wire cord and 6.2×3.2 mm oval Pebble LEDs through the 4.6 mm snap-in throat into the 8.0×3.6 mm internal dovetail chamber all the way up to Segment 14 (zero glue or tape needed!)",
                "8c. Route the pre-terminated 3-pin JST-SM input plug (and power-injection pigtails) through Trunk_Base's cob_wire_conduit into the Hollow Root Vault: connect White Data to Grove GPIO26 and clamp Red (+5V) / Black (GND) into WAGO-3 (+5V_LED) & WAGO-4 (GND_LED) fed by the dedicated 12V→5V 5A buck converter",
            ],
            "clearance_note": "The track's 8.0×3.6 mm underside dovetail chamber has a 4.6 mm snap-in throat (with 45° self-supporting retention lips) that mechanically locks both the 6.2 mm oval Pebble LEDs and 3-wire cord in place with zero glue or tape.",
        },
        {
            "step": 9,
            "title": "Step 9 — Thread Topper Cable Through 10×8mm Conduit, Snap On Conduit_Cover_Strip & Seat Apple Topper (#4)",
            "subtitle": "9a) Thread pre-terminated JST-SM plug straight through 10×8mm rear (-X) conduit to GPIO32 & WAGO-3/4 → 9b) Seat Sparkleiot 16-Bit Ring → 9c) Place Apple Topper (#4)",
            "camera_target": [0, 0, 465],
            "camera_pos": [225, -225, 525],
            "hardware": [
                "9a. Thread the pre-terminated 1m 3-Pin JST-SM Extension Cable (B0CT827QQC) straight down the oversized 10.0×8.0 mm rear (-X) Connector-Pass-Through conduit into the Hollow Root Vault (connect Center Data to Grove Yellow GPIO32 and +5V/GND to WAGO-3 & WAGO-4), then press-fit the brown Conduit_Cover_Strip flush into the groove",
                "9b. Seat the Ø45.0 mm Sparkleiot 16-Bit WS2812 RGB LED Ring (B09YTMNGTD) flat into the Ø46.2×2.5 mm recessed ring seat on the top rim of Trunk_Top (#3 at Z = 447.5 mm)",
                "9c. Lower the Sculpted Heart-Shaped Crimson Apple Topper (#4, with Woody Stem & Emerald Leaf) onto Trunk_Top's upward Ø59.40×4.0 mm Crown Centering Tenon Collar (which telescopes inside the topper's Ø60.00 mm base socket with 0.30 mm radial clearance so the topper locks concentrically onto the trunk!)",
            ],
            "clearance_note": "The upgraded 10.0 mm wide × 8.0 mm deep rear (-X) conduit lets pre-terminated JST-SM, PH2.0, SH1.0, and Dupont plugs pass straight through without cutting or de-pinning wires!",
        },
        {
            "step": 10,
            "title": "Step 10 — Insert 8 Magnetic Switch LEDs Into Upgraded 4-Color Planets #8 → #1 & Snap-Click Onto Balconies",
            "subtitle": "For each larger 4-color sculpted planet (#8 Neptune at bottom to #1 Mercury at top): insert its wireless Magnetic Switch LED and snap-click onto Balcony Peg #8 → #1",
            "camera_target": [0, 0, 235],
            "camera_pos": [395, -380, 290],
            "hardware": [
                "10a. Press 1× wireless Bambu Single LED Magnetic Control Switch Light (Ø7.5×6.0 mm) through the 45° self-centering entry funnel into the upper Ø8.0×6.0 mm LED chamber of each Planet (#8 Neptune → #1 Mercury)",
                "10b. Match the hidden number inside each planet's bottom bore (8..1) with the number engraved on top of each Track Balcony Peg (8..1) and press down until the internal Ø8.44 mm detent groove clicks onto the peg's Ø8.12 mm snap bead",
            ],
            "clearance_note": "Each upgraded 4-color planet is 40–55% larger in diameter with an integrated Ø13.6 mm Orbital Pedestal Foot Collar that raises the globe and rings above the track wall and rolling marbles (0.000 mm³ collision!).",
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
            "return_chute_end_deg": -62.0,
            "return_chute_end_r": 25.0,
            "top_feeder_start_deg": 1700.0,
            "top_feeder_start_r": 35.0,
            "top_feeder_rise_z": 17.55,
            "auger_pitch": 48.0,
            "auger_ball_orbit_r": 25.0,
            "auger_z_start": 47.0,
            "auger_z_end": 435.5,
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
