"""Centralized parametric constants and conical helix equations for the
Grav-Mass Day 'Falling Apple Cascade' modular 3D-printable marble run tree.

Target Printer: Snapmaker U1 (Max build envelope per part: 260 x 260 x 280 mm).
All dimensions are in millimeters (mm) and angles in degrees unless noted.
"""

from __future__ import annotations

import math
import build123d as bd

# ---------------------------------------------------------------------------
# Global Manufacturing Constraints & Sizing (Snapmaker U1)
# ---------------------------------------------------------------------------
MAX_BUILD_X = 260.0
MAX_BUILD_Y = 260.0
MAX_BUILD_Z = 280.0

U1_BED_X = 270.0
U1_BED_Y = 270.0
U1_BED_Z = 270.0
SAFE_PLATE_ZONE = 235.0
MIN_PART_CLEARANCE = 12.0
ORCA_PLATE_STRIDE_X = 324.0
ORCA_PLATE_STRIDE_Y = 324.0

# ---------------------------------------------------------------------------
# Snapmaker U1 4-Toolhead Color & Filament Mapping
# ---------------------------------------------------------------------------
TOOLHEAD_PALETTE: dict[int, dict[str, str]] = {
    1: {
        "name": "Dark Wood Brown",
        "hex": "#4A2F1D",
        "filament_type": "PLA",
        "description": "PLA/PETG Matte Brown (Trunk & Cantilever Brackets)",
    },
    2: {
        "name": "Translucent Emerald Green",
        "hex": "#00A86B",
        "filament_type": "PETG",
        "description": "Translucent Green PETG (Helical Track Segments)",
    },
    3: {
        "name": "Silk Gold / Brass",
        "hex": "#D4AF37",
        "filament_type": "PLA",
        "description": "Silk Gold PLA (Apple Topper, Auger Halves, Jupiter, Saturn)",
    },
    4: {
        "name": "Glossy Crimson Red",
        "hex": "#C41E3A",
        "filament_type": "PLA",
        "description": "Silk Red PLA (Rolling Apple Marbles, Topper Stem/Leaf, Mars, Earth)",
    },
}


def assign_toolhead(part: bd.Solid, label: str, toolhead_id: int) -> bd.Solid:
    """Assign build123d Color, label, and toolhead metadata to a Solid part."""
    spec = TOOLHEAD_PALETTE[toolhead_id]
    part.color = bd.Color(spec["hex"])
    part.label = label
    part.toolhead_id = toolhead_id  # type: ignore[attr-defined]
    part.hex_color = spec["hex"]    # type: ignore[attr-defined]
    return part

# ---------------------------------------------------------------------------
# Core Specified Parametric Constants
# ---------------------------------------------------------------------------
BALL_DIAMETER = 25.0

TRACK_INNER_WIDTH = 34.0
TRACK_INNER_WALL_H = 12.0
TRACK_OUTER_WALL_H = 18.0

LED_CHANNEL_W = 8.0                         # 8.0 mm internal dovetail chamber width (fits Ø6.2×3.2 mm B0CCS11V7H WS2812B Pebble LEDs)
LED_CHANNEL_THROAT_W = 4.6                  # 4.6 mm snap-in throat opening (retains Pebble LEDs & 3-wire cord without glue/tape)
LED_CHANNEL_D = 3.6                         # 3.6 mm total channel depth (v = -12.0..-8.4 mm, 45° self-supporting retention lips)

AUGER_BORE_DIA = 41.0
AUGER_OD = 38.0
AUGER_SHAFT_DIA = 9.0
AUGER_PITCH = 46.0
AUGER_BALL_ORBIT_R = 17.5
AUGER_FLUTE_R = 13.3
AUGER_LIFT_ANGLE_DEG = -90.0

HELIX_TOP_R = 60.0
HELIX_BOT_R = 145.0
HELIX_PITCH = 79.0
HELIX_TURNS = 4.5

FIT_TOLERANCE = 0.20

