# Full Printability & Joint Remediation (`Grav-Mass Tree`)

*   **Author:** Ignacio Martinez (`ignacio82`)
*   **Status:** Proposed
*   **Date:** 2026-11-15

--------------------------------------------------------------------------------

## Overview

This design targets every mechanical joint `FAIL`, hardware envelope `RISK`, and 3D-printing failure documented in [ASSEMBLY_AUDIT.md](../../ASSEMBLY_AUDIT.md) so all 18 build plates of the Grav-Mass Tree slice without support errors on a Snapmaker U1 (`0.4 mm` hardened-steel nozzle, `270 × 270 × 270 mm` bed, `240 × 240 mm` safe print zone) and assemble without physical interference, wiring traps, or manual trimming. All geometry changes are constrained to hardware already in [docs/BOM.md](../BOM.md), prioritize first-pass printability and single-axis mechanical engagement over preserving pre-printed brown parts, and gate publication on automated B-Rep checks plus empirical fit selection via calibration coupons (`Test_Coupons_PLA.3mf` and `Test_Coupons_PETG.3mf`).

### System & Coordinate Primer

The Grav-Mass Tree (`~527 mm` tall, `~336 mm` base footprint) is a motorized closed-loop kinetic marble-run sculpture. A central 3-section trunk (`trunk_base`, `trunk_mid`, `trunk_top`, split at `Z = 150 mm` and `Z = 300 mm`) houses an internal 2-stage Archimedes auger (`auger_lower`, `auger_upper`) driven by an `N20` 12V gear motor (`B0BFRPMSW6`) through `Motor_Clutch_Driver`. Two-piece twist-lock bayonet marbles (`Apple_Hemisphere_A` + `Apple_Hemisphere_B`, `Ø 25.0 mm`, each holding a wireless `KC013` Y-shape 3-LED unit) ride up a vertical `-Y` flute inside the trunk, exit below the `trunk_top` topper collar (`crown_collar`, `Z = 450 mm`), roll down `4.5` turns of a segmented PETG conical track (`track_seg_01..14`) supported by radial cantilever brackets (`bracket_01..26` at `60°` azimuth steps), pass six acoustic timing gates (`G0` at `1605°`, `G1` at `1350°`, `G2` at `990°`, `G3` at `630°`, `G4` at `270°`, `G5` at `15°`), and queue at the bottom scoop (`-90°`). `8×` lit Solar System planets (`Mercury`..`Neptune`) perch on outer track balconies (`Magic_LED_Wand` holds a trigger magnet that taps planets or marbles to cycle their wireless magnetic LEDs).

*   **Track Local Coordinates `(u, v, w)`:** `u` points radially outward from helix centerline (`-u` toward trunk, `+u` outward); `v` points vertically (`v = 0` at the trough flat shoulders, `-v` downward to the track underside); `w` points along the local tangent (`-w` uphill, `+w` downhill).
*   **Global Trunk Frame:** `-Y` (`270°`) is the front ball-lift flute; `+Y` (`90°`) faces north; `-X` (`180°`) is the global rear barrel-jack face (`+X` is `0°`). Keyhole bracket orientations are stated in each bracket's own radial frame (inward plug toward trunk center axis, then drop `-Z`).
*   **Base Snapmaker U1 Toolheads (`T1–T4`) & 18-Plate Map:** `T1` = Dark Wood Brown PLA (`#4A2F1D`); `T2` = Translucent Emerald Teal PETG (`#00A86B`); `T3` = Silk+ Gold PLA (`#D4AF37`); `T4` = Basic Crimson Red PLA (`#C41E3A`). Single-color plates: `Plates 1–2` (`T1` trunk, covers/tray, `Motor_Clutch_Driver`, adapter), `Plates 3–4` (`T1` brackets `01..12` and `13..26`), `Plates 5–13` (`T2` `track_seg_01..14` + extracted apple leaf), `Plate 14` (`T3` `auger_lower/upper`), `Plate 15` (`T4` bayonet marbles). Multi-color `PLA`-only plates (swapping toolhead colors per plate): `Plate 16` (`golden_apple_topper` + `Magic_LED_Wand`), `Plate 17` (`Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn` — `T2` = Ivory White `#F5EFE6`), `Plate 18` (`Earth`, `Uranus`, `Neptune` — `T1` Marine Blue `#1E5AA8`, `T2` Silk Gold `#D4AF37`, `T3` Ivory White `#F5EFE6`).

| Reference Code | Description (`docs/BOM.md` / `ASSEMBLY_AUDIT.md`) |
| --- | --- |
| `C008` / `A092` / `A096` | M5Stack ATOM Lite ESP32 (`C008`) mated atop Atomic H-Bridge Driver (`A092`) with `HY2.0-4P` Grove cables (`A096`) and `HT3.96-4P` screw terminals |
| `DC-099` / `UCTRONICS` | `B07C7VSRBG` `M11 × 0.75` panel-mount `5.5 × 2.1 mm` 12V barrel jack / `B07XXWQ49N` `12V -> 5V` `5A` buck + `1000 µF` capacitor (`B07WPWFSNQ`) |
| `B0CCS11V7H` / `B09YTMNGTD` / `B0CT827QQC` | Track underside `6.2 × 3.2 mm` addressable pebble LED wire / `Ø 45 × 3 mm` Sparkleiot topper LED ring / `JST-SM` `3-pin` topper harness |
| `KA006` / `KC013` / `B0BYF4X65F` | `Ø 7.5 × 6.0 mm` planet magnetic LED / `Ø 18.0 × 6.5 mm` marble Y-shape LED / `50-pack` `M2.5 × 6 mm` button-head screws |
| `Lamp Kit 001`, `CA001`, `PG002`, `IA005`, `XA007` | Legacy deleted hardware pockets/constants (old `Ø 60 mm` puck, `Ø 4 × 2 mm` magnets, `9 g` servo, PDB, toggle switch, and `Base_Bottom_Cover`) |
| `J4`, `J6`, `J7`, `J8`, `J9`, `J10`, `J12`, `J13`, `J14`, `J15`, `J16`, `J17` | Audit IDs: `N20` D-shaft (`J4`), bracket pegs (`J6`), scarf seams (`J7`), joint clip (`J8`), top marble discharge (`J9`), `KA006`/balcony (`J10`), wand magnet (`J12`), bottom lid (`J13`), topper socket (`J14`), pebble channel (`J15`), rear conduit (`J16`), `trunk_base` electronics bays (`J17`) |

--------------------------------------------------------------------------------

## The Problem

The B-Rep audit in [ASSEMBLY_AUDIT.md](../../ASSEMBLY_AUDIT.md) established that multiple unprinted plates and electronic interfaces fail even after fixing the closed bracket pocket:

1.  **Track Assembly Deadlocks & Snap Failure (`J6`, `J7`, `J8`):** Track scarf pegs point uphill tangentially (`-w`), whereas bracket alignment pegs point vertically (`+Z`). Because rigid track segments `02..14` cannot travel along both axes simultaneously (`370.63 mm³` / `310.97 mm³` interference), builders cannot seat a segment onto both its preceding segment and supporting brackets. Existing snap beads never interfere (`r = 2.04 mm` inside `2.15 mm`; `r = 2.12 mm` inside `2.20 mm`), and `Track_Joint_Clip` collides with `bracket_02` (`1,067.40 mm³`).
2.  **Marble Interference, Top Cantilever & Conduit Blockage (`J9`, `J16`, `Plates 5, 13`):** Sweeping a `Ø 24.90 mm` marble out of `trunk_top` hits the `-Y/-X` trunk bark wall by `42.93 mm³` at `1690°` — missed earlier because `verify_model.py` excluded `trunk_top` from the swept-ball check. Past `bracket_24` (`1440°`), `track_seg_13..14` cantilever `180°` unsupported, both `track_seg_01` (`Plate 5`) and `track_seg_14_top_entry` (`Plate 13`) sit on `0.0 mm²` knife-edge bed contact, and `180°` brackets cross the `-X` wire conduit (`213.13 mm³`) unless pre-threaded.
3.  **LED Channel Depth, Crush Ribs & Mixed Polymers (`J10`, `J12`, `J15`, `Plates 16, 18`):** The underside track channel only provides `1.20 mm` full-width height for `6.2 × 3.2 mm` pills (`16.41 mm³` interference), and `0.35 mm` acoustic click micro-ribs fall below `0.42 mm` extrusion width. All 8 planet bores omit `KA006` crush ribs (`0.0000 mm³` interference), while both `Plate 16` (`apple_green_leaf` on `apple_brown_stem`) and `Plate 18` co-print `T2 PETG` layers inside `PLA` objects (`docs/BOM.md` includes no Green PLA).
4.  **Legacy Collisions & Trunk Electronics Squeeze (`J4`, `J13`, `J14`, `J17`):** Inside `trunk_base`, `Base_Bottom_Cover` overlaps `Battery_Cover` (`438.83 mm³`) while referencing deleted `CA001` magnets; `DC-099` faces a `15.2 mm` bulkhead exceeding typical `8–11 mm` `M11 × 0.75` thread reach; `A092`'s `HT3.96-4P` plug clashes (`1,817.85 mm³`); `Lamp Kit 001` (`2,980.18 mm³`) remains in legacy CAD/test checks; and `Motor_Clutch_Driver` relies on plastic hoop friction (`J4`).
5.  **Unsupported Bridges & Overhangs (`Plates 1, 14, 15`):** With supports off, `Plate 1` forces a `135 mm` flat vault bridge (`25–31 mm` bay spans), `Plate 14` (`auger`) prints a `68.9°` unsupported helical blade overhang `208 mm` tall on a `68.5 mm²` footprint, and `Plate 15` (`Apple_Hemisphere_A`) prints a horizontal equatorial exterior shoulder (`r = 10.52 -> 12.50 mm` at `Z = 2.65 mm`) flagged as a `24.9 mm` ring bridge.

