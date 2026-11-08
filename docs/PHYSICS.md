# 📐 Measuring Earth's Gravity ($g$) with the Model (Galileo–Newton Gravity Chronometer)

Just as Galileo diluted Earth's gravity using an inclined plane so he could measure acceleration without high-speed clocks, the **4.5-turn conical helical track** dilutes vertical free-fall (`Δh = 348.92 mm`) over a **`2,868.34 mm` (`2.87 m`)** spiral path (`average slope ≈ 7.0°`), slowing a `4.18 s` descent to a pace you can accurately time with a smartphone or stopwatch to estimate **$g \approx 9.81\text{ m/s}^2$**!

## 1. Built-In Physical Measurement Scales & Timing Gates

Three precision measurement systems are molded directly into the 3D-printed track and trunk:
- **6 Timing Gates (`G0`–`G5`) on the Helical Track (`track_seg_14_top_entry` → `track_seg_01`):**
  - **Engraved Outer-Wall Labels (`G0`–`G5`):** Deeply debossed on the outer rail wall at each gate.
  - **`3.6 mm` Top-Rim Sighting V-Notches:** Cut into the top rim of the outer rail so you can visually sight (or film) the exact instant a marble's center crosses each gate.
  - **`0.35 mm` Acoustic Click Micro-Ribs:** Molded across the bottom of the curved trough at each gate (`G0`–`G5`). As a marble rolls over each gate, it emits a crisp, audible **`"tick!"`** without slowing down—allowing **$\pm 1\text{ ms}$ acoustic timing** using a smartphone microphone!
- **Continuous `100 mm` (`10 cm`) Helical Arc-Length Scale (`s`):** Engraved tick marks every `100 mm` along the true 3D conical spiral path from `G0` (`s = 0 mm`) to `G5` (`s = 2,868.3 mm`), with bold double-ticks every `500 mm`.
- **Front Trunk Vertical Elevation Scale (`Δh`):** Horizontal graduation ticks every `25 mm` (`50 mm` medium, `100 mm` major) flanking the front `-Y` gothic viewing windows of [`trunk_base`](../output/trunk_base.stl), [`trunk_mid`](../output/trunk_mid.stl), and [`trunk_top`](../output/trunk_top.stl).

## 2. Reference Table of Timing Gate Coordinates (`G0` to `G5`)

Notice that gates **`G1`, `G2`, `G3`, and `G4`** all lie directly on the **front `-Y` centerline spine** (`1350°`, `990°`, `630°`, and `270°` — separated by exact `360°` full turns), so all four gates can be viewed or filmed from a single front camera angle!

| Timing Gate | Track Segment & Position | Helix Angle (`θ`) | Elevation (`Z`) | Cumulative Vertical Drop (`Δh` from `G0`) | True 3D Spiral Distance (`s` from `G0`) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **`G0`** | [`track_seg_14_top_entry`](../output/track_seg_14_top_entry.stl) *(Top Release Gate)* | `1605.0°` | `414.71 mm` | `0.00 mm` | `0.00 mm` |
| **`G1`** | [`track_seg_12`](../output/track_seg_12.stl) *(Turn 1 Front `-Y` Spine)* | `1350.0°` | `358.75 mm` | `55.96 mm` | `305.79 mm` |
| **`G2`** | [`track_seg_09`](../output/track_seg_09.stl) *(Turn 2 Front `-Y` Spine)* | `990.0°` | `279.75 mm` | `134.96 mm` | `837.40 mm` |
| **`G3`** | [`track_seg_06`](../output/track_seg_06.stl) *(Turn 3 Front `-Y` Spine)* | `630.0°` | `200.75 mm` | `213.96 mm` | `1,486.55 mm` |
| **`G4`** | [`track_seg_03`](../output/track_seg_03.stl) *(Turn 4 Front `-Y` Spine)* | `270.0°` | `121.75 mm` | `292.96 mm` | `2,253.58 mm` |
| **`G5`** | [`track_seg_01`](../output/track_seg_01.stl) *(Bottom Finish Gate)* | `15.0°` | `65.79 mm` | `348.92 mm` | `2,868.34 mm` |

---

## 3. Step-by-Step: 3 Ways to Measure Marble Transit Time ($\Delta t$)

