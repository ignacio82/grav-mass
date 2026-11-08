# 📋 Documentation Refactoring Notes (`docs/REFACTOR_NOTES.md`)

## 1. Content Completeness & Section Mapping Checklist

Every section and heading from the original 468-line monolithic `README.md` (`commit 7e9a8dc`) has been mapped and preserved without altering technical meaning, dimensions, part numbers, formulas, or GPIO assignments:

| Status | Original `README.md` Section / Heading | Original Lines | New Location |
| :---: | :--- | :---: | :--- |
| ✅ | `# 🍎🌲 Grav-Mass Day "Falling Apple Cascade" Marble Run Tree` (Title, Badges, Simulator Link, Overview Paragraph) | `L1–L9` | [`README.md`](../README.md) (`L1–L11`) |
| ✅ | `## ✨ Key Features` | `L12–L19` | Condensed 1-line summary bullets with doc links in [`README.md`](../README.md) (`L15–L21`); full details preserved in respective `docs/*.md` files |
| ✅ | `## 🛒 Complete Shopping List (Bill of Materials & Where to Buy)` | `L22–L25` | [`docs/BOM.md`](BOM.md) (`L1–L5`) |
| ✅ | `### 1. Electronics, Single-Cable 12V Power Distribution & Wireless Magnetic LEDs (100% Solder-Free)` (18-row table) | `L26–L49` | Generated from [`bom/bom.yaml`](../bom/bom.yaml) into [`docs/BOM.md`](BOM.md) (`<!-- BOM:BEGIN -->` .. `<!-- BOM:END -->`) |
| ✅ | `#### 🗺️ Complete Mechanical & Electrical Connection Diagram (One-Cable 12V Solder-Free Edition)` (`mermaid` `flowchart TB`) | `L51–L96` | [`docs/BOM.md`](BOM.md) (`## 🗺️ Complete Mechanical & Electrical Connection Diagram`) |
| ✅ | `### 2. Fasteners (Only 2 Screws Needed!)` (1-row table) | `L100–L105` | Generated from [`bom/bom.yaml`](../bom/bom.yaml) into [`docs/BOM.md`](BOM.md) |
| ✅ | `### 3. 3D Printing Filament (Snapmaker U1 4-Toolhead Palettes — Max 4 Colors Per Plate)` (6-row table) | `L108–L118` | Generated from [`bom/bom.yaml`](../bom/bom.yaml) into [`docs/BOM.md`](BOM.md) |
| ✅ | `## 🖨️ 3D Printing & Support Guide (18 Pre-Arranged .3mf Build Plates...)` | `L121–L127` | [`docs/PRINTING.md`](PRINTING.md) (`L1–L8`) |
| ✅ | `### Plate-by-Plate Breakdown & Support Settings` (Plates 1–18 table + `"On build plate only"` note) | `L128–L153` | [`docs/PRINTING.md`](PRINTING.md) (`L10–L35`) |
| ✅ | `## 🔧 Step-by-Step Physical Assembly Instructions` & `### 🔢 Hidden Inner Assembly Numbering System` | `L156–L171` | [`docs/ASSEMBLY.md`](ASSEMBLY.md) (`L1–L16`) |
| ✅ | `### Step 1` through `### Step 9` (Physical Assembly Steps 1–9) | `L174–L255` | [`docs/ASSEMBLY.md`](ASSEMBLY.md) (`L20–L101`) |
| ✅ | `## 📐 Measuring Earth's Gravity ($g$) with the Model (Galileo–Newton Gravity Chronometer)` | `L258–L260` | [`docs/PHYSICS.md`](PHYSICS.md) (`L1–L3`) |
| ✅ | `### 1. Built-In Physical Measurement Scales & Timing Gates` | `L262–L270` | [`docs/PHYSICS.md`](PHYSICS.md) (`L5–L13`) |
| ✅ | `### 2. Reference Table of Timing Gate Coordinates (G0 to G5)` | `L272–L284` | [`docs/PHYSICS.md`](PHYSICS.md) (`L15–L27`) |
| ✅ | `### 3. Step-by-Step: 3 Ways to Measure Marble Transit Time ($\Delta t$)` | `L287–L302` | [`docs/PHYSICS.md`](PHYSICS.md) (`L31–L46`) |
| ✅ | `### 4. Physics Formula & Marble Core Rotational Inertia ($\kappa$)` (Equations A & B, $\kappa$ table, Bonus Experiment) | `L305–L330` | [`docs/PHYSICS.md`](PHYSICS.md) (`L50–L75`) |
| ✅ | `## 🏠 Smart Home Integration (ESPHome + Home Assistant — Single-Cable 12V, Zero Soldering)` | `L333–L337` | [`docs/SMART_HOME.md`](SMART_HOME.md) (`L1–L5`) |
| ✅ | `### 0. Electrical Architecture & Voltage Compatibility (12V Input + Isolated 5V LED Buck)` | `L339–L345` | [`docs/SMART_HOME.md`](SMART_HOME.md) (`L7–L13`) |
| ✅ | `### 1. Zero-Solder Parts List for ESPHome / Home Assistant` | `L346–L364` | Replaced duplicate table with direct SKU/section links to [`docs/BOM.md`](BOM.md) in [`docs/SMART_HOME.md`](SMART_HOME.md) (`L15–L22`), preserving the M5Stack `A092` official pinout doc link |
| ✅ | `### 2. Zero-Solder Pinout & Terminal Map (A092 + C008 + 5V Buck Inside trunk_base)` (`mermaid` `flowchart LR` + entity table) | `L365–L408` | [`docs/SMART_HOME.md`](SMART_HOME.md) (`L24–L67`) |
| ✅ | `### 3. Flashing the Included ESPHome Configuration (esphome/grav-mass-tree.yaml)` | `L410–L434` | [`docs/SMART_HOME.md`](SMART_HOME.md) (`L69–L93`) |
| ✅ | `## 🌐 Live 3D Web App & Local CAD Development` (`Live GitHub Pages App`, `Running the Web App Locally`, `Regenerating All CAD Files...`) | `L437–L458` | [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) (`L1–L22`, plus new `## Editing the BOM` section at `L24–L40`) |
| ✅ | `## 📜 License (CC BY-NC 4.0 + MIT — Free to Print & Remix, No Commercial Sales)` | `L462–L468` | [`README.md`](../README.md) (`L50–L56`) |