Without fixing these geometry, slicing, and verification gaps together, printing `Plates 5–18` wastes `~1.4 kg` of filament on parts that cannot snap together, fail to retain LEDs, pinch rolling marbles, or delaminate.

--------------------------------------------------------------------------------

## Goals

*   **Single-Axis `-Z` Track Assembly & Splice:** Make every track segment (`01..14`) install in a single `-Z` vertical motion onto bracket-aligned stepped lap seams and compliant bracket split-tine snaps (`0.0000 mm³` swept insertion interference, `0` conical seam pins, `0` mid-span timing-gate collisions).
*   **Unobstructed Marble & `150°` Wiring Paths:** Eliminate the `42.93 mm³` top-discharge marble collision across every `5°` swept-sphere step (`1710° -> -90°`) against the entire trunk/topper/track assembly, support the upper helix past `1440°` (`brackets 25–26` + top cradle), and move the wire conduit off the `180°` bracket column (`0.0000 mm³` plug sweep with all brackets installed).
*   **Positive LED & Shaft Retention:** Deepen the under-track LED channel so `6.2 × 3.2 mm` pills push upward edge-on (`3.2 mm` through `4.6 mm` throat) with `<= 45°` support-free flares and rotate flat recessed above brackets (`0.0000 mm³` interference); add physical crush ribs inside `KA006` bores; and lock `Motor_Clutch_Driver` mechanically onto the `N20` D-shaft in matte PLA (`M2.5 × 6 mm` clamp).
*   **Single-Polymer & Clean-Bed Printability:** Eliminate `0.0 mm²` knife-edge track bed contacts (`Plates 5, 13`), `135 mm` vault bridges (`Plate 1`), `68.9°` full-span auger overhangs (`Plate 14` + brim), `Plate 15` equatorial shoulder steps, and mixed `PLA`/`PETG` objects across both `Plate 16` and `Plate 18`.
*   **Accessible Upright Electronics Tray & `3.8 mm` Bulkhead (`docs/BOM.md` Only):** Consolidate trunk wiring onto one upright `Bottom_Electronics_Lid` tray nested flush in the base rabbet (`4× M2.5 × 6 mm` screws) with datasheet-plus-cable clearance for `DC-099` (`3.8 mm` bulkhead), `A092+C008` (`+16/+22 mm` plug/Grove slack), `UCTRONICS`, and `2× WAGO 221-415`.
*   **Single-Polymer Calibration & Consolidated B-Rep Gating:** Split calibration coupons into thermal-matched `Test_Coupons_PLA.3mf` (`60 °C`) and `Test_Coupons_PETG.3mf` (`75 °C`), and consolidate all joint, physics, and plate gates into [cad/verify_model.py](../../cad/verify_model.py) (+ shared plate audit helper).

--------------------------------------------------------------------------------

## Non-Goals

*   **Preserving Pre-Printed Parts:** Keeping already-printed `trunk_base` (`Plate 1`) or `bracket_01..24` (`Plates 3–4`) parts is out of scope when modifying them improves clearances, printability, or wiring access.
*   **Adding Hardware Outside `docs/BOM.md`:** No heat-set brass inserts, extra magnets (`CA001`), retired light kits (`Lamp Kit 001`), toggle switches (`XA007`), or extra filaments (such as Green PLA) will be added. Small press parts such as the `Ø 8 × 2 mm` `Magic_LED_Wand` magnet continue to allow a drop of user-supplied cyanoacrylate adhesive if coupon dry-fits slip.
*   **Physical Bench Testing During CAD Generation:** Because physical electronics are unavailable for dry-fitting right now, virtual sweeps validate datasheet bounds plus generous cable-bend margins; final slip-vs-force selection awaits printing the two calibration plates.

--------------------------------------------------------------------------------

## Critical User Journeys (CUJs)

### CUJ 1: Single-Polymer Coupon Calibration Before Production Slicing

*   **Given:** The builder opens `Test_Coupons_PLA.3mf` (`60 °C` bed, `T1` Brown / `T3` Silk Gold / `T4` Crimson Red) and `Test_Coupons_PETG.3mf` (`75 °C` bed, `T2` Emerald PETG) configured at true production thermal profiles across stepped `[0.10, 0.15, 0.20, 0.25] mm` / `[7.00..7.30] mm` clearance ladders.
*   **When:** The builder prints both compact coupon plates, presses a `KA006` LED into the 4-ribbed planet cup, dry-fits a split-tine bracket peg and balcony peg into tilted PETG sockets, twists a `6.2 × 3.2 mm` pebble pill edge-on into the channel slice, tests the `45°`-chamfered marble twist lock, and clamps the `Motor_Clutch_Driver` `M2.5` screw onto the `N20` D-shaft.
*   **Then:** Each joint achieves secure retention without cracked bosses, delaminated lines, or falling LEDs, fixing final tolerances before slicing `Plates 1–18`.

### CUJ 2: Deadlock-Free Printing and Single-Pass Tree Assembly

*   **Given:** All 18 `.3mf` plates pass automated B-Rep and printability checks, with `Plates 16–18` `PLA`-only and `Plates 1–4, 14–15` support-free (`enable_support = 0`).
*   **When:** The builder prints all plates, clamps `Motor_Clutch_Driver` onto the `N20` shaft, bolts `DC-099` through the `3.8 mm` `-X` bulkhead, wires `UCTRONICS` (`+ 1000 µF` cap), `2× WAGO 221-415`, `WAGO 221-413` / inline fuses (in the open vault slack zone), and `A092+C008` upright onto the `Bottom_Electronics_Lid` tray, lowers `trunk_base` over the tray (`4× M2.5`), drops `auger_lower/upper` and `trunk_mid/top`, threads the `JST-SM` topper cable down the `150°` conduit (`3×` section strips), drops all 26 keyhole brackets radially-then-`-Z`, drops `track_seg_01..14` straight `-Z` onto brackets and prior seams, pushes `B0CCS11V7H` pills edge-on into the underside channel, and seats planets and the apple leaf/topper.
*   **Then:** Every component slides along unobstructed single-axis paths with zero trapped plugs or jammed marbles, and `Ø 25.0 mm` marbles cycle through `4.5` turns without pinching or stalling.

### CUJ 3: Consolidated Automated Regression Gating

*   **Given:** A developer edits `cad/*.py` or `.3mf` plate packing.
*   **When:** They execute `cad/generate_all.py`, `cad/verify_model.py`, and `scripts/gen_bom.py --check`.
*   **Then:** The suite automatically checks swept `Ø 24.90 mm` marbles against the complete core+topper+track assembly, simultaneous `-Z` `track_seg_02` and `seg_03` drops onto seated brackets, split-tine snap engagement, `KA006` crush-rib engagement, edge-on/seated `6.2 × 3.2 mm` pebble envelopes, `JST-SM` `150°` sweep with all 26 brackets seated, `DC-099`/`A092`/tray clearances, full-radius auger bottom-scoop clearance, `min_bed >= 25 mm²` across all 18 plates, `max_bridge <= 12 mm` on support-free plates (`1–4, 14–15`), and single-polymer `.3mf` components.

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

The remediation unifies all 18 production plates onto one consistent mechanical, electrical, and slicer architecture strictly using hardware in [docs/BOM.md](../BOM.md).

### Audit-to-Remediation Summary Matrix

