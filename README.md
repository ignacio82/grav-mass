# 🍎🌲 Grav-Mass Day "Falling Apple Cascade" Marble Run Tree

[![License: CC BY-NC 4.0 (3D Model & CAD)](https://img.shields.io/badge/3D_Model_%26_CAD-CC_BY--NC_4.0_(Non--Commercial)-crimson)](LICENSE)
[![License: MIT (Web App & ESPHome)](https://img.shields.io/badge/Web_App_%26_ESPHome-MIT-emerald)](LICENSE)

> **🌐 [Launch the Live 3D Simulator, Step-by-Step Assembly Studio & Plate Inspector (`newton.martinez.fyi`)](https://newton.martinez.fyi/)**

<!-- TODO: add photo/GIF of the finished build -->

A motorized, closed-loop kinetic marble run sculpture (~527 mm tall × ~336 mm base diameter) celebrating Isaac Newton's **Grav-Mass Day** (December 25) and the Solar System. Engineered for 4-color multi-material 3D printing on the **Snapmaker U1** (`270 × 270 × 270 mm` build volume), this model lifts `Ø 25.0 mm` glowing crimson apple marbles up a two-stage internal Archimedes screw auger inside a bark-textured hollow tree trunk, discharges them beneath an illuminated sculpted Heart-Shaped Red Apple Topper, and cascades them down a `4.5`-turn conical emerald-green helical track past **8 multi-color, magnetically-lit Solar System planets**.

---

## ✨ Key Features

- **15 Single-Color + 3 Dedicated 4-Color Build Plates (18 Plates Total):** Pre-arranged for Snapmaker OrcaSlicer (`0.4 mm` nozzle) with zero prime towers on Plates 1–15 and zero convex-hull overlaps — see **[`docs/PRINTING.md`](docs/PRINTING.md)**.
- **One-Cable, 100% Solder-Free `12V` Power & ESPHome Smart Control (`A092` + `C008`):** Powered by one external `12V 5A` adapter feeding 3 fused WAGO `221` branches for the ESP32 controller, `12V 150 RPM N20` motor, and isolated `5V 5A` LED buck rail — see **[`docs/SMART_HOME.md`](docs/SMART_HOME.md)** and **[`POWER_ARCHITECTURE.md`](POWER_ARCHITECTURE.md)**.
- **Wireless Glowing Marbles (`KC013`), Planets (`KA006`) & RGB Lantern Apple Topper (`B09YTMNGTD`):** 6 twist-lock hollow apple marbles and 8 sculpted Solar System planets toggled with the magnetic **`Magic_LED_Wand`** — see **[`docs/BOM.md`](docs/BOM.md)**.
- **Hidden Inner Assembly Numbering System:** Every trunk section (`1–4`), auger half (`1–2`), bracket (`1–24`), track segment (`1–14`), planet/peg (`1–8`), and marble half (`A`/`B`) has debossed alignment marks that hide completely once assembled — see **[`docs/ASSEMBLY.md`](docs/ASSEMBLY.md)**.
- **Galileo–Newton Gravity Chronometer (`G0–G5` Timing Gates & Elevation Scales):** Molded `100 mm` spiral arc-length ticks, `25 mm` elevation ticks, and `0.35 mm` acoustic click micro-ribs for measuring $g \approx 9.81\text{ m/s}^2$ — see **[`docs/PHYSICS.md`](docs/PHYSICS.md)**.

---

## 🚀 Quick Start

1. **🛒 Buy Components & Filament:** Order the off-the-shelf solder-free electronics, `2× M2.5 × 6 mm` screws, and filament spools from **[`docs/BOM.md`](docs/BOM.md)** (or import **[`bom/bom.csv`](bom/bom.csv)** directly into a spreadsheet).
2. **🖨️ Slice & Print the 18 Plates:** Open **[`output/3mf/GravMass_Tree_Ultimate_U1.3mf`](output/3mf/GravMass_Tree_Ultimate_U1.3mf)** (or individual plate `.3mf` files) and follow the plate support settings in **[`docs/PRINTING.md`](docs/PRINTING.md)**.
3. **🔧 Assemble the Tree:** Follow Steps 1–9 and the hidden inner numbering guide in **[`docs/ASSEMBLY.md`](docs/ASSEMBLY.md)** Alongside the **[Live 3D Assembly Studio (`newton.martinez.fyi`)](https://newton.martinez.fyi/)**.
4. **⚡ Flash ESPHome & Run:** Flash **[`esphome/grav-mass-tree.yaml`](esphome/grav-mass-tree.yaml)** onto the `C008` ATOM Lite and plug in the single `12V DC` barrel cord per **[`docs/SMART_HOME.md`](docs/SMART_HOME.md)**.

---

## 📚 Documentation Index

| Document | Contents |
| :--- | :--- |
| **[`docs/BOM.md`](docs/BOM.md)** | Complete shopping list (electronics, fasteners, filament) generated from [`bom/bom.yaml`](bom/bom.yaml) + system connection flowchart (`bom/bom.csv` also available) |
| **[`docs/PRINTING.md`](docs/PRINTING.md)** | 18-plate `.3mf` breakdown, toolhead palettes, support settings, and why `"On build plate only"` is used |
| **[`docs/ASSEMBLY.md`](docs/ASSEMBLY.md)** | Hidden inner assembly numbering system table and step-by-step physical assembly instructions (Steps 1–9) |
| **[`docs/PHYSICS.md`](docs/PHYSICS.md)** | Galileo–Newton Gravity Chronometer guide, `G0–G5` timing gate coordinates, 3 timing methods, $\hat{g}$ equations, and $\kappa$ inertia table |
| **[`docs/SMART_HOME.md`](docs/SMART_HOME.md)** | ESPHome + Home Assistant integration, zero-solder pinout flowchart & terminal map, and flashing instructions |
| **[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)** | Running the 3D web app locally, regenerating CAD / physics verification, and editing the machine-readable BOM |
| **[`POWER_ARCHITECTURE.md`](POWER_ARCHITECTURE.md)** | Full electrical engineering specification, power budget, fuse schedule, wire-gauge voltage drop math, and multimeter commissioning checklist |
| **[`docs/REFACTOR_NOTES.md`](docs/REFACTOR_NOTES.md)** | Documentation refactoring section map, assumptions, verification checklist, and noted suspected issues |

---

## 📜 License (`CC BY-NC 4.0` + `MIT` — Free to Print & Remix, No Commercial Sales)

This project is dual-licensed (see **[`LICENSE`](LICENSE)** for the full legal text):
- **3D Models, Parametric CAD (`cad/*.py`), Printable Files (`output/*.stl`, `output/*.step`, `output/3mf/*.3mf`), 3D Mesh Buffers (`webapp/assets/meshes.bin`), and Documentation:** Licensed under the **[Creative Commons Attribution-NonCommercial 4.0 International License (`CC BY-NC 4.0`)](https://creativecommons.org/licenses/by-nc/4.0/)**.
  - **✅ Permitted:** You are free to download, 3D-print, modify, remix, display publicly (classrooms, science fairs, museums, videos/streams), and share the model and derivatives for **non-commercial** purposes with attribution to **Ignacio Martinez (`github.com/ignacio82/grav-mass`)**.
  - **🚫 Strictly Prohibited (No Selling the Model):** You may **not** sell, rent, paywall, or commercially redistribute the digital 3D model files (`.stl`, `.step`, `.3mf`, `meshes.bin`, or `cad/*.py`) or remixes thereof on any marketplace (Etsy, Cults3D, Printables Store/Club, Thingiverse, Patreon, eBay, Amazon, etc.), and you may **not** sell physical 3D-printed copies or kits of this model without prior written permission from the copyright holder.
- **Web Application Viewer Code (`webapp/*.js`, `webapp/*.html`, `webapp/*.css`) & ESPHome Firmware (`esphome/*.yaml`):** Licensed under the permissive **[MIT License](LICENSE)**.
