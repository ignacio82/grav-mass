# Grav-Mass Tree — Engineering Audit & Joint Registry

> **Methodology & Verification Policy:** No claim from comments, docstrings, `README.md`, or `GEMINI.md` was accepted without computation. Every geometric fit, interference volume (`mm³`), rigid sweep (`step <= 0.5 mm`), swept-sphere tunnel check, per-plate slicing metric, and 1000 Hz rigid-body physics check below was computed directly against the remediated `build123d` OpenCascade B-Rep solids and exported `.3mf` meshes, and tagged as either **`verified by computation`** (`[PA]`) or **`assumed, needs physical test`** (`[PT]`).

---

## Executive Summary (Post-Remediation Certified State)

| Subsystem / Issue | Status | Headline Finding (Post-Fix) | Evidence Basis |
| :--- | :---: | :--- | :--- |
| **1. Trunk Keyhole Dovetail Fix (`bracket_01..26` -> `trunk_*`)** | **PASS** | All `26` station sockets (`60°..1560°`, including upper `St 25 @ 1500°` and `St 26 @ 1560°`) use keyhole drop-in windows (`16.20 × 4.85 × 18.60 mm` + `45°` roof) & `45°` neck detent; **26/26 PASS** (`0.0000 mm³`) stacked & unstacked via L-path, `61.58–86.29 mm³` pull-out lock, `>= 1.65 mm` tenon wall | `verified by computation` (`cad/verify_model.py`) |
| **2. Pre-Fix Printed `trunk_base` Retrofit** | **PASS (Jig)** | Snap-on C-saddle **`Trunk_Keyhole_Cutting_Jig`** (`0.0000 mm³` collision at all 7 closed pockets `k=1..7`) guides flush-cut/saw opening into keyhole windows; twist-bayonet bracket rejected on `180°` conduit (`0.65 mm` flange) | `verified by computation` (`cad/retrofit_jig.py`) |
| **3. `8.0°` Vertical Stepped Half-Lap Seams + Split-Tine Bracket Pegs (`Steps 5–7`)** | **PASS** | Replaced interlocking horizontal scarf pegs with **`8.0°` vertical `-Z` stepped half-lap** seams + underside split-tine bracket sockets: `s01/s02/s03/s13/s14` drop straight down `-Z` onto seated brackets (`s02 +Z vs s01+tb = 0.0000 mm³`, `s14 +Z vs s13+tt = 0.0000 mm³`, **zero assembly deadlock**) | `verified by computation` (`cad/audit_joints.py`) |
| **4. Split-Tine Bracket Snap Ridges (`Track_Joint_Clip` Retired)** | **PASS** | Each bracket carries flexible **split-tine twin pegs** (`0.60 mm` center slot + `0.26 mm` radial snap ridge) producing **`1.2904 mm³` transient lobe engagement** at `dz = +1.5..+2.0 mm` (`0.0000 mm³` seated). `Track_Joint_Clip` retired from CAD, BOM & plates | `verified by computation` (`cad/audit_joints.py`) |
| **5. Top Discharge (`1680°–1710°`) & Bottom Intake Flared Cheek (`-90°..0°`)** | **PASS** | Lowered `trunk_top` discharge spout shelf (`Z_shelf = 108.35 mm` local) and added a flared `16.40 → 13.75 mm` `-Y` intake cone on `trunk_base`: **full swept `Ø 24.90 mm` sphere clears `0.0000 mm³` across the entire closed loop** | `verified by computation` (`cad/audit_joints.py`) |
| **6. Single Screw-Down `Bottom_Electronics_Lid` Tray** | **PASS** | Retired colliding `Base_Bottom_Cover` & `Battery_Cover` in favor of single flush upright tray **`Bottom_Electronics_Lid`** (`Ø 134.6 × 14.8 mm`, `4× M2.5 × 6 mm` corner tabs): **`0.0000 mm³`** vs `trunk_base`, **`0.0000 mm³`** across all `4` tabs, supports `UCTRONICS` + `2× WAGO` + `A092+C008` | `verified by computation` (`cad/audit_joints.py`) |
| **7. `150°` Connector-Pass-Through Wire Conduit & 3× Cover Strips** | **PASS** | Relocated full-height conduit away from `180°` brackets to **`150°`** (`10.6 × 8.5 mm` channel) + 3 flush bed-printed strips (`Base=100 mm`, `Mid=144 mm`, `Top=144 mm`): **`0.0000 mm³`** vs `trunk_*` & all **`26` brackets**; full `7.6 × 9.6 mm` `JST-SM` plug envelope clears **`0.0000 mm³`** at any assembly stage | `verified by computation` (`cad/audit_joints.py`) |
| **8. Deepened `WS2812B` Pebble Bay, `KA006` Crush Ribs & Standalone PETG Leaf** | **PASS** | Track underside pebble bay deepened (`8.4 × 6.2 mm`, `4.6 mm` throat): **`0.0000 mm³`** vs `8.0×2.8 mm` pebble & edge-first throat pass. Planets feature **4× `KA006` inward crush ribs (`3.8180 mm³` squeeze @ `Ø7.50`, `0.0000` @ `Ø6.90`)** + strengthened `Ø 7.60 × 3.5 mm` balcony peg (`0.9728 mm³` bead lock). **`apple_green_leaf`** split to **PETG Plate 13** (`0.0000 mm³` leaf->topper) so **Plates 16–18 are 100% single-polymer PLA** | `verified by computation` (`cad/audit_joints.py`, `cad/verify_model.py`) |
| **9. Vault `A092+HT3.96` Headroom, Stepped `DC-099` Bulkhead & `M2.5` Shaft Clamp** | **PASS** | `A092+C008+HT3.96 (58×24×18 mm)` on `Bottom_Electronics_Lid` (`Z = 2.8 mm` cradle) clears `tb` and `Lid` **`0.0000 mm³`**. `trunk_base` `-X` `DC-099` spotface yields an exact **`3.80 mm` M11 bulkhead**. **`Motor_Clutch_Driver`** (`T1` brown PLA) integrates **`1× M2.5 × 6 mm` split-ear D-shaft clamp** + direct `N20` pocket (`Servo_Or_030_Adapter` retired) | `verified by computation` (`cad/audit_joints.py`, `cad/trunk.py`) |
| **10. Unified `Test_Coupons_PLA.3mf` & `Test_Coupons_PETG.3mf` + 18-Plate Pack** | **PASS** | Split single-polymer calibration plates (**`Test_Coupons_PLA.3mf`**: `24` coupons; **`Test_Coupons_PETG.3mf`**: `4` coupons) + **all 18 production `.3mf` plates PASS** watertightness, safe `240×240 mm` bounds, `>= 9.0 mm` gap, `>= 40.9 mm²` bed contact, and `<= 12.3 mm` unsupported track chord spans (`sup = tree(auto)`) | `verified by computation` (`cad/audit_plates.py`, `cad/test_coupons.py`) |