| Audit ID / Plate | Defect Summary | Architectural Fix | Verification Gate |
| --- | --- | --- | --- |
| `J4`, `Plate 14` | `N20` slip fit; `68.9°` auger overhang + tall tip risk | Matte `T1` Brown PLA hub + radial `M2.5` clamp over D-shaft (`Z <= 6.5 mm`); full-radius `45°` auger taper + `10 mm` brim | Auger bottom-scoop check; hub D-bore interference; `supp=0` audit |
| `J6`, `J7`, `J8`, `Plates 3–13` | `-w` scarf vs `+Z` peg deadlock; clip clash; zero snap grip | Bracket-aligned `-Z` stepped shoulder seams (`60°` intervals); delete `Track_Joint_Clip`; XY-slotted split-tine bracket snaps (`b01..26`) | Simultaneous `-Z` track+bracket sweep; `+0.8 mm` snap retention check |
| `J9`, `Plates 2, 4, 5, 13` | `42.93 mm³` top-discharge pinch; unsupported `>1440°`; `0 mm²` bed | Curved swept-ball `trunk_top` relief + wider feeder start radius; `b25–26` + vertical spout shelf; flat `Z=0` track datum pads | Full-assembly `5°` swept-ball check (`1710° -> -90°`); `min_bed >= 25 mm²` |
| `J10`, `J12`, `Plates 16–18` | No `KA006` crush ribs; mixed `PETG`-in-`PLA` on `Plates 16, 18` | Subtracted rib notches leaving solid `KA006` inward ribs + compliant balcony peg; leaf moved to `Plate 13`; `Plate 18` `3-color PLA`; tuned wand bore + CA fallback | `KA006` interference `> 0.30 mm³`; XML single-polymer check (`16–18`) |
| `J13`, `J17`, `Plate 1` | Lid overlap; `135 mm` vault bridge; `15.2 mm` jack wall; plug clash | Upright `Bottom_Electronics_Lid` tray (`4× M2.5`, `14 × 14 mm` port); open `45°` vault cone; outer `Ø 16 mm` `DC-099` spotface (`3.8 mm`); `A092` open-vault clearance; legacy purge | `trunk_base` + electronics + tray `0.0000 mm³` interference; `max_bridge <= 12 mm` |
| `J14`, `Plate 16` | Legacy `Lamp Kit 001` (`2,980.18 mm³`) breaks topper base | Retain `Ø 60.0 × 4.6 mm` `crown_collar` socket + `Ø 46.5 mm` `Sparkleiot` optical throat; remove legacy puck depth | Topper-on-trunk `crown_collar` shear/fit check |
| `J15`, `Plates 5–13` | `1.20 mm` LED bay clashes with `3.2 mm` pills; `0.35 mm` micro-rib | Deepen track underside for `45°` flare + full-width `8.4 × 3.6 mm` pill bay; raise acoustic micro-rib to `0.50 mm` | Edge-on entry + flat seated pill sweep; wall thickness check |
| `J16`, `Plates 1–2` | `180°` brackets block conduit; strips mismatch sections | Rotate conduit, tenon/socket flats, bark mask, and topper slot to `150°`; 3 section-matched cover strips | `JST-SM` `150°` sweep with all 26 brackets seated |
| `Plate 15` | `24.9 mm @ 2.6 mm` equatorial bridge on `Apple_Hemisphere_A` | Symmetric `45°` exterior chamfer seam (`A` male cone into `B` female cone) + true radial ring bridge calculation | Pair bayonet clearance + `max_bridge <= 12 mm` (`supp = 0`) |

### 1. Deadlock-Free Assembly Graph (Target Dependency Order)

```text
  [1. Electronics Tray & trunk_base Drive (Plates 1, 2)]
       ├─ Bolt DC-099 barrel jack into 3.8 mm outer-spotfaced -X bulkhead
       ├─ Clamp matte T1 Motor_Clutch_Driver radially onto N20 D-shaft (1x M2.5x6) & seat in base
       ├─ Wire UCTRONICS (+1000uF cap), 2x WAGO 221-415, A092+C008 (+16/+22 mm clearance) onto upright tray;
       │    tuck WAGO 221-413 & inline fuses in open 150,000 mm3 slack zone
       └─ Drop trunk_base over tray into Ø135 x 3.0 mm flush rabbet (4x M2.5x6 screws, 14x14 mm C008 port)
               │
               ▼
  [2. Central Core Stack & 150 deg Conduit (Plates 2, 13, 14, 16)]
       ├─ Drop auger_lower -> auger_upper (full-radius 45 deg blade underside taper, brim-printed)
       ├─ Drop trunk_mid -> trunk_top (keyed tenons flattened at 150 deg; zero bracket interference)
       ├─ Thread JST-SM topper cable down 150 deg conduit + snap 3x section cover strips
       └─ Seat Sparkleiot Ø45 mm ring, assemble T2 leaf into T1 stem, drop golden_apple_topper
               │
               ▼
  [3. Keyhole Brackets -> Helical Track -> Pebble LEDs -> Planets & Marbles (Plates 3–18)]
       ├─ Drop all 26 keyhole brackets radially-then--Z (brackets 25 & 26 support top turns)
       ├─ Drop track_seg_01..14 straight -Z onto bracket-aligned stepped shoulder laps & split-tine pegs
       ├─ Push 6.2x3.2 mm B0CCS11V7H pills edge-on through 4.6 mm throat and rotate flat into 8.4x3.6 mm bay
       └─ Press KA006 LEDs into 4-ribbed planet cups -> snap onto compliant balcony pegs; twist marbles
```

### 2. Core Mechanical & Structural Changes by Subsystem

#### A. Bracket-Supported `-Z` Track Seams & Split-Tine Alignment Pegs (`J6`, `J7`, `J8`, `Plates 3–13`)
*   **Bracket-Station Stepped Shoulder Seams:** Once `Track_Joint_Clip` and tangential `-w` scarf pegs are deleted, segments install purely vertically (`-Z`). Keeping segment boundaries on `60°` bracket stations (`seg_01: -90°..+60°`, `seg_02..13: 60°..180° .. 1380°..1500°`, `seg_14: 1500°..1710°`) places every seam directly atop a `11.0 mm`-wide bracket saddle (`~12.8 mm` solid track web at `u = ±10.6 mm` outside the center LED channel).
    *   *Stepped Shoulder Half-Lap:* Upper and lower overlap flanges step radially on the thick outer/inner shoulder zones (`|u| >= 5.5 mm`, avoiding the thin `~2.6 mm` central web above the LED bay, where segments meet in a clean vertical butt seam).
    *   *Eliminated Components:* Removes all `13×` horizontal conical seam pins, all `13×` mid-span PETG screw bosses/counterbores, and `Track_Joint_Clip`.
    *   *Timing-Gate & Balcony Safety:* Pin explicit planet balcony azimuths clear of all `6` timing gates (`G0..G5`) rather than computing balconies from shifted segment midpoints.
*   **Compliant Split-Tine Pegs (`brackets` & `track`):** Replace non-contacting annular peg beads with slotted split-tine cantilevers expanding radially inside recessed internal track sockets (`+Z` peg stems experience bending stress across horizontal print layers at the saddle root, so radial snap interference is capped tightly at `<= 0.10 mm` with `0.5 mm` root fillets).

#### B. Top Discharge Relief, Upper Track Support & Bed Contact (`J9`, `Plates 2, 4, 5, 13`)
*   **`trunk_top` Swept-Ball Relief:** Carve a curved `Ø 27.6 mm` swept-sphere exit relief into the `-Y/-X` outer bark of `trunk_top` and widen the feeder start radius smoothly back into the upper helix, eliminating the `42.93 mm³` marble collision at `1690°` while keeping the marble bilaterally guided.
*   **Upper Helix Support:** Add `bracket_25` (`1500°`) and `bracket_26` (`1560°`, packed onto `Plate 4` reusing existing `trunk.py`/`track.py` slot loops) plus an unpinned flat vertical cradle shelf on `trunk_top` directly beneath the `1710°` spout collar.
*   **Track Bed Datum Lands:** Trim local entry/exit undersides to flat horizontal `Z = 0.00 mm` pads (`>= 40.0 mm²` target footprint) on `track_seg_01` (`Plate 5`) and `track_seg_14_top_entry` (`Plate 13`) to prevent `0.0 mm²` knife-edge delamination.

#### C. Deepened `45°` Edge-On Pebble LED Channel & Printable Micro-Rib (`J15`, `Plates 5–13`)
*   **Geometric Flare Fix (`45°` Support-Free Lips):** Deepen the track underside sufficiently that widening from the `4.6 mm` snap throat to the `8.4 mm` internal pill bay rises at a true `45°` overhang (`1.9 mm` vertical flare per `1.9 mm` radial step) and still leaves `>= 3.4 mm` full-width vertical chamber height plus `>= 2.6 mm` solid web beneath the ball trough (shifting trunk bracket socket `Z` offset down symmetrically to hold helix track elevation unchanged).
*   **Acoustic Micro-Rib:** Increase the inward timing-gate ridge from `0.35 mm` (`< 0.42 mm` extrusion width) to `0.50 mm` so it slices as a continuous single perimeter without encroaching on a `Ø 25.0 mm` marble (`0.0000 mm³` interference).