# ---------------------------------------------------------------------------
# Official Bambu Lab CyberBrick Hardware Dimensions & Clearances
# (ZK004 Beginner Kit / ZK003 Ultimate Kit + LA002 N20 Motor)
# ---------------------------------------------------------------------------
SLIP_FIT_CLEARANCE = FIT_TOLERANCE          # 0.20 mm radial (0.40 mm diametrical)
DOVETAIL_CLEARANCE = 0.15                   # 0.15 mm radial clearance on 45-deg dovetails
HEX_COUPLE_CLEARANCE = 0.15                 # 0.15 mm clearance for auger hex joint

# 1. CyberBrick Magnet (CA001 — Nominal Ø 4.0 x 2.0 mm)
CA001_MAGNET_NOMINAL_DIA = 4.00
CA001_MAGNET_NOMINAL_H = 2.00
MAGNET_DIA = 4.25                           # Ø 4.25 mm captive cavity for CA001 4x2 mm magnet
MAGNET_DEPTH = 2.20                         # 2.20 mm height for CA001 4x2 mm magnet
MAGNET_SKIN_THICKNESS = 0.40                # 0.40 mm (2-layer @ 0.20 mm) child-safe enclosing skin

# 2. CyberBrick Machine Screw (AA050 — M2.5 x 6 mm BHCS)
AA050_M25_TAP_DIA = 2.25                    # Ø 2.25 mm self-tapping M2.5 boss hole
AA050_M25_TAP_DEPTH = 6.50                  # 6.50 mm boss hole depth
AA050_M25_THROUGH_DIA = 2.75                # Ø 2.75 mm M2.5 clearance through-hole
AA050_M25_CBORE_DIA = 5.00                  # Ø 5.00 mm button-head counterbore
AA050_SCREW_LENGTH = 6.00

# 3. Receiver Stack (XA004 Receiver Shield + XA003 Core Board) in Trunk_Base
XA004_RECEIVER_BAY_X = 48.0
XA004_RECEIVER_BAY_Y = 36.0
XA004_RECEIVER_BAY_Z = 22.0

# 4. 14500 Li-ion Battery Pack (7.4V 800mAh) & Power Switch (XA007) in Trunk_Base
BATTERY_14500_BAY_X = 54.0
BATTERY_14500_BAY_Y = 31.0
BATTERY_14500_BAY_Z = 16.5

XA007_SWITCH_BAY_X = 22.0
XA007_SWITCH_BAY_Y = 14.0
XA007_SWITCH_BAY_Z = 12.0

# 5. Auger Lift Motor (LA002 N20 150rpm Gear Motor + PG002 9g Servo / LA024 030 Gearbox Adapter)
LA002_N20_POCKET_X = 12.4
LA002_N20_POCKET_Y = 10.4
LA002_N20_POCKET_Z = 26.0

PG002_SERVO_BAY_X = 23.2
PG002_SERVO_BAY_Y = 12.5
PG002_SERVO_BAY_Z = 24.0

# 6. WS2812 LED Hub (XA006) & RGB LED Beads (KB003 — IDC0.8 4PIN)
XA006_HUB_BAY_X = 26.0
XA006_HUB_BAY_Y = 18.0
XA006_HUB_BAY_Z = 8.0

KB003_LED_SOCKET_X = 10.5
KB003_LED_SOCKET_Y = 8.5
KB003_LED_SOCKET_Z = 5.0

# 7. Topper Release Gate Servo (PG001 — 180° 9g Servo with Clutch Protection)
PG001_SERVO_BAY_X = 23.2
PG001_SERVO_BAY_Y = 12.5
PG001_SERVO_BAY_Z = 24.0

# 8. Handheld "Newton's Apple" Wireless Remote (XA005 + XA003 + AAA Battery Case + Controls)
XA005_TX_BAY_X = 48.0
XA005_TX_BAY_Y = 36.0
XA005_TX_BAY_Z = 18.0

AAA_BATTERY_BOX_X = 54.0
AAA_BATTERY_BOX_Y = 38.0
AAA_BATTERY_BOX_Z = 14.0

XA009_JOYSTICK_CUTOUT_DIA = 20.0
XA010_ROCKER_CUTOUT_X = 19.5
XA010_ROCKER_CUTOUT_Y = 13.0
XA008_BUTTON_CUTOUT_DIA = 12.2