1. **Method 1 — Smartphone Acoustic Stopwatch via [Phyphox](https://phyphox.org/) ($\pm 1\text{ ms}$ Precision, Recommended):**
   - Install the free open-source **[Phyphox](https://phyphox.org/)** physics app (iOS / Android) and open **Acoustic Stopwatch** (or **Audio Scope**).
   - Set your phone beside the tree and release a single marble from rest at **`G0`** (or let the auger discharge it at the top).
   - As the marble crosses the `0.35 mm` acoustic micro-ribs at **`G0` → `G5`**, it produces sharp audio click spikes. Log the elapsed time $\Delta t$ into the **[Web App Gravity Lab (`newton.martinez.fyi`)](https://newton.martinez.fyi/)**.
2. **Method 2 — Smartphone Slow-Motion Video (`120 fps` or `240 fps`):**
   - Point your phone camera at the front `-Y` face of the tree in `120 fps` or `240 fps` slow-motion mode (where `G1`, `G2`, `G3`, and `G4` are stacked vertically in a single frame).
   - Count the video frames between the start gate (`f_A`) and finish gate (`f_B`):
     $$\Delta t = \frac{f_B - f_A}{\text{fps}}$$
3. **Method 3 — Live Web App Stopwatch & Multi-Trial Averager ([`newton.martinez.fyi`](https://newton.martinez.fyi/)):**
   - Open **[https://newton.martinez.fyi/](https://newton.martinez.fyi/)** and use the **🍎 Newton Gravity Lab ($g$-Estimator)** panel in the left sidebar.
   - Select your gate pair (e.g. `G0 → G5` or `G1 → G4`) and your marble core configuration ($\kappa$).
   - Click **⏱️ Tap Start Gate (Physical)** when the marble crosses your start gate and **🛑 Tap Finish Gate** when it crosses your finish gate (or enter your measured $\Delta t$ in seconds in the **Log Δt** input box).
   - Repeat for **$N = 5\text{ to }10$ drops**—because random human reaction-time jitter ($\sigma_t \approx 0.08\text{ s}$) averages out by $1/\sqrt{N}$, averaging 10 trials yields an accurate estimate of $g$ within `1–2%`!

---

## 4. Physics Formula & Marble Core Rotational Inertia ($\kappa$)

When a sphere of radius $R = 12.50\text{ mm}$ and moment of inertia $I$ rolls without slipping along a twin-rail circular trough (effective rolling contact radius $r_{\text{eff}} < R$), gravitational potential energy $m g \Delta h$ splits into both **translational kinetic energy** $\left(\frac{1}{2} m v^2\right)$ and **rotational kinetic energy** $\left(\frac{1}{2} I \omega^2 = \frac{1}{2} m (\kappa - 1) v^2\right)$, where the **total rotational inertia multiplier** is:
$$\kappa = 1 + \frac{I}{m\,r_{\text{eff}}^2}$$

### Equation A — Release from Rest at Gate `G0` ($s_0 = 0$)
For a marble released from rest at `G0` that travels helical distance $s$ and drops vertically by $\Delta h$ in average time $\overline{\Delta t}$ (with $s$ and $\Delta h$ in meters, or dividing $\text{mm}/\text{s}^2$ by $1000$):
$$\hat{g} = \frac{2\,\kappa\,s^2}{\Delta h \cdot (\overline{\Delta t})^2}$$

### Equation B — Universal Two-Gate Estimator (Any Gate Pair $G_A \to G_B$)
Even if you measure between two intermediate gates (such as the front-spine gates **`G1 → G4`** where the marble is already moving at `G1`), kinematics from rest at `G0` gives the exact closed-form two-gate estimator used by the Web App:
$$\hat{g} = \frac{2\,\kappa\,\Delta s_{AB}\,\left(\sqrt{s_B} - \sqrt{s_A}\right)^2}{\Delta h_{AB} \cdot (\overline{\Delta t_{AB}})^2}$$
where $\Delta s_{AB} = s_B - s_A$ and $\Delta h_{AB} = \Delta h_B - \Delta h_A$.

### Rotational Inertia Multiplier ($\kappa$) for Each Marble Core Option

| Marble Core Configuration (Inside `Apple_Hemisphere_A` + `B`) | Mass Distribution | Rotational Inertia Multiplier ($\kappa$) | Expected `G0 → G5` Transit Time ($g = 9.81\text{ m/s}^2$) |
| :--- | :--- | :---: | :---: |
| **Bambu Y-Shape 3-LED Light (`KC013` Warm White / `KC012` Cool White, `Ø 18.0 × 6.5 mm` + `CR1632`)** | 3-LED Y-board + `CR1632` (`Ø 16.0 × 3.2 mm`) steel coin cell in `Ø 18.70 × 7.30 mm` chamber | **`κ = 1.48`** | **`~4.21 s`** |
| **Glowing LED + `M8` Steel Hex Nut Ring *(Recommended)*** | Heavy steel nut + LED concentrated near center + thin PLA shell | **`κ = 1.46`** | **`~4.18 s`** |
| **Heavy `Ø 12.7 mm` (`1/2"`) Chrome Steel Ball Core** | Dense solid steel sphere (`~8.4 g`) concentrated at the center | **`κ = 1.42`** | **`~4.12 s`** |
| **Hollow `PLA` Thin-Shell Lantern + LED Only** | Mass concentrated in the outer `~1.9 mm` spherical shell wall | **`κ = 1.54`** | **`~4.29 s`** |

> **🔬 Bonus Physics Experiment — Prove Galileo's Equivalence Principle & Rotational Inertia!**  
> Roll a **Steel-Core Marble ($\kappa = 1.42$)** and a **Hollow-Shell Marble ($\kappa = 1.54$)** down the track and time both. Even though the steel-core marble finishes `~0.17 s` faster because more of its mass is concentrated near its center (lower $I / m R^2$), when you select each marble's corresponding $\kappa$ in the formula (or in the Web App selector), **both marbles compute the exact same gravitational acceleration $\hat{g} \approx 9.81\text{ m/s}^2$**!