#### D. `150°` Wire Conduit, Upright Electronics Tray & Vault Cleanup (`J13`, `J16`, `J17`, `Plates 1–2`)
*   **Coupled `150°` Conduit Relocation:** Move the `10.0 × 8.5 mm` vertical connector groove from `180°` to **`150°`** (midway between the `120°` and `180°` bracket columns), adding matching `150°` radial flats on male/female trunk tenons (preventing wall slicing at `Z = 150 / 300 mm`), bark-furrow masking around `150°` for flush strip seating, a `150°` exit notch at the top Sparkleiot collar, and `3×` section-matched cover strips (`trunk_base`, `trunk_mid`, `trunk_top`).
*   **Upright Electronics Tray & Clean Vault Cone:** Invert open-top component snap cradles (`UCTRONICS` shifted clear of the wand holster with `-X` capacitor clearance, unstacked `2× WAGO 221-415`, and `A092+C008` oriented with `+16/+22 mm` `HT3.96-4P` / `A096` plug space facing open center volume) onto an upright `Ø 135 mm`-class `Bottom_Electronics_Lid` tray nested flush in `Z = 0..2.8 mm` (`4×` perimeter root-tab `M2.5 × 6 mm` screws, `14 × 14 mm` `C008` LED/button port). Leave wire-inline `B087BT1PH3` fuses and `2× WAGO 221-413` in the open `~150,000 mm³` vault slack zone instead of molding speculative wire clips.
*   **Vault Bridge & Bulkhead Fixes:** Delete all retired pockets/covers (`Base_Bottom_Cover`, `Battery_Cover`, `xa007_boss`, `pg002`, `batt`, `cable_slot`), leave `trunk_base` as an unobstructed `45°` internal cone with central `N20` shroud seated above the `Z = 3.0 mm` tray datum, and cut an external `Ø 16.0 mm` perpendicular spotface on `-X` reducing the `DC-099` bulkhead to `3.8 mm` (`>= 4.2 mm` nut thread engagement, zero inner bore cut below `Z = 0`).

#### E. Auger Taper, `T1` Clamped Driver, Mated Marble Seam & Polymer Fixes (`J4`, `J10`, `J12`, `J14`, `Plates 2, 13–18`)
*   **Full-Span `45°` Auger Taper (`Plate 14`) & `T1` Driver (`Plate 2`):** Slope the entire `14.5 mm` radial underside of the auger blade (`r = 4.5..19.0 mm`) at `45°` while keeping the top carry face horizontal at `46.0 mm` pitch (verifying bottom scoop clearance) and add a `10.0 mm` outer bed brim (`Plate 14`). Reassign `Motor_Clutch_Driver` to matte `T1` Dark Brown `PLA` on `Plate 2` (eliminating `Silk Gold` hoop splitting) with an enlarged lower hub collar overlapping the `N20` D-shaft (`Z <= 6.5 mm`) clamped by `1× M2.5 × 6 mm` set screw prior to inserting the motor into `trunk_base`.
*   **Symmetrically Chamfered Marble Seam (`Plate 15`):** Replace the horizontal equatorial exterior step on `Apple_Hemisphere_A` (`Z = 2.65 mm`) with a `45°` conical exterior chamfer nesting into a matching `45°` recessed female rim seat on `Apple_Hemisphere_B`, retaining the existing `45°` internal domes inside the `Ø 25.00 mm` shell.
*   **Topper Socket, Planet Ribs & Single-Polymer `Plates 16, 18`:** Retain a `Ø 60.0 × 4.6 mm` `crown_collar` socket and `Ø 46.5 mm` `Sparkleiot` optical throat in `golden_apple_topper` (`J14`); carve rib voids out of the planet socket cutter so `4×` solid inward crush ribs grip `KA006` above a compliant split-tine balcony peg; keep `Magic_LED_Wand` at a tuned magnet bore + CA glue fallback; move `apple_green_leaf` onto `Plate 13` (`T2 PETG` keyed snap-in leaf); and lock `Plate 18` to `3-color PLA-only` (`T1` Marine Blue `#1E5AA8`, `T2` Silk Gold `#D4AF37`, `T3` Ivory White `#F5EFE6`).

--------------------------------------------------------------------------------

## Alternatives Considered

### Alternative A: Preserve Pre-Printed `trunk_base` and `bracket_01..24`, Adapting Only Unprinted Plates (`track_seg_01..14` and `Plates 17–18`)
*   **Pros:** Saves `~760 cm³` of Dark Wood Brown PLA and print time on `trunk_base` and the 24 brackets (`Trunk_Keyhole_Cutting_Jig.stl` opens existing dovetail roofs).
*   **Cons:** Pre-printed brackets fix track pegs as rigid rings without split-tine compliance and keep `180°` brackets straddling the rear wire conduit (`J16`). Keeping `trunk_base` untouched leaves the `15.2 mm` `DC-099` bulkhead (`J17`), `A092` plug clash (`1,817.85 mm³`), and `135 mm` vault bridge unresolved.
*   **Reason for Rejection:** Reprinting updated brown parts avoids tight tolerance workarounds, removes wiring traps, and lowers the risk of scrapping later PETG and multi-color plates.

### Alternative B: Tool-Free Printed Snap-Fits Across Every Track Seam (Zero Screws)
*   **Pros:** Removes all `M2.5 × 6 mm` screws from track assembly.
*   **Cons:** Relies purely on friction/snap fits across `Motor_Clutch_Driver` torque transfer and bottom tray retention, whereas `5×` existing screws from the `B0BYF4X65F` 50-pack positively clamp the tray and `N20` D-flat with `45` spares left.
*   **Reason for Rejection:** Retaining `5× M2.5 × 6 mm` screws solely where mechanical clamping or serviceable enclosure closure matters (`4×` tray + `1×` motor D-flat) while letting bracket-supported `-Z` shoulder seams lock vertically onto split-tine pegs avoids screw bosses on narrow track edges.

### Alternative C: Screws-First Across Every Mid-Span Track Seam & Bracket Peg (`60+` Screws)
*   **Pros:** Applies threaded clamping across every segment joint and bracket saddle.
*   **Cons:** Consumes more than the included `50`-screw pack (`B0BYF4X65F`), requires driving dozens of vertical screws inside `47 mm` inter-turn clearance, and crowds the `4.0 mm` track shoulders next to `Ø 25.0 mm` marbles.
*   **Reason for Rejection:** Exceeds the existing hardware budget and introduces unnecessary assembly friction when bracket-supported `-Z` stepped laps achieve positive alignment without fasteners.

### Alternative D: Keep `Bambu Lamp Kit 001` Dual Compatibility in `trunk_top` (`J14`)
*   **Pros:** Supports either lighting puck in `golden_apple_topper`.
*   **Cons:** The `Ø 60.0 × 18.5 mm` Lamp Kit puck clashes (`2,980.18 mm³`) with `trunk_top`'s `crown_collar`, weakens the top discharge spout, and contradicts [docs/BOM.md](../BOM.md).
*   **Reason for Rejection:** `docs/BOM.md` specifies only the `Sparkleiot Ø 45` ring (`B09YTMNGTD`); pruning retired `19.0 mm` puck depth removes phantom collisions while preserving the `crown_collar` socket (`Ø 60.0 × 4.6 mm`).

### Alternative E: Co-Print Teal `PETG` Inside `PLA` Globes/Topper or Purchase Green `PLA`
*   **Pros:** Keeps green leaves (`Plate 16`) and continents/belts (`Plate 18`) combined in multi-color prints.
*   **Cons:** Co-printing `PETG` inside `PLA` layers fails inter-layer welding; purchasing Green PLA violates the `docs/BOM.md` zero-new-purchases scope.
*   **Reason for Rejection:** Extracting the leaf onto `Plate 13` (`T2 PETG` snap-in) and converting `Plate 18` to `3-color PLA-only` (`Marine Blue`, `Silk Gold`, `Ivory White` already in `docs/BOM.md`) keeps single-polymer bonding with zero added purchases.

### Alternative F: Enable `tree(auto)` Supports on `Plates 14–15` Instead of Modifying CAD Geometry
*   **Pros:** Zero CAD edits to auger or marble hemispheres.
*   **Cons:** Leaves support scars along the `208 mm` auger blade edge (`Plate 14`) and inside marble bayonet mating surfaces (`Plate 15`).
*   **Reason for Rejection:** Full-radius `45°` auger underside sloping (plus brim) and a mated `45°` marble equatorial rim keep both plates support-free (`enable_support = 0`) while gating scoop clearance directly in verification tests.