---

## 2. Assumptions & Design Decisions

1. **Integer `qty` for Optional & Multi-Pack BOM Items (`bom/bom.yaml`):**
   - To satisfy strict validation (`qty` is a positive integer for every item in `bom/bom.yaml` and `bom/bom.csv`), optional items (`U190`, `B07V5CW1MG`, `B0CMCFGXSL`) and multi-piece packs/kits (`B07NKT2P2F`, `B087BT1PH3`, `B07WPWFSNQ`) store `qty: 1` (with `optional: true` for the 3 optional items), while storing their exact table display strings (`qty_display`, `status`, and `link_text`) in the `notes` field. This allows [`scripts/gen_bom.py`](../scripts/gen_bom.py) to reproduce the original `README.md` table cells character-for-character while keeping `qty` strictly a positive `int`.
2. **Placement of `<!-- BOM:BEGIN -->` / `<!-- BOM:END -->` and the Connection Diagram in `docs/BOM.md`:**
   - The three generated tables (`Electronics`, `Fasteners`, and `3D Printing Filament`) are generated between `<!-- BOM:BEGIN -->` and `<!-- BOM:END -->` in [`docs/BOM.md`](BOM.md), and the `## 🗺️ Complete Mechanical & Electrical Connection Diagram` Mermaid flowchart sits immediately below `<!-- BOM:END -->` in the same file.
