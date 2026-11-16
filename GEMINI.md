# GEMINI.md — AI Engineering Knowledge Base & Design Invariants for Grav-Mass Tree

> [!IMPORTANT]
> **MANDATORY INSTRUCTIONS FOR FUTURE AI AGENTS:**
> 1. **Read Before Modifying:** Before changing any CAD geometry (`cad/*.py`) or 3D webapp logic (`webapp/*`), read this entire `GEMINI.md` document carefully. Every dimension, angle, and boolean rule documented here was learned by solving real physical, geometric, and OpenCascade B-Rep constraints.
> 2. **Verify Every Change:** After any CAD edit, you **must** run the full build, verification, and webapp export pipeline from `/home/ignacio/grav-mass`:
>    ```bash
>    uv run --with build123d python3 -u cad/generate_all.py && \
>    uv run --with build123d --with trimesh --with scipy --with rtree python3 -u cad/verify_model.py && \
>    uv run --with numpy python3 -u cad/export_webapp_assets.py
>    ```
> 3. **Update This File Continuously:** Whenever you discover a new geometric constraint, fix an OpenCascade/B-Rep boolean pitfall, change a parametric constant, or refine the mechanics/webapp, **you must update this `GEMINI.md` file** before completing your turn so future AI sessions inherit your findings.

---

## 1. Project Overview & Repository Structure

The **Grav-Mass Day "Falling Apple Cascade" Marble Run Tree** is a 3D-printable, motorized closed-loop kinetic sculpture (~527 mm tall, ~336 mm base diameter) engineered for multi-color FDM printing on the **Snapmaker U1** (4 toolheads, `270 × 270 × 270 mm` build volume, `240 × 240 mm` safe print zone).

```text
/home/ignacio/grav-mass/
├── GEMINI.md                     # AI engineering knowledge base & design invariants (KEEP UPDATED!)
├── README.md                     # Concise project overview, quick start, and documentation index
├── docs/                         # Split user/developer documentation (BOM.md, PRINTING.md, ASSEMBLY.md, PHYSICS.md, SMART_HOME.md, DEVELOPMENT.md, REFACTOR_NOTES.md)
├── bom/                          # Machine-readable BOM source of truth (bom.yaml) & generated spreadsheet (bom.csv)
├── scripts/
│   └── gen_bom.py                # Validates bom/bom.yaml and generates docs/BOM.md tables & bom/bom.csv (--check supported)
├── cad/
│   ├── common_params.py          # Single source of truth for all parametric constants & helix/spiral equations
│   ├── trunk.py                  # Trunk_Base (12V DC jack + UCTRONICS buck + WAGO + A092/C008 + N20), Trunk_Mid/Top, Bottom_Electronics_Lid, Conduit_Cover_Strip_*
│   ├── auger.py                  # 2-stage Archimedes screw (auger_lower, auger_upper) + Motor_Clutch_Driver (brown T1 + M2.5 clamp)
│   ├── brackets.py               # 26 exact-radius station cantilever brackets (bracket_01..26) + crowned saddles + keyhole tenons
│   ├── track.py                  # 14 helical track segments (8.0° stepped half-laps, split-tine sockets, planet balconies, ramps)
│   ├── topper_planets.py         # 4-color PLA Red Apple Topper, standalone PETG leaf, 8 PLA planets (crush ribs), Magic_LED_Wand, bayonet marbles
│   ├── export_3mf_plates.py      # Multi-body 3MF plate packer & validator (Plates 1–18 + unified 18-plate .3mf)
│   ├── export_webapp_assets.py   # Tessellates B-Rep solids + colored_subparts into webapp/assets/{manifest.json,meshes.bin}
│   ├── generate_all.py           # Master build script exporting 63 parts (.step + .stl) and all .3mf build plates
│   ├── verify_model.py           # Automated B-Rep manifold, interference, clearance, and 3D physics verification suite
│   └── audit_joints.py / audit_plates.py / test_coupons.py / retrofit_jig.py # Fit coupons, per-plate slicing gates & jig
├── output/
│   ├── *.step / *.stl            # Individual CAD parts (AP214 STEP + binary STL @ 0.01 mm deflection)
│   ├── full_tree_assembly.step   # Complete multi-part 3D assembly STEP
│   └── 3mf/                      # Ready-to-slice Snapmaker U1 multi-color .3mf build plates
└── webapp/
    ├── index.html                # Interactive Three.js WebGL simulator, assembly guide, and build-plate inspector
    ├── app.js                    # Physics simulation, Magic Wand interactive planet lighting, X-Ray, and camera modes
    ├── styles.css                # UI styling
    ├── assets/                   # Generated manifest.json + binary mesh bundle (meshes.bin)
    └── output -> ../output       # Relative symlink enabling direct .3mf and .step downloads from the webapp UI
```

---

## 2. Snapmaker U1 4-Toolhead Palette & Build-Plate Rules