STEEL_BALL_DIA = 12.70                      # 1/2-inch (12.7 mm) steel ball bearing weight core
STEEL_BALL_CAVITY_DIA = 13.10               # Ø 13.1 mm internal clearance cavity for steel bearing / AA050 cluster
HEMISPHERE_SNAP_CLEARANCE = 0.15            # 0.15 mm radial snap clearance on split Apple hemispheres

PUCK_SOCKET_DIA = 60.0                      # Legacy reference constant
PUCK_SOCKET_DEPTH = 19.0

# ---------------------------------------------------------------------------
# Trunk, Hollow Root Vault, Snap-In Cradles & Connector-Pass-Through Conduit
# ---------------------------------------------------------------------------
TRUNK_TOTAL_HEIGHT = 450.0
TRUNK_NUM_SECTIONS = 3
TRUNK_SECTION_HEIGHT = 150.0                # 3 x 150 mm = 450 mm total vertical trunk height
TRUNK_OUTER_DIA = 68.0
TRUNK_OUTER_R = TRUNK_OUTER_DIA / 2.0       # 34.0 mm outer radius (houses Ø41 bore + Ø26.6 ball lift flute)
TRUNK_BASE_FLANGE_DIA = 185.0               # Ø 185.0 mm diagonal root-tip footprint (150x150 mm cardinal AABB)
TRUNK_BASE_FLANGE_R = TRUNK_BASE_FLANGE_DIA / 2.0
TRUNK_FLARE_HEIGHT = 50.0

ROOT_VAULT_CLEAR_DIA = 135.0                # Ø 135.0 mm internal clear electronics vault diameter
ROOT_VAULT_CLEAR_R = ROOT_VAULT_CLEAR_DIA / 2.0
ROOT_VAULT_CLEAR_H = 50.0                   # 50.0 mm tall internal electronics vault beneath bulkhead
ROOT_VAULT_MIN_SLACK_VOL_MM3 = 150_000.0    # >= 150,000 mm³ (150 cm³) unobstructed Cable Slack Dump Zone
MOTOR_SHROUD_OD = 28.0                      # Ø 28.0 mm protective cylindrical shroud around motor & clutch

ATOM_LITE_CRADLE_X = 24.5                   # 24.5 x 24.5 x 10.6 mm M5Stack ATOM Lite (C008) snap-in cradle
ATOM_LITE_CRADLE_Y = 24.5
ATOM_LITE_CRADLE_Z = 10.6
ATOM_LITE_FRONT_CLEARANCE_MM = 30.0         # >= 30.0 mm straight unobstructed cable clearance in front of Grove/pins
BOARD_BAY_MIN_SPACING_MM = 18.0             # >= 18.0 mm spacing between IA005 PDB, MOSFET driver & motor shroud

UCTRONICS_BUCK_BAY_X = 64.2                 # UCTRONICS B07XXWQ49N (U6223, 63.0 x 27.0 x 10.0 mm) 5V 5A buck bay
UCTRONICS_BUCK_BAY_Y = 28.2
UCTRONICS_BUCK_BAY_Z = 12.0

WAGO_221_BAY_X = 19.8                       # WAGO 221-415 (30.0 x 18.6 x 8.4 mm) dual-stack lever-nut bay
WAGO_221_BAY_Y = 31.2
WAGO_221_BAY_Z = 18.0

IA005_PDB_BAY_X = 10.6                      # Legacy Bambu IA005 4-Ch PDB bay (10.6 x 53.6 x 10.6 mm)
IA005_PDB_BAY_Y = 53.6
IA005_PDB_BAY_Z = 10.6

DUAL_MOSFET_BAY_X = 24.0                    # Legacy Dual-Channel MOSFET bay (24.0 x 18.0 x 12.0 mm)
DUAL_MOSFET_BAY_Y = 18.0
DUAL_MOSFET_BAY_Z = 12.0

DC_BARREL_JACK_BORE_DIA = 11.4              # Ø 11.40 mm clearance bore for M11x0.75 (DC-099 5.5x2.1mm 12V panel jack)
DC_BARREL_JACK_Z_CENTER = 10.0              # Z = 10.0 mm center height on rear (-X) root flange of trunk_base