3. **Deduplicating the Smart Home Parts Table (`docs/SMART_HOME.md`):**
   - Section 1 of [`docs/SMART_HOME.md`](SMART_HOME.md) replaces the duplicated 14-row shopping table with categorized bullet links pointing directly to [`docs/BOM.md` §1 (Electronics)](BOM.md#1-electronics-single-cable-12v-power-distribution--wireless-magnetic-leds-100-solder-free) and [`docs/BOM.md` §2 (Fasteners)](BOM.md#2-fasteners-only-2-screws-needed). The external link to the [Official M5Stack `A092` Pinout Docs](https://docs.m5stack.com/en/atom/Atomic_HDriver_Base) that previously appeared only in the duplicate table was preserved in [`docs/SMART_HOME.md`](SMART_HOME.md).

---

## 3. Resolved Review Items & Electronic Component Dimension Audit

All 8 items previously flagged for human review have been resolved and verified across the BOM, documentation, and CAD geometry:

1. **Build Plate Count (`18 Plates` in `docs/PRINTING.md` & `GEMINI.md`) — ✅ Resolved:**
   - Updated [`GEMINI.md`](../GEMINI.md) Sections 1 and 2.4 to document the **18-plate layout** (`Plates 1–15` pure single-color + `Plates 16–18` dedicated 4-color, `5 × 4` OrcaSlicer plate grid) and all 49 exported CAD parts.
2. **Rear `-X` DC Barrel Jack Bore Diameter & Z-Height (`Ø 11.4 mm` at `Z = 10.0 mm`) — ✅ Resolved:**
   - Updated all 5 occurrences in [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) (Sections 3.1, 4.1, 4.2, 8, and 9 Step 2) from `Ø 11.2 mm` (`Z = 9.5 mm`) to **`Ø 11.4 mm` at `Z = 10.0 mm` (`M11 × 0.75` `Ø 11.0 mm` thread)**, matching [`cad/common_params.py`](../cad/common_params.py) (`DC_BARREL_JACK_BORE_DIA = 11.4`, `DC_BARREL_JACK_Z_CENTER = 10.0`), [`docs/BOM.md`](BOM.md), and [`docs/ASSEMBLY.md`](ASSEMBLY.md).
3. **Under-Track LED Channel & Starter Pocket Dimensions (`8.0 × 3.6 mm` Dovetail, `4.6 mm` Throat) — ✅ Resolved:**
   - Updated [`GEMINI.md`](../GEMINI.md) Section 5.5 to match [`cad/common_params.py`](../cad/common_params.py) (`LED_CHANNEL_W = 8.0`, `LED_CHANNEL_THROAT_W = 4.6`, `LED_CHANNEL_D = 3.6`) and [`cad/track.py`](../cad/track.py) (`10.0 × 16.0 × 3.7 mm` starter feed pocket at `theta = -70°`) for the `BTF-LIGHTING B0CCS11V7H` `WS2812B` Pebble/Seed Pixel Flexible Wire (`6.2 × 3.2 mm` oval resin drops).
4. **Cantilever Branch Bracket Engraving Description (`1–24` Station Digits + `1–4` Tier Bars) — ✅ Resolved:**
   - Updated the **Hidden Inner Assembly Numbering System** table in [`docs/ASSEMBLY.md`](ASSEMBLY.md) and [`GEMINI.md`](../GEMINI.md) so the **Cantilever Branch Brackets** row lists **`1` – `24` *(Station Digit + `1–4` Tier Bars)***, matching [`docs/ASSEMBLY.md`](ASSEMBLY.md) Step 5 and [`cad/brackets.py`](../cad/brackets.py) (`build_all_24_station_brackets`).
5. **Marble LED SKU (`KC013` Warm White / `KC012` Cool White) — ✅ Resolved:**
   - Standardized [`docs/PHYSICS.md`](PHYSICS.md) Section 4 and [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) Section 3.1 to list **`KC013`** (Warm White primary BOM SKU) alongside **`KC012`** (identical-dimension Cool White variant, also listed in `alt_skus` in [`bom/bom.yaml`](../bom/bom.yaml)).
6. **ESPHome Entity Names & IDs (`docs/SMART_HOME.md` & `POWER_ARCHITECTURE.md` vs. `esphome/grav-mass-tree.yaml`) — ✅ Resolved:**
   - Aligned both [`docs/SMART_HOME.md`](SMART_HOME.md) and [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) with the exact entity names and IDs defined in [`esphome/grav-mass-tree.yaml`](../esphome/grav-mass-tree.yaml):
     - `sensor.motor_bus_voltage_12v_vin` (`id: vin_12v_bus_voltage`, `name: "Motor Bus Voltage (12V VIN)"`)
     - `binary_sensor.12v_supply_voltage_out_of_range_alert` (`id: supply_12v_rail_fault`, `name: "12V Supply Voltage Out of Range Alert"`)
     - `binary_sensor.auger_motor_fault_stall_alert` (`id: motor_driver_fault`, `name: "Auger Motor Fault / Stall Alert"`)
     - `select.5v_led_buck_current_limit_profile` (`id: power_supply_mode`, `name: "5V LED Buck Current Limit Profile"`)
     - `sensor.measured_5v_led_buck_current_ina226_hardware` (`name: "Measured 5V LED Buck Current (INA226 Hardware)"`)
     - `button.unjam_auger_reverse_1_5s_resume` (`name: "Unjam Auger (Reverse 1.5s & Resume)"`)
     - `light.helical_track_rgbic_cob_strip` (`id: track_cob_strip`, `name: "Helical Track RGBIC COB Strip"`)
     - `light.golden_apple_topper_ring` (`id: apple_topper_ring`, `name: "Golden Apple Topper Ring"`)
7. **Power Supply & Buck Converter Models (`BTF-LIGHTING B01D8FLSV8` & `UCTRONICS B07XXWQ49N / U6223`) — ✅ Resolved:**
   - Updated all remaining `MEAN WELL GST60A12-P1J` and `DFRobot DFR0205` references in [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) to `BTF-LIGHTING B01D8FLSV8` and `UCTRONICS B07XXWQ49N (U6223)`.
8. **Hardcoded Local `file://` Links in `POWER_ARCHITECTURE.md` — ✅ Resolved:**
   - Replaced both `file:///home/ignacio/grav-mass/esphome/grav-mass-tree.yaml` links in [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) (lines 413 and 440) with relative repository path `esphome/grav-mass-tree.yaml`.

### Verified Electronic Component Dimensions vs. CAD Mounting Clearances

Every electronic component and fastener in [`bom/bom.yaml`](../bom/bom.yaml) was audited against manufacturer datasheets and 3D boolean gauge checks in [`cad/verify_model.py`](../cad/verify_model.py). Notably, manufacturer verification showed that the **UCTRONICS `B07XXWQ49N` (`U6223`) `12V → 5V 5A` buck converter** measures **`63.0 × 27.0 × 10.0 mm`** (rather than `63 × 20 × 10 mm`); [`cad/trunk.py`](../cad/trunk.py) and [`cad/common_params.py`](../cad/common_params.py) were updated so `trunk_base` provides a dedicated `+Y` snap-in cradle (`64.2 × 28.2 × 12.0 mm` at `(-4.0, +36.5 mm)` with open `-X`/`+X` screw-terminal wire portals) and a dedicated `+X` WAGO `221-415` organizer cradle (`19.8 × 31.2 × 18.0 mm` at `(+44.5, -12.0 mm)`):

| SKU / Part ID | Component | Verified Datasheet Dimensions | CAD Mounting Pocket / Bore (`cad/*.py`) | Verified Clearance & Fit |
| :---: | :--- | :--- | :--- | :--- |
| **`B07C7VSRBG`** | `5.5 × 2.1 mm` Threaded Panel-Mount DC Barrel Jack (`DC-099`) | **`M11 × 0.75` (`Ø 11.0 mm`)** thread, `Ø 13.8 mm` front flange, `14.0 mm` hex nut | **`Ø 11.40 mm` bore** (`Z = 10.0 mm`) through `5.0 mm` rear `-X` wall + `7.5 mm` open vault nut space + `12.0 × 24.0 × 9.5 mm` pigtail portal | **`+0.40 mm` diametral clearance** (`0.0 mm³` interference on `Ø 11.20 mm` gauge) |
| **`B07XXWQ49N`** (`U6223`) | UCTRONICS `DC 9V–36V to 5.0V 5A (25W)` Screw-Terminal Buck Converter | **`63.0 × 27.0 × 10.0 mm`** (`L × W × H`) | **`64.2 × 28.2 × 12.0 mm`** `+Y` snap-in cradle at `(-4.0, +36.5, Z = 0..12.0 mm)` + `20.0 × 12.0 mm` open `-X`/`+X` terminal wire portals | **`+1.2 mm` X/Y, `+2.0 mm` Z clearance** (`0.0 mm³` interference on `63 × 27 × 10 mm` gauge) |
| **`B07NKT2P2F`** (`221-415` / `221-413`) | WAGO `221` Lever-Nut Connectors (`5× 221-415`, `5× 221-413`, `5× 221-412`) | `221-415`: **`30.0 × 18.6 × 8.4 mm`** (`2×` stacked = `30.0 × 18.6 × 16.8 mm`); `221-413`: **`18.7 × 18.6 × 8.4 mm`** | **`19.8 × 31.2 × 18.0 mm`** `+X` snap-in cradle at `(+44.5, -12.0, Z = 0..18.0 mm)` + `26.0 × 18.0 mm` open `-X` wire portal | **`+1.2 mm` X/Y/Z clearance** (`0.0 mm³` interference on `18.6 × 30.0 × 16.8 mm` dual-stack gauge) |
| **`B087BT1PH3`** | Pre-Wired Inline Blade Fuse Holders (`F0 = 5A`, `F1 = 2A`, `F2 = 3A`) | Flexible inline holder body (`~32 × 14 × 38 mm`) with `16/18 AWG` leads | Routes inside the **`Ø 135.0 × 50.0 mm` (`426.3 cm³`)** unobstructed Hollow Root Vault | **`426,340 mm³` open vault slack** (`2.8×` the `150,000 mm³` minimum requirement) |
| **`B07WPWFSNQ`** | BOJACK `1000 µF 16V 105 °C` Radial Electrolytic Capacitor | **`Ø 10.0 × 17.0 mm`** radial can (`5.0 mm` lead pitch) | Leads clamp directly into `B07XXWQ49N` `OUT+` & `GND` screw terminals via the `20.0 × 12.0 mm` `+X` wire portal | Unobstructed clearance inside open vault |
| **`A092` + `C008`** | M5Stack Atomic H-Driver Base (`A092`) + ATOM Lite ESP32 (`C008`) | Stacked: **`48.0 × 24.0 × 18.0 mm`** (`C008` alone: **`24.0 × 24.0 × 9.5 mm`**) | **`49.2 × 25.2 × 20.4 mm`** stepped `-Y` bay at `(0.0, -33.0 mm)` (`18.9 mm` clear above `Battery_Cover`'s `1.4 mm` lip) + `54.6 × 31.6 × 16.9 mm` outer bay | **`+1.2 mm` X/Y, `+0.9 mm` Z clearance** (`0.0 mm³` interference on `48 × 24 × 18 mm` gauge) |
| **`B0BFRPMSW6`** (`LA002` size) | `12V DC 150 RPM N20` Micro Metal Gear Motor (`Ø 3.0 mm` D-Shaft) | **`10.0 × 12.0 × 25.0 mm`** gearbox+body, **`Ø 3.0 × 9.0 mm` D-shaft** (`2.5 mm` flat) | `Servo_Or_030_Adapter` (`12.4 × 10.4 × 26.0 mm`) in `trunk_base` (`12.8 × 10.8 × 26.3 mm`); `Motor_Clutch_Driver` **`Ø 3.15 mm` D-bore** | **`+0.4–0.8 mm` body clearance, `+0.15 mm` D-shaft clearance** (`0.0 mm³` interference) |
| **`B0CCS11V7H`** | BTF-LIGHTING `DC5V` `WS2812B` Pebble/Seed Pixel String (`50 LEDs`) | **`6.2 × 3.2 mm`** oval resin LED drops on **`~3.4 × 1.4 mm`** 3-wire cord | **`8.0 × 3.6 mm` internal dovetail chamber** (`4.6 mm` snap-in throat) + **`10.0 × 16.0 × 3.7 mm`** starter pocket under `track_seg_01` | **`+1.8 mm` width, `+0.4 mm` depth clearance** inside dovetail; retained by `4.6 mm` throat lips |
| **`B09YTMNGTD`** & **`B0CT827QQC`** | Sparkleiot 16-Bit WS2812 RGB Ring + `1 m` 3-Pin `JST-SM` Extension | Ring: **`Ø 45.0 mm` OD × `Ø 32.0 mm` ID × `~3.2 mm` H**; `JST-SM` plug: `~10.0 × 6.2 mm` | **`Ø 46.2 × 2.5 mm` top crown recess** in `trunk_top` (`Z = 447.5 mm`) + **`10.0 × 8.0 mm` rear `-X` trunk conduit** | **`+1.2 mm` OD clearance** (`0.0 mm³` interference on `9.6 × 7.6 × 450 mm` conduit gauge) |
| **`KC013`** (`KC012`) & **`B07V5CW1MG`** | Bambu Lab Y-Shape 3-LED Magnetic Control Switch Light (`CR1632`) | **`Ø 18.0 × 6.5 mm`** PCB + `CR1632` (`Ø 16.0 × 3.2 mm`) coin cell | **`Ø 18.70 × 7.30 mm`** equatorial chamber inside `Apple_Hemisphere_A` + `B` (`z = -3.65..+3.65 mm`) | **`+0.70 mm` diametral, `+0.80 mm` axial clearance** (`0.0 mm³` interference) |
| **`KA006`** & **`B0CMCFGXSL`** | Bambu Lab Single LED Magnetic Control Switch Light (`CR927` + Magnet) | LED: **`Ø 7.50 × 6.00 mm`** (`CR927` `Ø 9.5 × 2.7 mm`); Magnet: **`Ø 8.00 × 2.00 mm`** | Planet upper bore: **`Ø 8.00 × 6.00 mm`** (`Z = 3.60..9.60 mm`, `Ø 7.40 mm` crush ribs) over **`Ø 7.60 × 3.50 mm` balcony peg**; Wand star socket: **`Ø 8.30 × 2.20 mm`** | **`0.10 mm` crush-rib press fit** for LED, **`+0.40 mm` slip/snap fit** on balcony peg, **`+0.30 mm`** magnet socket |
| **`U190`** *(Optional)* | M5Stack Unit `INA226-10A` High-Side I2C Current/Power Sensor | **`32.0 × 24.0 × 10.2 mm`** (`HT3.96-4P` + Grove `HY2.0-4P`) | Seats inside the open `Ø 135.0 × 50.0 mm` Hollow Root Vault inline with `WAGO-3` | Unobstructed clearance inside open vault |
| **`B0BYF4X65F`** | `M2.5 × 6 mm` Button Head Cap Machine Screws (`2×`) | **`M2.5 × 6.0 mm`** thread, `Ø 4.5 × 1.5 mm` button head | `Battery_Cover` **`Ø 2.80 mm` through-holes** (`Ø 5.0 × 1.6 mm` counterbores) into `trunk_base` **`Ø 2.20 × 6.0 mm` self-tapping bosses** at `(±30.0, -33.0 mm)` | Exact `M2.5` self-tapping boss engagement |

---

## 4. Automated Verification Summary

- **SKU & Table Parity:** All 33 SKUs, ASINs, and part codes appearing in the original `README.md` (`B01D8FLSV8`, `B07C7VSRBG`, `B07XXWQ49N`, `U6223`, `B07NKT2P2F`, `221-412`, `221-413`, `221-415`, `B087BT1PH3`, `B07WPWFSNQ`, `A092`, `C008`, `A096`, `B0BFRPMSW6`, `LA002`, `B0CCS11V7H`, `B09YTMNGTD`, `B0CT827QQC`, `KC013`, `KC012`, `KA006`, `U190`, `B07V5CW1MG`, `CR1632`, `B0CMCFGXSL`, `CR927`, `B0BYF4X65F`, `11801`, `32501`, `13405`, `10200`, `11100`, `11600`) are present in [`bom/bom.yaml`](../bom/bom.yaml), and [`docs/BOM.md`](BOM.md) + [`bom/bom.csv`](../bom/bom.csv) are generated deterministically by [`scripts/gen_bom.py`](../scripts/gen_bom.py).
- **Generator Idempotency & `--check`:** Running `uv run --with pyyaml python3 scripts/gen_bom.py` twice produces zero diff (`git diff --exit-code docs/BOM.md bom/bom.csv`), and `uv run --with pyyaml python3 scripts/gen_bom.py --check` exits `0`.
- **Markdown Link & Anchor Check:** Checked all internal relative links and heading anchors across all 10 markdown files (`README.md`, `docs/*.md`, `GEMINI.md`, `POWER_ARCHITECTURE.md`): **0 broken relative links or anchors**, and **0 hardcoded `file://` links**.
- **CAD & Webapp Verification Pipeline:** Full `generate_all.py`, `verify_model.py`, and `export_webapp_assets.py` pipeline passes with `0.000 mm³` interference across all electronic component gauges and mechanical joints.