All parts map to 4 toolheads defined in [`TOOLHEAD_PALETTE`](file:///home/ignacio/grav-mass/cad/common_params.py#L22-L54):

| Toolhead | Name | Material | Hex Color | Primary Parts & Sub-Components |
| :--- | :--- | :--- | :--- | :--- |
| **Toolhead 1 (`T1`)** | Matte Dark Wood Brown | PLA | `#4A2F1D` | `trunk_base`, `trunk_mid`, `trunk_top`, `Bottom_Electronics_Lid`, `Conduit_Cover_Strip_*`, `Motor_Clutch_Driver`, `bracket_01..26`, Apple Topper stem/collar, planet craters, Wand shaft |
| **Toolhead 2 (`T2`)** | Translucent Teal Green | PETG | `#00A86B` | **Plates 5–13 ONLY:** `track_seg_01..14` + standalone `apple_green_leaf` (never mixed onto PLA multi-color Plates 16–18!) |
| **Toolhead 3 (`T3`)** | Silk Gold / Brass | PLA | `#D4AF37` | `auger_lower`, `auger_upper`, planet rings/continents/zones, Wand star head & pommel |
| **Toolhead 4 (`T4`)** | Glossy Crimson Red | PLA | `#C41E3A` | `golden_apple_topper` body, `Apple_Hemisphere_A/B` marbles, Mars/Jupiter/Venus features, Wand bezel |

### Build-Plate Packing & OrcaSlicer 3MF Rules (`cad/export_3mf_plates.py`)
1. **Safe Print Zone:** Every plate must fit strictly inside **`240.0 × 240.0 mm`** (`X, Y in [-120.0, +120.0] mm` relative to plate center) and height `<= 270.0 mm`.
2. **Minimum Part Clearance:** Every distinct object on a build plate must maintain **`>= 8.0 mm` XY bounding-box clearance** (`MIN_PART_CLEARANCE = 8.0 mm`) from every other object on the same plate (`verify_model.py` and `export_3mf_plates.py` enforce this and raise a `RuntimeError` if violated).
3. **Flat Bed Adhesion (`Z = 0.00 mm`):** Every printable part must have its bottom face resting flat at `Z = 0.00 mm` with a substantial planar footprint (`>= 25 mm²`).
4. **18-Plate Layout (15 Pure Single-Color Plates + 3 Dedicated 4-Color PLA Plates):**
   - **Plates 1–4 (`100% Toolhead 1 — Dark Wood Brown #4A2F1D`, zero filament swaps):**
     - `Plate_1_SingleColor_Brown_Trunk_Base.3mf` (`trunk_base`)
     - `Plate_2_SingleColor_Brown_Trunk_Upper_And_Covers.3mf` (`Bottom_Electronics_Lid`, `trunk_mid`, `trunk_top`, `Conduit_Cover_Strip_Mid`, `Conduit_Cover_Strip_Top`, `Conduit_Cover_Strip_Base`, `Motor_Clutch_Driver`)
     - `Plate_3_SingleColor_Brown_Brackets_01_To_12.3mf` (`bracket_01`..`bracket_12`)
     - `Plate_4_SingleColor_Brown_Brackets_13_To_26.3mf` (`bracket_13`..`bracket_26`)
   - **Plates 5–13 (`100% Toolhead 2 — Translucent Teal Green #00A86B` PETG, zero filament swaps):**
     - `Plate_5_SingleColor_Green_Track_01.3mf`, `Plate_6..8` (`02..04`), `Plate_9` (`05, 13`), `Plate_10` (`06, 12`), `Plate_11` (`07, 11`), `Plate_12` (`08, 10`), `Plate_13_SingleColor_Green_Track_09_And_14.3mf` (`track_seg_09`, `track_seg_14_top_entry`, standalone `apple_green_leaf`).
   - **Plate 14 (`100% Toolhead 3 — Silk Gold #D4AF37` PLA, zero filament swaps):**
     - `Plate_14_SingleColor_Gold_Auger_And_Drive.3mf` (`auger_lower`, `auger_upper`)
   - **Plate 15 (`100% Toolhead 4 — Crimson Red #C41E3A` PLA, zero filament swaps):**
     - `Plate_15_SingleColor_Red_Apple_Marbles.3mf` (`6× apple_hemisphere_a_01..06`, `6× apple_hemisphere_b_01..06`)
   - **Plates 16–18 (`Dedicated 4-Color Single-Polymer PLA Plates`):**
     - `Plate_16_MultiColor_Topper_And_Wand.3mf` (`golden_apple_topper`, `Magic_LED_Wand` — PLA `T1 #4A2F1D, T2 #F5EFE6, T3 #D4AF37, T4 #C41E3A`)
     - `Plate_17_MultiColor_Planets_Warm_And_Gas_Giants.3mf` (`planet_mercury`, `planet_venus`, `planet_mars`, `planet_jupiter`, `planet_saturn` — PLA `T1 #4A2F1D, T2 #F5EFE6, T3 #D4AF37, T4 #C41E3A`)
     - `Plate_18_MultiColor_Planets_Ocean_And_Ice_Giants.3mf` (`planet_earth`, `planet_uranus`, `planet_neptune` — PLA `T1 #1E5AA8, T2 #D4AF37, T3 #F5EFE6, T4 #C41E3A`)
5. **OrcaSlicer Multi-Plate 2D Grid Alignment (`ORCA_PLATE_STRIDE_X = 324.0 mm`, `ORCA_PLATE_STRIDE_Y = 324.0 mm`):**
   - In Snapmaker OrcaSlicer / BambuStudio (`PartPlateList` in `PartPlate.cpp`), `N = 18` plates are arranged in a **`5 × 4` grid** (`cols = 5`, `rows = 4`) with `stride_x = 270.0 * 1.20 = 324.0 mm` and `stride_y = 270.0 * 1.20 = 324.0 mm`.
   - Plate `p_idx` (`0..17`) has `row = p_idx // 5`, `col = p_idx % 5`, origin `(col * 324.0, -row * 324.0)`, bed bounds `[col * 324.0 .. col * 324.0 + 270.0, -row * 324.0 .. -row * 324.0 + 270.0]`, and center `(col * 324.0 + 135.0, -row * 324.0 + 135.0)`.
   - All mesh vertices in `3D/3dmodel.model` are centered at `(0, 0)` in local parent XY (`z_min = 0.0`), and the `<build><item transform="...">` places each object at `(col * 324.0 + 135.0 + cx, -row * 324.0 + 135.0 + cy, 0.0)` for multi-plate (`GravMass_Tree_Ultimate_U1.3mf`) or `(135.0 + cx, 135.0 + cy, 0.0)` for single-plate `.3mf` files.
6. **Unified Multi-Color Parent Objects (`<components>` + `<part subtype="normal_part">`):**
   - Multi-color parts (`golden_apple_topper`, `planet_mercury..neptune`, `Magic_LED_Wand`, `apple_topper_stem_leaf`) attach a `.colored_subparts` list of `(label, toolhead_id, hex_color, child_solid)` tuples to the parent `bd.Solid`.
   - `_inject_orca_metadata_into_3mf()` in [`cad/export_3mf_plates.py`](file:///home/ignacio/grav-mass/cad/export_3mf_plates.py) groups all colored sub-volumes of each multi-color part into a **single parent `<object id="{comp_id}" name="{pp.name}" type="model"><components>...</components></object>`** with one `<build><item>` in `3D/3dmodel.model` and one `<object id="{comp_id}">` containing `<part id="{sub_id}" subtype="normal_part">` entries (each with its own `<metadata key="extruder" value="..."/>`) in `Metadata/model_settings.config`. This ensures OrcaSlicer loads each multi-color part as one unified object that moves, slices, and prints together.

---

## 3. Critical Real-World Physics & Geometric Invariants (Lessons Learned)

### 3.1 Simplified Electronics Architecture (Low Complexity, High Reliability)
We deliberately eliminated high-failure, high-complexity electronics and mechanisms:
- **Removed:** Top servo gate (`PG001` + `Topper_Gate_Arm`), mid-tier diverter (`Track_Seg_07_Diverter` + `Track_Diverter_Flipper`), manual hand crank (`Hand_Crank_Handle`), wireless remote (`XA004`), wired RGB strip hubs (`XA006` + `KB003`), and magnets inside marbles/clutch.
- **Retained (Only 3 Simple, Self-Contained Lighting/Drive Systems):**
  1. **Auger Drive (`trunk_base`):** 1× `12V 150 RPM N20` Gear Motor (`B0BFRPMSW6`, pressed directly into `trunk_base`'s `12.8 × 10.8 × 26.2 mm` shroud pocket — `Servo_Or_030_Adapter` retired), `M5Stack A092 + C008` ESPHome controller, `UCTRONICS` `12V→5V` buck, `WAGO 221` hub, and rear `DC-099` barrel jack (`J1`). Direct drive via brown `T1` `Motor_Clutch_Driver` with `1× M2.5 × 6 mm` D-flat clamping screw.
  2. **Topper Illumination (`golden_apple_topper` + `trunk_top`):** 1× **`Ø 45.0 mm` Sparkleiot 16-Bit WS2812 RGB LED Ring (`B09YTMNGTD`)** seated in `trunk_top`'s `Ø 46.2 × 2.5 mm` crown recess (`Z = 447.5 mm`) with `1 m` `JST-SM` cable (`B0CT827QQC`) routed down the **`150°` `10.6 × 8.5 mm` conduit** (`zero` bracket interference!). *(Do not use Lamp Kit 001 with crown collar.)*
  3. **Wireless Planet Illumination (`planet_mercury..neptune` + `Magic_LED_Wand`):** 8× **Bambu Lab Single LED Magnetic Control Switch Lights** (`Ø 7.5 × 6.0 mm` self-contained battery-powered magnetic-toggle LED units) pressed into the bottom of each planet, toggled ON/Mode/OFF by tapping the planet with the printable **Magic LED Wand** holding the included `Ø 8.0 × 2.0 mm` neodymium trigger magnet in its star tip.
  - *Why not trigger planet LEDs with magnets inside the rolling marbles?* The planets sit on outer-rim balconies at `u = +30.0 mm` (`30 mm` radially outside the track centerline), while the Bambu magnetic LED switch requires `<= 5–8 mm` proximity for `>= 60 ms`. Moreover, magnets inside rolling marbles cause marbles to clump together in the bottom queue and stick to the steel motor housing. The Magic Wand is 100% reliable and interactive.

### 3.2 Closed-Loop Marble Path & Gravity Invariants (`BALL_DIAMETER = 25.0 mm`)
Every transition in the closed-loop marble path must obey gravity (strictly downhill outside the auger) and must **never** require timed gates or synchronized auger phase:

1. **Vertical Auger Lift (`Z = 54.5 mm -> 435.5 mm`):**
   - Marbles ride up the `-Y` vertical ball flute (`X = 0.0, Y = -17.5 mm`, flute radius `13.3 mm`, auger bore `Ø 41.0 mm`, auger OD `38.0 mm`, pitch `46.0 mm`).
   - **Timing-Independent Bottom Auger Scoop (`Z = 37.22..54.50 mm`):** In `trunk_base`, the helical auger flight begins at `Z = 37.22 mm` while the radial intake floor is at `Z = 54.50 mm`. If a marble enters the flute when the auger blade is not aligned, the marble simply sits safely on the `Z = 54.50 mm` floor until the rotating screw flight rises from below (`Z = 37.22 -> 54.50 mm`) and scoops it up smoothly.
2. **Top Discharge Spout (`Z = 435.5 mm -> 431.8 mm`, Below the Crown LED Seat):**
   - The `Ø 45.0 mm` Sparkleiot LED ring sits in `trunk_top`'s crown seat (`Z = 447.5..450.5 mm`) directly beneath `golden_apple_topper` (`Z >= 450.0 mm`).
   - Therefore, marbles exit `trunk_top` through a sloped `-Y` discharge tunnel below the crown pocket: from `(0.0, -17.5, 435.5)` down to `(0.0, -42.5, 431.8)` (`-3.7 mm` downhill drop over `25.0 mm` radial travel, `~8.4°` slope), with `trunk_top`'s lower spout shelf at `Z_shelf = 108.35 mm` local (`408.35 mm` global) clearing `track_seg_14_top_entry` (`0.0000 mm³`).
3. **Top Feeder Catch Basin (`track_seg_14_top_entry`, `theta = 1710° -> 1620°`):**
   - Defined in [`closed_loop_track_point`](file:///home/ignacio/grav-mass/cad/common_params.py#L308-L343) with `TOP_FEEDER_START_DEG = 1710.0` (`4 * 360° + 270°`, directly on the `-Y` axis at `R = 42.5 mm, Z = 425.0 mm`, marble center `Z = 431.8 mm`) spiraling smoothly outward and downward to `1620.0°` (`R = 60.0 mm, Z = 418.0 mm`).
   - **CRITICAL WALL INVARIANT (No Green Wall Across the Downhill Ramp!):**
     - When the marble exits `trunk_top` along `-Y` to `(0.0, -42.5, 431.8)`, it turns toward **`-X`** (`1710° -> 1620°`) to roll down the ramp.
     - Therefore, `top_endcap_wall` (`Box(6.0, 29.0, 30.0)` at `(+16.5, -47.0, 413.0)`) must sit **strictly on the `+X` dead-end side (`X >= +13.5 mm`)** to block the `+X` dead end and guide the marble toward `-X`.
     - **NEVER** place a full-width collar box (`X = -17..+17 mm`) across `Y = -44.5..-30.5 mm` at the top or bottom port! A box extending to `X = -17.0 mm` leaves a solid vertical wall at `X = -17.0..-13.8 mm` directly across the `-X` downhill ramp (the "solid green wall" bug spotted in `output/top.png`).
4. **Main Conical Helix (`track_seg_13..02`, `theta = 1620° -> 0°`):**
   - `4.5` turns (`1620°`), tapering linearly in radius from `HELIX_TOP_R = 60.0 mm` (`1620°`, `Z = 418.0 mm`) to `HELIX_BOT_R = 145.0 mm` (`0°`, `Z = 62.5 mm`) with `HELIX_PITCH = 79.0 mm` per turn (`>= 51 mm` vertical clearance between consecutive turns).
5. **Bottom Return & Single-File Queueing Ramp (`track_seg_01`, `theta = 14° -> 0° -> -90°`):**
   - Spirals inward and **strictly downhill** from `14°` (`R = 144.2 mm, Z = 65.57 mm`) to `RETURN_CHUTE_END_DEG = -90.0°` (`R = 42.0 mm, Z = 48.5 mm`, `RETURN_CHUTE_DROP_Z = 14.0 mm`, marble center `Z = 55.3 mm` on the `-Y` axis) using an arc-length-matched vertical drop profile (`w_z = 1.62*w - 0.62*w^2 + 0.72*w^2*(1-w)^2`) that maintains a **`>= 4.82°` (`4.82°..6.85°`) downhill slope at every single degree** across the rapid `dr/dtheta` inward bend, then drops radially along `+Y` through a continuous **`8.73°` downhill U-chute** (`track_seg_01` `radius = 13.8 mm`, paired on `trunk_base` with a single flared `16.40 → 13.75 mm` entry cone from `(0.0, -45.5, 56.3)` down to `(0.0, -17.5, 52.0)` so `Ø 24.90 mm` marbles clear `-90°..0°` bark by `0.0000 mm³` with zero tangent mesh slivery edges).
   - **Single-File Queue Capacity:** Because `-90°..+60°` is a continuous downhill trough terminated by `bot_endcap_wall` on the `-X` dead-end side (`X <= -13.5 mm`), up to 5 marbles naturally queue single-file (`>= 26.0 mm` center-to-center spacing) whenever the bottom auger pocket is occupied or paused, and self-start from a dead stop into the vertical auger flute as soon as the pocket clears.
   - **Curve-Normal Cross-Section Alignment (`closed_loop_section_plane`):** Along `14° -> -90°`, the radius drops rapidly from `144.2 mm` to `42.0 mm`, so the path tangent turns inward relative to the circumferential vector. [`closed_loop_section_plane`](file:///home/ignacio/grav-mass/cad/common_params.py#L379-L418) blends the local section plane normal with the true XY curve normal via `blend = math.sin(math.pi * (w ** 0.75))` (lofted with `n_sections = 36`) so the `34.0 mm` trough stays perpendicular to the rolling direction (`0.000 mm³` interference with a `Ø 25.0 mm` marble at every `5°` step) while remaining 100% identical to `helix_section_plane` at `theta = 14°` and `theta = 1620°`.

---

## 4. OpenCascade / `build123d` Pitfalls & Solutions

1. **Zero-Thickness Tangent Boolean Non-Manifold Edges (`s01.is_manifold == False`):**
   - In `cad/track.py`, `bot_endcap_wall` and `top_endcap_wall` have their inner X face at `|X| = 13.50 mm`.
   - If `cutter_cyl` uses `radius = 13.50 mm`, its cylindrical wall is **exact-tangent (`0.000 mm` overlap)** to the endcap box face at `|X| = 13.50 mm`, causing OpenCascade to produce a non-manifold edge (`is_manifold == False`).
   - **Solution:** Always use `radius = 13.80 mm` (and `floor_keep` width `27.60 mm`) for `cutter_cyl` on both `bottom_return_ramp` and `top_feeder_ramp` so the boolean cut overlaps the `|X| = 13.50 mm` wall by `0.30 mm`, guaranteeing `is_valid = True` and `is_manifold = True`.
2. **Never Call `.solid()` on Disjoint Multi-Solid Unions:**
   - In `build123d`, calling `.solid()` on a `Shape` or `Compound` containing 2+ disconnected solids (for example, `vortex_north + vortex_south` on Uranus, or two overlapping-in-2D-but-partitioned star triangles `tri_a + tri_b` on `Magic_LED_Wand`) raises `ValueError: Expected exactly one solid, found 2`.
   - **Solution:** Keep multi-part feature layers typed as `bd.Shape` and iterate `for s in shape.solids():` when registering `colored_subparts` (see [`_finalize_multicolor_planet`](file:///home/ignacio/grav-mass/cad/topper_planets.py#L140-L185) and [`build_magic_led_wand`](file:///home/ignacio/grav-mass/cad/topper_planets.py#L645-L750)).
3. **Sequential Boolean Partitioning for Multi-Color Parts:**
   - Slicers (OrcaSlicer / Snapmaker Luban / Bambu Studio) require multi-color sub-meshes within a `.3mf` component to have **`0.000 mm³` internal overlap**.
   - Always partition multi-color parts sequentially (`core = full_body - layer_a - layer_b`, `part_a = full_body & layer_a`, etc.) and verify zero pairwise intersection in `verify_model.py`.

---

## 5. Bottom-Loading Planet Pedestal, Magic Wand & Ergonomic Enhancements

1. **Bottom-Loading Planet Pedestal, Crush Ribs & Wireless LED Bore (`cad/track.py` & `cad/topper_planets.py`):**
   - Each of the 8 Solar System planets (`planet_mercury..neptune`) sits on an outer-rim balcony (`u = +30.0 mm, v_top = +18.0 mm`) on track segments `01, 03, 05, 06, 08, 10, 12, 14` at `PLANET_ANCHOR_DEGS = (1590, 1320, 1080, 840, 600, 480, 240, -15)`.
   - **Track Balcony Mounting Peg (`cad/track.py`):** Upward cylinder **`Ø 7.60 × 3.50 mm`** (`PLANET_PEG_DIA = 7.60 mm`, `PLANET_PEG_HEIGHT = 3.50 mm`) with a `0.60 mm` top lead-in chamfer and **`Ø 8.36 mm` snap bead** (`+0.18 mm/side` radial snap interference into `Ø 8.00 mm` bore / `Ø 8.46 mm` detent groove).
   - **Unified Planet Bottom Bore (`cad/topper_planets.py`):** Open-bottom vertical cylindrical bore **`Ø 8.00 × 10.00 mm`** (`Z = 0.00..10.00 mm`, with `Ø 8.46 mm` internal snap groove) topped by a `45°` conical light-diffuser roof (`Z = 10.00..12.00 mm`):
     - **Upper Chamber (`Z = 3.60..9.60 mm`, `6.00 mm` tall):** Houses the **Bambu Lab Single LED Magnetic Control Switch Light (`KA006`)** (`Ø 7.50 × 6.00 mm`) retained by **4× vertical `0.85 mm`-wide inward crush ribs** (`Ø 7.10 mm` inscribed diameter, `+0.20 mm/side` interference against `Ø 7.50 mm` capsule).
     - **Lower Entry (`Z = 0.00..3.50 mm`, `3.50 mm` tall):** Slides directly over the **`Ø 7.60 × 3.50 mm`** upward peg on the track balcony (`0.20 mm` radial slip-fit clearance; `Ø 8.36 mm` bead clicks into the `Ø 8.46 mm` detent groove).
2. **Support-Free Gothic-Arched Viewing Windows (`_make_arched_viewing_window_cutter` in `cad/trunk.py`):**
   - `trunk_base`, `trunk_mid`, and `trunk_top` feature `14.0 mm` inner-width (`18.0 mm` outer-flared `45°` bark bevel) viewing windows along the `-Y` ball lift flute topped by `45°` pointed gothic-arch roofs and sills so they print without horizontal bridges while keeping the `Ø 25.0 mm` marbles 100% captive.
3. **Integrated Root-Flare Magic Wand Holster (`trunk_base` in `cad/trunk.py`):**
   - Located at `theta = +30.0°` (`R = 52.0 mm -> X = +45.03 mm, Y = +26.00 mm`, dead-center between the `0°` and `60°` bracket columns where there are zero brackets above). Features a `R = 9.0 mm` boss (`Z = 0..27.0 mm`) with a `Ø 12.0 mm` vertical bore (`Z = 5.5..27.5 mm` + `45°` conical floor) that holds the `Ø 11.2 mm` golden pommel of `Magic_LED_Wand` upright.
4. **Keyhole Drop-In Bracket Sockets, Neck Friction Bumps & Debossed Tier Bars (`cad/trunk.py`, `cad/brackets.py`, `cad/retrofit_jig.py`):**
   - **Keyhole Drop-In Joint (`cad/common_params.py` & `cad/trunk.py`):** `make_female_dovetail_slot_cutter` opens a rectangular drop-in entry window above each lower `45°` dovetail wedge (`DOVETAIL_ENTRY_W = 16.20 mm`, `DOVETAIL_ENTRY_DEPTH = 4.85 mm`, `DOVETAIL_ENTRY_H = 18.60 mm`, capped by a `45°` support-free gable roof `DOVETAIL_ENTRY_PEAK_W = 1.60 mm`). Brackets insert radially at `+16.0 mm` and drop `-Z` into the `45°` dovetail seat over symmetric `±Y` neck friction bumps (`DOVETAIL_DETENT_Y_HALF = 3.44 mm` vs `DOVETAIL_NECK_W/2 = 3.30 mm`, ~`0.14 mm` per-side wedge). Verified **26/26 PASS stacked & unstacked** (`0.0000 mm³` interference).
   - **Pre-Fix Trunk Retrofit (`cad/retrofit_jig.py`):** Generates `output/Trunk_Keyhole_Cutting_Jig.{stl,step}` (`0.0000 mm³` collision at `k = 1..7`) to guide manual flush-saw removal of pre-fix closed pocket roofs.
   - **26 Stations (`bracket_01..26`, `60°..1560°`), Split-Tine Pegs & `8.0°` Stepped Half-Laps (`cad/brackets.py` & `cad/track.py`):** Brackets `#1–#26` (including `#25 @ 1500°` and `#26 @ 1560°` supporting the upper feeder curve) drop onto keyhole slots, stay clear of the `150°` wiring conduit, carry `1..4` V-notch tally bars (`X = -4.35 mm`), and use flexible split-tine alignment pegs (`0.60 mm` central slot + `0.26 mm` radial snap ridge) under `8.0°` vertical `-Z` stepped half-lap track seams (`Track_Joint_Clip` retired).
5. **Single-Cable `12V` Zero-Solder Vault, Stepped `DC-099` Boss, Clamp Coupler & Cover (`cad/trunk.py`, `cad/auger.py`, `cad/test_coupons.py`, `ASSEMBLY_AUDIT.md`):**
   - **Single Flush Bottom Cover (`Bottom_Electronics_Lid`):** `Ø 134.6 × 2.8 mm` upright tray with `4× M2.5 × 6 mm` mounting tabs recessed flush inside `trunk_base` (`0.000 mm³` clash vs vault/bays; `Battery_Cover` and `Base_Bottom_Cover` retired). `Motor_Clutch_Driver` uses a split-ear D-shaft pinch clamp (`1× M2.5 × 6 mm` screw) and sits in a direct `12.8 × 10.8 × 26.2 mm` shroud pocket (`Servo_Or_030_Adapter` retired).
   - **Stepped `DC-099` Flange (`6.8 mm` wall) & Printable Coupons (`Test_Coupons_PLA.3mf` / `Test_Coupons_PETG.3mf`):** `dc_099` outer counterbore reduces thread clamping thickness from `15.2 mm` to `6.8 mm` and aligns `xa007` toggle clear of the nut; `track_seg_01` and `track_seg_14_top_entry` include `Z = 0` sacrificial root-flare / base pads (`>= 56.2 mm²` bed contact); `cad/test_coupons.py` exports separate polymer-pure `Test_Coupons_PLA.3mf` and `Test_Coupons_PETG.3mf` calibration plates (`0.10–0.25 mm`). See [`ASSEMBLY_AUDIT.md`](ASSEMBLY_AUDIT.md) for current verification metrics.
   - **Hollow Root Vault (`Ø 135.0 × 50.0 mm`, `> 420 cm³` open slack volume in `trunk_base`):**
     - **Unobstructed `45°` Self-Supporting Hollow Root Vault (`Ø 135.0 × 50.0 mm`, `Z = 3.0..50.0 mm`):** Houses `Bottom_Electronics_Lid` (`Ø 134.6 × 2.8 mm` tray recessed flush at `Z = 0..2.8 mm` with `4× M2.5 × 6 mm` mounting tabs) beneath the `Ø 28.0 mm` central N20 motor shroud tower, rear `6.8 mm` stepped `-X` `DC-099` barrel jack (`Z = 11.5 mm`), **M5Stack `A092 + C008`**, **UCTRONICS `12V→5V 5A` buck**, and **WAGO `221-415`** blocks with generous slack and zero ceiling bridging.
     - **Dedicated `+Y` Snap-In Buck Converter Cradle (`(-4.0, +36.5, Z = 0..12.0 mm)`):** `64.2 × 28.2 × 12.0 mm` pocket with `20.0 × 12.0 mm` open `-X`/`+X` wire portals fits the **UCTRONICS `DC 9V–36V to 5.0V 5A (25W)` Screw-Terminal Buck Converter (`B07XXWQ49N` / `U6223`, `63.0 × 27.0 × 10.0 mm`)**.
     - **Dedicated `+X` Snap-In Lever-Nut Organizer Cradle (`(+44.5, -12.0, Z = 0..18.0 mm)`):** `19.8 × 31.2 × 18.0 mm` pocket with a `26.0 × 18.0 mm` open `-X` wire-access face fits **2× stacked WAGO `221-415` 5-port lever-nut blocks (`30.0 × 18.6 × 8.4 mm` each, `B07NKT2P2F`)**.
   - **Wire Conduits & Top Crown Ring Seat (`trunk_base` & `trunk_top`):**
     - `motor_to_pdb_tunnel` (`X = 0.0, Y = -11.5, Z = -0.1..7.5 mm`): `6.5 × 7.6 mm` pass-through for the **`12V DC 150 RPM N20` motor (`B0BFRPMSW6`, `10.0 × 12.0 × 25.0 mm`)** leads into the vault.
     - `cob_wire_entry_port` (`X = +16.5, Y = -31.5, Z = 35.0..41.5 mm`) + `cob_wire_conduit` (`X = +16.5, Y = -27.5, Z = 6.0..41.5 mm`): Feeds the under-track **`WS2812B` Pebble Wire (`B0CCS11V7H`)** leads from `track_seg_01` straight down into the vault.
     - Oversized `10.6 × 8.5 mm` unobstructed `150°` Connector-Pass-Through trunk conduit (`Z = 0..450 mm`, concealed by full-length section-matched `Conduit_Cover_Strip_{Base,Mid,Top}` `100 / 144 / 144 mm`) routes the `1 m` 3-pin `JST-SM` extension cable (`B0CT827QQC`) up to the **`Ø 46.2 × 2.5 mm` top crown recess** in `trunk_top` (`Z = 447.5 mm`) for the **`Ø 45.0 mm` OD × `Ø 32.0 mm` ID Sparkleiot 16-Bit WS2812 RGB Ring (`B09YTMNGTD`)**.
   - **Deep Snap-In `8.4 × 6.2 mm` (`4.6 mm` Throat) Underside Dovetail Channel & `10.0 × 16.0 mm` Starter Pocket (`cad/track.py` & `cad/brackets.py`):**
     - `make_track_profile_wire()` features an **`8.4 mm` wide × `6.2 mm` total depth** internal dovetail chamber (`LED_CHANNEL_W = 8.4 mm`, `LED_CHANNEL_D = 6.2 mm`, `3.6 mm` full-width bay above the **`4.6 mm` snap-in throat**) in `TRACK_BASE_Y = -15.5 mm` so the `50×` `6.2 × 3.2 mm` oval resin drops of the **BTF-LIGHTING `DC5V` WS2812B Pebble/Seed Pixel Flexible Wire (`B0CCS11V7H`)** recess flush above bracket saddles (`0.000 mm³` collision). `build_cantilever_bracket()` spaces the twin split-tine pegs at `BRACKET_PEG_SPACING_U = 10.6 mm` (`u = ±10.6 mm`) with a **`13.8 mm` wide** `led_notch` bridge.
     - `track_seg_01` includes a recessed `10.0 × 16.0 × 3.7 mm` starter feed pocket at `theta = -70.0°` on its underside.
6. **Realistic Heart-Shaped 5-Lobed Apple Topper Silhouette & Bark-Textured Trunk-Crown Pedestal (`golden_apple_topper` in `cad/topper_planets.py`):**
   - *Why the Apple Previously Looked Like a Cylinder or Tomato:*
     1. `trunk_top` has `Ø 68.0 mm` (`R = 34.0 mm`), and the Bambu Lab LED Lamp Kit 001 puck (`Ø 60.0 × 18.5 mm`) sits in the bottom `Z = 0..18.5 mm` of `golden_apple_topper`.
     2. When the red apple shell was oblate (`51.9 mm` tall × `83.8 mm` wide, `H/W = 0.62`), had a flat horizontal top rim, and had its green leaf resting on the red top surface like a tomato sepal, it resembled a tomato rather than a true apple.
   - *Solution:*
     - Partition `Z = 0.0..19.30 mm` (`R = 33.2 -> 31.2 mm` with organic vertical bark ridges `lobe_amp = -0.75`) as a **Bark-Textured Dark Wood Brown Trunk-Crown Pedestal (`Toolhead 1 #4A2F1D`, `apple_brown_trunk_collar_1`)** so the lamp housing blends seamlessly into the bark-textured wooden tree trunk.
     - Above `Z = 19.30 mm` (`Z = 19.25..93.8 mm`, `74.5 mm` tall × `82.5 mm` wide, `H/W = 0.90`), the **Crimson Red Apple (`Toolhead 4 #C41E3A`, `apple_red_shell`)** features:
       * A narrow, tucked-in **5-knobbed bottom calyx base (`Ø 46.0 mm` at `Z = 19.25 mm`, `lobe_amp = 0.048`)**,
       * Long, tapered lower apple cheeks widening gradually up to **high, broad upper shoulders (`Ø 82.5 mm` at `Z = 64..70 mm`, ~72% up the apple body)**,
       * An iconic **heart-shaped double-crowned top silhouette (`z_crown_amp = 2.6 mm` saddle wave `0.65*cos(2*theta) + 0.35*cos(5*theta)`)** where the left and right upper crown lobes rise to `Z = 93.8 mm` and dip down in the center (`Z = 89.5 mm`) before plunging into a deep funnel-like stem cavity (`Z = 74.0 mm`),
       * **Standalone Snap-In Emerald Green PETG Leaf (`apple_green_leaf` on Plate 13) + Curved Woody Stem (`T1` PLA, `Z = 84.8..108.5 mm`):** Keeps `Plate 16` 100% pure PLA by moving the 5-section cambered ovate leaf to `Plate 13` (Translucent Green PETG `#00A86B`) with a snap-in stem socket clear above the crimson apple crown.
       * **Contoured `~2.2 mm` Thin-Walled Hollow Lantern Interior (`lantern_cavity_rings`, `Z = 18.8..85.8 mm`):** Instead of a narrow internal cone that leaves `20–30 mm` of solid infill blocking the LED light, `build_golden_apple_topper` subtracts a 15-ring 5-lobed antiprism cavity (`R_inner = R_outer - 2.2 mm`, with `z_crown_amp = 2.10 mm` matching the heart-shaped upper crown lobes and a self-supporting vaulted dome directly beneath the `Z = 86.0 mm` stem dimple). This creates a uniform **`~2.2 mm` translucent crimson lantern shell** with **zero internal infill** between the LED puck and the outer surface, while `stem_w0` starts at `Z = 84.8 mm` (`z_offset = -84.8` in `build_apple_topper_stem_leaf`) so the opaque brown stem embeds cleanly into the top stem basin without protruding into the hollow red lantern chamber.
       * **Thin-Shell Hollow Dome & `Ø 18.70 × 7.30 mm` Universal Y-Shape LED Chamber in `Apple_Hemisphere_A` & `Apple_Hemisphere_B`:** The central equatorial chamber (`z = -3.65..+3.65 mm`, `R = 9.35 mm`, `Ø 18.70 mm`) houses the **Bambu Lab Y-Shape LED Light with Magnetic Control Switch (`KC012 / KC013`, `Ø 18.0 × 6.5 mm`, 3 LEDs + `CR1632` battery)** with `+0.70 mm` diametrical and `+0.80 mm` axial clearance (as well as the `Ø 7.5 × 6.0 mm` Single LED `KA006`, `M8` hex nut, or `Ø 12.7 mm` steel ball), transitioning seamlessly into the `~1.9 mm` thin-shell hollow lantern dome up to `Z = ±10.65 mm`.
       * **Quarter-Turn 3-Lug Bayonet Twist-Lock Marble Coupling (`build_apple_hemisphere_a` & `build_apple_hemisphere_b`):** `Apple_Hemisphere_A` features a smooth cylindrical male bayonet neck (`R_neck = 10.30 mm`) and **3 protruding radial lugs (`R_lug = 11.15 mm`, `32°` wide at `0°, 120°, 240°`)** with a `45°` bottom elephant's-foot relief chamfer and `45°` top locking cam ramp. `Apple_Hemisphere_B` features a smooth `R_bore = 10.52 mm` throat (`+0.44 mm` diametrical clearance), **3 open vertical entry keyway slots (`42°` wide, `R = 11.40 mm` for zero-force drop-in)**, and **3 clockwise two-stage helical cam undercut locking tunnels (`R_tunnel = 11.38 mm`, `-64°..+21°`)** that trap the 3 lugs under a solid PLA retaining ceiling when twisted `-45°` clockwise.
7. **Support-Free Organic Bark Texture & Hidden Inner Engraved Assembly Numbers (`cad/trunk.py`, `cad/auger.py`, `cad/brackets.py`, `cad/track.py`, `cad/topper_planets.py`):**
   - **Organic Bark Texture (`_bark_furrow_depth`, `_make_bark_textured_trunk_column`, `_make_bark_textured_base_hub` in `cad/trunk.py`):** Lofted `120`-point cross-section rings with `1.45 mm` radial bark furrows (`<= 3°` vertical slope, 100% support-free) parameterized by continuous `z_global = 0..450 mm` so bark ridges align across `trunk_base -> trunk_mid -> trunk_top`. The `60°` bracket dovetail columns (`d60 <= 6.5°`) and `270°` (`-Y`) ball port/window strip remain smooth at `R = TRUNK_OUTER_R = 34.0 mm` so brackets and track endcaps mate flush with `0.000 mm³` interference.
   - **Hidden Inner Engraved Numbers (`make_engraved_label_solid` in `cad/common_params.py`):** Rectilinear 7-segment `bd.Box` cutters (`Z in [-depth, +depth]`) deboss hidden assembly numbers into mating/internal surfaces that become 100% invisible once assembled:
     - `trunk_base`, `trunk_mid`, `trunk_top`, `golden_apple_topper`: **`1`**, **`2`**, **`3`** on top mating rims (`Z = 165, 165, 150 mm`), **`4`** inside topper diffuser cone (`Z = 47.9 mm`).
     - `auger_lower`, `auger_upper`: **`1`** on top of male hex peg (`Z = 208 mm`), **`2`** on top of shaft (`Z = 198 mm`).
     - `bracket_01..26`: Arabic station number **`1`–`26`** in the recessed top saddle (`X = reach_x, Z = 16.25 mm` between the two pegs) + `1–4` V-notch tier bars on the `-X` dovetail tenon face.
     - `track_seg_01..14`: **`1`–`14`** near each stepped half-lap mating shoulder (`u = +5.8, v = -6.0 mm`).
     - `planet_mercury..neptune` & Track Balcony Pegs: **`1`–`8`** (`1` = Mercury .. `8` = Neptune) inside each planet's bottom LED bore ceiling (`Z = 11.8 mm`) and on the flat top of each matching `Ø 7.60 mm` track balcony peg (`u = 30.0, v = 21.5 mm`).
     - `Apple_Hemisphere_A/B`: **`A`** and **`B`** inside the internal core cavity ceiling.
8. **Galileo–Newton Gravity Chronometer (`TIMING_GATE_ANGLES_DEG`, `helix_arc_length_from_top`, `theta_for_helix_arc_length` in `cad/common_params.py`, `cad/track.py`, `cad/trunk.py`):**
   - **6 Timing Gates (`G0`..`G5` at `1605°, 1350°, 990°, 630°, 270°, 15°`):** `G1`–`G4` align vertically along the front `-Y` spine (`270° mod 360°`, `Δh = 79.0 mm` apart). Each gate has a top-rim sighting notch (`u = 18.3 mm, v = 18.0 mm`), engraved outer-wall label (`"G0"`..`"G5"` at `u = 20.6 mm`), and a `0.50 mm` inward acoustic click micro-rib (`CLICK_RIB_PROTRUSION_MM = 0.50 mm`) for smartphone acoustic stopwatch timing (`Phyphox`).
   - **True 3D Spiral Arc-Length Ticks (`100 mm` / `500 mm`):** Closed-form antiderivative `helix_arc_length_from_top` and Newton-Raphson inverse `theta_for_helix_arc_length` place graduation ticks every `100 mm` (`s = 100..2800 mm` from `G0`), with deeper `500 mm` major ticks and engraved decimeter labels (`5, 10, 15, 20, 25`).
   - **Front Trunk Elevation Scale (`_cut_front_elevation_ruler_for_section` in `cad/trunk.py`):** Horizontal `25 mm` / `50 mm` / `100 mm` elevation ticks (`Z_global = 75..425 mm`) flanking the gothic-arched front `-Y` viewing windows on `trunk_base`, `trunk_mid`, and `trunk_top`.
9. **Single-Cable `12V DC` Solder-Free Power Architecture (`POWER_ARCHITECTURE.md`, `cad/trunk.py`, `esphome/grav-mass-tree.yaml`):**
   - **Why `12V` Input + Dedicated `5V` Buck Converter:** `M5Stack A092` requires `DC 9–24V` input (its TI `DRV8876` H-bridge switches `VIN` directly to `M1/M2`, and its internal `MP1584EN` buck regulator requires headroom above `5V` to power the stacked `C008` ATOM Lite). Meanwhile, `C008`'s USB-C port has a `500 mA` Schottky diode limit (`D1`) and `LA002` is a `6V` (`3–7V`) motor.
   - **Rear `-X` `12V` DC Barrel Jack Port (`DC_BARREL_JACK_BORE_DIA = 11.4 mm` at `Z = 10.0 mm` in `cad/trunk.py`):** Accepts a standard threaded `5.5 × 2.1 mm` female panel-mount DC barrel jack (`DC-099`, `M11 × 0.75` thread) with a `12.0 × 24.0 × 9.5 mm` internal vault portal (`dc_jack_vault_portal`) opening into the `Ø 135 × 50 mm` Hollow Root Vault. Verified by `dc_jack_gauge` (`Ø 11.20 mm` = `0.0 mm³` collision) and `dc_jack_over` (`Ø 13.40 mm` > `0.0 mm³` flange shoulder stop) in `cad/verify_model.py`.
   - **3-Branch Fused WAGO `221` Distribution & Strict `5V` Rail Isolation:**
     - **Main Input (`J1` `B07C7VSRBG` → `F0 = 5A` `B087BT1PH3` → `WAGO-1 +12V_BUS` & `WAGO-2 STAR_GND` `B07NKT2P2F`):** Fed by a single external `12V 5A (60W)` adapter (`BTF-LIGHTING B01D8FLSV8`).
     - **Branch 1 & 3 (`F1 = 2A` → `A092 VIN/GND`):** Powers `A092` + `C008` (internal `12V→5V` regulator) and drives a **`12V DC 150 RPM N20` motor (`B0BFRPMSW6`)** directly on `A092` `M1/M2` (preserving `GPIO22` `nFAULT` stall protection).
     - **Branch 2 (`F2 = 3A` → `UCTRONICS 12V → 5.0V 5A` Screw-Terminal Buck Converter `B07XXWQ49N` (`U6223`, `63.0 × 27.0 × 10.0 mm` in the `+Y` `64.2 × 28.2 × 12.0 mm` cradle at `(-4.0, +36.5)`) + `1000 µF 16V` Cap `B07WPWFSNQ` → `WAGO-3 +5V_LED` & `WAGO-4 GND_LED`):** Powers the 50 Track LEDs (`B0CCS11V7H`, with dual-end power injection) and 16 Topper LEDs (`B09YTMNGTD`). **NEVER connect `WAGO-3 (+5V_LED)` to `C008`/`A092`'s `5V` rail—always leave the `A096` Grove `Red (+5V)` wire capped/unconnected!**
   - **ESPHome Telemetry & Current Governor (`esphome/grav-mass-tree.yaml`):** `GPIO33` monitors the `12V` supply rail (`10.8V–13.5V` window), I2C (`GPIO21/25`) supports the plug-and-play `M5Stack Unit INA226-10A (U190)` hardware shunt sensor (`0x41`), and the `250 ms` software current governor (`default_max_current_ma = 2000 mA`) enforces the selected current ceiling with no artificial minimum brightness floor.

---

## 6. Webapp Architecture & Cache-Busting Checklist

Whenever you modify CAD geometry or `webapp/app.js`:
1. Run `uv run --with numpy python3 -u cad/export_webapp_assets.py` to regenerate `webapp/assets/manifest.json` and `webapp/assets/meshes.bin` **before** bumping the version tag (never bump `?v=N` before `export_webapp_assets.py` finishes, or a browser refreshing mid-build will cache the old binary under the new version tag).
2. Increment the cache-busting query parameter `?v=N` in **both**:
   - [`webapp/index.html`](file:///home/ignacio/grav-mass/webapp/index.html#L632) (`<script type="module" src="app.js?v=46"></script>`)
   - [`webapp/app.js`](file:///home/ignacio/grav-mass/webapp/app.js#L798-L803) (`fetch("assets/manifest.json?v=46", { cache: "no-store" })` and `fetch("${manifest.binary_file}?v=46", { cache: "no-store" })`)
   so browsers never render stale cached STL buffers or scripts.
3. **Preserve Custom Domain `CNAME` (`newton.martinez.fyi`) on `gh-pages`:**
   - The GitHub Pages deployment uses the custom domain `newton.martinez.fyi` (`webapp/CNAME`). Always preserve `CNAME` (`newton.martinez.fyi`) in the root of the `gh-pages` branch and never overwrite or delete it when deploying updates.
4. **Never Push the `120000 output -> ../output` Symlink to `gh-pages` (Always Include `.nojekyll` and Map `output` to `main:output` Tree):**
   - Locally, `webapp/output` is a relative symlink (`120000 output -> ../output`). If that symlink is pushed directly to the root of the `gh-pages` branch, `../output` points outside the repository root and causes GitHub Pages (`actions/jekyll-build-pages`) to crash with `Errno::ENOENT: /github/workspace/output`, leaving `https://newton.martinez.fyi/` frozen on an old build!
   - Always keep `webapp/.nojekyll` committed in `webapp/`, and when constructing a `gh-pages` commit tree from `main:webapp`, replace the `120000 output` entry with `040000 tree $(git rev-parse main:output) output` so GitHub Pages builds succeed with zero extra storage overhead and `/output/3mf/*.3mf` downloads work.