TENON_HEIGHT = 15.0                         # 15 mm interlocking male/female joint height
TENON_NOMINAL_R = 27.5                      # Nominal coupling interface radius (between R_bore=20.5 and R_out=34.0)
TENON_KEY_FLAT_DEPTH = 2.0                  # 2 mm keyed flat to prevent axial twisting

WIRE_CONDUIT_W = 10.0                       # 10.0 mm wide x 8.0 mm deep connector-pass-through trunk conduit
WIRE_CONDUIT_D = 8.0                        # Fits JST-SM / SH1.0 / PH2.0 / Dupont plugs & inline switch without cutting
CONDUIT_COVER_STRIP_H = 68.0                # Snap-on brown cover strip height (68.0 x 10.2 x 2.6 mm)
BASE_BOTTOM_COVER_THICK = 3.0               # 3.0 mm thick twist-lock / magnetic ventilated bottom service lid

# Dovetail socket parameters (45-deg overhang, downward tapered)
DOVETAIL_RADIAL_DEPTH = 4.5                 # Radial depth into trunk wall (R=34.0 down to R=29.5)
DOVETAIL_NECK_W_TOP = 7.0                   # Entry neck width at top of slot
DOVETAIL_BASE_W_TOP = DOVETAIL_NECK_W_TOP + 2.0 * DOVETAIL_RADIAL_DEPTH  # 16.0 mm (45-deg walls)
DOVETAIL_TAPER_W = 0.8                      # Downward width taper over slot height for wedge lock
DOVETAIL_SLOT_H = 18.0                      # Active vertical engagement height of dovetail slot
DOVETAIL_ANGULAR_STEP_DEG = 60.0            # 60-deg increments along helical slope (6 per turn)

# ---------------------------------------------------------------------------
# Auger Parameters
# ---------------------------------------------------------------------------
AUGER_FLIGHT_THICKNESS = 2.4
AUGER_HALF_HEIGHT = 198.0                   # Two halves (2 x 198 = 396 mm, Z = 37.22..433.32 mm below Z=450 Lamp Puck)
AUGER_HEX_ACROSS_FLATS = 5.0
AUGER_HEX_HEIGHT = 10.0
N20_DSHAFT_DIA = 3.0
N20_DSHAFT_FLAT = 0.5

# ---------------------------------------------------------------------------
# Track Cross-Section & Segmentation Parameters
# ---------------------------------------------------------------------------
TRACK_TROUGH_R = 16.0
TRACK_SHOULDER_INNER_X = 13.0               # Flat shoulders from |u|=13.0 to |u|=17.0 mm
TRACK_HALF_INNER_W = TRACK_INNER_WIDTH / 2.0  # 17.0 mm
TRACK_INNER_WALL_THICK = 3.0                # Inner wall u in [-20.0, -17.0]
TRACK_OUTER_WALL_THICK = 3.6                # Outer wall u in [+17.0, +20.6] (houses 2.2 mm magnet pocket)
TRACK_OUTER_LIP_INSET = 1.0                 # 1.0 mm inward-angled retention lip
TRACK_BASE_Y = -12.0                        # Bottom datum face of track profile

TRACK_SEGMENT_ARC_DEG = 120.0               # 120-deg arc segments (3 per full rotation)
TRACK_SCARF_ANGLE_DEG = 15.0                # 15-deg angled scarf/lap joint in roll direction
TRACK_DOWEL_DIA = 2.0                       # Legacy reference dowel constant
TRACK_DOWEL_DEPTH = 6.0
TRACK_DOWEL_OFFSET_U = 14.2                 # Radial positions u = -14.2 and +14.2 mm (under flat shoulders, clear of u=±10.6 bracket sockets)
TRACK_DOWEL_OFFSET_V = -4.2                 # Vertical position v = -4.2 mm for male/female snap tenons

# Integrated Male-to-Female Snap-Lock Track Joint + Retrofittable Track_Joint_Clip
TRACK_TENON_PEG_DIA = 3.80                  # Twin Ø 3.80 mm male under-shoulder tenon pegs on uphill end
TRACK_TENON_SNAP_DIA = 4.08                 # Ø 4.08 mm annular snap-lock retention ring on male pegs
TRACK_TENON_LENGTH = 5.0                    # 5.0 mm male tenon protrusion into Ø 4.30 x 5.60 mm female socket
TRACK_SIDEWALL_TAB_LEN = 2.8                # 2.8 mm inner & outer sidewall anti-torsion tongue tabs
TRACK_JOINT_CLIP_LEN = 16.0                 # 16.0 mm snap-on underside U-cradle splice clamp length