--------------------------------------------------------------------------------

## Risks & Mitigations

*   **Cross-Layer Bending at Split-Tine Peg Roots (`brackets` & `track`):** `+Z` pegs experience cantilever bending across horizontal layers during snap insertion.
    *   *Mitigation:* Cap radial interference per tine at `<= 0.10 mm`, include `0.5 mm` root fillets, validate fatigue across `[0.10..0.25] mm` PETG/PLA coupons (`CUJ 1`), and verify `> 2.0 mm³` physical snap overlap in `verify_model.py`.
*   **Long-Term PETG Creep Under Elevated Track Weight:** Concentrating lap seams onto `60°` bracket saddles increases sustained point load if track segments twist.
    *   *Mitigation:* Distribute contact across both stepped shoulder zones (`u = ±10.6 mm` over the `11.0 mm` bracket saddle) engaged by twin pegs (`track_seg_01` and `track_seg_14` receive extra bed-adhesion pads and upper brackets `25–26` + top cradle).
*   **PLA Thermal Softening Inside Enclosed Base Tray (`trunk_base`):** `A092` (`5V/12V` motor driver) and `UCTRONICS` (`5V` buck) sit inside a `PLA` root housing (`~50–60 °C` glass transition).
    *   *Mitigation:* Use a `12V / 5A` derated buck (`< 50%` duty), isolate PCBs on raised standoffs inside open-top tray cradles with free air convection around the `~150,000 mm³` upper vault dome plus the `14 × 14 mm` port (`Bottom_Electronics_Lid` stays solid at outer tabs, avoiding thin bridges).
*   **Unmeasured Wire/Plug Clearance Variance Across Electronics Batches:** Real `HT3.96-4P`, `HY2.0-4P`, and inline fuse wire stiffness cannot be physically tested prior to coupon/first-article build.
    *   *Mitigation:* Leave all `WAGO 221-413` blocks and inline fuses free inside the `150,000 mm³` open slack dome rather than tight rigid clips, and reserve `+16/+22 mm` modeled cable envelopes around `A092+C008`.
*   **`26`-Station Vertical Tolerance Stack-Up:** Adding `2` upper brackets increases cumulative seam alignment sensitivity at `track_seg_14`.
    *   *Mitigation:* Keep the `1710°` spout dock as a flat vertical support cradle without a tight horizontal pin, and verify simultaneous `-Z` drop + `5°` swept-ball continuity end-to-end.

--------------------------------------------------------------------------------

## Open Questions

*   **Empirical Printer Shrinkage & Snap Force Calibration (`assumed, needs physical test` via `Test_Coupons_PLA.3mf` & `Test_Coupons_PETG.3mf`):** Computational geometry validates nominal bounds, while actual split-tine snap effort in PETG vs PLA, `KA006` crush-rib press fit inside PLA, continuous-ribbon `6.2 × 3.2 mm` pill edge-on twist maneuverability inside a curved track slice, and `M2.5` tapping torque in the `T1` motor driver hub depend on Snapmaker U1 extrusion flow and must be locked across the two coupon plates before full slicing.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Single-Polymer Manufacturing Rule:** Every multi-color object (`Plates 16–18`) must strictly share one polymer family (`PLA` only) verified by XML extruder-to-filament inspection so co-printed boundaries weld without delamination.
*   **Minimum Printable Feature Width (`0.40 mm` Nozzle):** All crush ribs, snap tines, and micro-ribs must maintain `>= 0.84 mm` wall thickness (`2 × 0.42 mm` extrusion line width) or `>= 0.50 mm` continuous outward ridge (`click_rib`) so OrcaSlicer generates continuous toolpaths.
*   **Hardware Budget Constraint:** Zero external purchases beyond [docs/BOM.md](../BOM.md); hardware consumption drops to `5 / 50` existing `M2.5 × 6 mm` screws (`45` spares left), and `Plates 1–4, 14–15` print strictly with `enable_support = 0` (`max_bridge <= 12.0 mm`), while `min_bed >= 25.0 mm²` applies across all 18 plates.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Implementation executes sequentially in **4 buildable phases** (`Phase A -> Phase B -> Phase C -> Phase D`). Every phase ends with an explicit CLI verification gate so no symbol deletion or interface change breaks downstream builds mid-flight.

### Target Files & Artifacts Inventory

*   **Modified Python Sources:** [`cad/common_params.py`](../../cad/common_params.py), [`cad/trunk.py`](../../cad/trunk.py), [`cad/auger.py`](../../cad/auger.py), [`cad/brackets.py`](../../cad/brackets.py), [`cad/track.py`](../../cad/track.py), [`cad/topper_planets.py`](../../cad/topper_planets.py), [`cad/export_3mf_plates.py`](../../cad/export_3mf_plates.py), [`cad/generate_all.py`](../../cad/generate_all.py), [`cad/verify_model.py`](../../cad/verify_model.py), [`cad/verify_physics.py`](../../cad/verify_physics.py), [`cad/audit_plates.py`](../../cad/audit_plates.py), [`cad/test_coupons.py`](../../cad/test_coupons.py), [`cad/retrofit_jig.py`](../../cad/retrofit_jig.py), [`cad/export_webapp_assets.py`](../../cad/export_webapp_assets.py), [`scripts/gen_bom.py`](../../scripts/gen_bom.py).
*   **Retired / Consolidated Files:** Fold standalone duplicate checks from [`cad/audit_joints.py`](../../cad/audit_joints.py) and [`cad/test_bracket_insertion.py`](../../cad/test_bracket_insertion.py) directly into `cad/verify_model.py` (update imports or mark as thin wrappers calling `verify_model.py` helpers so direct CLI invocations remain valid).
*   **Modified BOM, Docs & Webapp Files:** [`bom/bom.yaml`](../../bom/bom.yaml), [`docs/BOM.md`](../BOM.md), [`bom/bom.csv`](../../bom/bom.csv), [`docs/ASSEMBLY.md`](../ASSEMBLY.md), [`docs/PRINTING.md`](../PRINTING.md), [`README.md`](../../README.md), [`GEMINI.md`](../../GEMINI.md), [`ASSEMBLY_AUDIT.md`](../../ASSEMBLY_AUDIT.md), [`webapp/app.js`](../../webapp/app.js), [`webapp/index.html`](../../webapp/index.html).
*   **Generated Output Globs & Deleted Legacy Outputs:** Regenerate `output/*.step`, `output/*.stl`, `output/full_tree_assembly.step`, `output/3mf/*.3mf` (including `output/3mf/Test_Coupons_PLA.3mf` and `output/3mf/Test_Coupons_PETG.3mf`), and `webapp/assets/{manifest.json,meshes.bin}`; purge retired artifacts (`output/Base_Bottom_Cover.*`, `output/Battery_Cover.*`, `output/Track_Joint_Clip.*`, old mixed-polymer `output/3mf/Test_Coupons.3mf` if split, and rename `Plate_4_SingleColor_Brown_Brackets_13_To_24.3mf` -> `Plate_4_SingleColor_Brown_Brackets_13_To_26.3mf`, `Plate_2_...` updated parts).

---

### Phase A: Core Constants, `150°` Trunk Tray/Vault, Full Auger Taper & Driver Clamp

