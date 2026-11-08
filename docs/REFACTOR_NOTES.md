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

## 3. Suspected Issues (Noticed in Existing Docs, Intentionally Left Unchanged)

Per the refactoring constraints (*"Do NOT change the content's meaning. Move text, don't rewrite it. Do not 'fix' physics, part numbers, dimensions, or GPIO assignments. If you notice an inconsistency or something that looks wrong, do not correct it. List it in `docs/REFACTOR_NOTES.md` under 'Suspected issues'"*), the following inconsistencies were observed and left untouched:

1. **Build Plate Count (`18 Plates` in `README.md` / `docs/PRINTING.md` vs. `6 Plates` in `GEMINI.md`):**
   - The existing `README.md` (now [`docs/PRINTING.md`](PRINTING.md)) documents **18 pre-arranged `.3mf` build plates** (15 single-color plates `Plate_1`..`Plate_15` + 3 dedicated 4-color plates `Plate_16`..`Plate_18`). However, [`GEMINI.md`](../GEMINI.md) Section 2.4 still describes an earlier **6-plate layout** (`Plates 1–5` single-color + `Plate 6` multi-color).
2. **Rear `-X` DC Barrel Jack Bore Diameter & Z-Height (`Ø 11.4 mm` at `Z = 10.0 mm` vs. `Ø 11.2 mm` at `Z = 9.5 mm`):**
   - In [`docs/BOM.md`](BOM.md) (row `B07C7VSRBG` and the Mermaid connection diagram), [`docs/ASSEMBLY.md`](ASSEMBLY.md) (Step 2.2), and [`GEMINI.md`](../GEMINI.md) (Section 5.9), the rear `-X` panel-mount DC barrel jack port on `trunk_base` is specified as **`Ø 11.4 mm` (`Ø 11.40 mm`) at `Z = 10.0 mm`** (with `B07C7VSRBG` described as `Ø 11.0 mm` `M11 × 0.75` thread).
   - In [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) (Sections 3.1, 4.1, 4.2, 8, and 9 Step 2), the same port on `trunk_base` is repeatedly described as **`Ø 11.2 mm` at `X = -72.0, Y = 0.0, Z = 9.5 mm`**.
3. **Under-Track LED Channel & Starter Pocket Dimensions (`docs/ASSEMBLY.md` vs. `GEMINI.md`):**
   - [`docs/BOM.md`](BOM.md) and [`docs/ASSEMBLY.md`](ASSEMBLY.md) Step 6.5 describe the under-track LED channel as an **`8.0 × 3.6 mm` internal dovetail chamber (`4.6 mm` snap-in throat)** with a **`10.0 × 16.0 × 3.7 mm` starter feed pocket** for the `B0CCS11V7H` WS2812B pebble wire.
   - [`GEMINI.md`](../GEMINI.md) Section 5.5 still describes an earlier **`13.0 × 2.5 mm` underside COB channel** and **`14.6 × 16.0 × 2.8 mm` `cob_pcb_pocket`** for a `12.0 mm` PAUTIX RGBIC COB strip (`B0CH149KMC`).
4. **Cantilever Branch Bracket Engraving Description (`1–4` in Numbering Table vs. `1–24` in Step 5):**
   - In [`docs/ASSEMBLY.md`](ASSEMBLY.md), the **Hidden Inner Assembly Numbering System** table states that the Cantilever Branch Brackets have Arabic digits **`1`, `2`, `3`, or `4`** in the recessed top saddle between the two `Ø 4.0 mm` pegs.
   - However, **Step 5** in [`docs/ASSEMBLY.md`](ASSEMBLY.md) states that each of the 24 station brackets (`bracket_01`..`bracket_24`) has its exact station number (**`1` through `24`**) engraved face-up in the recessed top saddle (in addition to `1–4` horizontal tier bars on the back of the dovetail tenon).