BRACKET_PEG_DIA = 4.0                       # Nominal twin alignment peg diameter on bracket top
BRACKET_PEG_SPACING_U = 10.6                # Pegs at u = -10.6 and +10.6 mm (straddling 13.0 mm RGBIC COB LED slot)
BRACKET_PEG_HEIGHT = 4.5
BRACKET_EYELET_DIA = 2.5                    # 2.5 mm acoustic bell/chime hanging hole

# ---------------------------------------------------------------------------
# Conical Helix Equations
# ---------------------------------------------------------------------------
HELIX_TOTAL_DEG = HELIX_TURNS * 360.0       # 1620.0 degrees
HELIX_TOTAL_HEIGHT = HELIX_TURNS * HELIX_PITCH  # 355.5 mm
HELIX_Z_START = 62.5                        # Bottom track height at theta=0° (Z_marble = 69.3 mm)
HELIX_Z_END = HELIX_Z_START + HELIX_TOTAL_HEIGHT  # 418.0 mm at theta=1620° (below Z=450 Lamp Puck)

# Closed-loop spiral extensions:
#   - Bottom Return Collector & Queueing Ramp: theta = 0.0° (R=145, Z=62.5) -> -90.0° (-Y axis, R=42.0, Z=48.5)
#   - Topper-to-Track Enclosed Catch Basin   : theta = 1715.0° (-Y/+X, R=42.5, Z=425.0) -> 1620.0° (-X, R=60, Z=418.0)
RETURN_CHUTE_END_DEG = -90.0
RETURN_CHUTE_END_R = 42.0
RETURN_CHUTE_DROP_Z = 14.0

TOP_FEEDER_START_DEG = 1710.0
TOP_FEEDER_START_R = 42.5
TOP_FEEDER_RISE_Z = 7.0


def helix_fraction(theta_deg: float) -> float:
    """Return normalized parameter u in [0, 1] along the 4.5-turn helix."""
    return float(theta_deg) / HELIX_TOTAL_DEG


def helix_radius(theta_deg: float) -> float:
    """Conical helix centerline radius R(theta) tapering from HELIX_BOT_R to HELIX_TOP_R."""
    u = helix_fraction(theta_deg)
    return HELIX_BOT_R + (HELIX_TOP_R - HELIX_BOT_R) * u


def helix_z(theta_deg: float) -> float:
    """Conical helix elevation Z(theta) rising at HELIX_PITCH per 360 degrees."""
    return HELIX_Z_START + HELIX_PITCH * (float(theta_deg) / 360.0)


def helix_point(theta_deg: float) -> bd.Vector:
    """3D centerline point on the conical helix at angle theta_deg."""
    r = helix_radius(theta_deg)
    rad = math.radians(theta_deg)
    return bd.Vector(r * math.cos(rad), r * math.sin(rad), helix_z(theta_deg))


def helix_tangent(theta_deg: float) -> bd.Vector:
    """Unit tangent vector along increasing theta_deg of the conical helix."""
    rad = math.radians(theta_deg)
    r = helix_radius(theta_deg)
    dr_dtheta = (HELIX_TOP_R - HELIX_BOT_R) / math.radians(HELIX_TOTAL_DEG)
    dz_dtheta = HELIX_PITCH / (2.0 * math.pi)
    dx = dr_dtheta * math.cos(rad) - r * math.sin(rad)
    dy = dr_dtheta * math.sin(rad) + r * math.cos(rad)
    dz = dz_dtheta
    return bd.Vector(dx, dy, dz).normalized()