#### A.1 [`cad/common_params.py`](../../cad/common_params.py)
*   **Packing & Bed Rules:** Align `SAFE_PLATE_ZONE = 240.0` and `MIN_PART_CLEARANCE = 8.0` to match the verified Snapmaker U1 layout and `audit_plates.py`.
*   **Underside LED Channel & Offset:** Set `TRACK_BASE_Y = -15.5`, `LED_CHANNEL_W = 8.4`, `LED_CHANNEL_THROAT_W = 4.6`, `LED_CHANNEL_D = 6.2` (`45°` flare `1.9 mm` rise `-14.8..-12.9`, `8.4 × 3.6 mm` pill bay `-12.9..-9.3`, `2.63 mm` solid center web beneath `v_trough = -6.6726`). Add `DOVETAIL_SLOT_Z_OFFSET = -33.5` (replacing all hardcoded `- 30.0` expressions across `trunk.py`, `verify_model.py`, `retrofit_jig.py`, and `export_webapp_assets.py`).
*   **Track Seams, Brackets, Planets & Acoustic Rib:** Set `TRACK_SEAM_MODE = "BRACKET_STEPPED_LAP"`, `TRACK_LAP_ARC_DEG = 8.0`, `TRACK_LAP_WALL_MIN = 3.2`, `BRACKET_STATION_COUNT = 26`, `TOP_FEEDER_START_R = 47.0`, `TOP_FEEDER_START_DEG = 1710.0`, `CLICK_RIB_PROTRUSION_MM = 0.50`, and explicit `PLANET_ANCHOR_DEGS = (1590.0, 1320.0, 1080.0, 840.0, 600.0, 480.0, 240.0, -15.0)` (verify zero overlap with `TIMING_GATE_ANGLES_DEG = (1605.0, 1350.0, 990.0, 630.0, 270.0, 15.0)`).
*   **`150°` Conduit & Electronics Tray Constants:** Set `WIRE_CONDUIT_ANGLE_DEG = 150.0`, `WIRE_CONDUIT_W = 10.6`, `WIRE_CONDUIT_D = 8.5`. Replace `PUCK_SOCKET_*` (`60.0, 19.0`) with `CROWN_SOCKET_DIA = 60.0` and `CROWN_SOCKET_DEPTH = 4.6`. Add explicit `BOTTOM_TRAY_OUTER_DIA = 134.6`, `BOTTOM_TRAY_RABBET_DIA = 135.0`, `BOTTOM_TRAY_THICK = 2.80`, and `BOTTOM_TRAY_TAB_COORDS` (`4×` perimeter root-tab `M2.5` XY coordinates clear of `WAGO`/`N20`/`DC-099`).
*   **Glyph Floor & Symbol Deprecation/Purge:** Keep `make_engraved_label_solid()` minimum `stroke_w` floor at `0.65 mm` (leaving existing `2.5–2.6 mm` `char_h` on small `R = 2.25 mm` marble/planet apexes unchanged). Delete unused constants only after synchronized caller cleanup: `CA001_MAGNET_*`, `MAGNET_*`, `XA004_*`, `XA005_*`, `XA006_*`, `XA007_*`, `XA008_*`, `XA009_*`, `XA010_*`, `IA005_*`, `PG001_*`, `PG002_*`, `KB003_*`, `BATTERY_14500_BAY_*`, `DUAL_MOSFET_BAY_*`, `AAA_BATTERY_BOX_*`, `BASE_BOTTOM_COVER_THICK`, `TRACK_SCARF_ANGLE_DEG`, `TRACK_DOWEL_*`, `BRACKET_PEG_BEAD_*` (or keep temporary aliases until Phase C completes).

#### A.2 [`cad/trunk.py`](../../cad/trunk.py) & [`cad/retrofit_jig.py`](../../cad/retrofit_jig.py)
*   **`150°` Coupled Conduit Changes:** Rotate `_cut_rear_wire_conduit()` to `150.0°` (`WIRE_CONDUIT_ANGLE_DEG`); add a `150.0°` radial chord flat (`R <= 24.50 mm` male, `R <= 24.70 mm` female) on `make_keyed_male_tenon()` and `make_keyed_female_socket_cutter()`; suppress bark furrows within `±10.0°` of `150.0°` inside `_bark_furrow_depth()` and `_make_bark_textured_base_hub()`; rotate `topper_ring_wire_slot` in `build_trunk_top()` to `150.0°`; and replace single `build_conduit_cover_strip()` with section-matched `build_conduit_cover_strips()` exporting `Conduit_Cover_Strip_Base` (`L = 100.0 mm`), `Conduit_Cover_Strip_Mid` (`L = 144.0 mm`), and `Conduit_Cover_Strip_Top` (`L = 144.0 mm`).
*   **Clean Vault Cone, `DC-099` Spotface & Upright `Bottom_Electronics_Lid` Tray:**
    *   Purge `build_base_bottom_cover()`, `xa007_boss`, `xa007_bay`, `xa007_toggle_slot`, `pg002_bay`, `batt_bay`, `batt_m25`, `sw_m25`, `front_cradle_frame`, `buck_cradle_frame`, `wago_cradle_frame`, and `cable_slot` from `trunk_base`, leaving `vault_cone` (`Ø 135 mm` opening at `Z = 0..16.4`, `45°` cone up to `Z = 50 mm`, `max_bridge <= 10.0 mm`) with only `motor_shroud_tower` (pocket raised to `Z = 3.20..29.40 mm` above the tray with side wire tunnel) and `wand_pillar` (`(+45.03, +26.00)`).
    *   Cut an outer `-X` `Ø 16.0 mm` cylindrical spotface centered on `(X = -72.5, Y = 0, Z = 10.0)` into the `5.0 mm` vault cylinder (`Ø 135 mm`, inner wall `X = -67.5`) stopping at `X = -71.3 mm`, achieving an exact `3.80 mm` bulkhead around the `Ø 11.40 mm` `DC-099` bore with zero `< Z = 0` internal cuts.
    *   Rename/refactor `build_battery_cover()` -> `build_bottom_electronics_lid()` forming an upright `Z = 0.00..2.80 mm` `Ø 134.6 mm` electronics tray seating flush into a `Ø 135.0 × 3.00 mm` vault rabbet with `4×` outer flange tabs (`Ø 2.75 mm` through + `Ø 5.00 mm` cylindrical counterbores for `AA050` `M2.5 × 6 mm` BHCS), upward open-top `1.6 mm`-wall snap cradles (`10–14 mm` tall) for `UCTRONICS` (shifted `-X` away from `wand_pillar` with `-X` `1000 µF` cap space), unstacked `2× WAGO 221-415` (`Z <= 14.0 mm` total height leaving `> 16 mm` lever flip clearance under `vault_cone`), `A092+C008` oriented with `+16.0 mm` `HT3.96-4P` and `+22.0 mm` `A096` plug clearance toward open center volume, `14 × 14 mm` `C008` port at center of `A092` footprint, and debossed `"A"`, `"12"`, `"G"` orientation glyphs via existing `make_engraved_label_solid()`. Keep `2× WAGO 221-413` and `3×` inline fuses free in the `150,000 mm³` open slack zone.
*   **`trunk_top` Ball Relief & `1710°` Dock (`J9`):** Carve the curved `Ø 27.6 mm` swept-ball relief along `1710° -> 1660°` at `TOP_FEEDER_START_R = 47.0` in `-Y/-X` of `trunk_top`, shift keyhole socket Z placements using `DOVETAIL_SLOT_Z_OFFSET = -33.5`, and add a flat unpinned horizontal cradle shelf (`Y = -47.0..-37.0, Z = TOP_FEEDER_TOP_Z - 15.5`) supporting `track_seg_14_top_entry`. Verify [`cad/retrofit_jig.py`](../../cad/retrofit_jig.py) compatibility against `DOVETAIL_SLOT_Z_OFFSET`.

#### A.3 [`cad/auger.py`](../../cad/auger.py)
*   **`Motor_Clutch_Driver` (`T1` Matte Brown PLA, `Plate 2`):** Extend the `Ø 18.0 mm` (`R = 9.0 mm`) lower hub collar down across `Z = 0.0..6.5 mm` enclosing `d_bore` (`Z = 0.00..6.50 mm`), tapering at `45°` into the upper `Ø 16.0 mm` hex platform (`Z = 6.5..10.0 mm`); cut a `+X` horizontal `Ø 2.20 mm` radial pilot bore at `Z = 3.25 mm` perpendicular to the `x = +1.075 mm` D-flat (`7.925 mm` radial thread wall, clamped with `1× M2.5 × 6 mm` screw before dropping motor into `trunk_base`); assign toolhead `1` (`Dark Wood Brown PLA`).
*   **Full-Span `45°` Auger Blade Taper (`Plate 14`):** Replace the rectangular `AUGER_FLIGHT_THICKNESS = 2.4 mm` sweep section in `_build_auger_core()` with a right trapezoid spanning the entire `14.5 mm` blade radius (`r = 4.5..19.0 mm`): horizontal top lift face (`46.0 mm` pitch), `2.4 mm` outer edge thickness, and a continuous `45°` inward-sloped underside (`16.9 mm` root thickness at `r = 4.5 mm`), keeping `>= 12.0 mm` vertical clearance above `Ø 25.0 mm` spheres and preserving `scoop_under_margin >= 9.5 mm` at `Z = 37.22..54.50 mm`.

*   **Phase A Gate:** Run a quick Python validation importing `common_params`, `trunk`, `auger`, and `retrofit_jig` checking `.is_valid()` / `.is_manifold()`, `Bottom_Electronics_Lid` + vault clearance (`0.0000 mm³`), `150°` tenon/conduit sweep, and `auger` bottom-scoop clearance (`>= 9.5 mm`).

---

### Phase B: `26` Split-Tine Brackets, `-Z` Stepped-Lap Track & Topper/Planets/Marble Geometry