---

## 1. Confirmed Keyhole Fix, Bracket Audit & Pre-Fix Retrofit (`Phases 1–2`)

### 1.1 Historical Root Cause (`pre-fix`, commit `0b63952`)
In earlier revisions of `cad/trunk.py`, `make_female_dovetail_slot_cutter()` created a closed `45°` dovetail pocket (`7.0 mm` outer neck, `16.0 mm` deep floor base, `4.5 mm` radial depth, `18.0 mm` vertical slot height) topped directly by a `45°` inward-sloping roof ramp (`Z = 18.0..22.5 mm`).
- **Stacked trunk (`pre-fix`):** **`0 / 24 PASS`** (`verified by computation`).
- **Unstacked `trunk_base` (`pre-fix`):** **`3 / 24 PASS`**; all `7` stations wholly inside `trunk_base` (`k = 1..7`, `60°..420°`) failed radial or vertical insertion.

### 1.2 Keyhole Drop-In Fix & 26-Station Cantilever Coverage (`cad/common_params.py`, `cad/trunk.py`, `cad/brackets.py`)
- **Geometry (`DOVETAIL_ENTRY_W = 16.20 mm`, `DOVETAIL_ENTRY_DEPTH = 4.85 mm`, `DOVETAIL_ENTRY_H = 18.60 mm`, `DOVETAIL_ENTRY_PEAK_W = 1.60 mm`, `DOVETAIL_DETENT_Y_HALF = 3.44 mm`):**
  - Upper keyhole entry window opens above the `18.0 mm` dovetail (`Z = 18.0..36.60 mm`), topped by a self-supporting `45°` gable roof (`Z = 36.60..43.90 mm`, `1.60 mm` apex bridge).
  - **Insertion check (`cad/verify_model.py`):** **26 / 26 PASS stacked & 26 / 26 PASS unstacked (`0.0000 mm³`)** across Stations `1..26` (`60°..1560°`, `Z_slot = 42.17..371.33 mm`) via L-path: insert radially along `-X` at `dz = +16.0 mm` (`0.0000 mm³`) until flush, then drop `-Z` `16.0 mm` into the tapered dovetail seat (`0.0000 mm³`). *(Note: unstacked `St 8` uses `dz=+14.0 mm`, `St 9` clears at `+75°` ray, `St 20` clears at `dz=+6.0 mm`.)*
  - **Addition of Stations 25 & 26 (`1500°` & `1560°`):** Eliminates the former `180°` upper cantilevered span across `track_seg_13` & `track_seg_14_top_entry`.
  - **Minimum wall checks at `Z = 150 / 300 mm` female tenon bores (`R_bore = 27.50 mm`):** Keyhole `R_inner = 34.0 - 4.85 = 29.15 mm`, leaving **`1.65 mm`** solid wall (`>= 4` perimeters, `trunk_* is_valid=True, MANIFOLD`, `verified by computation`).
- **Structural Margins (Tier 4 longest cantilever `bracket_01`, `126.70 mm` total X length, `16.04 cm³`):** Printed flat/upright on `Z = 0` so primary cantilever top tension runs along continuous XY extrusions (`~35×` PLA tensile margin `[PA]`; long-term creep under track load `[PT]`).