def helix_section_plane(theta_deg: float, scarf_tilt_deg: float = 0.0) -> bd.Plane:
    """Return a local coordinate plane at theta_deg on the conical helix.

    Local X (u): radially outward from the trunk axis.
    Local Y (v): vertical (+Z), optionally tilted forward along the tangent by
                 scarf_tilt_deg to form the 15-degree angled scarf/lap joint.
    Local Z (w): orthogonal to X and Y along the helix progression direction.
    """
    pt = helix_point(theta_deg)
    rad = math.radians(theta_deg)
    r_dir = bd.Vector(math.cos(rad), math.sin(rad), 0.0)
    t_dir = bd.Vector(-math.sin(rad), math.cos(rad), 0.0)
    z_dir = bd.Vector(0.0, 0.0, 1.0)
    tilt_rad = math.radians(scarf_tilt_deg)
    y_dir = (z_dir * math.cos(tilt_rad) + t_dir * math.sin(tilt_rad)).normalized()
    z_norm = r_dir.cross(y_dir).normalized()
    return bd.Plane(origin=pt, x_dir=r_dir, z_dir=z_norm)


def closed_loop_track_point(theta_deg: float) -> bd.Vector:
    """Return 3D centerline point along the complete closed-loop track path:
      - theta in [RETURN_CHUTE_END_DEG, 14.0): C2-smooth bottom inward spiral return & queuing ramp
        (tangent-continuous transition below Gate G5 at 15.0° with R_curv >= 38.6 mm down to
        Z = 50.0 mm at -90° on the -Y axis).
      - theta in [14.0, HELIX_TOTAL_DEG]: Continuous analytical conical helix.
      - theta in (HELIX_TOTAL_DEG, TOP_FEEDER_START_DEG]: Top inward spiral catch basin from the
        trunk_top -Y discharge spout at 1715° (R = 42.5 mm, Z = 425.0 mm) down to 1620° (R = 60.0 mm, Z = 418.0 mm).
    """
    t_bot_start = 14.0
    if theta_deg < t_bot_start:
        span = t_bot_start - RETURN_CHUTE_END_DEG  # 104.0 deg
        w = max(0.0, min(1.0, (t_bot_start - theta_deg) / span))
        s = (4.0 * w * w + 18.0 * w * w * w) / (1.0 + 4.0 * w * w + 17.0 * w * w * w)
        r_helix = HELIX_BOT_R + (HELIX_TOP_R - HELIX_BOT_R) * (theta_deg / HELIX_TOTAL_DEG)
        r = r_helix * (1.0 - s) + RETURN_CHUTE_END_R * s
        z_start = helix_z(t_bot_start)
        z_end = HELIX_Z_START - RETURN_CHUTE_DROP_Z
        omw = 1.0 - w
        w_z = 1.62 * w - 0.62 * w * w + 0.72 * w * w * omw * omw
        z = z_start - (z_start - z_end) * w_z
        rad = math.radians(theta_deg)
        return bd.Vector(r * math.cos(rad), r * math.sin(rad), z)
    if theta_deg > HELIX_TOTAL_DEG:
        span = TOP_FEEDER_START_DEG - HELIX_TOTAL_DEG
        w = max(0.0, min(1.0, (theta_deg - HELIX_TOTAL_DEG) / span))
        s = w * w * (3.0 - 2.0 * w)
        r = (
            HELIX_TOP_R
            + (HELIX_TOP_R - HELIX_BOT_R)
            * ((theta_deg - HELIX_TOTAL_DEG) / HELIX_TOTAL_DEG)
            * (1.0 - s)
            - (HELIX_TOP_R - TOP_FEEDER_START_R) * s
        )
        z = HELIX_Z_END + TOP_FEEDER_RISE_Z * w
        rad = math.radians(theta_deg)
        return bd.Vector(r * math.cos(rad), r * math.sin(rad), z)
    return helix_point(theta_deg)