#### B.1 [`cad/brackets.py`](../../cad/brackets.py)
*   Rename `build_all_24_station_brackets()` -> `build_all_station_brackets()` (using `range(1, BRACKET_STATION_COUNT + 1)` for `bracket_01..26`) and expose an alias temporarily if needed during Phase B. Keep `top_z = DOVETAIL_SLOT_H - 0.25 = 17.75 mm`.
*   Replace the rigid `Ø 4.24 mm` peg bead on the twin `Ø 4.00 × 4.50 mm` `+Z` alignment pegs (`u = ±10.6 mm`, `0.50 mm` root fillet) with **split-tine cantilevers**: a tangential `±Y` through-slot (`0.85 mm` wide × `2.80 mm` deep from peg tip) and symmetric `0.90 mm`-tall (axial `Z`) × `Ø 4.38 mm` radial snap lobes (`<= 0.10 mm` radial flex per tine in `Ø 4.20 mm` PETG lead-in socket expanding into a `Ø 4.56 mm` internal pocket).

#### B.2 [`cad/track.py`](../../cad/track.py)
*   **Bracket-Aligned `-Z` Stepped Shoulder Seams:** Keep segment bounds on `60°` bracket azimuths (`seg_01: -90°..+60°`, `seg_02..13: 60°..180° .. 1380°..1500°`, `seg_14: 1500°..1710°`). Delete `make_track_male_tenon_local()`, `make_track_female_socket_local()`, `make_track_joint_clip()`, and all dowel/sidewall-tongue cuts. At every intermediate `60°` boundary, cut matching upper/lower stepped half-laps (`8.0°` overlap arc, `>= 3.2 mm` vertical shoulder flanges across `|u| >= 5.5 mm`, vertical butt seam across `|u| < 5.5 mm` so the central `8.4 × 3.6 mm` LED bay stays continuous) with paired through/blind `Ø 4.20 / Ø 4.56 mm` split-tine sockets engaging the shared bracket's twin pegs at `u = ±10.6 mm`.
*   **Shared LED Channel Helper & Acoustic Micro-Rib:** Extract `_append_led_channel_points()` used by both `make_track_profile_wire()` and `make_track_endcap_wire()` (`TRACK_BASE_Y = -15.5`, `45°` flare `-14.8..-12.9`, `8.4 × 3.6 mm` pill bay `-12.9..-9.3`). Set `click_rib` protrusion to `CLICK_RIB_PROTRUSION_MM = 0.50 mm` at `G0..G5`, and sculpt horizontal `Z = 0.00 mm` underside datum lands (`>= 40.0 mm²`) on `track_seg_01` and `track_seg_14_top_entry`.
*   **Explicit Planet Balconies & Compliant Balcony Pegs:** Place the 8 planet balconies strictly using `PLANET_ANCHOR_DEGS` (zero timing-gate overlaps) and add a `±X` `0.85 mm × 2.40 mm` split flex slot with twin `0.85 mm`-tall × `Ø 8.32 mm` snap lobes on each `Ø 7.60 × 3.50 mm` upward balcony peg.

#### B.3 [`cad/topper_planets.py`](../../cad/topper_planets.py)
*   **Topper Socket & Leaf Extraction (`J2`, `J14`, `Plate 16`):** Replace `puck_socket` (`Ø 60 × 19.0 mm`) and legacy puck `wire_notch` in `build_golden_apple_topper()` with `CROWN_SOCKET_DIA = 60.0 mm` × `CROWN_SOCKET_DEPTH = 4.6 mm` (`0.5 mm` lead-in chamfer) mating over `crown_collar`, topped by a `Ø 46.5 × 14.4 mm` conical/cylindrical light throat up to `lantern_cavity_rings` (`Z = 19.0..83.8 mm`). Remove `apple_green_leaf` from `build_golden_apple_topper()`, cut a `3.2 × 2.2 × 4.5 mm` keyed rectangular leaf socket on `apple_brown_stem`, and export a separate single-color `apple_green_leaf` (`T2` Teal `PETG`) with matching male peg (reusing `build_apple_topper_stem_leaf()` geometry patterns).
*   **`KA006` Crush Ribs (`J10`), Wand Bore (`J12`) & Plate 15 Chamfer:** In `_make_planet_socket_cutter()`, **subtract** `4× 0.85 mm`-wide radial rib notches (`R_tip = 3.55 mm` -> `Ø 7.10 mm` inscribed grip across `Z = 3.6..9.6 mm`) from the subtractive cutter body so 4 solid PLA crush ribs protrude inward around `KA006`; widen the lower entry groove (`Z = 1.25..2.85 mm`) to `Ø 8.46 mm` to latch the split balcony peg. Leave `Magic_LED_Wand` at a clean `Ø 8.05 × 2.20 mm` magnet bore (no speculative ribs; CA fallback per `Non-Goals`). On `Apple_Hemisphere_A/B`, retain `lantern_dome_a/b` unchanged and replace `A`'s flat `Z_print = 2.65 mm` exterior step with a `45°` conical chamfer (`r = 10.52 -> 12.50 mm`) nesting into a symmetric `45°` conical female rim seat in `B` (`Ø 25.00 mm` external sphere maintained).
*   **`Plate 18` `3-Color PLA` Reassignment:** Recolor green (`#00A86B`) and ice (`#F0F4F8`) sub-volumes on `planet_earth` (oceans `#1E5AA8` [`T1`], continents `#D4AF37` [`T2`], ice `#F5EFE6` [`T3`]), `planet_uranus` (globe `#1E5AA8` [`T1`], polar/rings `#F5EFE6` [`T3`], accent `#D4AF37` [`T2`]), and `planet_neptune` (globe `#1E5AA8` [`T1`], wind belts `#F5EFE6` [`T3`], storm/accent `#D4AF37` [`T2`]).

*   **Phase B Gate:** Build `brackets`, `track`, and `topper_planets` standalone verifying all 14 track segments, 26 brackets, topper crown mount, planet ribs (`> 0.30 mm³` interference vs `Ø 7.50 mm` cylinder), and `A+B` sphere closure are valid manifold solids.

---

### Phase C: `.3mf` Plate Packing, Coupons & Consolidated Verification Suite

#### C.1 [`cad/export_3mf_plates.py`](../../cad/export_3mf_plates.py) & [`cad/generate_all.py`](../../cad/generate_all.py)
*   Swap `Battery_Cover`/`Base_Bottom_Cover` -> `Bottom_Electronics_Lid` (`Z = 0` tray), `Conduit_Cover_Strip` -> `Conduit_Cover_Strip_{Base,Mid,Top}` (`150°` assembly coords), move `Motor_Clutch_Driver` to `Plate 2` alongside `trunk_top`, `Bottom_Electronics_Lid`, `Servo_Or_030_Adapter`, and the 3 strips (verified inside `240 × 240 mm`, `>= 8.0 mm` clearance); pack `bracket_13..26` (`14` parts, updated grid spacing) onto `Plate 4_SingleColor_Brown_Brackets_13_To_26.3mf`; place `apple_green_leaf` in open bed space on `Plate 13`; delete `Track_Joint_Clip`; update `build_and_export_full_assembly()` to use bracket-aligned track arcs and `PLANET_ANCHOR_DEGS`; update `PLATE_FILAMENT_PALETTES["Plate_18_..."]` to `(["#1E5AA8", "#D4AF37", "#F5EFE6", "#C41E3A"], ["PLA", "PLA", "PLA", "PLA"])`; make `_color_to_toolhead_id(hex_color, plate_name)` palette-aware; inject `brim_type = outer_only, brim_width = 10.0` per object on `auger_lower` / `auger_upper` (preserving `0` brim elsewhere in `GravMass_Tree_Ultimate_U1.3mf`); and expand `generate_all.py` `obsolete_parts` cleanup to purge retired `.step`/`.stl`/`.3mf` artifacts.

