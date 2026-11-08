# 🌐 Live 3D Web App & Local CAD Development

## Live GitHub Pages App (`newton.martinez.fyi`)
Open **[https://newton.martinez.fyi/](https://newton.martinez.fyi/)** on desktop or mobile to:
- Watch the **coupled 3D rigid-body physics simulation** (sub-stepped gravitational acceleration $a_s(\theta)$, centrifugal outer-wall trough banking $\phi = \arctan(a_c / g \cos\alpha)$ with radial/vertical ball climb, outer-wall rubbing friction, inelastic $e = 0.52$ sphere-to-sphere queueing, and live telemetry for peak speed, banking angle, and wall derailment margin across 3 selectable surface friction presets).
- Click **"✨ Cycle All 14 LEDs Mode"**, **"🪄 Tap Next Planet with Wand"**, or **tap directly on any 3D planet or rolling marble** to animate the Magic Wand and cycle the internal wireless LEDs.
- Step through the **12-Stage Piece-by-Piece Interactive Assembly Guide** (with the `⏮ Prev Piece` / `Next Piece ⏭` connection controller) or inspect & download all **18 Snapmaker U1 Build Plates (15 Single-Color + 3× 4-Color Plates, configured for a 0.4 mm nozzle)**.

## Running the Web App Locally
```bash
python3 -m http.server 8420 --directory webapp
```
Then open `http://localhost:8420` in your browser.

## Regenerating All CAD Files & Running B-Rep + 3D Physics Certification
To rebuild all `.step`, `.stl`, `.3mf` plates, and webapp 3D assets from Python [`build123d`](https://github.com/gumyr/build123d) source and run both the automated B-Rep metrology suite ([`cad/verify_model.py`](../cad/verify_model.py)) and the **1000 Hz 3D Rigid-Body & Triangle-Mesh Contact Physics Certification Suite** ([`cad/verify_physics.py`](../cad/verify_physics.py)):
```bash
uv run --with build123d python3 -u cad/generate_all.py && \
uv run --with build123d --with trimesh --with scipy --with rtree python3 -u cad/verify_model.py && \
uv run --with build123d --with trimesh --with scipy --with rtree python3 -u cad/verify_physics.py && \
uv run --with numpy python3 -u cad/export_webapp_assets.py
```

## Editing the BOM
[`bom/bom.yaml`](../bom/bom.yaml) is the single source of truth for all electronics, fasteners, and filaments. Do not edit the generated tables in [`docs/BOM.md`](BOM.md) or [`bom/bom.csv`](../bom/bom.csv) by hand:

1. Edit [`bom/bom.yaml`](../bom/bom.yaml).
2. Run the BOM generator to validate the YAML and regenerate [`docs/BOM.md`](BOM.md) and [`bom/bom.csv`](../bom/bom.csv):
   ```bash
   uv run --with pyyaml python3 scripts/gen_bom.py
   ```
3. Verify that the generated outputs are in sync (`--check` exits non-zero if out of date):
   ```bash
   uv run --with pyyaml python3 scripts/gen_bom.py --check
   ```
4. Commit [`bom/bom.yaml`](../bom/bom.yaml), [`bom/bom.csv`](../bom/bom.csv), and [`docs/BOM.md`](BOM.md) together.