5. **Marble LED SKU (`KC013` vs. `KC012`/`KC013`):**
   - [`docs/BOM.md`](BOM.md) and [`docs/ASSEMBLY.md`](ASSEMBLY.md) Step 1 list the Bambu Lab Y-Shape 3-LED light strictly as **`KC013`** (Warm White).
   - [`docs/PHYSICS.md`](PHYSICS.md) Section 4 (Rotational Inertia Multiplier $\kappa$ table) and [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) Section 3.1 refer to **`KC012`/`KC013`**. (`KC012` is preserved in `alt_skus` in [`bom/bom.yaml`](../bom/bom.yaml)).
6. **Legacy `cob_strip` Entity ID & Friendly Name Differences (`docs/SMART_HOME.md` vs. `POWER_ARCHITECTURE.md`):**
   - [`docs/SMART_HOME.md`](SMART_HOME.md) lists the track LED entity ID as `light.helical_track_rgbic_cob_strip` (retaining `cob_strip` in the identifier even though the hardware uses the `B0CCS11V7H` WS2812B pebble wire) and lists `sensor.12v_supply_rail_voltage_vin`, `binary_sensor.12v_power_rail_voltage_alert`, and `binary_sensor.auger_motor_fault_stall_alert`.
   - [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) Section 11 refers to different friendly names (`Motor Bus Voltage (VIN)`, `12V Supply Rail Healthy`, `Motor Driver Fault / Stall`, `Zone 2 — Helical Track Pebble Strip`, `Zone 1 — Apple Topper Ring`).
7. **Alternative Power Supply & Buck Converter Models in `POWER_ARCHITECTURE.md`:**
   - While [`docs/BOM.md`](BOM.md) standardized on the `BTF-LIGHTING B01D8FLSV8` `12V 5A` power supply and `UCTRONICS B07XXWQ49N` (`U6223`) `12V→5V 5A` buck converter, [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) (Sections 2.1, 3.2, 4.1, 4.2, 5.1, 6, 8, 9, 10, 11) still references `MEAN WELL GST60A12-P1J` / `GST36A12-P1J` and `DFRobot DFR0205` in several diagrams and narrative paragraphs.
8. **Hardcoded Local `file://` Links in `POWER_ARCHITECTURE.md`:**
   - [`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md) lines 413 and 440 contain local filesystem URLs (`file:///home/ignacio/grav-mass/esphome/grav-mass-tree.yaml`) instead of relative repository paths (`esphome/grav-mass-tree.yaml`).

---

## 4. Automated Verification Summary

- **SKU & Table Parity:** All 33 SKUs, ASINs, and part codes appearing in the original `README.md` (`B01D8FLSV8`, `B07C7VSRBG`, `B07XXWQ49N`, `U6223`, `B07NKT2P2F`, `221-412`, `221-413`, `221-415`, `B087BT1PH3`, `B07WPWFSNQ`, `A092`, `C008`, `A096`, `B0BFRPMSW6`, `LA002`, `B0CCS11V7H`, `B09YTMNGTD`, `B0CT827QQC`, `KC013`, `KC012`, `KA006`, `U190`, `B07V5CW1MG`, `CR1632`, `B0CMCFGXSL`, `CR927`, `B0BYF4X65F`, `11801`, `32501`, `13405`, `10200`, `11100`, `11600`) are present in [`bom/bom.yaml`](../bom/bom.yaml), and all 31 generated table rows/headers in [`docs/BOM.md`](BOM.md) match the original `README.md` tables verbatim (with relative paths adjusted to `../`).
- **Generator Idempotency & `--check`:** Running `uv run --with pyyaml python3 scripts/gen_bom.py` twice produces zero diff (`git diff --exit-code docs/BOM.md bom/bom.csv`), and `uv run --with pyyaml python3 scripts/gen_bom.py --check` exits `0`.
- **Markdown Link & Anchor Check:** Checked **182 internal relative links and heading anchors** (and 55 external URLs) across all 10 markdown files (`README.md`, `docs/*.md`, `GEMINI.md`, `POWER_ARCHITECTURE.md`): **0 broken relative links or anchors**.
- **Hard Constraint Audit:** Zero files under `cad/`, `output/`, `webapp/`, or `esphome/` were modified (`git diff main -- cad/ output/ webapp/ esphome/` is empty).