def closed_loop_section_plane(theta_deg: float, scarf_tilt_deg: float = 0.0) -> bd.Plane:
    """Return a local cross-section plane along the closed-loop track path."""
    pt = closed_loop_track_point(theta_deg)
    rad = math.radians(theta_deg)
    r_dir = bd.Vector(math.cos(rad), math.sin(rad), 0.0)
    t_dir = bd.Vector(-math.sin(rad), math.cos(rad), 0.0)
    t_bot_start = 14.0
    if theta_deg < t_bot_start or theta_deg > HELIX_TOTAL_DEG:
        eps = 0.25
        p_prev = closed_loop_track_point(theta_deg - eps)
        p_next = closed_loop_track_point(theta_deg + eps)
        tan_xy = bd.Vector(p_next.X - p_prev.X, p_next.Y - p_prev.Y, 0.0)
        if tan_xy.length > 1e-6:
            t_curve = tan_xy.normalized()
            if theta_deg < t_bot_start:
                w = max(0.0, min(1.0, (t_bot_start - theta_deg) / (t_bot_start - RETURN_CHUTE_END_DEG)))
                blend = math.sin(math.pi * (w ** 0.75))
            else:
                w = max(0.0, min(1.0, (theta_deg - HELIX_TOTAL_DEG) / (TOP_FEEDER_START_DEG - HELIX_TOTAL_DEG)))
                blend = math.sin(math.pi * w)
            t_dir = (t_dir * (1.0 - blend) + t_curve * blend).normalized()
            r_dir = bd.Vector(t_dir.Y, -t_dir.X, 0.0).normalized()
    z_dir = bd.Vector(0.0, 0.0, 1.0)
    tilt_rad = math.radians(scarf_tilt_deg)
    y_dir = (z_dir * math.cos(tilt_rad) + t_dir * math.sin(tilt_rad)).normalized()
    z_norm = r_dir.cross(y_dir).normalized()
    return bd.Plane(origin=pt, x_dir=r_dir, z_dir=z_norm)


def make_engraved_label_solid(
    text: str,
    char_h: float = 4.0,
    depth: float = 0.75,
    stroke_w: float | None = None,
) -> bd.Shape:
    """Build a manifold 3D rectilinear 7-segment / block-stroke cutter for hidden assembly
    numbers and letters ('0'-'9', 'A', 'B').

    Centered at (X=0, Y=0, Z=0) with total Z thickness `2.0 * depth` (`Z in [-depth, +depth]`)
    so placing the cutter on a planar surface (`Z_local = 0`) cleanly debosses `depth` into the
    solid while extending `depth` into air (eliminating coplanar boolean faces).
    """
    t = stroke_w if stroke_w is not None else max(0.55, 0.22 * char_h)
    w = 0.64 * char_h
    h = char_h
    hz = 2.0 * depth
    pitch_x = w + 0.30 * char_h

    # Segment map in local character coordinates (dx, dy, bw, bh)
    qh = 0.25 * (h - t)
    vh = 0.50 * (h - t) + t
    seg_defs = {
        "TOP": (0.0, 0.5 * (h - t), w, t),
        "MID": (0.0, 0.0, w, t),
        "BOT": (0.0, -0.5 * (h - t), w, t),
        "TL": (-0.5 * (w - t), qh, t, vh),
        "TR": (0.5 * (w - t), qh, t, vh),
        "BL": (-0.5 * (w - t), -qh, t, vh),
        "BR": (0.5 * (w - t), -qh, t, vh),
        "CV": (0.0, 0.0, t, h),
        "C1_TOP": (-0.18 * w, 0.5 * (h - t), 0.36 * w + t, t),
        "B_TOP": (-0.08 * w, 0.5 * (h - t), 0.84 * w, t),
        "B_TR": (0.34 * (w - t), qh, t, vh),
        "G_IN": (0.22 * w, 0.0, 0.56 * w, t),
    }
    char_map = {
        "0": ("TOP", "BOT", "TL", "TR", "BL", "BR"),
        "1": ("CV", "BOT", "C1_TOP"),
        "2": ("TOP", "TR", "MID", "BL", "BOT"),
        "3": ("TOP", "TR", "MID", "BR", "BOT"),
        "4": ("TL", "MID", "TR", "BR"),
        "5": ("TOP", "TL", "MID", "BR", "BOT"),
        "6": ("TOP", "TL", "MID", "BL", "BR", "BOT"),
        "7": ("TOP", "TR", "BR"),
        "8": ("TOP", "MID", "BOT", "TL", "TR", "BL", "BR"),
        "9": ("TOP", "TL", "TR", "MID", "BR", "BOT"),
        "A": ("TOP", "TL", "TR", "MID", "BL", "BR"),
        "B": ("B_TOP", "MID", "BOT", "TL", "BL", "B_TR", "BR"),
        "G": ("TOP", "TL", "BL", "BOT", "BR", "G_IN"),
    }

    chars = [c for c in text.upper() if c in char_map]
    if not chars:
        chars = ["1"]

    n_c = len(chars)
    x_start = -0.5 * (n_c - 1) * pitch_x
    shape_accum: bd.Shape | None = None

    for idx, ch in enumerate(chars):
        cx = x_start + idx * pitch_x
        ch_solid: bd.Shape | None = None
        for s_key in char_map[ch]:
            dx, dy, bw, bh = seg_defs[s_key]
            box = bd.Pos(cx + dx, dy, 0.0) * bd.Box(
                bw,
                bh,
                hz,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
            )
            ch_solid = box if ch_solid is None else (ch_solid + box)
        if ch_solid is not None:
            shape_accum = ch_solid if shape_accum is None else (shape_accum + ch_solid)

    assert shape_accum is not None
    return shape_accum