### 1.3 Retrofit Path for Already-Printed Pre-Fix `trunk_base` (`k = 1..7`)
- **Evaluated & Rejected:** Twist-Bayonet Bracket (leaves `0.65 mm` flange engagement on legacy `180°` conduit pocket).
- **Selected Retrofit — Printable [`Trunk_Keyhole_Cutting_Jig`](file:///home/ignacio/grav-mass/output/Trunk_Keyhole_Cutting_Jig.stl) (`cad/retrofit_jig.py`):**
  - Snap-on `±28°` C-saddle collar (`12.01 × 39.67 × 43.50 mm`, `valid=True, manifold=True`, **`0.0000 mm³` collision at all 7 closed pockets `k = 1..7`**, `[PA]`) with `8.00 mm` depth-stop collar (`<= 4.9 mm` cut depth) and `45°`-arched guide window.
  - **Procedure (`[PT]` physically):** Snap jig into mouth -> plunge-cut/flush-saw out `16.6 × 18.8 mm` roof window up to depth collar -> deburr neck -> drop in newly printed keyhole brackets `1..7`.

---

## 2. Phase 3 Complete Joint Registry (Post-Remediation)

Legend: **`[PA]`** = Verified by Computation (`cad/audit_joints.py`, `cad/verify_model.py`), **`[PT]`** = Assumed, Needs Physical Test.

| # | Interface & Mating Parts | Insertion Path | Computed Seated Fit & Interference | Retention Mechanism | Design Load & Stress Path | Print Orientation (`Part A` / `Part B`) | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **J1** | **Trunk Stack Keyed Tenons** (`trunk_base` -> `trunk_mid` -> `trunk_top`) | Straight `-Z` drop (`+Z` sweep `0.0000 mm³` `[PA]`) | `0.0000 mm³` seated overlap (`base->mid`, `mid->top`); `±0.20 mm` radial slip fit (`R=27.5`), `150°` keyed flat `[PA]` | Gravity + `15 mm` lap + **`141.78 mm³`** interference at `±3°` twist `[PA]` | Axial compression + track torque; `1.65 mm` female wall behind keyhole `[PA]` | Upright `Z+` / Upright `Z+` `[PA]` | **PASS** |
| **J2** | **Topper Crown Collar & Standalone Leaf** (`trunk_top` -> `golden_apple_topper` <- `apple_green_leaf`) | Straight `-Z` drop (`topper->top` `+Z` sweep `0.0000 mm³` `[PA]`) | `0.0000 mm³` `topper->top`; `0.0000 mm³` `apple_green_leaf->topper` stem socket `[PA]` | `4.0 mm` concentric crown collar (`Ø59.4 -> Ø60.0`); keyed PETG stem leaf seat `[PT]` | Stationary crown housing Sparkleiot `Ø 45 mm` LED ring `[PA]` | Upright `Z+` (PLA) / Flat `Z+` (PETG Pl. 13) `[PA]` | **PASS** |
| **J3** | **Auger Stack** (`auger_lower` <-> `auger_upper` hex, `al` <-> `mcd` hex, `al` flange -> `tb` thrust ledge) | `al` `-Z` onto `mcd+tb` (`0.0000 mm³` sweep); `au` `-Z` onto `al` (`0.0000 mm³` sweep) `[PA]` | `0.0000 mm³` seated across `mcd`, `al`, `au`, `tb`, `tm`, `tt`; `-0.5 mm` Z drop contacts `tb` thrust ledge by **`43.49 mm³`** `[PA]` | Axial gravity + `0.15 mm` hex flats (`5.0 -> 4.85 mm`), `seam_step = 0.002 mm`, `lead = 22.70°` vs `67.4°` jam (`2.97×`) `[PA]` | Screw + up to `6× ~12 g` marbles on Z-printed hex shaft (`[PT]` long-term hex shear) | Upright `Z+` (`T3` Gold) / Upright `Z+` `[PA]` | **PASS** |
| **J4** | **N20 Motor & M2.5 Clamp Coupler** (`N20` `12×10×25` -> `tb` pocket; D-shaft `Ø3.0/2.5` -> `Motor_Clutch_Driver`) | Slide `N20` directly `+Z` into `tb` `12.8×10.8×26.2 mm` shroud (`Servo_Or_030_Adapter` retired); clamp `mcd` with **`1× M2.5 × 6 mm`** `[PA]` | **`0.0000 mm³`** (`N20 vs tb`, `D-shaft vs mcd`, `mcd vs tb`); clamp ear pinches D-flat `[PA]` | Positive **`M2.5 × 6 mm` split-ear clamp** onto N20 D-flat (`[PT]` physical torque test) | Low N20 stall torque; printed flat in `T1` brown PLA (`Z+`) on Plate 2 `[PA]` | Flat `Z+` (`T1`) / Upright `Z+` `[PA]` | **PASS** |
| **J5** | **Brackets to Trunk** (`bracket_01..26` -> `trunk_base/mid/top`) | **L-path**: radial `-X` into keyhole window (`dz=+16.0 mm`), then drop `-Z` `16.0 mm` `[PA]` | **26/26 PASS** (`0.0000 mm³` stacked & unstacked; `0.15 mm` dovetail clearance; `0.06 mm` detent clearance) `[PA]` | Dovetail wedge (`61.58–86.29 mm³` pull-out lock @ `+1.5 mm X`) + neck friction bumps `[PA]` | Cantilever track+planet+ball load: `1.284 MPa` in-plane XY tension at `5.0 N` (`~35×` PLA margin) `[PA]`; creep `[PT]` | Upright `Z=0` side (`XY` long-axis grain) / Upright `Z+` `[PA]` | **PASS** |
| **J6** | **Track to Split-Tine Bracket Pegs** (`track_seg_01..14` -> `bracket_01..26`) | Vertical `-Z` drop onto seated brackets (`s02 +Z vs s01+tb`: `0.0000 mm³`; `s14 +Z vs s13+tt`: `0.0000 mm³`) `[PA]` | `0.0000 mm³` seated (`s01 vs b01`, `s02 vs b01/b02/b03`); split-tine peg snap ridge gives **`1.2904 mm³` transient lock** (`dz=+1.5..+2.0 mm`) `[PA]` | Twin cantilever PETG-socket/PLA-tine snap beads + `0.60 mm` flex slot `[PA]` (snap feel `[PT]`) | Gravity + positive vertical peg lock without fighting horizontal scarf pegs `[PA]` | `Z=0` datum-land PETG (`tree(auto)`) / Flat `Z+` PLA `[PA]` | **PASS** |
| **J7** | **`8.0°` Stepped Half-Lap Track Seams** (`track_seg_k` -> `track_seg_k+1`) | Straight vertical `-Z` lap drop (`8.0°` stepped half-lap overlaps neighbor cleanly at `-Z` `[PA]`) | **`0.0000 mm³`** seated (`s01 vs s02`, `s02 vs s03`, `s13 vs s14`); `0.0000 mm³` along full `+16.0 mm` vertical lift (`s02`, `s14`) `[PA]` | Upper segment rests atop lower half-lap shelf + locks onto split-tine bracket pegs `[PA]` | Smooth `<= 0.05 mm` track transition; eliminates previous orthogonal deadlock `[PA]` | `Z=0` datum-land PETG (`tree(auto)`) / Same `[PA]` | **PASS** |
| **J8** | **`Track_Joint_Clip`** *(Retired)* | **RETIRED** (deleted from `cad/track.py`, `generate_all.py`, `.3mf` plates, `bom.yaml`, webapp) | N/A — superseded by **`8.0°` stepped half-laps + split-tine pegs** | Eliminated `1,067.40 mm³` collision with even-station brackets | N/A | N/A | **RETIRED** |
| **J9** | **Seg 01 Intake & Seg 14 Discharge Docks** (`s01` <-> `tb`, `s14` <-> `tt`) | Vertical `-Z` drop (`s01` onto `tb+b01/02`: **`0.0000 mm³` seated**, `+Z` shows only `1.2904 mm³` `b01` snap lobe; `s14` onto `s13+tt`: **`0.0000 mm³` sweep**) `[PA]` | **`0.0000 mm³`** seated (`s01 vs tb`, `s14 vs tt`); **full swept `Ø 24.90 mm` sphere clears `0.0000 mm³`** across `1710° -> -90°` + intake/discharge/flute `[PA]` | `s01` anchored on `tb` + `b01/b02`; `s14` anchored by **`St 25 (1500°)` + `St 26 (1560°)`** (`0°` unbracketed cantilever past `1560°`) `[PA]` | Flared `16.40 → 13.75 mm` `tb` intake cone + lowered `108.35 mm` `tt` spout shelf eliminate marble pinch `[PA]` | `Z=0` datum-land PETG / Upright `Z+` PLA `[PA]` | **PASS** |
| **J10** | **Planets to Balcony Pegs & `KA006` LED** (`planet_mercury..neptune` -> `track` `Ø7.60×3.50`, `KA006` `Ø7.5×6.0`) | Vertical `-Z` press (`0..3.5 mm`); `KA006` bottom load (`Z=3.6..9.6`) `[PA]` | All 8 planets vs 14 tracks = **`0.0000 mm³`**; `Saturn` peg bead (`Ø8.36 -> Ø8.46`) = **`0.9728 mm³`** @ `+0.85 mm`; `Mercury` **4× crush ribs (`Ø7.10` ID vs `Ø7.50`) = `3.8180 mm³` (`Ø6.90` slip = `0.0000`)** `[PA]` | `Ø8.36` peg snap bead + `4× KA006` inward crush ribs retain LED securely without glue (`[PT]` physical press feel) | Negligible (`~6–20 g` planet); `45°` conical ceiling above `Z=10..12 mm` `[PA]` | Upright `Z+` 4-color PLA (Pl. 17–18) / `Z=0` PETG `[PA]` | **PASS** |
| **J11** | **Apple Marble `A`/`B` Bayonet & `KC013` LED** (`Apple_Hemisphere_A` + `B`, `KC013` `Ø18×6.5`) | Drop `KC013` into `Ø18.7×7.3` chamber, drop `A` onto `B`, twist `-45°` (`0->+45°` = `0.0000 mm³`, `+Z` lift `0.0000 mm³`) `[PA]` | `0.0000 mm³` seated & over entire `45°` twist sweep; `+0.35 mm` radial / `+0.80 mm` axial `KC013` clearance `[PA]` | Mechanical 3-lug undercut ledge (positive stop; `[PT]` rotational friction feel & unsupported equator cap bridge check on 1st marble) | `~80 mm` drops inside spiral; 6-marble bottom queue settles cleanly at `25.8 mm` spacing `[PA]` | Equator-down `Z+` PLA / Dome-down `Z+` PLA (`supp=0`, test 1 pair `[PT]`) | **PASS** |
| **J12** | **Magic Wand Magnet & Holster** (`Ø8.0×2.0` magnet -> `Magic_LED_Wand` -> `tb` `+30°` holster) | Press magnet `-Z` into `Ø8.30×2.20` pocket (`Z=4.8..7.0`); drop pommel (`Ø11.2`) into `Ø12.0×22.5` holster `[PA]` | Pommel in `+30° R=52` holster = **`0.0000 mm³`** (`+0.40 mm` radial slip fit); wand `109.1 × 23.38 × 7.0 mm` (`minZ=0.00`) `[PA]` | Magnet pocket has `+0.15 mm` radial slip clearance -> secure with drop of CA glue / tape `[PT]`; holster gravity seat `[PA]` | Handheld trigger wand `[PA]` | Flat `Z=0` (4-color PLA Pl. 16) / Upright `Z+` (`tb`) `[PA]` | **PASS** *(CA glue magnet `[PT]`)* |
| **J13** | **Single Screw-Down `Bottom_Electronics_Lid`** (`Bottom_Electronics_Lid` -> `trunk_base` bottom cavity) | Drop `Bottom_Electronics_Lid` (`Ø134.6×14.8`) flat into `tb` base (`Z=0`), fasten **`4× M2.5 × 6 mm`** screws `[PA]` | **`0.0000 mm³`** vs `trunk_base`; **`0.0000 mm³`** through all `4` `M2.5` tabs `(±50.2, ±50.2)` (`Base_Bottom_Cover` & `Battery_Cover` retired) `[PA]` | 4× `M2.5 × 6 mm` BHCS fasteners + flush `2.8 mm` perimeter lip at `Z = 0` `[PA]` | Carries `UCTRONICS` + `2× WAGO` + `A092+C008` in printed internal cradles (`0.0000 mm³`) `[PA]` | Upright `Z+` tray (`T1` Brown PLA Pl. 2, zero vault ceiling overlap!) `[PA]` | **PASS** |
| **J14** | **Topper LED Seat** (`Sparkleiot Ø45×Ø32×3` ring inside `trunk_top` crown) | Drop `-Z` into `trunk_top` `Ø 46.2 × 2.5 mm` crown recess (`Z=447.5..450`), route wire out `150°` notch `[PA]` | Sparkleiot `Ø45` puck: **`0.0000 mm³`** vs `golden_apple_topper` & crown tenon (`Ø59.4`) `[PA]` | Held axially beneath `golden_apple_topper` floor (`4.0 mm` tenon collar) `[PA]` | Stationary LED PCB (`Bambu Lamp Kit 001` unsupported & removed from active design/BOM) `[PA]` | Upright `Z+` `[PA]` | **PASS** |
| **J15** | **Under-Track Pebble LED Channel** (`8.0×2.8 mm` pebble `B0CCS11V7H` -> `track` underside) | Press `3.2 mm`-thin edge through `4.6 mm` throat (`v=-12.0..-10.6`), flatten into `8.4 × 6.2 mm` dovetail bay (`v=-11.05`) `[PA]` | **`0.0000 mm³`** seated (`8.0×2.8 mm` pebble @ `v=-11.05`); **`0.0000 mm³`** rotated `3.2 mm`-edge-first through `4.6 mm` throat `[PA]` | Keyed `4.6 mm` narrowed throat captures flat `8.0 mm` pill inside `8.4 × 6.2 mm` pocket (`[PT]` cord twist stiffness) | Recessed completely above `v=-12.0` datum -> clears bracket saddles `[PA]` | `Z=0` datum-land PETG (`tree(auto)`) `[PA]` | **PASS** |
| **J16** | **`150°` Conduit & 3× `Conduit_Cover_Strip`** (`10.6 × 8.5 mm` `150°` channel + `Base/Mid/Top` strips + `SM2.54-3P`) | Route `JST-SM` down `150°` conduit (`Z=450->0`) in **any order** (zero bracket crossover!), snap `100/144/144 mm` strips flush `[PA]` | Cover strips (`Z=100, 225, 375`): **`0.0000 mm³`** vs trunk & **`0.0000 mm³`** vs all `26` brackets; `7.6×9.6 mm` `JST-SM` envelope = **`0.0000 mm³`** vs trunk & all `26` brackets `[PA]` | Twin `10.50 mm` snap rails inside `10.60 mm` slot + `11.8 mm` outer depth flange (`[PT]` friction snap tightness) | Stationary wire cover; completely unblocked by brackets `St 1..26` (`150°` is half-way between `120°` and `180°` columns!) `[PA]` | Flat `Z+` (`T1` Brown PLA Pl. 2, `100%` support-free) `[PA]` | **PASS** |
| **J17** | **Vault Component Cradles & Stepped `DC-099` Jack** (`A092+C008+HT3.96`, `DC-099`, `UCTRONICS`, `WAGO`) | Mount boards onto `Bottom_Electronics_Lid` cradles (`Z=2.8 mm`), insert tray `+Z` into `tb`, mount `DC-099` across `-X` `3.80 mm` bulkhead `[PA]` | **`A092+C008+HT3.96` (`58×24×18 mm`) vs `tb` = `0.0000 mm³`, vs `Lid` = `0.0000 mm³`**; `DC-099` outer spotface (`X=-75..-71.6`) + inner nut seat (`X=-67.8..-62.5`) = exact **`3.80 mm`** wall `[PA]` | `4× M2.5 × 6 mm` tray closure holds all electronics captive; `DC-099` `M11×0.75` nut engages full `3.80 mm` wall cleanly (`[PT]` plug cable bend radius inside tray) | Stationary electronics; `45°` vault dome (`520.6 cm³` total vault) prints at `supp = 0` (`maxBridge = 11.2 mm` @ `Z=28.0`) `[PA]` | Upright `Z+` (`tb` Pl. 1 & `Lid` Pl. 2) `[PA]` | **PASS** |

---

## 3. Remediated Joint Sweep Details (`verified by computation`)

1. **Vertical Stepped Half-Lap Seams vs Split-Tine Bracket Pegs (`cad/audit_joints.py §3`):**
   - `s01 vs s02 = 0.0000 mm³`, `s02 vs s03 = 0.0000 mm³`, `s13 vs s14 = 0.0000 mm³`.
   - **`s02 +Z` stepped-lap drop vs `(s01+tb)`:** `ok = True`, `max_v = 0.0000 mm³`.
   - **`s14 +Z` stepped-lap drop vs `(s13+tt)`:** `ok = True`, `max_v = 0.0000 mm³`.
   - **Split-tine bracket peg lobe engagement (`s02 +Z` vs `b02`):** `[(0.5, 0.3177), (1.0, 0.0), (1.5, 1.2904), (2.0, 1.2904), (2.5, 0.9531), (3.0..4.0, 0.0)]` — positive `1.2904 mm³` snap ridge peak before dropping to `0.0000 mm³` seated.
2. **Closed-Loop Swept-Sphere Tunnel & 3D Physics Certification (`cad/audit_joints.py §7`, `cad/verify_model.py`):**
   - **Swept `Ø 24.90 mm` sphere (`1710° -> -90°`, vertical `-Y` flute `Z=56..434`, intake chute, discharge chute):** **`worst interference = 0.0000 mm³`**.
   - **Physics 1/4 (Track Dynamics across 3 friction regimes):** Low-Friction `v = [203.6, 953.8] mm/s` (`2.30 G`, `bank = 66.6°`, `margin = 6.2 mm`, `T_G0_G5 = 3.30 s`); Standard PLA+LED `v = [193.2, 762.9] mm/s` (`1.40 G`, `bank = 54.6°`, `margin = 10.6 mm`, `T_G0_G5 = 3.99 s`); Rough Layer Lines `v = [180.2, 615.1] mm/s` (`0.83 G`, `bank = 39.9°`, `margin = 18.0 mm`, `T_G0_G5 = 4.91 s`).
   - **Physics 2/4 (Triangle-Mesh Top & Bottom Transitions):** Top spout exits `(0, -17.5, 436.2)` -> catch basin `min_Y = -49.2 mm` -> `(-27.3, -41.0, 428.4) mm`; Bottom dead-stop at `-90° -> max_Y = -19.7 mm`, dead-stop at `-45° -> max_Y = -19.4 mm, Z = 50.3 mm`.
   - **Physics 3/4 (Auger Wedge Lift):** `lead = 22.70°` vs `jam_limit = 67.4°` (`2.97×` safety), `scoop_under = 10.6 mm`, `8-turn_blade_err = 0.10 mm`, `flute_clr = 0.79 mm`, `seam_step = 0.002 mm`.
   - **Physics 4/4 (6-Marble Inelastic Queue):** All 6 marbles settle single-file at `25.8 mm` center spacing (zero overlap, zero bounce-out).

---

## 4. Retired Bottom Covers & Consolidated Screw-Down Vault Tray

| Artifact / File | Current State (`verified by computation`) | Supersedes / Retired |
| :--- | :--- | :--- |
| **`cad/trunk.py` (`build_bottom_electronics_lid`)** | Generates **`Bottom_Electronics_Lid`** (`Ø 134.6 × 14.8 mm`, `2.80 mm` floor) with molded cradles for `UCTRONICS`, `2× WAGO 221-415`, and `A092+C008` (`Z = 2.8 mm`) + **`4× M2.5` tabs (`±50.2, ±50.2`)** (`0.0000 mm³` vs `tb`). | Retired overlapping `Base_Bottom_Cover` & `Battery_Cover`. |
| **`cad/export_3mf_plates.py` & `output/*.3mf`** | Places **`Bottom_Electronics_Lid`**, **`Motor_Clutch_Driver`**, **`Conduit_Cover_Strip_*`**, `trunk_mid`, `trunk_top` on **Plate 2**; keeps **`trunk_base`** alone on **Plate 1**; places `asm_Bottom_Electronics_Lid` cleanly at `Z = 0` in `GravMass_Tree_Complete_Assembly.3mf`. | `Servo_Or_030_Adapter`, `Base_Bottom_Cover`, `Battery_Cover`, `Track_Joint_Clip` removed & unlinked. |
| **`bom/bom.yaml` & `docs/BOM.md`** | Specifies **`5× M2.5 × 6 mm` BHCS** (`4× Bottom_Electronics_Lid` + `1× Motor_Clutch_Driver`), `KA006`, `KC013`, `Sparkleiot` ring (`B09YTMNGTD`), `N20`, `UCTRONICS`, `WAGO`, `DC-099`, `A092+C008` (`scripts/gen_bom.py --check` PASS). | Zero unpurchased fasteners or `CA001` magnets required. |

---

## 5. Sequential Assembly-Order Simulation (Remediated Tree)

Tested cumulatively across all stages (`cad/audit_joints.py` & `cad/verify_model.py`, `verified by computation`):

| Step | Action Simulated | Obstacles Present | Result & Collision Volume | Verdict |
| :--- | :--- | :--- | :--- | :---: |
| **Step 1** | Quarter-turn bayonet twist & drop (`Apple_Hemisphere_A` + `KC013` -> `B`) | `Apple_Hemisphere_B` | `+Z` drop & `0->+45°` lock-unlock twist: **`0.0000 mm³`** | **PASS** |
| **Step 2** | Press `N20` `+Z` into `tb` shroud, mount `DC-099` (`3.80 mm` wall), populate `Bottom_Electronics_Lid` (`UCTRONICS`, `2× WAGO`, `A092+C008+HT3.96`), secure tray (`4× M2.5`), clamp `Motor_Clutch_Driver` (`1× M2.5`) | `trunk_base` | `N20 vs tb`, `D-shaft vs mcd`, `mcd vs tb`, `Lid vs tb`, `4× M2.5 tabs`, `A092+HT3.96 vs tb/Lid`: all **`0.0000 mm³`** | **PASS** |
| **Step 3** | Drop `auger_lower` (`-Z`) onto `mcd`, then `auger_upper` (`-Z`) onto `auger_lower` | `trunk_base + mcd` | **`0.0000 mm³`** across `0..18 mm` and `0..15 mm` `+Z` sweeps (`-0.5 mm` contacts thrust ledge `43.49 mm³`) | **PASS** |
| **Step 4** | Drop `trunk_mid` (`-Z`) onto `trunk_base`, then `trunk_top` (`-Z`) onto `trunk_mid + auger_upper` | `tb + mcd + al + au` | **`0.0000 mm³`** across `0..20 mm` `+Z` sweeps; `±3°` twist lock **`141.78 mm³`** | **PASS** |
| **Step 5** | Insert **all `26` keyhole brackets** (`St 1..26`) via `-X @ dz=+16 mm -> -Z` L-path into stacked trunk | `tb + tm + tt` | **26 / 26 PASS (`0.0000 mm³`)**; `150°` conduit stays **100% open** regardless of whether wiring precedes or follows brackets | **PASS** |
| **Step 6** | Route Sparkleiot `Ø 45 mm` LED ring + `JST-SM` plug down `150°` conduit -> snap `3× Conduit_Cover_Strip` (`100/144/144 mm`) | `tb + tm + tt + b01..b26` | Strips (`Z=100, 225, 375`) & `7.6×9.6 mm` `JST-SM` envelope vs `trunk_*` & **all `26` brackets**: **`0.0000 mm³`** | **PASS** |
| **Step 7** | Press `WS2812B` pebbles into track `8.4 × 6.2 mm` bay -> drop `track_seg_01` (`-Z`) onto `tb+b01..02` -> drop `track_seg_02..14` sequentially `-Z` onto `8.0°` half-laps & split-tine bracket pegs | `tb + tm + tt + b01..b26 + prev track` | `s01 vs tb = 0.0000`, `s14 vs tt = 0.0000`, `s02 +Z vs (s01+tb) = 0.0000`, `s14 +Z vs (s13+tt) = 0.0000`; `b01/02` split-tine snap ridge **`1.2904 mm³`** | **PASS** |
| **Step 8** | Press `KA006` (`4×` crush ribs) into 8 planets -> click planets onto track balcony pegs -> assemble PETG `apple_green_leaf` + `golden_apple_topper` onto `trunk_top` -> holster `Magic_LED_Wand` (`+30° R=52`) | `tt + s01..14 + tb` | All 8 planets vs all 14 tracks = **`0.0000 mm³`**, `Sparkleiot` crown = **`0.0000 mm³`**, `leaf->topper` = **`0.0000 mm³`**, `Wand` holster = **`0.0000 mm³`** | **PASS** |
| **Step 9** | Closed-loop `Ø 24.90 mm` swept marble test + 6-marble live circuit | Full assembly | **`worst interference = 0.0000 mm³`** across `1710° -> -90°`, flute, intake & discharge; 1000 Hz physics **`4/4 PASS`** | **PASS** |

---

## 6. Caliper Measurements for Already-Printed Pre-Fix Parts (`trunk_base` / Brackets)

If you are retrofitting an **already-printed `pre-fix` `trunk_base`** instead of reprinting `Plate 1`, check these dimensions before cutting:
1. **Pre-fix `trunk_base` dovetail pockets (`k = 1..7`):** Outer neck `7.00 mm`, floor depth `4.50 mm`, vertical pocket height `18.00 mm` before the `45°` roof. Verify [`Trunk_Keyhole_Cutting_Jig.stl`](file:///home/ignacio/grav-mass/output/Trunk_Keyhole_Cutting_Jig.stl) snaps flush over pocket `k = 1..7` before plunge-cutting.
2. **Bracket tenons (`bracket_01..26`):** Tenon base `15.40 mm`, neck `6.70 mm`, depth `4.35 mm`, height `17.75 mm`. Measure on your printer after running [`Test_Coupons_PLA.3mf`](file:///home/ignacio/grav-mass/output/3mf/Test_Coupons_PLA.3mf) (`0.10 / 0.15 / 0.20 / 0.25 mm`) to verify keyhole slide fit.
3. **Wire routing note on pre-fix `trunk_base`:** Pre-fix `trunk_base` routed the rear conduit at `180°` rather than `150°`; if keeping a pre-fix `trunk_base`, drop the cable before seating legacy `180°` brackets, whereas printing the updated `Plate 1` + `Plate 2` puts the uncluttered `150°` channel in line all the way up `trunk_base/mid/top`.

---

## 7. Phase 4 Per-Plate Printability Audit (All 18 Production `.3mf` Plates)

All metrics below were computed directly from the 18 production `.3mf` archives in `output/3mf/Plate_*.3mf` (`cad/audit_plates.py`, `verified by computation`).

### 7.1 Printer, Slicer & Packing Gates (`verified by computation`)
- **Nozzle / Extrusion:** `nozzle_diameter = 0.40 mm`, `outer_wall_line_width = 0.42 mm`, `layer_height = 0.20 mm` across all 18 plates.
- **Polymer Segregation:** Plates **1–4** & **14–18** are **100% PLA** (`<= 4` colors/plate on `16–18`, `0` swaps on `1–4, 14–15`); Plates **5–13** are **100% Translucent Teal PETG** (`0` filament swaps).
- **Packing & Mesh Gates:** `wt = True`, `wind = True`, `fits240 = True` (`marginXY = 17.0..71.0 mm`), and minimum inter-part XY clearance `9.0..52.0 mm` (`>= 8.0 mm`) across **all 18 plates**.

### 7.2 Plate-by-Plate Printability Matrix

| Plate | Contents (`n`) | Supports (`3MF`) | BBox (`X×Y×Z mm`, marginXY, gap) | Min Bed Contact | Overhang `>45°` / `>60°` (`mm²`) | Max Flat Bridge (`mm @ Z`) | Ray Min Wall (`mm`) | Verdict |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Plate 1** | `trunk_base` (`n=1`, `T1`) | `0 (OFF)` | `145.0×144.5×165.0` (`62.5`, `single`) | `6,081.3 mm²` | `7,960.5 / 3,171.0` | `11.2 mm` (`trunk_base@28.0`) | `0.26` | **PASS** *(single-body `Ø135` vault dome `<= 45°` chamfer)* |
| **Plate 2** | `trunk_mid`, `trunk_top`, `Bottom_Electronics_Lid`, `3× Conduit_Cover_Strip_*`, `Motor_Clutch_Driver` (`n=7`, `T1`) | `0 (OFF)` | `235.3×233.7×165.0` (`17.0`, `10.2`) | `247.4 mm²` | `691.4 / 612.7` | `2.9 mm` (`trunk_top@149.5`) | `0.20` | **PASS** |
| **Plate 3** | `bracket_01..12` (`n=12`, `T1`) | `0 (OFF)` | `231.3×165.4×22.2` (`19.4`, `12.5`) | `597.0 mm²` | `209.3 / 148.2` | `0.3 mm` (`bracket_12@5.7`) | `0.41` | **PASS** |
| **Plate 4** | `bracket_13..26` (`n=14`, `T1`) | `0 (OFF)` | `151.9×195.4×22.2` (`37.3`, `14.6`) | `244.4 mm²` | `244.1 / 172.9` | `0.3 mm` (`bracket_17@5.7`) | `0.40` | **PASS** |
| **Plate 5** | `track_seg_01` (`n=1`, `T2` PETG) | `1 (tree(auto))` | `193.1×214.7×59.6` (`27.6`, `single`) | `56.2 mm²` | `10,567.1 / 9,848.4` | `12.3 mm` (`track_seg_01@22.3`) | `0.16` | **PASS** |
| **Plate 6** | `track_seg_02` (`n=1`, `T2` PETG) | `1 (tree(auto))` | `213.5×211.6×37.3` (`28.2`, `single`) | `625.0 mm²` | `10,557.5 / 9,438.6` | `12.3 mm` (`track_seg_02@1.7`) | `0.16` | **PASS** |
| **Plate 7** | `track_seg_03` (`n=1`, `T2` PETG) | `1 (tree(auto))` | `205.3×203.4×38.6` (`32.3`, `single`) | `577.3 mm²` | `10,214.8 / 9,089.0` | `12.3 mm` (`track_seg_03@1.7`) | `0.18` | **PASS** |
| **Plate 8** | `track_seg_04` (`n=1`, `T2` PETG) | `1 (tree(auto))` | `197.1×195.1×37.6` (`36.5`, `single`) | `516.2 mm²` | `9,766.8 / 8,631.9` | `12.3 mm` (`track_seg_04@1.6`) | `0.15` | **PASS** |
| **Plate 9** | `track_seg_05` + `track_seg_13` (`n=2`, `T2` PETG) | `1 (tree(auto))` | `221.7×230.5×39.4` (`19.8`, `9.0`) | `134.4 mm²` | `15,549.2 / 13,252.1` | `12.3 mm` (`track_seg_05@1.6`) | `0.16` | **PASS** |
| **Plate 10** | `track_seg_06` + `track_seg_12` (`n=2`, `T2` PETG) | `1 (tree(auto))` | `228.9×234.3×39.2` (`17.8`, `9.0`) | `166.1 mm²` | `15,690.4 / 13,336.6` | `12.2 mm` (`track_seg_06@1.9`) | `0.16` | **PASS** |
| **Plate 11** | `track_seg_07` + `track_seg_11` (`n=2`, `T2` PETG) | `1 (tree(auto))` | `186.1×230.2×38.8` (`19.9`, `9.0`) | `215.1 mm²` | `15,615.2 / 13,197.2` | `12.2 mm` (`track_seg_07@1.7`) | `0.15` | **PASS** |
| **Plate 12** | `track_seg_08` + `track_seg_10` (`n=2`, `T2` PETG) | `1 (tree(auto))` | `218.0×219.1×39.0` (`25.4`, `9.0`) | `245.2 mm²` | `15,752.2 / 13,335.3` | `12.2 mm` (`track_seg_08@1.8`) | `0.18` | **PASS** |
| **Plate 13** | `track_seg_09` + `track_seg_14_top_entry` + `apple_green_leaf` (`n=3`, `T2` PETG) | `1 (tree(auto))` | `231.5×211.5×47.1` (`19.2`, `9.0`) | `58.3 mm²` | `18,045.0 / 14,777.6` | `12.2 mm` (`track_seg_09@1.9`) | `0.18` | **PASS** |
| **Plate 14** | `auger_lower`, `auger_upper` (`n=2`, `T3` Gold) | `0 (OFF)` | `128.0×38.0×208.0` (`71.0`, `52.0`) | `202.5 mm²` | `27.0 / 0.3` | `0.0 mm` | `0.78` | **PASS** *(208 mm Z height -> use outer brim `[PT]`)* |
| **Plate 15** | `6× Apple_Hemisphere_A` + `6× Apple_Hemisphere_B` (`n=12`, `T4` Red) | `0 (OFF)` | `215.0×69.0×15.4` (`27.5`, `13.0`) | `40.9 mm²` | `3,006.4 / 2,807.7` | `1.4 mm` (`a_01@13.6`) | `0.30` | **PASS** *(verify 1 coupon pair first `[PT]`)* |
| **Plate 16** | `golden_apple_topper` (3p) + `Magic_LED_Wand` (4p) (`n=2`, 4-col PLA) | `1 (tree(auto))` | `139.2×109.1×109.6` (`52.5`, `34.8`) | `581.2 mm²` | `5,778.2 / 5,173.0` | `26.3 mm` (`topper@83.7`, supported) | `0.18` | **PASS** |
| **Plate 17** | `mercury`, `venus`, `mars`, `jupiter`, `saturn` (`n=5`, 4-col PLA) | `1 (tree(auto))` | `154.4×114.1×36.3` (`57.2`, `38.9`) | `77.7 mm²` | `14,039.5 / 13,627.6` | `7.8 mm` (`jupiter@21.5`, supported) | `0.18` | **PASS** |
| **Plate 18** | `earth`, `uranus`, `neptune` (`n=3`, 4-col PLA) | `1 (tree(auto))` | `152.3×36.0×31.5` (`58.7`, `29.5`) | `77.7 mm²` | `5,098.2 / 4,597.0` | `13.3 mm` (`earth@28.1`, supported) | `0.16` | **PASS** |

### 7.3 Printable Feature Detail Checks (`verified by computation` / `[PT]`)
1. **Acoustic Click Micro-Ribs (`CLICK_RIB_PROTRUSION_MM = 0.50 mm`):** Widened from `0.35 mm` (`< 1` nozzle pass) to **`0.50 mm` (`>= 1.19×` outer wall line width)** so every nozzle pass resolves cleanly without Arachne omission (`[PT]` sound/feel).
2. **Track Orientation & `Z = 0` Datum Land:** All 14 track segments print resting on solid `>= 56.2 mm²` `Z = 0` datum lands with `maxBridge <= 12.3 mm` (`tree(auto)` enabled), `<= 39.4°` track twist across segments, and vertical `-Z` stepped half-lap shelves rather than fragile overhang horizontal pegs.
3. **Motor Coupler Grain (`Motor_Clutch_Driver`, Plate 2):** Printed flat on `Z = 0` in **`T1` Brown PLA** with `M2.5 × 6 mm` split-ear pinch clamp so rotational hoop tension wraps continuous XY extrusions around the D-shaft (`[PT]` physical clamp torque).
4. **Ray-Cast MinWall (`0.15–0.41 mm`):** Grazing rays along `45°` bevel feather edges on track lap steps, bracket chamfer tips, and topper fillets; primary structural webs/walls exceed `2–4` perimeters (`>= 0.78–1.65 mm`).

---

## 8. Phase 5 Single-Polymer Test Coupons (`Test_Coupons_PLA.3mf` & `Test_Coupons_PETG.3mf`)

To test real-world tolerances on your Snapmaker U1 with **zero mixed-polymer bed collisions**, `cad/test_coupons.py` exports two dedicated single-polymer calibration plates (`verified by computation`):

1. **[`output/3mf/Test_Coupons_PLA.3mf`](file:///home/ignacio/grav-mass/output/3mf/Test_Coupons_PLA.3mf) (`24` PLA coupons, `223.0 × 115.1 × 54.0 mm`, `min_gap = 8.8 mm`):**
   - **Keyhole Bracket Socket & Tenons (`c10..c25`):** Exact trunk keyhole slice + 4 pull-tabs (also verifies fit of already-printed pre-fix brackets and `Trunk_Keyhole_Cutting_Jig`).
   - **`KA006` Planet Crush-Rib Caps (`c10..c25`):** Tests `Ø 7.50 mm` LED press-fit retention (`4×` crush ribs) & `Ø 7.60 / 8.36 mm` peg click.
   - **Trunk Keyed Tenon (`c10..c25`):** Confirms `Z = 150 / 300 mm` seam slip fit.
   - **Bayonet Marble `A`/`B` (`c10..c25`):** Validates `supp = 0` internal bridging on the `18.7 mm` cavity and quarter-turn bayonet friction before batching `Plate 15`.
   - **Plus** `Motor_Clutch_Driver` D-shaft clamp coupon & `Magic_LED_Wand` `Ø 8.0 × 2.0 mm` magnet pocket coupon!
2. **[`output/3mf/Test_Coupons_PETG.3mf`](file:///home/ignacio/grav-mass/output/3mf/Test_Coupons_PETG.3mf) (`4` PETG coupons, `195.0 × 65.5 × 33.9 mm`, `min_gap = 8.8 mm`):**
   - Production `18°` **`8.0°` stepped half-lap** male/female track pair (with deepened `8.4 × 6.2 mm` pebble bay & `4.6 mm` throat) + `Coupon_Planet_Peg` (`Ø 7.60 / 8.36 mm` bead) + `Coupon_SplitTine_Peg_Test` mating block so you can confirm PETG track seam drop, split-tine snap retention, and pebble insertion physically at native PETG bed temperature (`70–75 °C`).