#### C.2 [`cad/verify_model.py`](../../cad/verify_model.py), [`cad/verify_physics.py`](../../cad/verify_physics.py), [`cad/audit_plates.py`](../../cad/audit_plates.py) & [`cad/test_coupons.py`](../../cad/test_coupons.py)
*   **Physics & Swept Checks:** Update [`cad/verify_physics.py`](../../cad/verify_physics.py) segment bounds (`1500..1710°`, `60..180°`, `-90..+60°`), feeder coordinates (`TOP_FEEDER_START_R = 47.0`), and full-span auger `scoop_under_margin >= 9.5 mm`.
*   **Consolidated B-Rep Assertions (`verify_model.py`):** Purge `Lamp Kit 001`, `CA001`, `PG001`, `KB003`, `XA007`, `Battery_Cover`, `Base_Bottom_Cover`, `Track_Joint_Clip`, `#00A86B` planet checks, and `6.2 × 1.0 mm` pebble probes. Add hard fail assertions for:
    1.  `Ø 24.90 mm` swept-ball probe in `<= 5°` / `<= 0.5 mm` steps across `1710° -> -90°` against **`trunk_base + trunk_mid + trunk_top + golden_apple_topper + track_seg_01..14`** (`0.0000 mm³` interference).
    2.  `26/26` bracket keyhole L-path sweeps + `-Z` simultaneous `track_seg_02` drop onto `seg_01 + b01..03` and `seg_03` drop onto `seg_02 + b03..05` (`0.0000 mm³` interference) + `> 2.0 mm³ @ +0.8 mm` axial pullout engagement on both bracket and planet split-tine snaps.
    3.  `KA006` (`Ø 7.50 mm`) vs `4` planet crush ribs (`> 0.30 mm³` interference), edge-on `3.2 × 6.2 mm` pill entry sweep (`0.5 mm` steps, `0.0000 mm³`) + flat seated sweep (`0.0000 mm³`), `JST-SM` `150°` sweep (`0.5 mm` steps, `0.0000 mm³`) with all 26 brackets + cover strips installed, `DC-099 <= 4.2 mm` wall, `A092` + `UCTRONICS` + `WAGO` + `Bottom_Electronics_Lid` (`0.0000 mm³`), and `crown_collar` (`Ø 59.40 mm` in `Ø 60.0 × 4.6 mm`) shear lock.
*   **Plate & XML Single-Polymer Gate (`audit_plates.py` + helper called by `verify_model.py`):** Fix annular bridge span to subtract inner hole spans (`max_bridge <= 12.0 mm` strictly enforced where `enable_support == 0` on `Plates 1–4, 14–15`), enforce `min_bed >= 25.0 mm²` across all `18` plates, and parse `Metadata/model_settings.config` (`<part><metadata key="extruder">`) + `Metadata/project_settings.config` (`filament_type`) failing if any multi-color object mixes `PLA` and `PETG`.
*   **Split Single-Polymer Coupons (`cad/test_coupons.py`):** Keep the existing 4-step `[0.10, 0.15, 0.20, 0.25] mm` template runner in `cad/test_coupons.py`, updating geometries to current hardware (tilted PETG `-Z` shoulder seam + edge-on pebble pill bay, `T1` + `T2` split-tine bracket/balcony snaps, `4`-ribbed `KA006` cup `Ø 7.00–7.30 mm`, `T1` `M2.5` D-shaft clamp hub, `45°`-chamfered marble bayonet pair, keyhole trunk + `150°` tenon pair) and exporting two thermal-matched single-polymer plates: `output/3mf/Test_Coupons_PLA.3mf` (`60 °C` bed) and `output/3mf/Test_Coupons_PETG.3mf` (`75 °C` bed).

*   **Phase C Gate:** Execute `uv run --with build123d python3 -u cad/generate_all.py && uv run --with build123d --with trimesh --with scipy --with rtree python3 -u cad/verify_model.py && uv run --with trimesh --with numpy --with scipy --with rtree python3 -u cad/audit_plates.py && uv run --with build123d --with trimesh python3 -u cad/test_coupons.py`.

---

### Phase D: BOM, Documentation & WebGL Synchronization

#### D.1 [`bom/bom.yaml`](../../bom/bom.yaml), [`scripts/gen_bom.py`](../../scripts/gen_bom.py), [`docs/BOM.md`](../BOM.md), [`bom/bom.csv`](../../bom/bom.csv)
*   Update `bom/bom.yaml`: set `M2.5 × 6 mm` BHCS quantity to `5` (`4×` tray + `1×` motor clamp, `45` spares left), rename `Battery_Cover` -> `Bottom_Electronics_Lid`, move `Motor_Clutch_Driver` to `Plate 2` (`T1`), relocate `apple_green_leaf` to `Plate 13` (`T2 PETG`), and update `Plate 18` filament slots (`T1` Marine Blue, `T2` Silk Gold, `T3` Matte Ivory White). Update the Mermaid diagram in `scripts/gen_bom.py` (`DEFAULT_BOM_MD_TEMPLATE`) and `docs/BOM.md` outside `<!-- BOM:BEGIN -->` markers (`150°` conduit, `26` brackets, `5×` screws, `Bottom_Electronics_Lid`), then regenerate `docs/BOM.md` and `bom/bom.csv`.

#### D.2 User Docs & Post-Remediation Audit ([`docs/ASSEMBLY.md`](../ASSEMBLY.md), [`docs/PRINTING.md`](../PRINTING.md), [`README.md`](../../README.md), [`GEMINI.md`](../../GEMINI.md), [`ASSEMBLY_AUDIT.md`](../../ASSEMBLY_AUDIT.md))
*   Update plate counts (`Plate 2`, `Plate 4` `13..26`, `Plate 13` leaf, `Plate 14` brim, `Plate 16/18` `PLA`-only), bracket counts (`24 -> 26`), screw counts (`5×`), `150°` conduit routing, upright tray wiring, edge-on pebble pill insertion, dual coupon print workflow, and record updated B-Rep measurements in post-remediation `ASSEMBLY_AUDIT.md`.

#### D.3 Webapp Bundle & Simulator Sync ([`cad/export_webapp_assets.py`](../../cad/export_webapp_assets.py), [`webapp/app.js`](../../webapp/app.js), [`webapp/index.html`](../../webapp/index.html))
*   In `cad/export_webapp_assets.py`: export `Bottom_Electronics_Lid`, `bracket_25/26`, `Conduit_Cover_Strip_{Base,Mid,Top}`, extracted `apple_green_leaf`, palette-aware `_color_to_toolhead_id()`, `PLANET_ANCHOR_DEGS` placements, `150°` assembly transforms, updated `SUBSYSTEM_LABELS` / `assembly_steps`, and sync `manifest["kinematics"]` directly from `common_params.py` constants (`RETURN_CHUTE_END_DEG`, `TOP_FEEDER_START_R`, `AUGER_PITCH`, `BRACKET_STATION_COUNT`).
*   In `webapp/app.js` & `webapp/index.html`: replace `closedLoopTrackPoint()` constants, `TIMING_GATES`, `hw_Topper_Rear_Cable` (`180°` -> `150°`), `TRACK_PIECE_SPECS` / `buildTrackJointVisualizer()` (`60°` bracket-lap seams, zero clips), `-Z` track drop animation, and `Plate 1/2/4/13/14/16/18` download labels/swatches; bump `?v=N` cache-busters across `webapp/index.html` and `webapp/app.js` only after `export_webapp_assets.py` finishes writing `manifest.json` and `meshes.bin`.

*   **Phase D Gate:** Run `uv run --with pyyaml python3 -u scripts/gen_bom.py --check && uv run --with numpy python3 -u cad/export_webapp_assets.py`.

---

### Verification Plan

*   **CAD Build & B-Rep Regression Gate:** `uv run --with build123d python3 -u cad/generate_all.py && uv run --with build123d --with trimesh --with scipy --with rtree python3 -u cad/verify_model.py` exits `0` with zero invalid/non-manifold solids, `26/26` keyhole L-path pass, `0.0000 mm³` simultaneous `-Z` `track_seg_02` and `seg_03` assembly, `0.0000 mm³` `5°` swept-ball check (`1710° -> -90°`) against core+topper+all `14` tracks, `0.0000 mm³` `150°` `JST-SM` sweep, `> 0.30 mm³` `KA006` crush-rib interference, `0.0000 mm³` edge-on + flat pebble LED sweeps, `scoop_under_margin >= 9.5 mm`, and `0.0000 mm³` vault/tray clearances.
*   **Plate Printability & Single-Polymer Gate:** `uv run --with trimesh --with numpy --with scipy --with rtree python3 -u cad/audit_plates.py` exits `0` (`min_bed >= 25.0 mm²` on `Plates 1–18`, `max_bridge <= 12.0 mm` where `enable_support == 0` on `Plates 1–4, 14–15`, `0` mixed `PLA`/`PETG` components on `Plates 16–18`).
*   **BOM & Webapp Consistency Gate:** `uv run --with pyyaml python3 -u scripts/gen_bom.py --check && uv run --with numpy python3 -u cad/export_webapp_assets.py` exits `0`.
*   **Physical Operator Gate (Required Before Slicing `Plates 1–18`):** Print `Test_Coupons_PLA.3mf` (`60 °C`) and `Test_Coupons_PETG.3mf` (`75 °C`) on the Snapmaker U1 to empirically lock split-tine bracket/balcony clearance, `KA006` crush-rib press force, continuous-wire `6.2 × 3.2 mm` pill edge-on twist fit, `45°`-chamfered marble twist torque, and `M2.5` `N20` D-flat clamping torque.

--------------------------------------------------------------------------------

*Drafted with EGM*