# ---------------------------------------------------------------------------
# Galileo-Newton Gravity Chronometer Constants & Exact Arc-Length Equations
# ---------------------------------------------------------------------------
GRAVITY_STANDARD_MPS2 = 9.80665

# 6 Timing Gates (G0..G5) along the conical helix:
#   - G0 (1605°): Top Start Gate right below the top feeder curve
#   - G1 (1350°), G2 (990°), G3 (630°), G4 (270°): Front -Y Spine Gates (1.00 turn / 79.0 mm apart)
#   - G5 (15°)  : Bottom Finish Gate right above the 0° bottom return ramp
TIMING_GATE_ANGLES_DEG: tuple[float, ...] = (1605.0, 1350.0, 990.0, 630.0, 270.0, 15.0)


def _helix_arc_antideriv(r_val: float) -> float:
    """Closed-form antiderivative F(R) = 0.5 * (R*sqrt(R^2 + c^2) + c^2*ln(R + sqrt(R^2 + c^2)))."""
    dr_dtheta = (HELIX_TOP_R - HELIX_BOT_R) / math.radians(HELIX_TOTAL_DEG)
    dz_dtheta = HELIX_PITCH / (2.0 * math.pi)
    c2 = dr_dtheta * dr_dtheta + dz_dtheta * dz_dtheta
    sq = math.sqrt(r_val * r_val + c2)
    return 0.5 * (r_val * sq + c2 * math.log(r_val + sq))


def helix_arc_length_from_top(theta_deg: float) -> float:
    """Return exact 3D spiral arc length s (in mm) along the conical helix from
    theta = 1620.0° (top of main helix) down to `theta_deg` in [0.0, 1620.0].
    """
    theta_clamped = max(0.0, min(HELIX_TOTAL_DEG, float(theta_deg)))
    r_cur = helix_radius(theta_clamped)
    dr_dtheta_abs = abs((HELIX_TOP_R - HELIX_BOT_R) / math.radians(HELIX_TOTAL_DEG))
    return (_helix_arc_antideriv(r_cur) - _helix_arc_antideriv(HELIX_TOP_R)) / dr_dtheta_abs


def theta_for_helix_arc_length(s_from_top_mm: float) -> float:
    """Invert `helix_arc_length_from_top` via Newton-Raphson to find exact `theta_deg`
    at rolled distance `s_from_top_mm` (in mm) from theta = 1620.0°.
    """
    s_max = helix_arc_length_from_top(0.0)
    target = max(0.0, min(s_max, float(s_from_top_mm)))
    # Linear initial guess
    theta = HELIX_TOTAL_DEG * (1.0 - target / s_max)
    dr_dtheta = (HELIX_TOP_R - HELIX_BOT_R) / math.radians(HELIX_TOTAL_DEG)
    dz_dtheta = HELIX_PITCH / (2.0 * math.pi)
    c2 = dr_dtheta * dr_dtheta + dz_dtheta * dz_dtheta
    for _ in range(8):
        err = helix_arc_length_from_top(theta) - target
        r_cur = helix_radius(theta)
        ds_ddeg = -math.sqrt(r_cur * r_cur + c2) * (math.pi / 180.0)
        theta -= err / ds_ddeg
        theta = max(0.0, min(HELIX_TOTAL_DEG, theta))
    return theta




