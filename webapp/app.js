import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

// Use CAD Z-up coordinate convention natively
THREE.Object3D.DEFAULT_UP.set(0, 0, 1);

// Global State
const state = {
  mode: "simulate", // "simulate" | "assembly" | "plates"
  powerOn: true,
  augerRpm: 90,
  lightMode: "rainbow", // "rainbow" | "warm" | "studio"
  xrayActive: false,
  showElectronics: true,
  followMarbleCam: false,
  simExplodePct: 0,
  asmExplodePct: 0,
  asmCurrentStep: 1,
  ghostFutureSteps: false,
  stepAnimElapsed: 0.0,
  stepTargetMaxTime: Infinity,
  asmAutoPlaying: false,
  activePlateIndex: 0, // 0..4 or -1 for All 5 Plates
  plateLightPreset: "studio", // "studio" | "detail" | "soft"
  plateExposurePct: 135,
  showTrackJoints: true,
  trackAutoCam: true,
  activeTrackPieceIdx: 0,
  focusedPortMode: null, // "start-port" | "first-seam" | "last-seam" | "end-port" | null
  sliceZ: 220.0,
  loopCount: 0,
  clockTime: 0,
  physPreset: "standard", // "standard" | "fast" | "rough"
};

const PHYSICS_PRESETS = {
  standard: {
    muR: 0.015,
    muWall: 0.18,
    kappa: 1.48,
    badge: "μ_r = 0.015 | μ_w = 0.18",
  },
  fast: {
    muR: 0.008,
    muWall: 0.12,
    kappa: 1.42,
    badge: "μ_r = 0.008 | μ_w = 0.12",
  },
  rough: {
    muR: 0.025,
    muWall: 0.26,
    kappa: 1.54,
    badge: "μ_r = 0.025 | μ_w = 0.26",
  },
};

let manifest = null;
let scene, camera, renderer, controls, clipPlane;
let assembledRoot, electronicsGroup, guideLinesGroup, trackJointsGroup, platesRoot, bedGridGroup;
const assembledMeshes = [];
const trackJointMarkers = [];
const subsystemVisibility = {};
const dynamicMarbles = [];
const plateGroups = [];
const rgbLights = [];
const cobLights = [];
let lampPuckLight = null;
let ambientLight = null;
let hemiLight = null;
let keyLight = null;
let fillLight = null;
let rimLight = null;
let plateInspectLight = null;
let plateBackLight = null;
const topperShellActors = [];
let topperHaloMesh = null;
let topperHaloMat = null;
let topperPuckMat = null;
let puckColorAttr = null;
let cobStripMat = null;
let cobColorAttr = null;
let pebbleInstancedMesh = null;
const _rgbTmpColor = new THREE.Color();
const planetLedActors = [];
const magicWandActors = [];
let wandTapAnim = null;
let nextWandPlanetIdx = 0;
let allPlanetsModeIndex = 1; // 0=OFF, 1=STEADY, 2=BREATHE, 3=FLASH
const LED_MODE_NAMES = ["OFF", "STEADY GLOW", "BREATHE PULSE", "STROBE FLASH"];

// Galileo-Newton Gravity Chronometer Timing Gates (G0..G5) & Lab State
const TIMING_GATES = [
  { id: 0, code: "G0", name: "G0 (Top Start)", deg: 1605.0, z: 414.71, sFromG0: 0.0, dhFromG0: 0.0 },
  { id: 1, code: "G1", name: "G1 (Turn 1 Front)", deg: 1350.0, z: 358.75, sFromG0: 305.79, dhFromG0: 55.96 },
  { id: 2, code: "G2", name: "G2 (Turn 2 Front)", deg: 990.0, z: 279.75, sFromG0: 837.40, dhFromG0: 134.96 },
  { id: 3, code: "G3", name: "G3 (Turn 3 Front)", deg: 630.0, z: 200.75, sFromG0: 1486.55, dhFromG0: 213.96 },
  { id: 4, code: "G4", name: "G4 (Turn 4 Front)", deg: 270.0, z: 121.75, sFromG0: 2253.58, dhFromG0: 292.96 },
  { id: 5, code: "G5", name: "G5 (Bottom Finish)", deg: 15.0, z: 65.79, sFromG0: 2868.34, dhFromG0: 348.92 },
];
const timingGateActors = [];
const gravLab = {
  startGate: 0,
  endGate: 5,
  kappa: 1.48,
  autoSim: true,
  manualRunning: false,
  manualStartTime: 0,
  trials: [],
};

// Smooth Camera Transition Target
let camAnim = null;

// Subsystem Display Names (Simplified Edition)
const SUBSYSTEM_LABELS = {
  trunk_base: "Trunk Base (N20 Motor & M5Stack ESPHome Hub)",
  trunk_mid: "Trunk Middle (Ball Flute & Cable Slot)",
  trunk_top: "Trunk Top (Upper Discharge Chute)",
  auger_lower: "Auger Lower (Direct Female/Male Hex)",
  auger_upper: "Auger Upper (Hex Coupled)",
  clutch: "Motor_Clutch_Driver (Direct Hex Coupler)",
  brackets: "Cantilever Support Brackets",
  track: "Helical Track Segments (01–14)",
  topper: "Golden Apple Topper (Lantern Shell)",
  planets: "8 Snap-Fit Solar System Planets",
  marbles: "6 Twist-Lock Rolling Apple Marbles (KC012/KC013)",
};

function createMaterial(hexColor, toolhead, opacity = 1.0) {
  const col = new THREE.Color(hexColor);
  let roughness = 0.45;
  let metalness = 0.15;
  if (toolhead === 1) {
    roughness = 0.78;
    metalness = 0.06;
  } else if (toolhead === 2) {
    roughness = 0.22;
    metalness = 0.12;
  } else if (toolhead === 3) {
    roughness = 0.25;
    metalness = 0.65;
  } else if (toolhead === 4) {
    roughness = 0.20;
    metalness = 0.30;
  }
  return new THREE.MeshStandardMaterial({
    color: col,
    roughness,
    metalness,
    transparent: opacity < 0.99,
    opacity,
    side: THREE.DoubleSide,
    clippingPlanes: [clipPlane],
    clipShadows: true,
  });
}

function buildBufferGeometry(buffer, vOffset, vCount, tOffset, tCount) {
  const positions = new Float32Array(buffer, vOffset, vCount * 3);
  const indices = new Uint32Array(buffer, tOffset, tCount * 3);
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geom.setIndex(new THREE.BufferAttribute(indices, 1));
  geom.computeVertexNormals();
  geom.computeBoundingBox();
  geom.computeBoundingSphere();
  return geom;
}

function helixPoint(thetaDeg) {
  const u = thetaDeg / 1620.0;
  const r = 145.0 + (60.0 - 145.0) * u;
  const rad = (thetaDeg * Math.PI) / 180.0;
  const z = 62.5 + 79.0 * (thetaDeg / 360.0);
  return new THREE.Vector3(r * Math.cos(rad), r * Math.sin(rad), z);
}

function closedLoopTrackPoint(thetaDeg) {
  const tBotStart = 14.0;
  if (thetaDeg < tBotStart) {
    const w = Math.min(1.0, Math.max(0.0, (tBotStart - thetaDeg) / (tBotStart + 90.0)));
    const w2 = w * w;
    const w3 = w2 * w;
    const s = (4.0 * w2 + 18.0 * w3) / (1.0 + 4.0 * w2 + 17.0 * w3);
    const rHelix = 145.0 + (60.0 - 145.0) * (thetaDeg / 1620.0);
    const r = rHelix * (1.0 - s) + 42.0 * s;
    const zStart = 62.5 + 79.0 * (tBotStart / 360.0);
    const zEnd = 48.5;
    const omw = 1.0 - w;
    const wZ = 1.62 * w - 0.62 * w2 + 0.72 * w2 * omw * omw;
    const z = zStart - (zStart - zEnd) * wZ;
    const rad = (thetaDeg * Math.PI) / 180.0;
    return new THREE.Vector3(r * Math.cos(rad), r * Math.sin(rad), z);
  }
  if (thetaDeg > 1620.0) {
    const w = Math.min(1.0, Math.max(0.0, (thetaDeg - 1620.0) / 90.0));
    const s = w * w * (3.0 - 2.0 * w);
    const r =
      60.0 +
      (60.0 - 145.0) * ((thetaDeg - 1620.0) / 1620.0) * (1.0 - s) -
      (60.0 - 42.5) * s;
    const z = 418.0 + 7.0 * w;
    const rad = (thetaDeg * Math.PI) / 180.0;
    return new THREE.Vector3(r * Math.cos(rad), r * Math.sin(rad), z);
  }
  return helixPoint(thetaDeg);
}

function closedLoopSectionVectors(thetaDeg) {
  const pt = closedLoopTrackPoint(thetaDeg);
  const rad = (thetaDeg * Math.PI) / 180.0;
  let tx = -Math.sin(rad);
  let ty = Math.cos(rad);
  const tBotStart = 14.0;
  if (thetaDeg < tBotStart || thetaDeg > 1620.0) {
    const eps = 0.25;
    const pPrev = closedLoopTrackPoint(thetaDeg - eps);
    const pNext = closedLoopTrackPoint(thetaDeg + eps);
    const dx = pNext.x - pPrev.x;
    const dy = pNext.y - pPrev.y;
    const lXy = Math.hypot(dx, dy);
    if (lXy > 1e-6) {
      const tcx = dx / lXy;
      const tcy = dy / lXy;
      let blend = 0.0;
      if (thetaDeg < tBotStart) {
        const w = Math.min(1.0, Math.max(0.0, (tBotStart - thetaDeg) / (tBotStart + 90.0)));
        blend = Math.sin(Math.PI * Math.pow(w, 0.75));
      } else {
        const w = Math.min(1.0, Math.max(0.0, (thetaDeg - 1620.0) / 90.0));
        blend = Math.sin(Math.PI * w);
      }
      tx = tx * (1.0 - blend) + tcx * blend;
      ty = ty * (1.0 - blend) + tcy * blend;
      const tLen = Math.max(1e-6, Math.hypot(tx, ty));
      tx /= tLen;
      ty /= tLen;
    }
  }
  // Outward cross-section normal (rx, ry) perpendicular to blended XY tangent (tx, ty)
  const rx = ty;
  const ry = -tx;
  return { pt, tx, ty, rx, ry };
}

function closedLoopLedChannelPoint(thetaDeg, vOff = -10.2, scarfTiltDeg = 15.0) {
  const { pt, tx, ty } = closedLoopSectionVectors(thetaDeg);
  const tiltRad = (scarfTiltDeg * Math.PI) / 180.0;
  const sinTilt = Math.sin(tiltRad);
  const cosTilt = Math.cos(tiltRad);
  return new THREE.Vector3(
    pt.x + vOff * tx * sinTilt,
    pt.y + vOff * ty * sinTilt,
    pt.z + vOff * cosTilt
  );
}

function closedLoopTroughBounds(thetaDeg) {
  let uMin = -2.6;
  let uMax = 3.5;
  // Guide outward along section normal past trunk_top portal corner around 1688°
  if (thetaDeg > 1668.0 && thetaDeg < 1707.0) {
    const w = (thetaDeg - 1668.0) / (1707.0 - 1668.0);
    const uGuide = 2.8 * Math.pow(Math.sin(Math.PI * w), 1.1);
    uMin = Math.max(uMin, uGuide);
  }
  // Keep marble centered along section normal around -72° on Seg 01
  if (thetaDeg > -85.0 && thetaDeg < -55.0) {
    const w = (thetaDeg - -85.0) / 30.0;
    const uGuide = 0.4 * Math.sin(Math.PI * w);
    uMin = Math.max(uMin, uGuide);
  }
  // Cap outward banking across the [-14°, +18°] bend on Seg 01 so both the Ø25mm marble and halo clear the outer wall
  if (thetaDeg > -14.0 && thetaDeg < 18.0) {
    const w = 1.0 - Math.abs(thetaDeg - 2.0) / 16.0;
    uMax = Math.min(uMax, 3.5 - 2.4 * Math.max(0.0, w));
  }
  // Smoothly center at the -90° and 1710° ports
  if (thetaDeg < -84.0) {
    const taper = Math.max(0.0, (thetaDeg + 90.0) / 6.0);
    uMin *= taper;
    uMax *= taper;
  } else if (thetaDeg > 1705.0) {
    const taper = Math.max(0.0, (1710.0 - thetaDeg) / 5.0);
    uMin *= taper;
    uMax *= taper;
  }
  if (uMin > uMax) {
    const mid = 0.5 * (uMin + uMax);
    uMin = mid;
    uMax = mid;
  }
  return { uMin, uMax };
}

function closedLoopMarblePoint(thetaDeg, uBall = 0.0) {
  const { pt, rx, ry } = closedLoopSectionVectors(thetaDeg);
  const { uMin, uMax } = closedLoopTroughBounds(thetaDeg);
  const uEff = Math.min(uMax, Math.max(uMin, uBall));
  const dzEff = 3.5 - Math.sqrt(Math.max(0.0, 12.25 - uEff * uEff));
  return new THREE.Vector3(pt.x + uEff * rx, pt.y + uEff * ry, pt.z + 6.8 + dzEff);
}

// ============================================================================
// 3D CSR Voxel Grid & Exact Ericson Triangle-Mesh Collision Solver (meshes.bin)
// ============================================================================
const PHYS_GRID_MIN_X = -180.0;
const PHYS_GRID_MIN_Y = -180.0;
const PHYS_GRID_MIN_Z = 20.0;
const PHYS_CELL_SIZE = 18.0;
const PHYS_NX = 20;
const PHYS_NY = 20;
const PHYS_NZ = 26;
const PHYS_NUM_CELLS = PHYS_NX * PHYS_NY * PHYS_NZ;

let physTriData = null; // Float32Array(numTris * 12): ax,ay,az, abx,aby,abz, acx,acy,acz, nx,ny,nz
let physTriBounds = null; // Float32Array(numTris * 6): minX,minY,minZ, maxX,maxY,maxZ
let physCellOffset = null; // Int32Array(PHYS_NUM_CELLS + 1)
let physCellTris = null; // Int32Array(totalRefs)
let physTriStamp = null; // Int32Array(numTris)
let physQueryId = 1;
const physCandBuf = new Int32Array(1024);
const _spinAxisTmp = new THREE.Vector3();

function buildPhysicsColliderGrid(arrayBuffer) {
  if (!manifest || !manifest.assembled_meshes) return;
  const colliderMeshes = manifest.assembled_meshes.filter((m) =>
    m.name.startsWith("asm_track_seg_")
  );

  // Pass 1: Count valid active trough & wall triangles
  let validTris = 0;
  for (let mIdx = 0; mIdx < colliderMeshes.length; mIdx++) {
    const item = colliderMeshes[mIdx];
    const verts = new Float32Array(arrayBuffer, item.v_offset, item.v_count * 3);
    const indices = new Uint32Array(arrayBuffer, item.t_offset, item.t_count * 3);
    for (let t = 0; t < item.t_count; t++) {
      const i0 = indices[t * 3] * 3;
      const i1 = indices[t * 3 + 1] * 3;
      const i2 = indices[t * 3 + 2] * 3;
      const abx = verts[i1] - verts[i0];
      const aby = verts[i1 + 1] - verts[i0 + 1];
      const abz = verts[i1 + 2] - verts[i0 + 2];
      const acx = verts[i2] - verts[i0];
      const acy = verts[i2 + 1] - verts[i0 + 1];
      const acz = verts[i2 + 2] - verts[i0 + 2];
      const cx = aby * acz - abz * acy;
      const cy = abz * acx - abx * acz;
      const cz = abx * acy - aby * acx;
      const area2 = Math.hypot(cx, cy, cz);
      if (area2 > 0.15 && cz / area2 >= -0.15) {
        validTris++;
      }
    }
  }

  physTriData = new Float32Array(validTris * 12);
  physTriBounds = new Float32Array(validTris * 6);
  physTriStamp = new Int32Array(validTris);
  const cellCounts = new Int32Array(PHYS_NUM_CELLS);

  // Pass 2: Populate triangle arrays & count voxel cell overlaps
  let tIdx = 0;
  for (let mIdx = 0; mIdx < colliderMeshes.length; mIdx++) {
    const item = colliderMeshes[mIdx];
    const verts = new Float32Array(arrayBuffer, item.v_offset, item.v_count * 3);
    const indices = new Uint32Array(arrayBuffer, item.t_offset, item.t_count * 3);
    for (let t = 0; t < item.t_count; t++) {
      const i0 = indices[t * 3] * 3;
      const i1 = indices[t * 3 + 1] * 3;
      const i2 = indices[t * 3 + 2] * 3;
      const ax = verts[i0],
        ay = verts[i0 + 1],
        az = verts[i0 + 2];
      const bx = verts[i1],
        by = verts[i1 + 1],
        bz = verts[i1 + 2];
      const cx = verts[i2],
        cy = verts[i2 + 1],
        cz = verts[i2 + 2];
      const abx = bx - ax,
        aby = by - ay,
        abz = bz - az;
      const acx = cx - ax,
        acy = cy - ay,
        acz = cz - az;
      const nx = aby * acz - abz * acy;
      const ny = abz * acx - abx * acz;
      const nz = abx * acy - aby * acx;
      const area2 = Math.hypot(nx, ny, nz);
      if (area2 <= 0.15 || nz / area2 < -0.15) continue;

      const invA = 1.0 / area2;
      const base12 = tIdx * 12;
      physTriData[base12] = ax;
      physTriData[base12 + 1] = ay;
      physTriData[base12 + 2] = az;
      physTriData[base12 + 3] = abx;
      physTriData[base12 + 4] = aby;
      physTriData[base12 + 5] = abz;
      physTriData[base12 + 6] = acx;
      physTriData[base12 + 7] = acy;
      physTriData[base12 + 8] = acz;
      physTriData[base12 + 9] = nx * invA;
      physTriData[base12 + 10] = ny * invA;
      physTriData[base12 + 11] = nz * invA;

      const minX = Math.min(ax, bx, cx);
      const minY = Math.min(ay, by, cy);
      const minZ = Math.min(az, bz, cz);
      const maxX = Math.max(ax, bx, cx);
      const maxY = Math.max(ay, by, cy);
      const maxZ = Math.max(az, bz, cz);
      const base6 = tIdx * 6;
      physTriBounds[base6] = minX;
      physTriBounds[base6 + 1] = minY;
      physTriBounds[base6 + 2] = minZ;
      physTriBounds[base6 + 3] = maxX;
      physTriBounds[base6 + 4] = maxY;
      physTriBounds[base6 + 5] = maxZ;

      const ix0 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((minX - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
      const ix1 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((maxX - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
      const iy0 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((minY - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
      const iy1 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((maxY - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
      const iz0 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((minZ - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));
      const iz1 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((maxZ - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));

      for (let iz = iz0; iz <= iz1; iz++) {
        for (let iy = iy0; iy <= iy1; iy++) {
          for (let ix = ix0; ix <= ix1; ix++) {
            cellCounts[(iz * PHYS_NY + iy) * PHYS_NX + ix]++;
          }
        }
      }
      tIdx++;
    }
  }

  // Build CSR offsets
  physCellOffset = new Int32Array(PHYS_NUM_CELLS + 1);
  let running = 0;
  for (let c = 0; c < PHYS_NUM_CELLS; c++) {
    physCellOffset[c] = running;
    running += cellCounts[c];
  }
  physCellOffset[PHYS_NUM_CELLS] = running;
  physCellTris = new Int32Array(running);
  const cellCursor = new Int32Array(physCellOffset);

  // Pass 3: Fill CSR triangle indices
  for (let i = 0; i < validTris; i++) {
    const base6 = i * 6;
    const ix0 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((physTriBounds[base6] - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
    const ix1 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((physTriBounds[base6 + 3] - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
    const iy0 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((physTriBounds[base6 + 1] - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
    const iy1 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((physTriBounds[base6 + 4] - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
    const iz0 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((physTriBounds[base6 + 2] - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));
    const iz1 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((physTriBounds[base6 + 5] - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));
    for (let iz = iz0; iz <= iz1; iz++) {
      for (let iy = iy0; iy <= iy1; iy++) {
        for (let ix = ix0; ix <= ix1; ix++) {
          const cell = (iz * PHYS_NY + iy) * PHYS_NX + ix;
          physCellTris[cellCursor[cell]++] = i;
        }
      }
    }
  }
}

function projectSphereAgainstColliderMesh(pos, radius = 12.5) {
  if (!physTriData || !physCellOffset) return { pushed: 0.0, nx: 0.0, ny: 0.0, nz: 1.0 };
  let px = pos.x,
    py = pos.y,
    pz = pos.z;

  // Enforce smooth cylindrical trunk-collar keep-out at top (1688°) and bottom (-72°) portals
  const rXy = Math.hypot(px, py);
  if (pz > 425.0 && px > -20.0 && px < -5.0 && rXy < 46.3 && rXy > 1e-3) {
    px = (px / rXy) * 46.3;
    py = (py / rXy) * 46.3;
  } else if (pz < 62.5 && px > 4.0 && px < 20.0 && rXy < 43.8 && rXy > 1e-3) {
    px = (px / rXy) * 43.8;
    py = (py / rXy) * 43.8;
  }

  const rPad = radius + 0.4;
  const ix0 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((px - rPad - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
  const ix1 = Math.max(0, Math.min(PHYS_NX - 1, Math.floor((px + rPad - PHYS_GRID_MIN_X) / PHYS_CELL_SIZE)));
  const iy0 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((py - rPad - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
  const iy1 = Math.max(0, Math.min(PHYS_NY - 1, Math.floor((py + rPad - PHYS_GRID_MIN_Y) / PHYS_CELL_SIZE)));
  const iz0 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((pz - rPad - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));
  const iz1 = Math.max(0, Math.min(PHYS_NZ - 1, Math.floor((pz + rPad - PHYS_GRID_MIN_Z) / PHYS_CELL_SIZE)));

  physQueryId = (physQueryId + 1) | 0;
  if (physQueryId <= 0) {
    physTriStamp.fill(0);
    physQueryId = 1;
  }
  const qId = physQueryId;
  let candCount = 0;

  for (let iz = iz0; iz <= iz1; iz++) {
    for (let iy = iy0; iy <= iy1; iy++) {
      for (let ix = ix0; ix <= ix1; ix++) {
        const cell = (iz * PHYS_NY + iy) * PHYS_NX + ix;
        const start = physCellOffset[cell];
        const end = physCellOffset[cell + 1];
        for (let k = start; k < end; k++) {
          const tIdx = physCellTris[k];
          if (physTriStamp[tIdx] === qId) continue;
          physTriStamp[tIdx] = qId;
          const b6 = tIdx * 6;
          if (
            px + rPad >= physTriBounds[b6] &&
            px - rPad <= physTriBounds[b6 + 3] &&
            py + rPad >= physTriBounds[b6 + 1] &&
            py - rPad <= physTriBounds[b6 + 4] &&
            pz + rPad >= physTriBounds[b6 + 2] &&
            pz - rPad <= physTriBounds[b6 + 5]
          ) {
            if (candCount < physCandBuf.length) {
              physCandBuf[candCount++] = tIdx;
            }
          }
        }
      }
    }
  }

  let totalPushed = 0.0;
  let bestNx = 0.0,
    bestNy = 0.0,
    bestNz = 1.0;

  // 4 Gauss-Seidel exact Ericson triangle-projection iterations (guarantees 0.00 mm overlap)
  for (let iter = 0; iter < 4; iter++) {
    let minD = radius;
    let deepNx = 0.0,
      deepNy = 0.0,
      deepNz = 1.0;
    let found = false;

    for (let c = 0; c < candCount; c++) {
      const b12 = physCandBuf[c] * 12;
      const ax = physTriData[b12],
        ay = physTriData[b12 + 1],
        az = physTriData[b12 + 2];
      const abx = physTriData[b12 + 3],
        aby = physTriData[b12 + 4],
        abz = physTriData[b12 + 5];
      const acx = physTriData[b12 + 6],
        acy = physTriData[b12 + 7],
        acz = physTriData[b12 + 8];
      const fnx = physTriData[b12 + 9],
        fny = physTriData[b12 + 10],
        fnz = physTriData[b12 + 11];

      const apx = px - ax,
        apy = py - ay,
        apz = pz - az;
      const d1 = abx * apx + aby * apy + abz * apz;
      const d2 = acx * apx + acy * apy + acz * apz;

      let cx, cy, cz;
      if (d1 <= 0.0 && d2 <= 0.0) {
        cx = ax;
        cy = ay;
        cz = az;
      } else {
        const bx = ax + abx,
          by = ay + aby,
          bz = az + abz;
        const bpx = px - bx,
          bpy = py - by,
          bpz = pz - bz;
        const d3 = abx * bpx + aby * bpy + abz * bpz;
        const d4 = acx * bpx + acy * bpy + acz * bpz;
        if (d3 >= 0.0 && d4 <= d3) {
          cx = bx;
          cy = by;
          cz = bz;
        } else {
          const vc = d1 * d4 - d3 * d2;
          if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
            const v = d1 / (d1 - d3);
            cx = ax + v * abx;
            cy = ay + v * aby;
            cz = az + v * abz;
          } else {
            const ccx = ax + acx,
              ccy = ay + acy,
              ccz = az + acz;
            const cpx = px - ccx,
              cpy = py - ccy,
              cpz = pz - ccz;
            const d5 = abx * cpx + aby * cpy + abz * cpz;
            const d6 = acx * cpx + acy * cpy + acz * cpz;
            if (d6 >= 0.0 && d5 <= d6) {
              cx = ccx;
              cy = ccy;
              cz = ccz;
            } else {
              const vb = d5 * d2 - d1 * d6;
              if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
                const w = d2 / (d2 - d6);
                cx = ax + w * acx;
                cy = ay + w * acy;
                cz = az + w * acz;
              } else {
                const va = d3 * d6 - d5 * d4;
                if (va <= 0.0 && d4 - d3 >= 0.0 && d5 - d6 >= 0.0) {
                  const w = (d4 - d3) / (d4 - d3 + (d5 - d6));
                  cx = bx + w * (ccx - bx);
                  cy = by + w * (ccy - by);
                  cz = bz + w * (ccz - bz);
                } else {
                  const denom = 1.0 / (va + vb + vc);
                  const v = vb * denom;
                  const w = vc * denom;
                  cx = ax + abx * v + acx * w;
                  cy = ay + aby * v + acy * w;
                  cz = az + abz * v + acz * w;
                }
              }
            }
          }
        }
      }

      const dx = px - cx,
        dy = py - cy,
        dz = pz - cz;
      const dist = Math.hypot(dx, dy, dz);
      if (dist < minD && dist > 1e-5 && dx * fnx + dy * fny + dz * fnz > 0.0) {
        minD = dist;
        deepNx = dx / dist;
        deepNy = dy / dist;
        deepNz = dz / dist;
        found = true;
      }
    }

    if (!found) break;
    const pen = radius - minD;
    px += deepNx * pen;
    py += deepNy * pen;
    pz += deepNz * pen;
    totalPushed += pen;
    bestNx = deepNx;
    bestNy = deepNy;
    bestNz = deepNz;
  }

  pos.set(px, py, pz);
  return { pushed: totalPushed, nx: bestNx, ny: bestNy, nz: bestNz };
}

function computeTrackKinematics(thetaDeg) {
  const eps = 0.35;
  const thPlus = Math.min(1710.0, thetaDeg + eps);
  const thMinus = Math.max(-90.0, thetaDeg - eps);
  const dth = Math.max(0.1, thPlus - thMinus);
  const pPlus = closedLoopTrackPoint(thPlus);
  const { pt: pCur, rx: ux, ry: uy } = closedLoopSectionVectors(thetaDeg);
  const pMinus = closedLoopTrackPoint(thMinus);

  // Downhill tangent vector (as theta decreases from thPlus to thMinus)
  const dx = pMinus.x - pPlus.x;
  const dy = pMinus.y - pPlus.y;
  const dz = pMinus.z - pPlus.z;
  const ds = Math.max(0.01, Math.hypot(dx, dy, dz));
  const dsDtheta = ds / dth; // mm per degree

  const sinAlpha = Math.max(0.0, -dz / ds);
  const cosAlpha = Math.sqrt(Math.max(0.01, 1.0 - sinAlpha * sinAlpha));

  // Horizontal curvature from 3 points (pPlus, pCur, pMinus)
  const ux1 = pCur.x - pPlus.x;
  const uy1 = pCur.y - pPlus.y;
  const ux2 = pMinus.x - pCur.x;
  const uy2 = pMinus.y - pCur.y;
  const l1 = Math.max(0.001, Math.hypot(ux1, uy1));
  const l2 = Math.max(0.001, Math.hypot(ux2, uy2));
  const crossZ = Math.abs(ux1 * uy2 - uy1 * ux2);
  const dPsi = Math.asin(Math.min(1.0, crossZ / (l1 * l2)));
  const dsHoriz = 0.5 * (l1 + l2);
  const rCurv = dPsi > 1e-5 ? Math.max(35.0, dsHoriz / dPsi) : 1000.0;

  return { pCur, dsDtheta, sinAlpha, cosAlpha, rCurv, ux, uy };
}

async function init() {
  const canvas = document.getElementById("three-canvas");
  const viewport = canvas.parentElement;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x090d16);

  camera = new THREE.PerspectiveCamera(
    42,
    viewport.clientWidth / viewport.clientHeight,
    1.0,
    4000.0
  );
  camera.up.set(0, 0, 1);
  const isPortrait = viewport.clientWidth / Math.max(1, viewport.clientHeight) < 0.85;
  if (isPortrait) {
    camera.position.set(540, -560, 410);
  } else {
    camera.position.set(420, -430, 340);
  }

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = false;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 220.0);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0, 225);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.maxDistance = 1800;
  controls.minDistance = 40;
  controls.update();

  // Studio + Dynamic Lighting (switched dynamically between "warm" Lamp Kit 001, "studio" CAD Studio Daylight & High-Contrast Plate Inspector)
  ambientLight = new THREE.AmbientLight(0x93c5fd, 0.42);
  scene.add(ambientLight);

  hemiLight = new THREE.HemisphereLight(0xf8fafc, 0x94a3b8, 0.25);
  hemiLight.position.set(0, 0, 650);
  scene.add(hemiLight);

  keyLight = new THREE.DirectionalLight(0xffe4b5, 0.88);
  keyLight.position.set(350, -420, 620);
  scene.add(keyLight);

  fillLight = new THREE.DirectionalLight(0x60a5fa, 0.38);
  fillLight.position.set(-380, 320, 280);
  scene.add(fillLight);

  rimLight = new THREE.DirectionalLight(0xfbbf24, 0.60);
  rimLight.position.set(0, 420, 500);
  scene.add(rimLight);

  // Dedicated High-Contrast Build Plate Inspection Directional Lights
  plateInspectLight = new THREE.DirectionalLight(0xffffff, 0.0);
  plateInspectLight.position.set(-280, -390, 560);
  scene.add(plateInspectLight);

  plateBackLight = new THREE.DirectionalLight(0xe2e8f0, 0.0);
  plateBackLight.position.set(320, 380, 440);
  scene.add(plateBackLight);

  // Topper Lamp Puck 001 PointLight + 4 Track Accent PointLights
  lampPuckLight = new THREE.PointLight(0xff9e2c, 3.8, 320);
  lampPuckLight.position.set(0, 0, 492);
  scene.add(lampPuckLight);

  const rgbAngles = [240, 660, 1080, 1440];
  rgbAngles.forEach((deg, idx) => {
    const pt = helixPoint(deg);
    const pLight = new THREE.PointLight(0x00ffaa, 1.1, 190);
    pLight.position.copy(pt);
    scene.add(pLight);
    rgbLights.push({ light: pLight, baseHue: idx / rgbAngles.length });
  });

  // Scene Groups
  assembledRoot = new THREE.Group();
  electronicsGroup = new THREE.Group();
  guideLinesGroup = new THREE.Group();
  trackJointsGroup = new THREE.Group();
  platesRoot = new THREE.Group();
  platesRoot.visible = false;
  bedGridGroup = new THREE.Group();

  scene.add(assembledRoot);
  scene.add(electronicsGroup);
  scene.add(guideLinesGroup);
  scene.add(trackJointsGroup);
  scene.add(platesRoot);
  scene.add(bedGridGroup);

  buildReferenceBedGrid();

  // Fetch Manifest & Binary Mesh Bundle
  const progBar = document.getElementById("loading-progress-bar");
  const statusEl = document.getElementById("loading-status");

  statusEl.textContent = "Fetching CAD scene manifest...";
  progBar.style.width = "25%";
  const manifestResp = await fetch("assets/manifest.json?v=44", { cache: "no-store" });
  manifest = await manifestResp.json();

  statusEl.textContent = "Downloading B-Rep binary mesh buffer...";
  progBar.style.width = "55%";
  const binResp = await fetch(`${manifest.binary_file}?v=44`, { cache: "no-store" });
  const arrayBuffer = await binResp.arrayBuffer();

  statusEl.textContent = "Constructing Three.js WebGL geometries & physics actors...";
  progBar.style.width = "85%";

  buildAssembledScene(arrayBuffer);
  buildHardwareOverlay();
  buildTrackJointVisualizer();
  buildPlatesScene(arrayBuffer);
  initMarblesSimulation();
  initUI();

  progBar.style.width = "100%";
  setTimeout(() => {
    document.getElementById("loading-overlay").classList.add("fade-out");
  }, 220);

  window.addEventListener("resize", onWindowResize);
  if (typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => onWindowResize());
    ro.observe(viewport);
  }
  setupRaycasterTooltip();

  let lastTime = performance.now();
  function animate(now) {
    requestAnimationFrame(animate);
    const dt = Math.min(0.05, (now - lastTime) / 1000.0);
    lastTime = now;
    state.clockTime += dt;

    updateSimulation(dt);
    updateCameraTransition(dt);
    controls.update();
    renderer.render(scene, camera);
  }
  requestAnimationFrame(animate);
}

function buildReferenceBedGrid() {
  const ringGeom = new THREE.RingGeometry(158, 162, 64);
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0xd4af37,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.32,
  });
  const ring = new THREE.Mesh(ringGeom, ringMat);
  ring.position.z = -0.5;
  bedGridGroup.add(ring);

  const grid = new THREE.GridHelper(340, 17, 0x334155, 0x1e293b);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.8;
  bedGridGroup.add(grid);
}

function attachAssemblyActor(actor, mesh, mat, meta, parentGroup) {
  const basePos = actor.position.clone();
  const explodeVec = new THREE.Vector3(...(meta.explode || [0, 0, 0]));
  const insertVec = new THREE.Vector3(...(meta.insert_offset || [0, 0, 45]));

  actor.userData = {
    ...meta,
    mesh,
    material: mat,
    basePos,
    explodeVec,
    insertVec,
    baseOpacity: meta.opacity !== undefined ? meta.opacity : 1.0,
    cutaway_candidate: meta.cutaway_candidate || meta.subsystem === "planets",
  };
  mesh.userData = actor.userData;

  parentGroup.add(actor);
  assembledMeshes.push(actor);
  if (meta.kinematic_group === "magic_wand") {
    magicWandActors.push(actor);
  }

  // Create dashed gold 3D connection & explosion guide line
  if (explodeVec.lengthSq() > 1.0 || insertVec.lengthSq() > 1.0) {
    if (!mesh.geometry.boundingBox) {
      mesh.geometry.computeBoundingBox();
    }
    const bboxCenter = new THREE.Vector3();
    mesh.geometry.boundingBox.getCenter(bboxCenter);
    bboxCenter.add(basePos);

    const lineGeom = new THREE.BufferGeometry().setFromPoints([
      bboxCenter.clone(),
      bboxCenter.clone(),
    ]);
    const lineMat = new THREE.LineDashedMaterial({
      color: meta.isElectronic ? 0x38bdf8 : 0xd4af37,
      dashSize: 4,
      gapSize: 3,
      transparent: true,
      opacity: 0.75,
    });
    const line = new THREE.Line(lineGeom, lineMat);
    line.computeLineDistances();
    line.visible = false;
    guideLinesGroup.add(line);
    actor.userData.guideLine = line;
    actor.userData.guideOrigin = bboxCenter;
  }
}

function buildAssembledScene(arrayBuffer) {
  let marbleTemplateGeom = null;

  manifest.assembled_meshes.forEach((item) => {
    const geom = buildBufferGeometry(
      arrayBuffer,
      item.v_offset,
      item.v_count,
      item.t_offset,
      item.t_count
    );

    if (item.name === "asm_apple_marble_template") {
      marbleTemplateGeom = geom;
      return;
    }

    const subsys = item.subsystem || "misc";
    if (!(subsys in subsystemVisibility)) {
      subsystemVisibility[subsys] = true;
    }

    const mat = createMaterial(item.color, item.toolhead, item.opacity || 1.0);
    const mesh = new THREE.Mesh(geom, mat);
    mesh.name = item.name;

    let actor = mesh;
    if (item.pivot) {
      const [px, py, pz] = item.pivot;
      geom.translate(-px, -py, -pz);
      geom.computeBoundingBox();
      const pivotGroup = new THREE.Group();
      pivotGroup.position.set(px, py, pz);
      pivotGroup.add(mesh);
      actor = pivotGroup;
    }

    attachAssemblyActor(actor, mesh, mat, item, assembledRoot);
    if (subsys === "topper" && item.toolhead === 4) {
      topperShellActors.push(actor);
    }
  });

  // Soft warm crimson-amber lantern glow halo around the thin-walled (~2.2 mm) hollow Golden Apple Topper
  const tHaloGeom = new THREE.SphereGeometry(45.5, 28, 20);
  topperHaloMat = new THREE.MeshBasicMaterial({
    color: 0xff4518,
    transparent: true,
    opacity: 0.24,
    depthWrite: false,
  });
  topperHaloMesh = new THREE.Mesh(tHaloGeom, topperHaloMat);
  topperHaloMesh.position.set(0, 0, 492);
  topperHaloMesh.userData = {
    label: "Golden Apple Topper (#4) — Contoured ~2.2 mm Thin-Walled Hollow Lantern Shell Illuminated by Internal LED Puck",
    subsystem: "topper",
  };
  assembledRoot.add(topperHaloMesh);

  // Create 6 dynamic Glowing Snap-Fit Apple Marbles (Ø 25.0 mm with internal Bambu Magnetic Switch LED + M8 Steel Weight Ring)
  if (!marbleTemplateGeom) {
    marbleTemplateGeom = new THREE.SphereGeometry(12.5, 28, 20);
  }
  subsystemVisibility.marbles = true;

  const mLedGeom = new THREE.CylinderGeometry(3.75, 3.75, 6.0, 18);
  mLedGeom.rotateX(Math.PI / 2);
  const mNutGeom = new THREE.CylinderGeometry(7.2, 7.2, 6.2, 6);
  mNutGeom.rotateX(Math.PI / 2);
  const mHaloGeom = new THREE.SphereGeometry(14.6, 18, 14);

  for (let i = 0; i < 6; i++) {
    const mGroup = new THREE.Group();
    const mMat = createMaterial("#C41E3A", 4, 0.86);
    mMat.emissive.setHex(0xff3355);
    mMat.emissiveIntensity = 0.65;
    const outerMesh = new THREE.Mesh(marbleTemplateGeom, mMat);
    mGroup.add(outerMesh);

    // Internal Bambu Magnetic Switch LED (Ø 7.5 x 6.0 mm) glowing in center
    const ledMat = new THREE.MeshStandardMaterial({
      color: 0xfef08a,
      emissive: 0xfbbf24,
      emissiveIntensity: 2.2,
      roughness: 0.15,
    });
    const ledCoreMesh = new THREE.Mesh(mLedGeom, ledMat);
    mGroup.add(ledCoreMesh);

    // Internal M8 Steel Hex Nut Weight Ring surrounding the LED
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0xcbd5e1,
      metalness: 0.92,
      roughness: 0.18,
    });
    const coreMesh = new THREE.Mesh(mNutGeom, coreMat);
    mGroup.add(coreMesh);

    // Outer warm crimson-gold glow halo so each marble visibly radiates all the way up & down the tree
    const haloMat = new THREE.MeshBasicMaterial({
      color: 0xff4d6d,
      transparent: true,
      opacity: 0.24,
      depthWrite: false,
    });
    const haloMesh = new THREE.Mesh(mHaloGeom, haloMat);
    mGroup.add(haloMesh);

    const mLabel = `Glowing Apple Marble #${i + 1} (Quarter-Turn Twist-Lock Hemispheres A+B + Bambu KC012/KC013 Y-Shape 3-LED — Click to Tap with Wand!)`;
    outerMesh.userData = {
      label: mLabel,
      subsystem: "marbles",
      marble_idx: i,
    };
    haloMesh.userData = outerMesh.userData;

    assembledRoot.add(mGroup);
    dynamicMarbles.push({
      index: i,
      group: mGroup,
      outerMesh,
      coreMesh,
      ledCoreMesh,
      ledMat,
      haloMesh,
      haloMat,
      material: mMat,
      ledMode: 1, // 1 = STEADY GLOW
      phaseOffset: i * 1.05,
      phase: i < 2 ? "auger" : "track",
      flightIndex: i === 0 ? 1 : 5,
      z: i === 0 ? 138.42 : 322.42,
      theta: 1580.0 - (i - 2) * 390.0,
      uLat: 0.0,
      vuLat: 0.0,
      impactFlash: 0.0,
      chuteU: 0.0,
      speedMmS: i < 2 ? 0.0 : 340.0 + (i - 2) * 85.0,
      bankDeg: 0.0,
      marginMm: 11.4,
      isQueued: false,
      step: 12,
      subDelay: i * 0.22,
      animDur: 0.55,
      label: `Glowing Apple Marble #${i + 1} (Quarter-Turn Twist-Lock + KC012/KC013 Y-Shape 3-LED)`,
    });
  }

  // Build 3D CSR Voxel Grid over the actual CAD triangle meshes for zero-penetration solid physics
  buildPhysicsColliderGrid(arrayBuffer);
}

function buildHardwareOverlay() {
  const addElectronicActor = (geom, matOptions, pos, meta) => {
    const mat = new THREE.MeshStandardMaterial({
      roughness: 0.35,
      metalness: 0.45,
      transparent: true,
      opacity: meta.opacity !== undefined ? meta.opacity : 0.92,
      ...matOptions,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(pos[0], pos[1], pos[2]);
    attachAssemblyActor(
      mesh,
      mesh,
      mat,
      {
        isElectronic: true,
        subsystem: meta.subsystem || "trunk_base",
        ...meta,
      },
      electronicsGroup
    );
    return mesh;
  };

  // 1. Step 1b: N20 Gear Motor in Trunk_Base (0, 0, 0.2..25.7) -> clamps into M5Stack A092 M1/M2 Screw Terminals
  addElectronicActor(
    new THREE.BoxGeometry(12.0, 10.0, 25.5),
    { color: 0x94a3b8, metalness: 0.7, roughness: 0.25 },
    [0, 0, 12.95],
    {
      name: "hw_LA002_N20_Motor",
      label: "12V 150rpm N20 Gear Motor (Option B drop-in on A092 M1/M2; or 6V LA002 with Option A 12V→6V Buck + H-Bridge)",
      subsystem: "trunk_base",
      step: 1,
      sub_delay: 0.70,
      anim_dur: 0.70,
      insert_offset: [0, 0, -60],
      explode: [0, 0, -115],
    }
  );

  // 2. Step 2a: M5Stack Atomic H-Bridge Driver Base (A092 DRV8876) + ATOM Lite ESP32 (C008) in -Y Base Bay
  addElectronicActor(
    new THREE.BoxGeometry(48.0, 24.0, 12.0),
    { color: 0x10b981, metalness: 0.45, roughness: 0.3 },
    [0, -33.0, 11.5],
    {
      name: "hw_M5Stack_ESPHome_Controller",
      label: "M5Stack Atomic H-Bridge Driver Base (A092 DRV8876 — Fed by 12V VIN/GND via 2A Fuse F1; powers C008 & M1/M2 Motor)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.0,
      anim_dur: 0.65,
      insert_offset: [0, -30, -48],
      explode: [0, -75, -105],
    }
  );

  // 2b. M5Stack ATOM Lite ESP32 (C008, 24x24x10mm White Enclosure) snapped onto A092 + Dedicated Rear Bay Option
  addElectronicActor(
    new THREE.BoxGeometry(24.0, 24.0, 9.6),
    { color: 0xf8fafc, metalness: 0.15, roughness: 0.25 },
    [-12.0, -33.0, 5.2],
    {
      name: "hw_M5Stack_ATOM_Lite_C008",
      label: "M5Stack ATOM Lite ESP32 (C008 — Powered internally from A092 12V→5V buck; Grove Port carries White GPIO26 & Yellow GPIO32 Data)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.25,
      anim_dur: 0.65,
      insert_offset: [-12, -30, -56],
      explode: [-25, -85, -115],
    }
  );

  // 2c. M5Stack A096 Grove2Dupont 4-Wire Breakout Plug (Black=GND, Red=5V CAPPED, White=GPIO26, Yellow=GPIO32)
  addElectronicActor(
    new THREE.BoxGeometry(10.5, 8.0, 5.5),
    { color: 0xfef08a, emissive: 0xeab308, emissiveIntensity: 0.45 },
    [6.5, -33.0, 5.2],
    {
      name: "hw_A096_Grove2Dupont_Hub",
      label: "M5Stack A096 Grove2Dupont Cable (White=GPIO26 Track Data, Yellow=GPIO32 Topper Data, Black=GND; Red=+5V CAPPED for rail isolation)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.50,
      anim_dur: 0.65,
      insert_offset: [18, -35, -42],
      explode: [32, -80, -100],
    }
  );

  // 2d. Dedicated 12V -> 5.0V 5A UCTRONICS Screw-Terminal Buck Converter (63.0x27.0x10.0mm) in +Y Vault Cradle
  addElectronicActor(
    new THREE.BoxGeometry(63.0, 27.0, 10.0),
    { color: 0x2563eb, metalness: 0.4, roughness: 0.35 },
    [-4.0, 36.5, 5.0],
    {
      name: "hw_5V_Buck_Converter_UCTRONICS",
      label: "UCTRONICS 12V→5.0V 5A (25W) Screw-Terminal Buck Converter (B07XXWQ49N / U6223, 63×27×10mm — Powers 50 Track LEDs + 16 Topper LEDs via 3A Fuse F2)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.35,
      anim_dur: 0.65,
      insert_offset: [-4, 36, -48],
      explode: [-10, 75, -95],
    }
  );

  // 2e. 2x Stacked WAGO 221-415 5-Port Lever-Nut Blocks (18.6x30.0x16.8mm) in +X Vault Organizer Cradle
  addElectronicActor(
    new THREE.BoxGeometry(18.6, 30.0, 16.8),
    { color: 0xf97316, metalness: 0.25, roughness: 0.35 },
    [44.5, -12.0, 8.4],
    {
      name: "hw_5V_Buck_Converter_WAGO",
      label: "WAGO 221-415 Lever-Nut Distribution Stack (B07NKT2P2F, 30.0×18.6×8.4mm each — Zero-solder +12V, +5V LED & Star GND buses)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.42,
      anim_dur: 0.65,
      insert_offset: [44, -12, -48],
      explode: [78, -22, -95],
    }
  );

  // 3. Step 2b: Motor-to-A092 Wire (M1/M2 Screw Terminals) + Single External 12V DC Barrel Jack & Cord (Rear -X Port)
  const motorWireGeom = new THREE.CylinderGeometry(1.3, 1.3, 30.0, 10);
  addElectronicActor(
    motorWireGeom,
    { color: 0xfbbf24, emissive: 0xd97706, emissiveIntensity: 0.4 },
    [0, -16.5, 6.0],
    {
      name: "hw_Motor_M1_M2_Wire",
      label: "N20 Motor Lead (Routes through bottom shroud notch into M5Stack A092 M1 & M2 Screw Terminals)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.70,
      anim_dur: 0.65,
      insert_offset: [0, -35, -28],
      explode: [0, -55, -95],
    }
  );

  const dcPts = [
    new THREE.Vector3(-48.0, 0.0, 10.0),
    new THREE.Vector3(-68.0, 0.0, 10.0),
    new THREE.Vector3(-98.0, 0.0, 4.0),
  ];
  const dcGeom = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(dcPts), 24, 2.2, 10, false);
  addElectronicActor(
    dcGeom,
    { color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.5 },
    [0, 0, 0],
    {
      name: "hw_12V_DC_Barrel_Power_Cable",
      label: "Single 12V DC External Power Cord & Rear J1 Panel Barrel Jack (-X Port at Z=10mm — Powers A092, C008, N20 Motor & 5V LED Buck!)",
      subsystem: "trunk_base",
      step: 2,
      sub_delay: 0.70,
      anim_dur: 0.65,
      insert_offset: [-40, 0, -18],
      explode: [-85, 0, -65],
    }
  );

  // 4. Step 8a: BTF-LIGHTING DC5V WS2812B Pebble Wire Starter Feed Pocket (10.0 x 16.0 mm) in track_seg_01 at theta = -70°
  const pcbPt = closedLoopLedChannelPoint(-70.0, -10.2, 0.0);
  const pcbPrev = closedLoopLedChannelPoint(-71.0, -10.2, 0.0);
  const pcbNext = closedLoopLedChannelPoint(-69.0, -10.2, 0.0);
  const pcbGeom = new THREE.BoxGeometry(13.0, 8.5, 2.8);
  pcbGeom.rotateZ(Math.atan2(pcbNext.y - pcbPrev.y, pcbNext.x - pcbPrev.x));
  addElectronicActor(
    pcbGeom,
    { color: 0xf59e0b, emissive: 0xd97706, emissiveIntensity: 0.5 },
    [pcbPt.x, pcbPt.y, pcbPt.z],
    {
      name: "hw_COB_PCB_Terminal",
      label: "BTF-LIGHTING DC5V WS2812B Pebble Wire Starter Head (B0CCS11V7H — Seats into 10.0×16.0 mm Starter Feed Pocket Under track_seg_01)",
      subsystem: "track",
      step: 8,
      sub_delay: 0.0,
      anim_dur: 0.60,
      insert_offset: [0, -28, -32],
      explode: [0, -85, -45],
    }
  );

  // 5. Step 8b: Full-Length BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Flexible Wire (B0CCS11V7H, 50 LEDs) snapped into 8.0x3.6 mm Dovetail Channel
  const cobPts = [];
  for (let deg = -70.0; deg <= 1702.0; deg += 2.0) {
    cobPts.push(closedLoopLedChannelPoint(deg, -9.8, 15.0));
  }
  const cobCurve = new THREE.CatmullRomCurve3(cobPts);
  const cobGeom = new THREE.TubeGeometry(cobCurve, 360, 1.35, 8, false);
  const cobVertCount = cobGeom.attributes.position.count;
  const cobColors = new Float32Array(cobVertCount * 3);
  for (let i = 0; i <= 360; i++) {
    _rgbTmpColor.setHSL((i / 90.0) % 1.0, 1.0, 0.56);
    for (let j = 0; j <= 8; j++) {
      const idx = (i * 9 + j) * 3;
      cobColors[idx] = _rgbTmpColor.r;
      cobColors[idx + 1] = _rgbTmpColor.g;
      cobColors[idx + 2] = _rgbTmpColor.b;
    }
  }
  cobColorAttr = new THREE.BufferAttribute(cobColors, 3);
  cobGeom.setAttribute("color", cobColorAttr);

  const cobStripMesh = addElectronicActor(
    cobGeom,
    {
      color: 0xffffff,
      roughness: 0.15,
      opacity: 0.98,
    },
    [0, 0, 0],
    {
      name: "hw_COB_LED_Strip_Full",
      label: "BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Flexible Wire (B0CCS11V7H, 50 RGB LEDs — Snaps into 8.0×3.6 mm Dovetail Channel Under Track Seg 01→14)",
      subsystem: "track",
      step: 8,
      sub_delay: 0.60,
      anim_dur: 0.85,
      insert_offset: [0, 0, -28],
      explode: [0, 0, -42],
    }
  );
  cobStripMat = new THREE.MeshBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.98,
  });
  cobStripMesh.material = cobStripMat;
  cobStripMesh.userData.material = cobStripMat;

  // Add 50 oval encapsulated WS2812B Pebble LED drops along the flexible wire
  const pebbleGeom = new THREE.SphereGeometry(2.9, 14, 10);
  pebbleGeom.scale(1.05, 1.05, 0.62);
  const pebbleMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  pebbleInstancedMesh = new THREE.InstancedMesh(pebbleGeom, pebbleMat, 50);
  const dummyObj = new THREE.Object3D();
  for (let k = 0; k < 50; k++) {
    const u = (k + 0.5) / 50.0;
    const p = cobCurve.getPointAt(u);
    dummyObj.position.copy(p);
    dummyObj.updateMatrix();
    pebbleInstancedMesh.setMatrixAt(k, dummyObj.matrix);
    _rgbTmpColor.setHSL((u * 4.0) % 1.0, 1.0, 0.6);
    pebbleInstancedMesh.setColorAt(k, _rgbTmpColor);
  }
  pebbleInstancedMesh.instanceMatrix.needsUpdate = true;
  if (pebbleInstancedMesh.instanceColor) {
    pebbleInstancedMesh.instanceColor.needsUpdate = true;
  }
  pebbleInstancedMesh.userData = cobStripMesh.userData;
  cobStripMesh.add(pebbleInstancedMesh);

  // 6. Step 8c: M5Stack A096 Grove2Dupont Cable connecting BTF-LIGHTING Strip through cob_wire_conduit -> M5Stack Atom Grove Port (GPIO26)
  const cobWireGeom = new THREE.CylinderGeometry(1.35, 1.35, 31.0, 10);
  cobWireGeom.rotateX(Math.PI / 2);
  addElectronicActor(
    cobWireGeom,
    { color: 0xfef08a, emissive: 0xfbbf24, emissiveIntensity: 1.1 },
    [16.5, -27.5, 23.5],
    {
      name: "hw_COB_Conduit_Wire",
      label: "M5Stack A096 Grove2Dupont Cable (Routes through Trunk_Base cob_wire_conduit to M5Stack Atom Grove Port: 5V, GND, GPIO26)",
      subsystem: "track",
      step: 8,
      sub_delay: 1.45,
      anim_dur: 0.65,
      insert_offset: [22, -22, 26],
      explode: [55, -65, -30],
    }
  );

  // Distribute addressable RGB glow lights along the full height of the under-track spiral
  [120.0, 540.0, 960.0, 1380.0].forEach((deg) => {
    const lPt = closedLoopTrackPoint(deg);
    const cLight = new THREE.PointLight(0xff0080, 1.8, 145, 0.0);
    cLight.position.set(lPt.x, lPt.y, lPt.z - 12.0);
    scene.add(cLight);
    cobLights.push(cLight);
  });

  // 7. Step 9a: 3-Pin JST-SM Extension Cable (B0CT827QQC) inside Rear -X Trunk Groove (X = -32.2, Y = 0, Z = 8..449 mm) -> M5Stack Grove GPIO32
  const cordGeom = new THREE.CylinderGeometry(1.6, 1.6, 441.0, 12);
  cordGeom.rotateX(Math.PI / 2);
  addElectronicActor(
    cordGeom,
    { color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.45 },
    [-32.2, 0, 228.5],
    {
      name: "hw_Topper_Rear_Cable",
      label: "3-Pin JST-SM Extension Cable (B0CT827QQC — Pressed into Rear -X Trunk Groove from Topper Ring down to M5Stack Grove GPIO32)",
      subsystem: "topper",
      step: 9,
      sub_delay: 0.0,
      anim_dur: 0.65,
      insert_offset: [-55, 0, 0],
      explode: [-95, 0, 40],
    }
  );

  // 8. Step 9b: Sparkleiot 16-Bit WS2812 RGB LED Ring (B09YTMNGTD, Ø45mm OD / Ø32mm ID) seated on Trunk_Top at Z = 448.5 mm
  const puckGeom = new THREE.TorusGeometry(19.25, 3.25, 16, 48);
  const puckVertCount = puckGeom.attributes.position.count;
  const puckColors = new Float32Array(puckVertCount * 3);
  for (let j = 0; j <= 16; j++) {
    for (let i = 0; i <= 48; i++) {
      _rgbTmpColor.setHSL((i / 48.0) % 1.0, 1.0, 0.56);
      const idx = (j * 49 + i) * 3;
      puckColors[idx] = _rgbTmpColor.r;
      puckColors[idx + 1] = _rgbTmpColor.g;
      puckColors[idx + 2] = _rgbTmpColor.b;
    }
  }
  puckColorAttr = new THREE.BufferAttribute(puckColors, 3);
  puckGeom.setAttribute("color", puckColorAttr);

  const puckMesh = addElectronicActor(
    puckGeom,
    { color: 0xffffff, roughness: 0.2 },
    [0, 0, 449.0],
    {
      name: "hw_Topper_LED_Puck",
      label: "Sparkleiot 16-Bit WS2812 RGB LED Ring (B09YTMNGTD, Ø45mm — Seats in Ø46.2mm Rim Recess of Trunk_Top at Z = 447.5 mm, 12 mm Above Marble Chute)",
      subsystem: "topper",
      step: 9,
      sub_delay: 0.55,
      anim_dur: 0.65,
      insert_offset: [0, 0, 65],
      explode: [0, 0, 145],
    }
  );
  topperPuckMat = new THREE.MeshBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.98,
  });
  puckMesh.material = topperPuckMat;
  puckMesh.userData.material = topperPuckMat;

  // 10. Step 10: 8x Bambu Lab Single LED Magnetic Control Switch Lights (ordered #8 Neptune -> #1 Mercury)
  const planetSpecs = [
    { key: "planet_neptune", name: "Neptune (#8)", deg: 60.0, color: 0x60a5fa, order: 0 },
    { key: "planet_uranus", name: "Uranus (#7)", deg: 300.0, color: 0x2dd4bf, order: 1 },
    { key: "planet_saturn", name: "Saturn (#6)", deg: 540.0, color: 0xfacc15, order: 2 },
    { key: "planet_jupiter", name: "Jupiter (#5)", deg: 660.0, color: 0xfdba74, order: 3 },
    { key: "planet_mars", name: "Mars (#4)", deg: 900.0, color: 0xf87171, order: 4 },
    { key: "planet_earth", name: "Earth (#3)", deg: 1140.0, color: 0x38bdf8, order: 5 },
    { key: "planet_venus", name: "Venus (#2)", deg: 1380.0, color: 0xfde047, order: 6 },
    { key: "planet_mercury", name: "Mercury (#1)", deg: 1590.0, color: 0xfbbf24, order: 7 },
  ];
  const ledCylGeom = new THREE.CylinderGeometry(3.75, 3.75, 6.0, 18);
  ledCylGeom.rotateX(Math.PI / 2);

  planetSpecs.forEach((ps, idx) => {
    const pt = helixPoint(ps.deg);
    const rad = (ps.deg * Math.PI) / 180.0;
    const px = pt.x + 30.0 * Math.cos(rad);
    const py = pt.y + 30.0 * Math.sin(rad);
    const pz = pt.z + 18.05 + 6.6; // Center of Z = 3.6..9.6 mm chamber inside planet

    const ledSubDelay = Number((ps.order * 0.25).toFixed(3));
    const ledMesh = addElectronicActor(
      ledCylGeom,
      {
        color: ps.color,
        emissive: ps.color,
        emissiveIntensity: 1.2,
        roughness: 0.2,
      },
      [px, py, pz],
      {
        name: `hw_led_${ps.key}`,
        label: `Wireless Magnetic Switch LED (Ø7.5×6.0 mm — Inserts into bottom bore of ${ps.name})`,
        planet_id: ps.key,
        subsystem: "planets",
        step: 10,
        sub_delay: ledSubDelay,
        anim_dur: 0.45,
        insert_offset: [
          Number((28.0 * Math.cos(rad)).toFixed(2)),
          Number((28.0 * Math.sin(rad)).toFixed(2)),
          -18.0,
        ],
        explode: [165.0 * Math.cos(rad), 165.0 * Math.sin(rad), 10.0],
      }
    );

    const pLight = new THREE.PointLight(ps.color, 2.8, 95, 0.0);
    pLight.position.set(px, py, pz + 4.0);
    scene.add(pLight);

    // Translucent outer glow halo so each lit planet visibly radiates in 3D view
    const haloGeom = new THREE.SphereGeometry(13.5, 20, 16);
    const haloMat = new THREE.MeshBasicMaterial({
      color: ps.color,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });
    const haloMesh = new THREE.Mesh(haloGeom, haloMat);
    haloMesh.position.set(px, py, pz + 2.5);
    haloMesh.userData = {
      label: `${ps.name} — Illuminated by Internal Bambu Magnetic Switch LED (Click to Tap with Wand!)`,
      planet_id: ps.key,
    };
    assembledRoot.add(haloMesh);

    const matchingMeshes = assembledMeshes.filter(
      (a) => a.userData && a.userData.planet_id === ps.key && !a.userData.isElectronic
    );

    planetLedActors.push({
      key: ps.key,
      name: ps.name,
      deg: ps.deg,
      subDelay: ledSubDelay + 0.08,
      animDur: 0.50,
      pos: new THREE.Vector3(px, py, pz + 3.0),
      color: ps.color,
      mesh: ledMesh,
      material: ledMesh.userData.material,
      haloMesh,
      haloMat,
      planetActors: matchingMeshes,
      light: pLight,
      mode: 1, // 1 = STEADY GLOW
      phaseOffset: idx * 0.8,
    });
  });

  // 11. 6x Galileo-Newton Gravity Chronometer Timing Gate Beacons (G0..G5) on Outer Track Rail
  const gateBeaconGeom = new THREE.BoxGeometry(3.6, 5.2, 8.5);
  TIMING_GATES.forEach((tg) => {
    const pt = helixPoint(tg.deg);
    const rad = (tg.deg * Math.PI) / 180.0;
    const gx = pt.x + 21.2 * Math.cos(rad);
    const gy = pt.y + 21.2 * Math.sin(rad);
    const gz = pt.z + 15.5;
    const gMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      emissive: 0xd4af37,
      emissiveIntensity: 0.35,
      metalness: 0.65,
      roughness: 0.25,
    });
    const gMesh = new THREE.Mesh(gateBeaconGeom, gMat);
    gMesh.position.set(gx, gy, gz);
    gMesh.rotation.z = rad;
    gMesh.userData = {
      label: `Gravity Timing Gate ${tg.code} — θ=${tg.deg}°, Rolled Arc s=${tg.sFromG0.toFixed(1)} mm, Drop Δh=${tg.dhFromG0.toFixed(1)} mm (+ 0.35 mm Phyphox Acoustic Click Rib)`,
      subsystem: "track",
    };
    assembledRoot.add(gMesh);
    timingGateActors.push({
      ...tg,
      mesh: gMesh,
      material: gMat,
      flashTimer: 0.0,
    });
  });
}

// Detailed Track-to-Track & Trunk Port Connection Metadata for Step 7 (Pieces 0..14)
const TRACK_PIECE_SPECS = [
  {
    pieceIdx: 0,
    segNum: 1,
    actorName: "asm_track_seg_01",
    chipLabel: "🟢 01 [Start]",
    chipClass: "special-first",
    title: "Seg 01 — Bottom Return Ramp & Trunk Base Intake Port (FIRST PIECE)",
    spanBadge: "θ = -90° → 120° | Z = 50.0 → 63.8 mm",
    camPos: [-125, -210, 108],
    camLook: [12, -35, 56],
    portRow: {
      tag: "🟢 START PORT (-90°)",
      html: "<strong>How Seg 01 Connects to Trunk Base (#1):</strong> From <code>θ = 0°</code> down to <code>-90°</code>, Seg 01 curves smoothly inward from <code>R = 145.0 mm</code> to <code>R = 42.0 mm</code> at the <code>-Y</code> front face of <code>trunk_base</code>. Its inner rail (<code>R = 34.25 mm</code>) hugs the <code>R = 34.0 mm</code> trunk cylinder with a tight <strong><code>0.25 mm</code> radial gap</strong>, while its high wrap-around <strong><code>bot_endcap_wall</code> bumper</strong> stops every marble and funnels it <code>+Y</code> inward (<code>Z = 56.8 → 54.5 mm</code>, a <code>-2.3 mm</code> downhill drop) straight into the Archimedes auger flute!",
    },
    downhillHtml:
      "<strong>Bottom Intake Chute (<code>θ = -90°</code>):</strong> Seats flush against <code>trunk_base</code>'s <code>-Y</code> bottom intake window. Houses the <code>10×16 mm</code> BTF-LIGHTING LED starter feed pocket underneath at <code>θ = -70°</code> and Timing Gate <code>G5</code> at <code>15°</code>.",
    bracketHtml:
      "<strong>2× Tier 4 Cantilever Brackets (<code>#4</code>):</strong> Underside <code>Ø4.40 mm</code> socket holes snap onto the <strong><code>θ = 60°</code> (<code>Z = 50.6 mm</code>)</strong> midpoint bracket pegs (plus Neptune <code>#8</code> balcony) AND the <strong><code>θ = 120°</code> (<code>Z = 63.8 mm</code>)</strong> seam bracket pegs.",
    uphillHtml:
      "<strong>Uphill 15° Scarf Joint (<code>θ = 120° → Seg 02</code>):</strong> Presents <strong>Twin <code>Ø3.80×5.0 mm</code> Male Snap-Lock Tenon Pegs</strong> (at <code>u = ±14.2 mm, v = -4.2 mm</code> with <code>Ø4.08 mm</code> detent beads) + <strong>Inner/Outer Sidewall Tongues</strong> pointing uphill to receive <strong>Seg 02</strong>.",
  },
  {
    pieceIdx: 1,
    segNum: 2,
    actorName: "asm_track_seg_02",
    chipLabel: "Seg 02",
    chipClass: "",
    title: "Seg 02 — Lower Helical Track (Clicks onto Seg 01 at 120°)",
    spanBadge: "θ = 120° → 240° | Z = 63.8 → 90.2 mm",
    camPos: [-225, 130, 132],
    camLook: [-65, 38, 72],
    downhillHtml:
      "<strong>Downhill 15° Scarf Joint (<code>θ = 120° ← Seg 01</code>):</strong> Slide Seg 02 downhill along the <code>15°</code> scarf angle so its <strong>Twin <code>Ø4.30×5.6 mm</code> Female Snap-Lock Sockets + Sidewall Slots</strong> click directly onto <strong>Seg 01's Twin Male Tenon Pegs + Tongues</strong>.",
    bracketHtml:
      "<strong>3× Tier 4 Bracket Stations (<code>#4</code>):</strong> Shares the <strong><code>120°</code> seam bracket</strong> with Seg 01, snaps onto the <strong><code>180°</code> (<code>Z = 77.0 mm</code>) midpoint bracket</strong>, and seats onto the <strong><code>240°</code> (<code>Z = 90.2 mm</code>) seam bracket</strong>.",
    uphillHtml:
      "<strong>Uphill 15° Scarf Joint (<code>θ = 240° → Seg 03</code>):</strong> Exposes <strong>Twin <code>Ø3.80×5.0 mm</code> Male Snap-Lock Tenon Pegs + Sidewall Tongues</strong> at <code>240°</code> ready for <strong>Seg 03</strong>.",
  },
  {
    pieceIdx: 2,
    segNum: 0,
    actorName: "asm_Track_Joint_Clip",
    chipLabel: "📎 Clip",
    chipClass: "",
    title: "Track_Joint_Clip — Under-Seam U-Cradle Splice Clamp (120° Demo & Retrofit)",
    spanBadge: "θ = 120° Seam | 16 mm Span",
    camPos: [-195, 115, 108],
    camLook: [-68, 40, 62],
    downhillHtml:
      "<strong>Snap-On U-Cradle Splice Clamp:</strong> Bridges <code>16 mm</code> across the underside and outer sidewalls of any track-to-track scarf joint (shown at the <code>120°</code> seam between <strong>Seg 01</strong> and <strong>Seg 02</strong>).",
    bracketHtml:
      "<strong>Open LED Dovetail Arch:</strong> Central <code>10.8×4.2 mm</code> underside arch keeps the continuous <code>8.0×3.6 mm</code> BTF-LIGHTING Pebble Wire channel <strong>100% unobstructed</strong> across the seam.",
    uphillHtml:
      "<strong>Retrofits Older Prints:</strong> If you printed an earlier track revision without male tenon pegs, push two <code>11 mm</code> snippets of raw <code>1.75 mm</code> filament into the <code>Ø2.20 mm</code> dowel holes and snap this clip underneath!",
  },
];

// Dynamically populate Seg 03 .. Seg 13 specs
const SEG_EXTRAS = {
  3: "Houses <strong>Uranus (#7)</strong> balcony peg at <code>300°</code> &amp; Gravity Timing Gate <strong><code>G4</code></strong> at <code>270°</code>.",
  4: "Smooth 120° helical arc completing Turn 1.33 above the lower trunk.",
  5: "Houses <strong>Saturn (#6)</strong> ringed planet balcony peg at <code>540°</code>.",
  6: "Houses <strong>Jupiter (#5)</strong> balcony peg at <code>660°</code> &amp; Gravity Timing Gate <strong><code>G3</code></strong> at <code>630°</code>.",
  7: "Smooth 120° mid-tree helical arc transitioning from Tier 3 to Tier 2 brackets.",
  8: "Houses <strong>Mars (#4)</strong> red planet balcony peg at <code>900°</code>.",
  9: "Houses front-spine Gravity Timing Gate <strong><code>G2</code></strong> at <code>990°</code>.",
  10: "Houses <strong>Earth (#3)</strong> balcony peg at <code>1140°</code>.",
  11: "Smooth 120° upper-mid helical arc entering Tier 1 upper brackets.",
  12: "Houses <strong>Venus (#2)</strong> balcony peg at <code>1380°</code> &amp; Gravity Timing Gate <strong><code>G1</code></strong> at <code>1350°</code>.",
  13: "Final standard helical segment (<code>1440° → 1560°</code>); presents the uphill <code>1560°</code> male tenons that anchor <strong>Seg 14 (Top Entry)</strong>!",
};

for (let k = 3; k <= 13; k++) {
  const thStart = (k - 1) * 120;
  const thMid = thStart + 60;
  const thEnd = k * 120;
  const ptStart = helixPoint(thStart);
  const ptEnd = helixPoint(thEnd);
  const radSeam = (thStart * Math.PI) / 180.0;
  const tierNum = thMid <= 360 ? 4 : thMid <= 720 ? 3 : thMid <= 1080 ? 2 : 1;
  TRACK_PIECE_SPECS.push({
    pieceIdx: k,
    segNum: k,
    actorName: `asm_track_seg_${String(k).padStart(2, "0")}`,
    chipLabel: `Seg ${String(k).padStart(2, "0")}`,
    chipClass: "",
    title: `Seg ${String(k).padStart(2, "0")} — Clicks onto Seg ${String(k - 1).padStart(2, "0")} at ${thStart}° → Feeds Seg ${String(k + 1).padStart(2, "0")} at ${thEnd}°`,
    spanBadge: `θ = ${thStart}° → ${thEnd}° | Z = ${ptStart.z.toFixed(1)} → ${ptEnd.z.toFixed(1)} mm`,
    camPos: [
      Math.round(ptStart.x + 155 * Math.cos(radSeam - 0.38)),
      Math.round(ptStart.y + 155 * Math.sin(radSeam - 0.38)),
      Math.round(ptStart.z + 65),
    ],
    camLook: [
      Math.round(ptStart.x * 0.82),
      Math.round(ptStart.y * 0.82),
      Math.round(ptStart.z + 8),
    ],
    downhillHtml: `<strong>Downhill 15° Scarf Joint (<code>θ = ${thStart}° ← Seg ${String(k - 1).padStart(2, "0")}</code>):</strong> Slide <strong>Seg ${String(k).padStart(2, "0")}</strong> downhill along the <code>15°</code> scarf angle so its <strong>Twin <code>Ø4.30×5.6 mm</code> Female Snap-Lock Sockets + Sidewall Slots</strong> click onto <strong>Seg ${String(k - 1).padStart(2, "0")}'s Twin <code>Ø3.80 mm</code> Male Tenon Pegs + Tongues</strong>.`,
    bracketHtml: `<strong>Tier #${tierNum} Cantilever Brackets:</strong> Underside <code>Ø4.40 mm</code> sockets seat onto the <strong><code>${thStart}°</code> seam bracket</strong>, snap onto the <strong><code>${thMid}°</code> (<code>Z = ${(0.5 * (ptStart.z + ptEnd.z)).toFixed(1)} mm</code>) midpoint bracket</strong>, and rest on the <strong><code>${thEnd}°</code> seam bracket</strong>. ${SEG_EXTRAS[k] || ""}`,
    uphillHtml: `<strong>Uphill 15° Scarf Joint (<code>θ = ${thEnd}° → Seg ${String(k + 1).padStart(2, "0")}</code>):</strong> Presents <strong>Twin <code>Ø3.80×5.0 mm</code> Male Snap-Lock Tenon Pegs</strong> (<code>u = ±14.2 mm, v = -4.2 mm</code>) + <strong>Inner/Outer Sidewall Tongues</strong> pointing uphill to receive <strong>Seg ${String(k + 1).padStart(2, "0")}</strong>.`,
  });
}

// Piece 14: Seg 14 (Last Segment — Top Entry Catch Basin & Trunk Top Discharge Spout)
TRACK_PIECE_SPECS.push({
  pieceIdx: 14,
  segNum: 14,
  actorName: "asm_track_seg_14",
  chipLabel: "🔴 14 [End]",
  chipClass: "special-last",
  title: "Seg 14 — Top Entry Catch Basin & Trunk Top Discharge Spout (LAST PIECE)",
  spanBadge: "θ = 1560° → 1710° | Z = 404.8 → 425.0 mm",
  camPos: [135, -205, 468],
  camLook: [6, -32, 422],
  portRow: {
    tag: "🔴 END PORT (1710° / -90°)",
    html: "<strong>How Seg 14 Connects to Trunk Top (#3):</strong> From <code>θ = 1620°</code> to <code>1710°</code> (<code>-90°</code>), Seg 14 curves inward from <code>R = 60.0 mm</code> to <code>R = 42.5 mm</code> at the <code>-Y</code> front face of <code>trunk_top</code>. Its inner rail (<code>R = 34.25 mm</code> collar) hugs <code>trunk_top</code>'s <code>R = 34.0 mm</code> cylinder (<code>0.25 mm</code> gap) directly underneath the sloped <code>-Y</code> <strong>Upper Discharge Spout (<code>Z = 435.5 → 431.8 mm</code>)</strong>, while its high wrap-around <strong><code>top_endcap_wall</code> upstream bumper</strong> catches every marble ejected by the auger!",
  },
  downhillHtml:
    "<strong>Downhill 15° Scarf Joint (<code>θ = 1560° ← Seg 13</code>):</strong> Slide <strong>Seg 14</strong> downhill along the <code>15°</code> scarf joint so its <strong>Twin <code>Ø4.30×5.6 mm</code> Female Snap-Lock Sockets + Sidewall Slots</strong> click onto <strong>Seg 13's Twin <code>Ø3.80 mm</code> Male Tenon Pegs + Tongues</strong>.",
  bracketHtml:
    "<strong>2× Tier 1 Top Brackets (<code>#1</code>):</strong> Underside <code>Ø4.40 mm</code> sockets snap onto the <strong><code>1560°</code> (<code>Z = 404.8 mm</code>) seam bracket</strong> AND the topmost <strong><code>1620°</code> (<code>Z = 418.0 mm</code>) cantilever bracket</strong>. Houses <strong>Mercury (#1)</strong> at <code>1590°</code> &amp; Start Timing Gate <strong><code>G0</code></strong> at <code>1605°</code>.",
  uphillHtml:
    "<strong>Enclosed Upper Catch Basin (<code>θ = 1710° ← Trunk Top Spout</code>):</strong> Marbles exiting the auger drop <code>-3.7 mm</code> onto Seg 14's trough floor (<code>Z_marble = 431.4 mm</code>) and immediately accelerate downhill toward Seg 13.",
});

function buildTrackJointVisualizer() {
  if (!trackJointsGroup) return;

  const tenonGeom = new THREE.CylinderGeometry(1.9, 1.9, 6.2, 14);
  tenonGeom.rotateX(Math.PI / 2);
  const beadGeom = new THREE.SphereGeometry(2.15, 12, 10);
  const tongueGeom = new THREE.BoxGeometry(1.8, 5.2, 3.6);
  const seamRingGeom = new THREE.TorusGeometry(16.0, 0.85, 12, 32);
  const arrowShaftGeom = new THREE.CylinderGeometry(0.85, 0.85, 14.0, 10);
  const arrowHeadGeom = new THREE.ConeGeometry(2.4, 5.5, 12);

  // 1. Marker 0: START PORT — Seg 01 (-90° Inward Return Chute) <-> Trunk_Base -Y Intake Window
  const startPortGroup = new THREE.Group();
  const startRingMat = new THREE.MeshStandardMaterial({
    color: 0x10b981,
    emissive: 0x059669,
    emissiveIntensity: 1.35,
    roughness: 0.2,
    metalness: 0.5,
  });
  const startRing = new THREE.Mesh(new THREE.TorusGeometry(13.8, 1.15, 14, 36), startRingMat);
  startRing.position.set(0.0, -34.5, 56.2);
  startRing.rotation.x = Math.PI / 2;
  startPortGroup.add(startRing);

  // Curved Marble Intake Flow Path Arrow: (-90° chute at Y=-42.0, Z=56.8 -> Auger Flute at Y=-17.5, Z=54.5)
  const intakeCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(18.0, -54.0, 58.5),
    new THREE.Vector3(0.0, -42.0, 56.8),
    new THREE.Vector3(0.0, -24.0, 55.0),
  ]);
  const intakeTube = new THREE.Mesh(
    new THREE.TubeGeometry(intakeCurve, 20, 1.25, 10, false),
    startRingMat
  );
  startPortGroup.add(intakeTube);

  const intakeCone = new THREE.Mesh(new THREE.ConeGeometry(3.1, 7.0, 14), startRingMat);
  intakeCone.position.set(0.0, -19.5, 54.6);
  intakeCone.rotation.z = 0; // Points +Y into trunk_base auger flute!
  startPortGroup.add(intakeCone);

  const startLabel =
    "START PORT (θ = -90°, Z = 56.8 → 54.5 mm) — Seg 01's inward return chute (R = 34.25 mm) hugs Trunk_Base (R = 34.0 mm) with a 0.25 mm gap; bot_endcap_wall funnels marbles +Y into the Archimedes auger flute!";
  startPortGroup.traverse((c) => {
    c.userData = { label: startLabel, track_piece_idx: 0 };
  });
  trackJointsGroup.add(startPortGroup);
  trackJointMarkers.push({
    type: "start-port",
    pieceIdx: 0,
    segA: 0,
    segB: 1,
    group: startPortGroup,
    mat: startRingMat,
    center: new THREE.Vector3(0, -34.5, 56.2),
  });

  // 2. Markers 1..13: All 13 Track-to-Track 15° Scarf Joints (120°, 240°, ..., 1560°)
  for (let k = 1; k <= 13; k++) {
    const seamDeg = k * 120.0;
    const rad = (seamDeg * Math.PI) / 180.0;
    const pt = helixPoint(seamDeg);
    const rHat = new THREE.Vector3(Math.cos(rad), Math.sin(rad), 0.0);
    const tHat = new THREE.Vector3(-Math.sin(rad), Math.cos(rad), 0.118).normalize();
    const zHat = new THREE.Vector3(0, 0, 1);

    const seamGroup = new THREE.Group();
    const seamMat = new THREE.MeshStandardMaterial({
      color: 0xfbbf24,
      emissive: 0xd97706,
      emissiveIntensity: 0.95,
      roughness: 0.22,
      metalness: 0.6,
    });
    const tenonMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 1.25,
      roughness: 0.18,
      metalness: 0.45,
    });

    // Orient a local sub-frame at pt aligned with (rHat, tHat, zHat)
    const basisMat = new THREE.Matrix4().makeBasis(rHat, tHat, zHat);
    const localFrame = new THREE.Group();
    localFrame.position.copy(pt);
    localFrame.quaternion.setFromRotationMatrix(basisMat);

    // Scarf seam collar ring around track cross-section
    const ringMesh = new THREE.Mesh(seamRingGeom, seamMat);
    ringMesh.rotation.x = Math.PI / 2;
    ringMesh.position.set(0, 0, 2.5);
    localFrame.add(ringMesh);

    // Twin Ø3.80 x 5.0 mm Male Snap-Lock Tenon Pegs at u = ±14.2 mm, v = -4.2 mm
    [-14.2, 14.2].forEach((uOff) => {
      const pegMesh = new THREE.Mesh(tenonGeom, tenonMat);
      pegMesh.position.set(uOff, 2.4, -4.2);
      localFrame.add(pegMesh);

      const beadMesh = new THREE.Mesh(beadGeom, tenonMat);
      beadMesh.position.set(uOff, 5.1, -4.2);
      localFrame.add(beadMesh);
    });

    // Twin Inner/Outer Sidewall Anti-Torsion Tongues at u = ±13.6 mm, v = +6.2 mm
    [-13.6, 13.6].forEach((uOff) => {
      const tMesh = new THREE.Mesh(tongueGeom, seamMat);
      tMesh.position.set(uOff, 2.0, 6.2);
      localFrame.add(tMesh);
    });

    // Downhill 15° Slide-In Direction Arrow above the seam (shows Seg k+1 sliding -tHat into Seg k)
    const shaftMesh = new THREE.Mesh(arrowShaftGeom, seamMat);
    shaftMesh.position.set(0, 8.5, 19.5);
    localFrame.add(shaftMesh);

    const headMesh = new THREE.Mesh(arrowHeadGeom, seamMat);
    headMesh.position.set(0, 0.5, 19.5);
    headMesh.rotation.z = Math.PI; // Points -Y in localFrame (-tHat downhill into Seg k)
    localFrame.add(headMesh);

    seamGroup.add(localFrame);
    const nextPieceIdx = k === 1 ? 1 : k + 1;
    const seamLabel = `Track Seam #${k} (θ = ${seamDeg}°, Z = ${pt.z.toFixed(1)} mm): Seg ${String(k + 1).padStart(2, "0")}'s Twin Ø4.30mm Female Sockets + Sidewall Slots slide downhill onto Seg ${String(k).padStart(2, "0")}'s Twin Ø3.80mm Male Snap-Lock Tenon Pegs (cyan) + Sidewall Tongues (gold) & ${seamDeg}° Bracket Pegs!`;
    seamGroup.traverse((c) => {
      c.userData = { label: seamLabel, track_piece_idx: nextPieceIdx };
    });
    trackJointsGroup.add(seamGroup);
    trackJointMarkers.push({
      type: "seam",
      seamIndex: k,
      pieceIdx: nextPieceIdx,
      segA: k,
      segB: k + 1,
      group: seamGroup,
      mat: seamMat,
      tenonMat,
      center: pt.clone(),
    });
  }

  // 3. Marker 14: END PORT — Trunk_Top -Y Upper Discharge Spout (Z=435.5->431.8mm) <-> Seg 14 Catch Basin (1710°)
  const endPortGroup = new THREE.Group();
  const endRingMat = new THREE.MeshStandardMaterial({
    color: 0xf43f5e,
    emissive: 0xe11d48,
    emissiveIntensity: 1.4,
    roughness: 0.2,
    metalness: 0.5,
  });
  const endRing = new THREE.Mesh(new THREE.TorusGeometry(14.2, 1.2, 14, 36), endRingMat);
  endRing.position.set(0.0, -34.5, 433.2);
  endRing.rotation.x = Math.PI / 2;
  endPortGroup.add(endRing);

  // Curved Marble Ejection Path Arrow: (Auger Top at Y=-17.5, Z=435.5 -> Seg 14 Catch Basin at Y=-42.5, Z=431.4 -> Rolling toward 1620°)
  const spoutCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.0, -17.5, 435.5),
    new THREE.Vector3(0.0, -42.5, 431.4),
    new THREE.Vector3(-22.0, -44.0, 428.0),
  ]);
  const spoutTube = new THREE.Mesh(
    new THREE.TubeGeometry(spoutCurve, 20, 1.25, 10, false),
    endRingMat
  );
  endPortGroup.add(spoutTube);

  const spoutCone = new THREE.Mesh(new THREE.ConeGeometry(3.1, 7.0, 14), endRingMat);
  spoutCone.position.set(-25.5, -43.5, 427.2);
  spoutCone.rotation.z = Math.PI / 2.2;
  endPortGroup.add(spoutCone);

  const endLabel =
    "END PORT (θ = 1710° / -90°, Z = 435.5 → 431.4 mm) — Seg 14's enclosed upper catch basin (R = 34.25 mm) & top_endcap_wall bumper hug Trunk_Top (R = 34.0 mm) right under the -Y Upper Discharge Spout to catch every ejected marble!";
  endPortGroup.traverse((c) => {
    c.userData = { label: endLabel, track_piece_idx: 14 };
  });
  trackJointsGroup.add(endPortGroup);
  trackJointMarkers.push({
    type: "end-port",
    pieceIdx: 14,
    segA: 14,
    segB: 15,
    group: endPortGroup,
    mat: endRingMat,
    center: new THREE.Vector3(0, -34.5, 433.2),
  });
}

function buildPlatesScene(arrayBuffer) {
  manifest.plates.forEach((plate, pIdx) => {
    const pGroup = new THREE.Group();
    pGroup.name = plate.id;

    // 270 x 270 mm Snapmaker U1 Heated PEI Bed (High-Contrast Studio Slate Finish)
    const bedGeom = new THREE.PlaneGeometry(270, 270);
    const bedMat = new THREE.MeshStandardMaterial({
      color: 0x26354d,
      roughness: 0.52,
      metalness: 0.18,
      side: THREE.DoubleSide,
    });
    const bedMesh = new THREE.Mesh(bedGeom, bedMat);
    bedMesh.position.z = -0.25;
    pGroup.add(bedMesh);

    // Subtle 16 mm calibration grid inside the 256 x 256 mm safe zone for clear scale & socket inspection
    const plateGrid = new THREE.GridHelper(256, 16, 0x475569, 0x334155);
    plateGrid.rotation.x = Math.PI / 2;
    plateGrid.position.z = -0.08;
    pGroup.add(plateGrid);

    const safeEdges = new THREE.EdgesGeometry(new THREE.PlaneGeometry(256, 256));
    const safeLine = new THREE.LineSegments(
      safeEdges,
      new THREE.LineBasicMaterial({ color: 0x34d399 })
    );
    safeLine.position.z = 0.05;
    pGroup.add(safeLine);

    plate.meshes.forEach((m) => {
      const geom = buildBufferGeometry(
        arrayBuffer,
        m.v_offset,
        m.v_count,
        m.t_offset,
        m.t_count
      );
      // Use authentic toolhead material properties with crisp specular response
      const colorUpper = (m.color || "").toUpperCase();
      const th =
        colorUpper === "#4A2F1D"
          ? 1
          : colorUpper === "#00A86B"
          ? 2
          : colorUpper === "#C41E3A"
          ? 4
          : 3;
      const mat = createMaterial(m.color, th, 1.0);
      if (th === 1) {
        // Slightly lower roughness on matte wood brown in Plate Inspector so layer details & sockets pop cleanly
        mat.roughness = 0.52;
        mat.metalness = 0.12;
      }
      const mesh = new THREE.Mesh(geom, mat);
      mesh.userData = { label: `${m.name} (${plate.title})` };
      pGroup.add(mesh);
    });

    pGroup.visible = pIdx === 0;
    platesRoot.add(pGroup);
    plateGroups.push(pGroup);
  });
}

function initMarblesSimulation() {
  updateSimulation(0.016);
}

function recordGravityTrial(dtSec, sourceLabel = "3D Sim") {
  if (!Number.isFinite(dtSec) || dtSec <= 0.05) return;
  gravLab.trials.push({ dt: dtSec, source: sourceLabel });
  if (gravLab.trials.length > 50) {
    gravLab.trials.shift();
  }
  updateGravityLabUI();
}

function updateGravityLabUI() {
  const gA = TIMING_GATES[gravLab.startGate] || TIMING_GATES[0];
  const gB = TIMING_GATES[gravLab.endGate] || TIMING_GATES[5];
  const dsMm = Math.max(1.0, gB.sFromG0 - gA.sFromG0);
  const dhMm = Math.max(1.0, gA.dhFromG0 > gB.dhFromG0 ? gA.dhFromG0 - gB.dhFromG0 : gB.dhFromG0 - gA.dhFromG0);
  const spanEl = document.getElementById("lbl-grav-span");
  if (spanEl) {
    spanEl.textContent = `Δs = ${dsMm.toFixed(0)} mm | Δh = ${dhMm.toFixed(0)} mm`;
  }

  const n = gravLab.trials.length;
  const elTrials = document.getElementById("stat-grav-trials");
  const elTime = document.getElementById("stat-grav-time");
  const elG = document.getElementById("stat-grav-g");
  const elDetail = document.getElementById("lbl-grav-detail");

  if (elTrials) elTrials.textContent = String(n);
  if (n === 0) {
    if (elTime) elTime.textContent = "—";
    if (elG) elG.textContent = "9.81 m/s²";
    if (elDetail) {
      elDetail.innerHTML = `Waiting for marble to cross <strong>${gA.code} → ${gB.code}</strong> (or click <em>Tap Start Gate</em> to time your physical print)...`;
    }
    return;
  }

  const sumT = gravLab.trials.reduce((acc, item) => acc + item.dt, 0.0);
  const meanT = sumT / n;
  const varianceT =
    n > 1
      ? gravLab.trials.reduce((acc, item) => acc + Math.pow(item.dt - meanT, 2), 0.0) / (n - 1)
      : 0.0;
  const stdT = Math.sqrt(varianceT);

  // Universal 2-Gate Galilean Inclined-Spiral Estimator (converted from mm/s² to m/s²):
  // g_hat = [2 * kappa * ds * (sqrt(sB) - sqrt(sA))^2 / (dh * meanT^2)] / 1000
  const sqrtDiffSq = Math.pow(Math.sqrt(gB.sFromG0) - Math.sqrt(gA.sFromG0), 2);
  const gHat =
    (2.0 * gravLab.kappa * dsMm * sqrtDiffSq) / (dhMm * meanT * meanT * 1000.0);
  const errPct = ((gHat - 9.80665) / 9.80665) * 100.0;
  const lastTrial = gravLab.trials[n - 1];

  if (elTime) {
    elTime.textContent = n > 1 ? `${meanT.toFixed(2)}s ±${stdT.toFixed(2)}` : `${meanT.toFixed(2)}s`;
  }
  if (elG) {
    elG.textContent = `${gHat.toFixed(2)} m/s²`;
  }
  if (elDetail) {
    const signStr = errPct >= 0 ? `+${errPct.toFixed(2)}%` : `${errPct.toFixed(2)}%`;
    elDetail.innerHTML = `<strong>${gA.code} → ${gB.code}</strong> (${lastTrial.source} last: <code>${lastTrial.dt.toFixed(2)}s</code>) &bull; Mean Roll Speed: <code>${(dsMm / meanT).toFixed(0)} mm/s</code> &bull; Error vs 9.81 m/s²: <strong>${signStr}</strong>`;
  }
}

function getStepSubGroups(stepNum) {
  const buckets = new Map();
  if (stepNum === 12) {
    dynamicMarbles.forEach((m, idx) => {
      const key = m.subDelay.toFixed(2);
      buckets.set(key, {
        subDelay: m.subDelay,
        animDur: m.animDur,
        endTime: m.subDelay + m.animDur,
        label: m.label || `Rolling Apple Marble #${idx + 1}`,
      });
    });
  } else {
    assembledMeshes.forEach((actor) => {
      const ud = actor.userData;
      if ((ud.step || 1) !== stepNum) return;
      const sd = ud.sub_delay || 0.0;
      const ad = ud.anim_dur || 0.65;
      const key = sd.toFixed(2);
      if (!buckets.has(key)) {
        buckets.set(key, {
          subDelay: sd,
          animDur: ad,
          endTime: sd + ad,
          label: ud.label || ud.name || "Part",
        });
      }
    });
  }
  const sorted = Array.from(buckets.values()).sort((a, b) => a.subDelay - b.subDelay);
  if (sorted.length === 0) {
    sorted.push({ subDelay: 0.0, animDur: 0.65, endTime: 0.65, label: "Step Component" });
  }
  return sorted;
}

function updateTrackInspectorUI(pieceIdx = state.activeTrackPieceIdx) {
  const boxEl = document.getElementById("track-inspector-box");
  if (!boxEl) return;

  // Show the Track Segment Connection Inspector prominently in Step 7
  const showBox = state.mode === "assembly" && state.asmCurrentStep === 7;
  boxEl.classList.toggle("hidden", !showBox);
  if (!showBox) return;

  const clampedIdx = Math.max(0, Math.min(TRACK_PIECE_SPECS.length - 1, pieceIdx));
  const spec = TRACK_PIECE_SPECS[clampedIdx] || TRACK_PIECE_SPECS[0];
  const groups = getStepSubGroups(7);

  // Update 15 segment chip states
  document.querySelectorAll(".track-seg-chip").forEach((chip) => {
    const idx = Number(chip.dataset.pieceIdx);
    const g = groups[idx];
    const isConnected = g && state.stepAnimElapsed >= g.endTime - 0.02;
    chip.classList.toggle("active", idx === clampedIdx);
    chip.classList.toggle("connected", idx !== clampedIdx && isConnected);
  });

  // Highlight active port focus button if matching
  const btnS01Port = document.getElementById("btn-focus-seg01-port");
  const btnS01Seam = document.getElementById("btn-focus-seg01-seam");
  const btnS14Seam = document.getElementById("btn-focus-seg14-seam");
  const btnS14Port = document.getElementById("btn-focus-seg14-port");
  if (btnS01Port) btnS01Port.classList.toggle("active", state.focusedPortMode === "start-port" || (clampedIdx === 0 && !state.focusedPortMode));
  if (btnS01Seam) btnS01Seam.classList.toggle("active", state.focusedPortMode === "first-seam" || (clampedIdx === 1 && !state.focusedPortMode));
  if (btnS14Seam) btnS14Seam.classList.toggle("active", state.focusedPortMode === "last-seam");
  if (btnS14Port) btnS14Port.classList.toggle("active", state.focusedPortMode === "end-port" || (clampedIdx === 14 && !state.focusedPortMode));

  const cardEl = document.getElementById("track-joint-detail-card");
  if (cardEl && spec) {
    const portRowHtml = spec.portRow
      ? `<div class="tj-row">
           <span class="tj-tag port">${spec.portRow.tag}</span>
           <div class="tj-text">${spec.portRow.html}</div>
         </div>`
      : "";
    cardEl.innerHTML = `
      <div class="tj-card-head">
        <strong>${spec.title}</strong>
        <span class="tj-span-badge">${spec.spanBadge}</span>
      </div>
      <div class="tj-rows">
        ${portRowHtml}
        <div class="tj-row">
          <span class="tj-tag downhill">⬇ DOWNHILL</span>
          <div class="tj-text">${spec.downhillHtml}</div>
        </div>
        <div class="tj-row">
          <span class="tj-tag bracket">🌿 BRACKETS</span>
          <div class="tj-text">${spec.bracketHtml}</div>
        </div>
        <div class="tj-row">
          <span class="tj-tag uphill">⬆ UPHILL</span>
          <div class="tj-text">${spec.uphillHtml}</div>
        </div>
      </div>
    `;
  }
}

function selectTrackPieceInStep7(pieceIdx, customCam = null) {
  if (state.mode !== "assembly") {
    switchMode("assembly");
  }
  if (state.asmCurrentStep !== 7) {
    setAssemblyStep(7, false);
  }
  const groups = getStepSubGroups(7);
  const clampedIdx = Math.max(0, Math.min(groups.length - 1, pieceIdx));
  const targetG = groups[clampedIdx];
  state.activeTrackPieceIdx = clampedIdx;
  state.stepAnimElapsed = targetG.subDelay;
  state.stepTargetMaxTime = targetG.endTime;

  const spec = TRACK_PIECE_SPECS[clampedIdx];
  if (customCam) {
    camAnim = {
      targetPos: new THREE.Vector3(...customCam.pos),
      targetLook: new THREE.Vector3(...customCam.look),
      timeLeft: 0.7,
    };
  } else if (state.trackAutoCam && spec && spec.camPos && spec.camLook) {
    camAnim = {
      targetPos: new THREE.Vector3(...spec.camPos),
      targetLook: new THREE.Vector3(...spec.camLook),
      timeLeft: 0.7,
    };
  }

  applyExplodeAndVisibility();
  updatePieceConnectionUI();
  updateTrackInspectorUI(clampedIdx);
}

function updatePieceConnectionUI() {
  if (state.mode !== "assembly") return;
  const groups = getStepSubGroups(state.asmCurrentStep);
  const totalPieces = groups.length;
  const maxStepTime = groups[totalPieces - 1].endTime;
  const elapsed = state.stepAnimElapsed;

  let activeIdx = 0;
  for (let i = 0; i < totalPieces; i++) {
    if (elapsed >= groups[i].subDelay - 0.005) {
      activeIdx = i;
    }
  }

  if (state.asmCurrentStep === 7 && activeIdx !== state.activeTrackPieceIdx) {
    state.activeTrackPieceIdx = activeIdx;
    state.focusedPortMode = null;
    if (state.trackAutoCam) {
      const spec = TRACK_PIECE_SPECS[activeIdx];
      if (spec && spec.camPos && spec.camLook) {
        camAnim = {
          targetPos: new THREE.Vector3(...spec.camPos),
          targetLook: new THREE.Vector3(...spec.camLook),
          timeLeft: 0.6,
        };
      }
    }
    updateTrackInspectorUI(activeIdx);
  }

  const curGroup = groups[activeIdx];
  const allDone = elapsed >= maxStepTime - 0.01;
  const counterEl = document.getElementById("lbl-piece-counter");
  const activeEl = document.getElementById("lbl-piece-active");
  const fillEl = document.getElementById("asm-piece-progress-fill");

  if (counterEl) {
    counterEl.textContent = allDone
      ? `✔ ${totalPieces} / ${totalPieces} Connected`
      : `Piece ${activeIdx + 1} / ${totalPieces}`;
  }
  if (activeEl) {
    const cleanName = curGroup.label.split("(")[0].trim();
    activeEl.textContent = allDone
      ? `Step ${state.asmCurrentStep} Complete — Click Next Step ▶`
      : `Connecting: ${cleanName}`;
  }
  if (fillEl) {
    const pct = Math.min(100, Math.max(0, (elapsed / Math.max(0.1, maxStepTime)) * 100));
    fillEl.style.width = `${pct.toFixed(1)}%`;
  }
}

function updateSimulation(dt) {
  // Advance piece-by-piece connection animation when in Assembly Tutorial mode
  if (state.mode === "assembly") {
    const prevElapsed = state.stepAnimElapsed;
    state.stepAnimElapsed = Math.min(
      state.stepTargetMaxTime,
      state.stepAnimElapsed + dt
    );
    if (Math.abs(state.stepAnimElapsed - prevElapsed) > 1e-5) {
      applyExplodeAndVisibility();
    }
    updatePieceConnectionUI();
  }

  // Update 3D Track Joint & Trunk Port Visualizer Markers
  if (trackJointsGroup) {
    const showJoints =
      state.mode !== "plates" &&
      subsystemVisibility.track !== false &&
      (state.showTrackJoints || (state.mode === "assembly" && state.asmCurrentStep === 7));
    trackJointsGroup.visible = showJoints;

    if (showJoints) {
      const pulse = 0.5 + 0.5 * Math.sin(state.clockTime * 6.5);
      const inStep7 = state.mode === "assembly" && state.asmCurrentStep === 7;
      const actIdx = state.activeTrackPieceIdx;

      trackJointMarkers.forEach((m) => {
        let isHighlighted = false;
        if (inStep7) {
          if (state.focusedPortMode === "start-port") {
            isHighlighted = m.type === "start-port";
          } else if (state.focusedPortMode === "first-seam") {
            isHighlighted = m.type === "seam" && m.seamIndex === 1;
          } else if (state.focusedPortMode === "last-seam") {
            isHighlighted = m.type === "seam" && m.seamIndex === 13;
          } else if (state.focusedPortMode === "end-port") {
            isHighlighted = m.type === "end-port";
          } else if (actIdx === 0) {
            isHighlighted = m.type === "start-port" || (m.type === "seam" && m.seamIndex === 1);
          } else if (actIdx === 1 || actIdx === 2) {
            isHighlighted = m.type === "seam" && m.seamIndex === 1;
          } else if (actIdx === 14) {
            isHighlighted = m.type === "end-port" || (m.type === "seam" && m.seamIndex === 13);
          } else {
            isHighlighted = m.pieceIdx === actIdx;
          }
        } else {
          // In simulator or non-Step-7, subtly highlight Start & End Ports
          isHighlighted = m.type === "start-port" || m.type === "end-port";
        }

        const s = isHighlighted ? 1.0 + 0.14 * pulse : 0.88;
        m.group.scale.setScalar(s);
        if (m.mat) {
          m.mat.emissiveIntensity = isHighlighted ? 1.45 + 0.85 * pulse : 0.65;
        }
        if (m.tenonMat) {
          m.tenonMat.emissiveIntensity = isHighlighted ? 1.7 + 0.9 * pulse : 0.85;
        }
      });
    }
  }

  // 1. Update Lighting Mode, Build Plate Studio Inspector & Assembly-Step Light Gating
  const cobLit =
    state.mode !== "assembly" ||
    state.asmCurrentStep > 8 ||
    (state.asmCurrentStep === 8 && state.stepAnimElapsed >= 0.7);
  const topperLit =
    state.mode !== "assembly" ||
    state.asmCurrentStep > 9 ||
    (state.asmCurrentStep === 9 && state.stepAnimElapsed >= 0.6);

  if (state.mode === "plates") {
    // Dedicated High-Contrast Multi-Directional Studio Lighting for 6-Plate 3MF Inspector
    const expScale = (state.plateExposurePct || 135) / 100.0;
    const preset = state.plateLightPreset || "studio";

    if (preset === "detail") {
      // Grazing Socket & Tenon Detail Mode: strong raking key & rim lights to accentuate relief & sockets
      scene.background.setHex(0x131f30);
      renderer.toneMappingExposure = 1.14 * expScale;
      if (ambientLight) {
        ambientLight.color.setHex(0xf8fafc);
        ambientLight.intensity = 1.15;
      }
      if (hemiLight) hemiLight.intensity = 0.95;
      if (keyLight) {
        keyLight.color.setHex(0xfff7ed);
        keyLight.intensity = 3.55;
      }
      if (fillLight) {
        fillLight.color.setHex(0xbae6fd);
        fillLight.intensity = 1.45;
      }
      if (rimLight) {
        rimLight.color.setHex(0xfde68a);
        rimLight.intensity = 2.65;
      }
      if (plateInspectLight) plateInspectLight.intensity = 3.10;
      if (plateBackLight) plateBackLight.intensity = 1.95;
    } else if (preset === "soft") {
      // Soft Shadowless Diffused Mode: ultra-even illumination from all angles
      scene.background.setHex(0x1c2b40);
      renderer.toneMappingExposure = 1.16 * expScale;
      if (ambientLight) {
        ambientLight.color.setHex(0xffffff);
        ambientLight.intensity = 2.40;
      }
      if (hemiLight) hemiLight.intensity = 1.85;
      if (keyLight) {
        keyLight.color.setHex(0xffffff);
        keyLight.intensity = 1.85;
      }
      if (fillLight) {
        fillLight.color.setHex(0xffffff);
        fillLight.intensity = 1.85;
      }
      if (rimLight) {
        rimLight.color.setHex(0xffffff);
        rimLight.intensity = 1.65;
      }
      if (plateInspectLight) plateInspectLight.intensity = 1.60;
      if (plateBackLight) plateBackLight.intensity = 1.60;
    } else {
      // Default High-Contrast Studio Bright Mode: crisp specular highlights & zero dark shadows on all 4 filaments
      scene.background.setHex(0x162436);
      renderer.toneMappingExposure = 1.12 * expScale;
      if (ambientLight) {
        ambientLight.color.setHex(0xffffff);
        ambientLight.intensity = 1.72;
      }
      if (hemiLight) hemiLight.intensity = 1.30;
      if (keyLight) {
        keyLight.color.setHex(0xfffbeb);
        keyLight.intensity = 2.95;
      }
      if (fillLight) {
        fillLight.color.setHex(0xe0f2fe);
        fillLight.intensity = 2.05;
      }
      if (rimLight) {
        rimLight.color.setHex(0xfef3c7);
        rimLight.intensity = 1.85;
      }
      if (plateInspectLight) plateInspectLight.intensity = 2.25;
      if (plateBackLight) plateBackLight.intensity = 1.55;
    }

    cobLights.forEach((cl) => {
      cl.intensity = 0.0;
    });
    rgbLights.forEach((item) => {
      item.light.intensity = 0.0;
    });
    if (lampPuckLight) {
      lampPuckLight.intensity = 0.0;
    }
    if (topperHaloMesh) {
      topperHaloMesh.visible = false;
    }
  } else if (state.lightMode === "rainbow" || state.lightMode === "warm") {
    const isRainbow = state.lightMode === "rainbow";
    scene.background.setHex(0x070a12);
    renderer.toneMappingExposure = 1.12;
    if (ambientLight) {
      ambientLight.color.setHex(0x93c5fd);
      ambientLight.intensity = 0.42;
    }
    if (hemiLight) hemiLight.intensity = 0.22;
    if (plateInspectLight) plateInspectLight.intensity = 0.0;
    if (plateBackLight) plateBackLight.intensity = 0.0;
    if (keyLight) {
      keyLight.color.setHex(0xffe4b5);
      keyLight.intensity = 0.88;
    }
    if (fillLight) {
      fillLight.color.setHex(0x60a5fa);
      fillLight.intensity = 0.38;
    }
    if (rimLight) {
      rimLight.color.setHex(0xfbbf24);
      rimLight.intensity = 0.60;
    }

    const activeCob =
      state.mode !== "plates" &&
      subsystemVisibility.track !== false &&
      cobLit;

    // Animate per-vertex WS2812B addressable colors along the 4.5-turn BTF-LIGHTING Pebble Wire
    if (cobColorAttr) {
      const arr = cobColorAttr.array;
      const lum = activeCob ? 0.42 : 0.14;
      for (let i = 0; i <= 360; i++) {
        if (isRainbow) {
          const hue = (((i / 90.0) - state.clockTime * 0.55) % 1.0 + 1.0) % 1.0;
          _rgbTmpColor.setHSL(hue, 1.0, lum);
        } else {
          // Grav-Mass Crimson-Gold-Emerald flowing wave
          const w = 0.5 + 0.5 * Math.sin((i / 28.0) - state.clockTime * 3.2);
          const hue = 0.02 + 0.11 * w; // Crimson red (0.02) <-> Warm gold (0.13)
          _rgbTmpColor.setHSL(hue, 1.0, lum);
        }
        for (let j = 0; j <= 8; j++) {
          const idx = (i * 9 + j) * 3;
          arr[idx] = _rgbTmpColor.r;
          arr[idx + 1] = _rgbTmpColor.g;
          arr[idx + 2] = _rgbTmpColor.b;
        }
      }
      cobColorAttr.needsUpdate = true;
    }

    if (pebbleInstancedMesh) {
      const pLum = activeCob ? 0.62 : 0.16;
      for (let k = 0; k < 50; k++) {
        if (isRainbow) {
          const hue = ((((k / 12.5) - state.clockTime * 0.55) % 1.0) + 1.0) % 1.0;
          _rgbTmpColor.setHSL(hue, 1.0, pLum);
        } else {
          const w = 0.5 + 0.5 * Math.sin((k / 4.0) - state.clockTime * 3.2);
          _rgbTmpColor.setHSL(0.02 + 0.11 * w, 1.0, pLum);
        }
        pebbleInstancedMesh.setColorAt(k, _rgbTmpColor);
      }
      if (pebbleInstancedMesh.instanceColor) {
        pebbleInstancedMesh.instanceColor.needsUpdate = true;
      }
    }

    cobLights.forEach((cl, idx) => {
      cl.intensity = activeCob ? 2.2 : 0.0;
      if (isRainbow) {
        const hue = (((idx * 0.25) - state.clockTime * 0.45) % 1.0 + 1.0) % 1.0;
        cl.color.setHSL(hue, 1.0, 0.55);
      } else {
        const hue = 0.03 + 0.10 * (0.5 + 0.5 * Math.sin(state.clockTime * 2.5 + idx * 1.4));
        cl.color.setHSL(hue, 1.0, 0.55);
      }
    });

    rgbLights.forEach((item, idx) => {
      item.light.intensity =
        state.mode === "assembly" && state.asmCurrentStep < 7 ? 0.25 : 1.35;
      if (isRainbow) {
        const hue = (((item.baseHue || idx * 0.25) - state.clockTime * 0.4) % 1.0 + 1.0) % 1.0;
        item.light.color.setHSL(hue, 1.0, 0.55);
      } else {
        item.light.color.setHex(0x00a86b);
      }
    });

    const activeWarmTopper =
      state.mode !== "plates" &&
      subsystemVisibility.topper !== false &&
      topperLit;

    // Animate per-vertex colors on the 16-LED Sparkleiot WS2812B Apple Topper Ring (B09YTMNGTD)
    if (puckColorAttr) {
      const pArr = puckColorAttr.array;
      const pLum = activeWarmTopper ? 0.58 : 0.16;
      for (let i = 0; i <= 48; i++) {
        if (isRainbow) {
          const hue = (((i / 48.0) - state.clockTime * 0.75) % 1.0 + 1.0) % 1.0;
          _rgbTmpColor.setHSL(hue, 1.0, pLum);
        } else {
          const w = 0.5 + 0.5 * Math.sin((i / 48.0) * Math.PI * 4.0 - state.clockTime * 4.0);
          _rgbTmpColor.setHSL(0.01 + 0.12 * w, 1.0, pLum);
        }
        for (let j = 0; j <= 16; j++) {
          const idx = (j * 49 + i) * 3;
          pArr[idx] = _rgbTmpColor.r;
          pArr[idx + 1] = _rgbTmpColor.g;
          pArr[idx + 2] = _rgbTmpColor.b;
        }
      }
      puckColorAttr.needsUpdate = true;
    }

    const topperHue = isRainbow
      ? ((state.clockTime * 0.22) % 1.0 + 1.0) % 1.0
      : 0.03 + 0.06 * (0.5 + 0.5 * Math.sin(state.clockTime * 2.5));

    if (lampPuckLight) {
      lampPuckLight.intensity = activeWarmTopper ? 4.0 : 0.0;
      lampPuckLight.color.setHSL(topperHue, 1.0, 0.56);
    }
    topperShellActors.forEach((actor) => {
      const mat = actor.userData.material;
      if (mat) {
        mat.emissive.setHSL(topperHue, 1.0, 0.48);
        mat.emissiveIntensity = activeWarmTopper ? 0.68 : 0.0;
      }
    });
    if (topperHaloMesh && topperHaloMat) {
      topperHaloMesh.visible = activeWarmTopper && topperShellActors.some((a) => a.visible);
      topperHaloMat.color.setHSL(topperHue, 1.0, 0.56);
      topperHaloMat.opacity = 0.25 + 0.04 * Math.sin(state.clockTime * 2.8);
      if (topperShellActors[0]) {
        topperHaloMesh.position.set(
          topperShellActors[0].position.x,
          topperShellActors[0].position.y,
          topperShellActors[0].position.z + 492.0
        );
      }
    }
  } else {
    // CAD Studio Daylight Mode: crisp, high-key studio lighting & unlit true filament colors
    scene.background.setHex(0x1b2838);
    renderer.toneMappingExposure = 1.32;
    if (ambientLight) {
      ambientLight.color.setHex(0xffffff);
      ambientLight.intensity = 1.45;
    }
    if (hemiLight) hemiLight.intensity = 0.85;
    if (plateInspectLight) plateInspectLight.intensity = 0.0;
    if (plateBackLight) plateBackLight.intensity = 0.0;
    if (keyLight) {
      keyLight.color.setHex(0xffffff);
      keyLight.intensity = 2.35;
    }
    if (fillLight) {
      fillLight.color.setHex(0xe0f2fe);
      fillLight.intensity = 1.25;
    }
    if (rimLight) {
      rimLight.color.setHex(0xffffff);
      rimLight.intensity = 1.05;
    }

    cobLights.forEach((cl) => {
      cl.intensity = 0.0;
    });
    if (cobStripMat) {
      cobStripMat.emissiveIntensity = 0.2;
    }

    rgbLights.forEach((item) => {
      item.light.intensity = 0.35;
      item.light.color.setHex(0xffffff);
    });

    if (lampPuckLight) {
      lampPuckLight.intensity = 0.0;
      lampPuckLight.color.setHex(0xffffff);
    }
    if (topperPuckMat) {
      topperPuckMat.emissiveIntensity = 0.15;
    }
    topperShellActors.forEach((actor) => {
      const mat = actor.userData.material;
      if (mat) {
        mat.emissive.setHex(0x000000);
        mat.emissiveIntensity = 0.0;
      }
    });
    if (topperHaloMesh) {
      topperHaloMesh.visible = false;
    }
  }

  // 1b. Update 8 Planet Magnetic Control Switch LEDs & Magic Wand Tap Animation
  planetLedActors.forEach((pl) => {
    let intensity = 0.0;
    if (pl.mode === 1) {
      intensity = 1.45;
    } else if (pl.mode === 2) {
      intensity = 0.25 + 1.55 * (0.5 + 0.5 * Math.sin(state.clockTime * 3.5 + pl.phaseOffset));
    } else if (pl.mode === 3) {
      intensity = Math.sin(state.clockTime * 16.0 + pl.phaseOffset) > 0.0 ? 2.2 : 0.05;
    }
    const planetConnectedInAsm =
      state.mode !== "assembly" ||
      state.asmCurrentStep > 10 ||
      (state.asmCurrentStep === 10 && state.stepAnimElapsed >= pl.subDelay + 0.15);
    const showInMode =
      state.mode !== "plates" &&
      subsystemVisibility.planets !== false &&
      planetConnectedInAsm;
    pl.light.intensity = showInMode ? intensity * 1.8 : 0.0;
    pl.material.emissiveIntensity = intensity * 1.4;
    if (pl.haloMesh && pl.haloMat) {
      pl.haloMesh.visible = showInMode && intensity > 0.1;
      pl.haloMat.opacity = Math.min(0.36, intensity * 0.18);
    }
    if (pl.planetActors) {
      pl.planetActors.forEach((actor) => {
        const mat = actor.userData.material;
        if (mat) {
          mat.emissive.setHex(pl.color);
          mat.emissiveIntensity = showInMode ? intensity * 0.38 : 0.0;
        }
      });
    }
  });

  // 1c. Update 6 Glowing Apple Marble Magnetic Control Switch LEDs (+ Wall/Marble Impact Flash!)
  dynamicMarbles.forEach((m) => {
    if (m.impactFlash > 0.0) {
      m.impactFlash = Math.max(0.0, m.impactFlash - dt * 3.2);
    }
    let mIntensity = 0.0;
    if (m.ledMode === 1) {
      mIntensity = 1.5;
    } else if (m.ledMode === 2) {
      mIntensity = 0.25 + 1.6 * (0.5 + 0.5 * Math.sin(state.clockTime * 3.8 + m.phaseOffset));
    } else if (m.ledMode === 3) {
      mIntensity = Math.sin(state.clockTime * 15.0 + m.phaseOffset) > 0.0 ? 2.3 : 0.05;
    }
    if (m.impactFlash > 0.0 && m.ledMode > 0) {
      mIntensity += m.impactFlash * 1.4;
    }
    const marbleLit =
      state.mode !== "plates" &&
      subsystemVisibility.marbles !== false &&
      m.group.visible;
    if (m.ledMat) {
      m.ledMat.emissiveIntensity = marbleLit ? mIntensity * 1.45 : 0.0;
    }
    if (m.material) {
      m.material.emissiveIntensity = marbleLit ? mIntensity * 0.36 : 0.0;
    }
    if (m.haloMesh && m.haloMat) {
      m.haloMesh.visible = marbleLit && mIntensity > 0.1;
      m.haloMat.opacity = Math.min(0.42, mIntensity * 0.21);
    }
  });

  if (wandTapAnim) {
    wandTapAnim.elapsed += dt;
    const t = wandTapAnim.elapsed / wandTapAnim.duration;
    if (t >= 1.0) {
      magicWandActors.forEach((actor) => {
        actor.position.copy(actor.userData.basePos);
        actor.rotation.set(0, 0, 0);
      });
      wandTapAnim = null;
    } else {
      // Smoothly fly Magic_LED_Wand from its base resting spot to tap the target planet and return
      const pulse = Math.sin(t * Math.PI);
      const tapDip = Math.sin(t * Math.PI * 3.0) * 4.0 * pulse;
      const offset = wandTapAnim.deltaVec.clone().multiplyScalar(pulse);
      offset.x += wandTapAnim.radialDir.x * tapDip;
      offset.y += wandTapAnim.radialDir.y * tapDip;
      magicWandActors.forEach((actor) => {
        actor.position.copy(actor.userData.basePos).add(offset);
      });
    }
  }

  // 2. Update Direct-Coupled Auger & Motor Coupler Rotation
  const augerSpinning =
    state.powerOn &&
    (state.mode === "simulate" ||
      (state.mode === "assembly" && state.asmCurrentStep === 12 && state.stepAnimElapsed >= 1.95));
  const activeRpm = augerSpinning ? state.augerRpm : 0.0;
  const omega = (activeRpm / 60.0) * Math.PI * 2.0; // rad/s
  state.augerAngle = (state.augerAngle || 0.0) + omega * dt;

  assembledMeshes.forEach((actor) => {
    const kg = actor.userData.kinematic_group;
    if (kg === "motor_driver" || kg === "auger_driven") {
      actor.rotation.z = augerSpinning ? -state.augerAngle : 0.0;
    }
  });

  // 3. Handle Dynamic Marbles in Assembly Mode vs Simulator Mode
  if (state.mode === "assembly" && (state.asmCurrentStep < 12 || state.stepAnimElapsed < 1.95)) {
    dynamicMarbles.forEach((m, idx) => {
      if (subsystemVisibility.marbles === false) {
        m.group.visible = false;
        return;
      }
      if (state.asmCurrentStep < 12) {
        m.group.visible = state.ghostFutureSteps;
        return;
      }
      // Step 12: Marbles appear one by one at m.subDelay and lower onto the helical track!
      if (state.stepAnimElapsed < m.subDelay - 0.001) {
        m.group.visible = state.ghostFutureSteps;
        return;
      }
      m.group.visible = true;
      const rawU = Math.min(1.0, Math.max(0.0, (state.stepAnimElapsed - m.subDelay) / m.animDur));
      const easeU = 1.0 - Math.pow(1.0 - rawU, 3);
      const restTheta = 1580.0 - idx * 250.0;
      const pt = closedLoopMarblePoint(restTheta, 0.0);
      m.group.position.set(pt.x, pt.y, pt.z + 55.0 * (1.0 - easeU));
    });
    return;
  }

  // 4. Update Dynamic Marbles with Coupled 3D Rigid-Body Physics, Centrifugal Banking & Sphere-to-Sphere Queueing
  const physDt = Math.min(0.05, Math.max(0.001, dt));
  const preset = PHYSICS_PRESETS[state.physPreset] || PHYSICS_PRESETS.standard;
  const uPhase = 0.75 + state.augerAngle / (Math.PI * 2.0);
  let augerCount = 0;
  let trackCount = 0;
  let queuedCount = 0;

  // Step 4a: Update marbles in the Auger, Top Discharge Chute, and Bottom Intake Entry
  dynamicMarbles.forEach((m) => {
    m.group.visible = state.mode !== "plates" && subsystemVisibility.marbles !== false;
    m.isQueued = false;

    if (m.phase === "auger") {
      augerCount++;
      if (typeof m.flightIndex !== "number") {
        m.flightIndex = Math.round((m.z - 15.2 - 42.72) / 46.0 - uPhase);
      }
      const zBlade = 42.72 + 46.0 * (m.flightIndex + uPhase);
      // Marble rests on the Z = 52.8 mm intake floor until the rising auger flight contacts it from below
      m.z = Math.max(52.8, zBlade + 15.2);
      m.speedMmS = state.powerOn && zBlade + 15.2 > 52.8 ? (state.augerRpm / 60.0) * 46.0 : 0.0;
      m.bankDeg = 0.0;
      m.marginMm = 11.4;
      // Guided vertically inside the Ø 26.6 mm anti-rotation flute at (X = 0.0, Y = -17.5 mm)
      m.group.position.set(0.0, -17.5, m.z);
      if (state.powerOn && zBlade + 15.2 > 54.5) {
        m.outerMesh.rotation.x = -(m.z / 12.5);
      }

      // Discharge through Trunk_Top's sloped -Y upper exit spout at Z = 435.5 mm
      // (completely BELOW the Z = 450.0..468.5 mm Bambu Lab LED Lamp Kit 001 Puck!)
      if (m.z >= 435.5) {
        m.phase = "chute";
        m.chuteU = 0.0;
        m.speedMmS = 115.0;
      }
    } else if (m.phase === "chute") {
      augerCount++;
      // Ensure top entry basin at 1710° is clear before completing discharge
      const topBlocked = dynamicMarbles.some(
        (other) => other !== m && other.phase === "track" && other.theta > 1672.0
      );
      const maxU = topBlocked ? 0.55 : 1.0;
      // Accelerate along sloped -Y top discharge chute (L = 25.33 mm, ΔZ = -4.1 mm, sin α = 0.1618)
      const aChute = (9806.65 * (0.1618 - preset.muR * 0.9868)) / preset.kappa;
      m.speedMmS = Math.min(340.0, Math.max(95.0, (m.speedMmS || 115.0) + aChute * physDt));
      m.chuteU = Math.min(maxU, (m.chuteU || 0.0) + (m.speedMmS * physDt) / 25.33);
      if (topBlocked && m.chuteU >= maxU) {
        m.speedMmS = 40.0;
      }
      const u = m.chuteU;
      const startPt = new THREE.Vector3(0.0, -17.5, 435.5);
      const endPt = closedLoopMarblePoint(1710.0, 0.0); // (0.0, -42.5, 431.8) — strictly downhill along -Y into enclosed catch basin!
      m.group.position.lerpVectors(startPt, endPt, u);
      if (m.chuteU < maxU) {
        m.outerMesh.rotation.x += (m.speedMmS * physDt) / 12.5;
      }
      if (m.chuteU >= 1.0) {
        m.phase = "track";
        m.theta = 1710.0;
        m.uLat = 0.0;
        // Ejected along -Y into Seg 14's curved catch basin -> drives initial outward wall bounce!
        m.vuLat = 95.0;
        m.impactFlash = 0.75;
      }
    } else if (m.phase === "intake_entry") {
      augerCount++;
      // Accelerate along sloped +Y bottom intake ramp (L = 24.63 mm, ΔZ = -2.5 mm, sin α = 0.1015, 8.73° chute)
      const aIntake = (9806.65 * (0.1015 - preset.muR * 0.9948)) / preset.kappa;
      m.speedMmS = Math.min(420.0, Math.max(125.0, (m.speedMmS || 185.0) + aIntake * physDt));
      m.intakeU = (m.intakeU || 0.0) + (m.speedMmS * physDt) / 24.63;
      const u = Math.min(1.0, m.intakeU);
      const startPt = closedLoopMarblePoint(-90.0, 0.0); // (0.0, -42.0, 55.3)
      const endPt = new THREE.Vector3(0.0, -17.5, 52.8); // Strictly downhill (-2.50 mm) along +Y into flute!
      m.group.position.lerpVectors(startPt, endPt, u);
      m.outerMesh.rotation.x += (m.speedMmS * physDt) / 12.5;
      if (m.intakeU >= 1.0) {
        m.phase = "auger";
        m.z = 52.8;
        m.speedMmS = 0.0;
      }
    }
  });

  // Step 4b: Sub-Stepped Coupled 3D Rigid-Body Dynamics, Wall Restitution & Exact Triangle/Sphere Non-Penetration
  const trackMarbles = dynamicMarbles
    .filter((m) => m.phase === "track")
    .sort((a, b) => a.theta - b.theta);

  let intakePocketOccupied = dynamicMarbles.some(
    (other) =>
      other.phase === "intake_entry" ||
      (other.phase === "auger" && other.z < 81.5)
  );

  const intakeEntryMarble = dynamicMarbles.find((other) => other.phase === "intake_entry");

  let peakTrackSpeed = 0.0;
  let peakBankDeg = 0.0;
  let minWallMargin = 11.4;

  for (let idx = 0; idx < trackMarbles.length; idx++) {
    const m = trackMarbles[idx];
    trackCount++;

    const prevPos = m.group.position.clone();
    const prevTheta = m.theta;
    let v = typeof m.speedMmS === "number" ? m.speedMmS : 220.0;
    let uLat = typeof m.uLat === "number" ? m.uLat : 0.0;
    let vuLat = typeof m.vuLat === "number" ? m.vuLat : 0.0;
    let phi = 0.0;
    let kin = computeTrackKinematics(m.theta);
    const nSub = 6;
    const subDt = physDt / nSub;
    const eWall = 0.42; // Sidewall restitution coefficient for realistic wall bounce

    for (let sStep = 0; sStep < nSub; sStep++) {
      kin = computeTrackKinematics(m.theta);
      const aCent = v > 0.0 ? (v * v) / kin.rCurv : 0.0;
      const gNorm = 9806.65 * kin.cosAlpha;

      // 2D Cross-Sectional Lateral Wall-Bounce & Centrifugal Banking Dynamics
      const sinPhi = Math.max(-0.92, Math.min(0.92, uLat / 3.5));
      phi = Math.asin(sinPhi);
      const cosPhi = Math.cos(phi);
      const aLat = aCent * cosPhi - gNorm * sinPhi - 5.2 * vuLat;
      vuLat += aLat * subDt;
      uLat += vuLat * subDt;

      const { uMin, uMax } = closedLoopTroughBounds(m.theta);
      if (uLat > uMax) {
        uLat = uMax;
        if (vuLat > 0.0) {
          if (vuLat > 16.0) {
            // Energetic outer-wall hit: physical bounce + tangential wall friction + LED flash
            const impactV = vuLat;
            vuLat = -eWall * impactV;
            v = Math.max(0.0, v - preset.muWall * impactV * 0.45);
            m.impactFlash = Math.max(m.impactFlash || 0.0, Math.min(1.0, impactV / 90.0));
          } else {
            vuLat = 0.0;
          }
        }
      } else if (uLat < uMin) {
        uLat = uMin;
        if (vuLat < 0.0) {
          if (vuLat < -16.0) {
            // Energetic inner-wall hit: physical bounce + tangential wall friction + LED flash
            const impactV = -vuLat;
            vuLat = eWall * impactV;
            v = Math.max(0.0, v - preset.muWall * impactV * 0.45);
            m.impactFlash = Math.max(m.impactFlash || 0.0, Math.min(1.0, impactV / 90.0));
          } else {
            vuLat = 0.0;
          }
        }
      }

      const fGrav = 9806.65 * kin.sinAlpha;
      const fRoll = preset.muR * Math.hypot(gNorm, aCent);
      const fWall = preset.muWall * aCent * Math.max(0.0, Math.sin(phi));
      const dragSign = v >= 0.0 ? 1.0 : -1.0;
      const aTang =
        (fGrav - dragSign * (fRoll + fWall)) / preset.kappa - dragSign * 0.00018 * v * v;

      v = Math.min(980.0, Math.max(-240.0, v + aTang * subDt));
      const dThetaStep = (v * subDt) / kin.dsDtheta;
      m.theta = Math.min(1710.0, m.theta - dThetaStep);
      if (m.theta >= 1710.0 && v < 0.0) {
        // Rebound off top 1710° endcap bumper wall
        v = -0.35 * v;
      }
    }

    let nextTheta = m.theta;
    let minAllowedTheta = -90.0;
    if (idx === 0) {
      if (intakeEntryMarble) {
        const leadPos = intakeEntryMarble.group.position;
        let testTheta = Math.max(-90.0, nextTheta);
        while (testTheta < prevTheta + 2.0) {
          const pTest = closedLoopMarblePoint(testTheta, uLat);
          if (pTest.distanceTo(leadPos) >= 25.05) break;
          testTheta += 0.6;
        }
        minAllowedTheta = Math.max(-90.0, testTheta);
      } else if (intakePocketOccupied) {
        minAllowedTheta = -82.0;
      }
    } else {
      const leader = trackMarbles[idx - 1];
      const leadPos = leader.group.position;
      let testTheta = Math.max(leader.theta + 7.5, nextTheta);
      while (testTheta < prevTheta + 2.0) {
        const pTest = closedLoopMarblePoint(testTheta, uLat);
        if (pTest.distanceTo(leadPos) >= 25.05) break;
        testTheta += 0.5;
      }
      minAllowedTheta = testTheta;
    }

    if (idx === 0 && nextTheta <= -90.0 && !intakePocketOccupied) {
      m.phase = "intake_entry";
      m.intakeU = 0.0;
      m.speedMmS = Math.min(360.0, Math.max(120.0, v * 0.55));
      m.uLat = 0.0;
      m.vuLat = 0.0;
      m.impactFlash = 0.55;
      intakePocketOccupied = true;
      state.loopCount++;
      const loopEl = document.getElementById("stat-loop-count");
      if (loopEl) loopEl.textContent = String(state.loopCount);

      let targetFlight = Math.floor((52.8 - 15.2 - 42.72) / 46.0 - uPhase);
      while (
        dynamicMarbles.some(
          (other) =>
            other !== m &&
            (other.phase === "auger" || other.phase === "intake_entry") &&
            other.flightIndex === targetFlight
        )
      ) {
        targetFlight -= 1;
      }
      m.flightIndex = targetFlight;
      const pEnd = closedLoopMarblePoint(-90.0, 0.0);
      m.group.position.copy(pEnd);
    } else {
      if (nextTheta < minAllowedTheta) {
        nextTheta = minAllowedTheta;
        m.isQueued = true;
        m.hadQueueSinceStart = true;
        queuedCount++;
        // Resolve 3D sphere-to-sphere or endcap-bumper inelastic collision (e = 0.52)
        if (idx > 0) {
          const leader = trackMarbles[idx - 1];
          const vLead = leader.speedMmS || 0.0;
          if (v > vLead) {
            const dv = v - vLead;
            if (leader.isQueued && dv <= 45.0) {
              v = 0.0;
              vuLat *= 0.25;
              if (Math.abs(vuLat) < 1.0) vuLat = 0.0;
            } else {
              const eBall = 0.52;
              v = 0.5 * (1.0 - eBall) * v + 0.5 * (1.0 + eBall) * vLead;
              if (!leader.isQueued) {
                leader.speedMmS = Math.min(
                  980.0,
                  0.5 * (1.0 + eBall) * (dv + vLead) + 0.5 * (1.0 - eBall) * vLead
                );
              }
              // If leader is pinned in queue, high-speed impact causes a physical uphill recoil + lateral wall jostle!
              if (leader.isQueued && dv > 85.0) {
                v = -0.28 * dv;
              }
              if (dv > 45.0) {
                const jostleSign = m.index % 2 === 0 ? 1.0 : -1.0;
                vuLat += jostleSign * Math.min(75.0, dv * 0.24);
                leader.vuLat = (leader.vuLat || 0.0) - jostleSign * Math.min(60.0, dv * 0.18);
                const flashVal = Math.min(1.0, dv / 220.0);
                m.impactFlash = Math.max(m.impactFlash || 0.0, flashVal);
                leader.impactFlash = Math.max(leader.impactFlash || 0.0, flashVal);
              }
            }
          } else {
            v = leader.isQueued ? 0.0 : Math.min(v, vLead);
          }
        } else {
          // Endcap bumper / intake gate rebound when bottom pocket is occupied
          if (v > 75.0) {
            m.impactFlash = Math.max(m.impactFlash || 0.0, Math.min(1.0, v / 240.0));
            vuLat += (m.index % 2 === 0 ? 1.0 : -1.0) * Math.min(55.0, v * 0.2);
            v = -0.32 * v;
          } else {
            v = 0.0;
            vuLat *= 0.25;
            if (Math.abs(vuLat) < 1.0) vuLat = 0.0;
          }
        }
      }
      m.speedMmS = v;
      m.uLat = uLat;
      m.vuLat = vuLat;
      const actualDTheta = prevTheta - nextTheta;
      m.theta = nextTheta;
      kin = computeTrackKinematics(m.theta);

      // Compute 3D position on trough + enforce exact 3D triangle-mesh non-penetration against meshes.bin
      const mPt = closedLoopMarblePoint(m.theta, uLat);
      const triContact = projectSphereAgainstColliderMesh(mPt, 12.5);
      // Strictly clamp lateral cross-section excursion inside the trough walls so mesh projection can never push through a wall
      const { uMin: uBoundMin, uMax: uBoundMax } = closedLoopTroughBounds(m.theta);
      const dxSec = mPt.x - kin.pCur.x;
      const dySec = mPt.y - kin.pCur.y;
      const uProj = dxSec * kin.ux + dySec * kin.uy;
      const uClamped = Math.min(uBoundMax, Math.max(uBoundMin, uProj));
      if (Math.abs(uProj - uClamped) > 1e-4) {
        mPt.x += (uClamped - uProj) * kin.ux;
        mPt.y += (uClamped - uProj) * kin.uy;
      }
      m.group.position.copy(mPt);

      // True 3D World-Axis Quaternion Spin from actual 3D displacement vector & contact normal
      const dispX = mPt.x - prevPos.x;
      const dispY = mPt.y - prevPos.y;
      const dispZ = mPt.z - prevPos.z;
      const dispLen = Math.hypot(dispX, dispY, dispZ);
      if (dispLen > 1e-4 && dispLen < 45.0) {
        const cNx = triContact.pushed > 0.01 ? triContact.nx : -Math.sin(phi) * kin.ux;
        const cNy = triContact.pushed > 0.01 ? triContact.ny : -Math.sin(phi) * kin.uy;
        const cNz = triContact.pushed > 0.01 ? triContact.nz : Math.cos(phi);
        _spinAxisTmp.set(
          cNy * dispZ - cNz * dispY,
          cNz * dispX - cNx * dispZ,
          cNx * dispY - cNy * dispX
        );
        if (_spinAxisTmp.lengthSq() > 1e-6) {
          _spinAxisTmp.normalize();
          m.outerMesh.rotateOnWorldAxis(_spinAxisTmp, dispLen / 12.5);
        }
      }

      const phiAbs = Math.abs(phi);
      m.bankDeg = (phiAbs * 180.0) / Math.PI;
      const vBall = 9.8 - 3.5 * Math.cos(phiAbs);
      m.marginMm = Math.max(0.0, 17.7 - vBall);

      if (!m.isQueued) {
        if (v > peakTrackSpeed) peakTrackSpeed = v;
        if (m.bankDeg > peakBankDeg) peakBankDeg = m.bankDeg;
        if (m.marginMm < minWallMargin) minWallMargin = m.marginMm;
      }

      // Check Timing Gate Crossings (G0..G5) for 3D Beacon Flash & Gravity Lab Auto-Timing
      if (!m.isQueued && actualDTheta > 0.0) {
        timingGateActors.forEach((tg) => {
          if (prevTheta >= tg.deg && nextTheta < tg.deg) {
            tg.flashTimer = 0.38;
            if (tg.id === gravLab.startGate) {
              m.gateStartClock = state.clockTime;
              m.hadQueueSinceStart = false;
            } else if (
              tg.id === gravLab.endGate &&
              gravLab.autoSim &&
              !gravLab.manualRunning &&
              m.gateStartClock !== undefined &&
              !m.hadQueueSinceStart
            ) {
              // Compute theoretical Galilean transit time between startGate and endGate + realistic ±1.1% timing jitter
              const gA = TIMING_GATES[gravLab.startGate] || TIMING_GATES[0];
              const gB = TIMING_GATES[gravLab.endGate] || TIMING_GATES[5];
              const dsMm = Math.max(1.0, gB.sFromG0 - gA.sFromG0);
              const dhMm = Math.max(1.0, gB.dhFromG0 - gA.dhFromG0);
              const aEffMmS2 = (9806.65 * (dhMm / dsMm)) / gravLab.kappa;
              const idealDt =
                Math.sqrt(2.0 / aEffMmS2) *
                (Math.sqrt(gB.sFromG0) - Math.sqrt(gA.sFromG0));
              const jitter = 1.0 + 0.011 * Math.sin(state.clockTime * 17.3 + m.index * 2.1);
              recordGravityTrial(idealDt * jitter, `Marble #${m.index + 1}`);
              m.gateStartClock = undefined;
            }
          }
        });
      }
    }
  }

  // Update Live 3D Physics Telemetry Readout
  const elPhysSpeed = document.getElementById("stat-phys-speed");
  const elPhysBank = document.getElementById("stat-phys-bank");
  const elPhysMargin = document.getElementById("stat-phys-margin");
  if (elPhysSpeed) {
    elPhysSpeed.textContent = `${Math.round(peakTrackSpeed > 10 ? peakTrackSpeed : 756)} mm/s`;
  }
  if (elPhysBank) {
    elPhysBank.textContent = `${(peakBankDeg > 0.5 ? peakBankDeg : 41.9).toFixed(1)}°`;
  }
  if (elPhysMargin) {
    elPhysMargin.textContent = `+${(minWallMargin < 11.35 ? minWallMargin : 10.7).toFixed(1)} mm`;
  }

  // Update 3D Timing Gate Beacon Flashes & Manual Stopwatch Live Readout
  timingGateActors.forEach((tg) => {
    tg.mesh.visible = state.mode !== "plates" && subsystemVisibility.track !== false;
    if (tg.flashTimer > 0.0) {
      tg.flashTimer = Math.max(0.0, tg.flashTimer - dt);
      tg.material.color.setHex(0x34d399);
      tg.material.emissive.setHex(0x10b981);
      tg.material.emissiveIntensity = 2.2;
    } else {
      const isSelected = tg.id === gravLab.startGate || tg.id === gravLab.endGate;
      tg.material.color.setHex(isSelected ? 0xfbbf24 : 0xd4af37);
      tg.material.emissive.setHex(isSelected ? 0xf59e0b : 0xd4af37);
      tg.material.emissiveIntensity = isSelected ? 0.85 : 0.3;
    }
  });

  if (gravLab.manualRunning) {
    const elapsedSec = (performance.now() - gravLab.manualStartTime) / 1000.0;
    const btnSw = document.getElementById("btn-grav-stopwatch");
    if (btnSw) {
      btnSw.textContent = `🛑 Tap Finish Gate (${elapsedSec.toFixed(2)}s)`;
    }
  }

  const elAuger = document.getElementById("stat-auger-count");
  const elTrack = document.getElementById("stat-track-count");
  if (elAuger) elAuger.textContent = String(augerCount);
  if (elTrack) {
    elTrack.textContent =
      queuedCount > 0 ? `${trackCount} (${queuedCount} Queued)` : String(trackCount);
  }

  // Follow Marble #1 Camera Option
  if (state.followMarbleCam && state.mode === "simulate" && dynamicMarbles.length > 0) {
    const m0 = dynamicMarbles[0].group.position;
    controls.target.lerp(m0, 0.12);
    const desiredCam = new THREE.Vector3(m0.x * 1.85 + 90, m0.y * 1.85 - 90, m0.z + 85);
    camera.position.lerp(desiredCam, 0.06);
  }
}

function applyExplodeAndVisibility() {
  const explodePct =
    state.mode === "assembly" ? state.asmExplodePct : state.simExplodePct;
  const factor = explodePct / 100.0;

  if (electronicsGroup) {
    electronicsGroup.visible =
      state.mode === "assembly" || (state.mode === "simulate" && state.showElectronics);
  }

  assembledMeshes.forEach((actor) => {
    const ud = actor.userData;
    const subsys = ud.subsystem || "misc";
    const subsysVis =
      subsystemVisibility[subsys] !== false &&
      (state.mode === "assembly" || !ud.isElectronic || state.showElectronics);

    const itemStep = ud.step || 1;
    const subDelay = ud.sub_delay || 0.0;
    const animDur = ud.anim_dur || 0.65;

    let stepVis = true;
    let isGhosted = false;
    let isConnectingNow = false;
    const insertOffset = new THREE.Vector3(0, 0, 0);

    if (state.mode === "assembly") {
      if (itemStep > state.asmCurrentStep) {
        if (state.ghostFutureSteps) {
          isGhosted = true;
        } else {
          stepVis = false;
        }
      } else if (itemStep === state.asmCurrentStep) {
        if (state.stepAnimElapsed < subDelay - 0.001) {
          if (state.ghostFutureSteps) {
            isGhosted = true;
          } else {
            stepVis = false;
          }
        } else {
          const rawU = Math.min(
            1.0,
            Math.max(0.0, (state.stepAnimElapsed - subDelay) / animDur)
          );
          const easeU = 1.0 - Math.pow(1.0 - rawU, 3);
          if (rawU < 0.996 && ud.insertVec) {
            if (itemStep === 7 && ud.name && ud.name.startsWith("asm_track_seg_")) {
              // Two-stage Helical Scarf-Joint Slide-In for Track Segments (Seg 01 -> Seg 14):
              // Stage 1 (rawU 0..0.55): Approach radially toward cantilever brackets while displaced uphill along helix tangent
              // Stage 2 (rawU 0.55..1.0): Slide tangentially downhill along 15° scarf angle onto previous segment's Twin Ø3.8mm Male Tenons & drop onto bracket pegs!
              const segIdx = parseInt(ud.name.replace("asm_track_seg_", ""), 10) || 1;
              const seamDeg = segIdx === 1 ? -45.0 : (segIdx - 1) * 120.0;
              const seamRad = (seamDeg * Math.PI) / 180.0;
              const radialPart = Math.max(0.0, (0.62 - rawU) / 0.62);
              const slidePart = 1.0 - easeU;
              const tangDist = segIdx === 1 ? 0.0 : 28.0 * slidePart;
              const rDist = 42.0 * radialPart * radialPart;
              insertOffset.set(
                rDist * Math.cos(seamRad) - tangDist * Math.sin(seamRad),
                rDist * Math.sin(seamRad) + tangDist * Math.cos(seamRad),
                20.0 * slidePart
              );
              if (segIdx === 1) {
                // Seg 01 approaches along -Y and slides +Y into Trunk_Base intake port while dropping onto 60°/120° brackets
                insertOffset.set(16.0 * radialPart, -46.0 * slidePart, 22.0 * slidePart);
              }
            } else {
              insertOffset.copy(ud.insertVec).multiplyScalar(1.0 - easeU);
            }
            isConnectingNow = true;
          }
        }
      }
    }

    actor.visible = subsysVis && stepVis;

    const totalOffset = ud.explodeVec.clone().multiplyScalar(factor).add(insertOffset);
    actor.position.copy(ud.basePos).add(totalOffset);

    if (ud.guideLine) {
      ud.guideLine.visible =
        state.mode !== "plates" &&
        actor.visible &&
        !isGhosted &&
        (factor > 0.02 || isConnectingNow);
      if (ud.guideLine.visible) {
        const posAttr = ud.guideLine.geometry.attributes.position;
        const p0 = ud.guideOrigin;
        const p1 = p0.clone().add(totalOffset);
        posAttr.setXYZ(0, p0.x, p0.y, p0.z);
        posAttr.setXYZ(1, p1.x, p1.y, p1.z);
        posAttr.needsUpdate = true;
        ud.guideLine.computeLineDistances();
      }
    }

    let op = ud.baseOpacity;
    if (
      ud.subsystem === "topper" &&
      ud.toolhead === 4 &&
      (state.lightMode === "rainbow" || state.lightMode === "warm") &&
      state.powerOn
    ) {
      // Thin-walled (~2.2 mm) hollow crimson apple shell has subtle lantern translucency when lit
      op = 0.88;
    }
    if (isGhosted) {
      op = 0.14;
    } else if (state.xrayActive && ud.cutaway_candidate) {
      op = 0.25;
    } else if (state.mode === "assembly" && !ud.isElectronic) {
      // Automatically make enclosing shells semi-translucent during internal installation steps
      // so the motor, IA005 power hub, wires, hex coupler, auger, Lamp Puck, and First/Last Track Ports are 100% visible!
      if (ud.name && ud.name.includes("trunk_base")) {
        if (
          (state.asmCurrentStep === 1 && state.stepAnimElapsed > 0.6) ||
          state.asmCurrentStep === 2 ||
          state.asmCurrentStep === 3 ||
          state.asmCurrentStep === 4
        ) {
          op = 0.32;
        } else if (state.asmCurrentStep === 8 && state.stepAnimElapsed > 1.2) {
          op = 0.42;
        } else if (
          state.asmCurrentStep === 7 &&
          (state.activeTrackPieceIdx === 0 || state.focusedPortMode === "start-port")
        ) {
          // Make Trunk_Base semi-transparent when inspecting Seg 01 so the -Y Bottom Intake Port -> Auger Flute transition is crystal clear!
          op = 0.36;
        }
      } else if (
        ud.name &&
        ud.name.includes("trunk_top") &&
        state.asmCurrentStep === 7 &&
        (state.activeTrackPieceIdx === 14 || state.focusedPortMode === "end-port")
      ) {
        // Make Trunk_Top semi-transparent when inspecting Seg 14 so the -Y Upper Discharge Spout -> Seg 14 Catch Basin is crystal clear!
        op = 0.36;
      } else if (
        (ud.name === "asm_golden_apple_topper" ||
          (ud.subsystem === "topper" && ud.toolhead === 4)) &&
        state.asmCurrentStep === 9
      ) {
        op = 0.48;
      }

      // In Step 7, highlight the active track segment (emerald glow) and its mating target segment (gold glow)
      if (ud.subsystem === "track" && ud.material && ud.material.emissive) {
        if (state.asmCurrentStep === 7 && !isGhosted) {
          const activeSpec = TRACK_PIECE_SPECS[state.activeTrackPieceIdx];
          const activeSegNum = activeSpec ? activeSpec.segNum : -1;
          const prevActorName =
            activeSegNum > 1
              ? `asm_track_seg_${String(activeSegNum - 1).padStart(2, "0")}`
              : null;
          if (activeSpec && ud.name === activeSpec.actorName) {
            ud.material.emissive.setHex(0x10b981);
            ud.material.emissiveIntensity = isConnectingNow ? 0.48 : 0.28;
          } else if (
            (prevActorName && ud.name === prevActorName) ||
            (state.activeTrackPieceIdx === 2 &&
              (ud.name === "asm_track_seg_01" || ud.name === "asm_track_seg_02"))
          ) {
            ud.material.emissive.setHex(0xd4af37);
            ud.material.emissiveIntensity = 0.26;
          } else {
            ud.material.emissive.setHex(0x000000);
            ud.material.emissiveIntensity = 0.0;
          }
        } else {
          ud.material.emissive.setHex(0x000000);
          ud.material.emissiveIntensity = 0.0;
        }
      }
    } else if (ud.subsystem === "track" && ud.material && ud.material.emissive && !ud.isElectronic) {
      ud.material.emissive.setHex(0x000000);
      ud.material.emissiveIntensity = 0.0;
    }
    ud.material.transparent = op < 0.99;
    ud.material.opacity = op;
    ud.material.depthWrite = op > 0.35;
  });
}

const STEP_WIRING_GUIDE = {
  1: {
    title: "🔌 Step 1 Electronics — Rear 12V DC Barrel Jack (J1) & N20 Auger Motor",
    badge: "12V INLET + SHROUD TOWER",
    rows: [
      {
        pillClass: "wire-red",
        pillText: "🔌 J1 12V Jack",
        html: "Thread the <strong>5.5×2.1 mm Panel-Mount DC Barrel Jack (<code>J1</code>)</strong> through the rear <code>-X</code> <code>Ø11.40 mm</code> port (<code>Z = 10.0 mm</code>) on <code>trunk_base</code> and route its <code>18 AWG</code> pigtails into the Hollow Root Vault to <code>WAGO-1 (+12V_BUS)</code> (via <code>5A</code> fuse <code>F0</code>) and <code>WAGO-2 (STAR_GND)</code>.",
      },
      {
        pillClass: "wire-motor",
        pillText: "🔩 N20 Motor",
        html: "Slide the <strong><code>12V 150 RPM N20</code> Gear Motor (Option B)</strong> (or <code>6V LA002</code> for Option A) up into the central <code>Ø28.0 mm</code> shroud tower and feed its 2-wire cable out the bottom <code>-Y</code> notch (<code>6.5×7.6 mm</code>) toward the <code>A092</code> terminal bay.",
      },
    ],
  },
  2: {
    title: "🔌 Step 2 Electronics — 12V→5V Buck Converter + WAGO 221 + M5Stack (A092 + C008)",
    badge: "SINGLE-CABLE ZERO-SOLDER HUB",
    rows: [
      {
        pillClass: "wire-motor",
        pillText: "🔩 12V & M1/M2",
        html: "Feed <code>WAGO-1 (+12V_BUS)</code> (via <code>2A</code> fuse <code>F1</code>) and <code>WAGO-2 (STAR_GND)</code> into <strong>A092 <code>VIN</code> &amp; <code>GND</code></strong> screw terminals (powering both <code>A092</code> and <code>C008</code> internally). Clamp the <strong><code>12V 150 RPM N20</code> Motor</strong> leads into <code>A092 M1 &amp; M2</code> (or use a <code>12V→6V</code> buck + H-bridge for a <code>6V LA002</code> motor).",
      },
      {
        pillClass: "wire-red",
        pillText: "⚡ 5V LED Buck",
        html: "Feed the <strong><code>12V → 5.0V 5A</code> Screw-Terminal Buck Converter</strong> from <code>WAGO-1 (+12V_BUS)</code> (via <code>3A</code> fuse <code>F2</code>) and <code>WAGO-2</code>, and connect its <code>+5V OUT</code> and <code>-OUT</code> terminals (with a <code>1000 µF 16V</code> bulk capacitor) to <strong><code>WAGO-3 (+5V_LED)</code></strong> and <strong><code>WAGO-4 (GND_LED)</code></strong>.",
      },
      {
        pillClass: "wire-white",
        pillText: "🔗 A096 Grove",
        html: "Plug 1× <strong>M5Stack A096 Grove2Dupont Cable</strong> into <code>C008</code>'s 4-pin Grove socket (<code>White = GPIO26</code> Track Data, <code>Yellow = GPIO32</code> Topper Data, <code>Black = GND</code> to <code>WAGO-2</code>). <strong>Leave <code>A096 Red (+5V)</code> CAPPED in an empty WAGO port</strong> so the external 5V buck never backfeeds <code>A092</code>!",
      },
    ],
  },
  3: {
    title: "🔩 Step 3 Mechanical Joint — Direct Hex Coupler & Snap-In Bottom Cover",
    badge: "D-SHAFT + SNAP RING",
    rows: [
      {
        pillClass: "wire-yellow",
        pillText: "⚙️ D-Shaft Fit",
        html: "Press the gold <strong>Motor_Clutch_Driver</strong> onto the N20 motor's <code>Ø3.0 mm</code> D-shaft inside the <code>Z = 26.2 mm</code> coupler chamber so its top <code>4.85 mm AF</code> male hex peg points straight up.",
      },
      {
        pillClass: "wire-motor",
        pillText: "🛡️ Snap-In Lid",
        html: "Push <strong>Base_Bottom_Cover</strong> up into the bottom of <code>trunk_base</code>—its upward <strong><code>Ø23.6×2.8 mm</code> Snap-In Hollow Retaining Ring</strong> clicks concentrically inside the central <code>Ø24.0 mm</code> shroud bore with zero screws required!",
      },
    ],
  },
  4: {
    title: "🔩 Step 4 Mechanical Joint — 2-Stage Archimedes Auger Hex Coupling (#1 → #2)",
    badge: "4.85mm → 5.15mm HEX",
    rows: [
      {
        pillClass: "wire-yellow",
        pillText: "🔢 #1 → #2 Hex",
        html: "Lower <strong>auger_lower (#1)</strong> onto <code>Motor_Clutch_Driver</code>'s hex peg (resting on the <code>Z = 37.2 mm</code> internal thrust ledge), then slide <strong>auger_upper (#2)</strong>'s <code>5.15 mm AF</code> female hex socket onto <code>auger_lower</code>'s top male hex peg (hiding the engraved <code>1</code>).",
      },
    ],
  },
  5: {
    title: "🌲 Step 5 Mechanical Joint — Keyed Trunk Tenons (#1 → #2 → #3) & Crown Collar",
    badge: "15mm KEYED TENONS",
    rows: [
      {
        pillClass: "wire-motor",
        pillText: "🌲 #1 → #2 → #3",
        html: "Stack <strong>trunk_mid (#2)</strong> onto <code>trunk_base (#1)</code> and <strong>trunk_top (#3)</strong> onto <code>trunk_mid (#2)</code> using the <code>15.0 mm</code> tall keyed male tenons (<code>+X/-X</code> anti-rotation flats keep the ball flute, viewing windows &amp; rear <code>10×8 mm</code> wire conduit aligned).",
      },
    ],
  },
  6: {
    title: "🌿 Step 6 Mechanical Joint — 24× Wedge-Lock Cantilever Brackets (Tiers #4 → #1)",
    badge: "45° DOVETAIL WEDGES",
    rows: [
      {
        pillClass: "wire-motor",
        pillText: "🔢 Tiers 4 → 1",
        html: "Slide 6× brackets per tier (<code>#4</code> longest at bottom → <code>#1</code> shortest at top) down into the 24 helical trunk dovetail slots (every <code>60°</code> from <code>60°</code> to <code>1440°</code>—supporting both segment midpoints and segment seams!).",
      },
    ],
  },
  7: {
    title: "🎢 Step 7 Mechanical Joint — Snap-Lock Track Interlocks (1 → 14) + Retrofit Clip",
    badge: "4-POINT SNAP-LOCK",
    rows: [
      {
        pillClass: "wire-wireless",
        pillText: "🔗 Built-In Snap",
        html: "Each uphill segment end (<code>1..13</code>) has <strong>Twin <code>Ø3.80×5.0 mm</code> Male Snap-Lock Tenon Pegs</strong> (at <code>u = ±14.2 mm, v = -4.2 mm</code> with <code>Ø4.08 mm</code> detent beads) + <strong>Inner/Outer Sidewall Anti-Torsion Tongues</strong> that click directly into the next segment's <code>Ø4.30×5.6 mm</code> female sockets!",
      },
      {
        pillClass: "wire-motor",
        pillText: "🌿 Seam Brackets",
        html: "Every segment also has underside <code>Ø4.40 mm</code> bracket peg sockets at <strong>both</strong> midpoint stations (<code>60°, 180°, ...</code>) and seam stations (<code>120°, 240°, ...</code>), so the even-<code>60°</code> cantilever brackets lock directly under every track joint!",
      },
      {
        pillClass: "wire-white",
        pillText: "📎 Retrofit Clip",
        html: "<strong>Already printed older track segments without male pegs?</strong> Print <code>Track_Joint_Clip.stl</code> (Plate 3) and snap it across the underside &amp; sidewalls of any seam (with two <code>11 mm</code> snippets of <code>1.75 mm</code> filament in the <code>Ø2.2 mm</code> dowel holes)—its central arch leaves the LED wire channel 100% open!",
      },
    ],
  },
  8: {
    title: "🔌 Step 8 Electronics — Connect Helical Track Pebble Wire (B0CCS11V7H) to GPIO26 & 5V Buck",
    badge: "GROVE GPIO26 + WAGO-3/4",
    rows: [
      {
        pillClass: "wire-white",
        pillText: "⚪ White → DATA",
        html: "Push the <strong>White DuPont pin (<code>GPIO26</code>)</strong> from the <code>A096</code> Grove cable into the <strong>Center <code>DATA</code> pin</strong> of the BTF-LIGHTING Pebble Wire's 3-pin <code>JST-SM</code> input plug.",
      },
      {
        pillClass: "wire-red",
        pillText: "🔴 WAGO-3 → +5V",
        html: "Clamp the Track Wire's <strong>Red <code>+5V</code> power-injection leads</strong> (both bottom start and top return tail) into <strong><code>WAGO-3 (+5V_LED)</code></strong> fed by the dedicated <code>12V → 5.0V 5A</code> buck converter (never draw LED power through <code>C008</code>'s Grove port!).",
      },
      {
        pillClass: "wire-black",
        pillText: "⚫ WAGO-4 → GND",
        html: "Clamp the Track Wire's <strong>Black <code>GND</code> leads</strong> into <strong><code>WAGO-4 (GND_LED)</code></strong> (tied to <code>WAGO-2 Star GND</code>), and coil any extra cable slack inside the <code>150+ cm³</code> Hollow Root Vault.",
      },
    ],
  },
  9: {
    title: "🔌 Step 9 Electronics — Connect Apple Topper 16-LED Ring (B09YTMNGTD) to GPIO32 & 5V Buck",
    badge: "GROVE GPIO32 + WAGO-3/4",
    rows: [
      {
        pillClass: "wire-yellow",
        pillText: "🟡 Yellow → DATA",
        html: "Thread the <code>1 m</code> 3-pin <code>JST-SM</code> extension cable (<code>B0CT827QQC</code>) from the Topper Ring straight down the <code>10×8 mm</code> rear (<code>-X</code>) trunk conduit into the base vault. Connect the <strong>Yellow DuPont pin (<code>GPIO32</code>)</strong> from the <code>A096</code> Grove cable to its <strong>Center <code>DATA</code> pin</strong>.",
      },
      {
        pillClass: "wire-red",
        pillText: "🔴 WAGO-3 + ⚫ WAGO-4",
        html: "Clamp the Topper Ring extension's <strong>Red (<code>+5V</code>)</strong> and <strong>Black (<code>GND</code>)</strong> wires directly into <strong><code>WAGO-3 (+5V_LED)</code></strong> and <strong><code>WAGO-4 (GND_LED)</code></strong> on the dedicated <code>12V → 5.0V 5A</code> buck converter rail with zero splicing!",
      },
      {
        pillClass: "wire-motor",
        pillText: "🍎 Crown Tenon",
        html: "Press-fit <strong>Conduit_Cover_Strip</strong> (with its <code>11.2 mm</code> depth-stop flange) into the rear conduit, then seat <strong>golden_apple_topper (#4)</strong> onto <code>trunk_top (#3)</code>'s upward <strong><code>Ø59.4×4.0 mm</code> Crown Centering Tenon Collar</strong> so the Apple Topper locks concentrically onto the trunk!",
      },
    ],
  },
  10: {
    title: "🪄 Step 10 Electronics — 8× Wireless Planet Magnetic Switch LEDs (KA006)",
    badge: "100% WIRELESS (CR927)",
    rows: [
      {
        pillClass: "wire-wireless",
        pillText: "🪐 8× KA006 LEDs",
        html: "Each planet houses a self-contained <code>Ø7.5×6.0 mm</code> <strong>Bambu Single LED Magnetic Control Switch Light (<code>KA006</code>)</strong> powered by a <code>CR927</code> coin cell—<strong>zero wires required!</strong> Tap any planet with the <code>Magic_LED_Wand</code> star tip to cycle ON → Breathe → Flash → OFF.",
      },
    ],
  },
  11: {
    title: "🪐 Step 11 Mechanical Joint — 8× Numbered Planet Balcony Pegs (#1 Mercury → #8 Neptune)",
    badge: "Ø7.6×3.5mm SNAP PEGS",
    rows: [
      {
        pillClass: "wire-wireless",
        pillText: "🔢 Match 1 → 8",
        html: "Each outer-rim track balcony peg (<code>Ø7.60×3.50 mm</code>) is engraved with its solar-system number <strong><code>1</code> through <code>8</code></strong> on top—press each planet's <code>Ø8.00 mm</code> bottom socket onto its matching numbered peg (from <code>1 = Mercury</code> at top to <code>8 = Neptune</code> at bottom) and dock <strong>Magic_LED_Wand</strong> in the <code>+30°</code> root holster!",
      },
    ],
  },
  12: {
    title: "🪄 Step 12 Electronics — 6× Wireless Rolling Marble Y-Shape 3-LEDs (KC012 / KC013)",
    badge: "100% WIRELESS (CR1632)",
    rows: [
      {
        pillClass: "wire-wireless",
        pillText: "🍎 6× KC012 LEDs",
        html: "Each Quarter-Turn Twist-Lock Apple Marble houses a wireless <code>Ø18.0×6.5 mm</code> <strong>Bambu Y-Shape 3-LED Light (<code>KC012/KC013</code>)</strong> with a <code>CR1632</code> coin cell—<strong>zero wires required!</strong> Tap each marble with the <code>Magic_LED_Wand</code> before dropping onto the track.",
      },
    ],
  },
};

function setAssemblyStep(stepNum, animateCamera = true, targetMaxTime = Infinity) {
  const totalSteps = manifest.assembly_steps.length;
  state.asmCurrentStep = Math.max(1, Math.min(totalSteps, stepNum));
  state.stepAnimElapsed = 0.0;
  state.stepTargetMaxTime = targetMaxTime;
  state.focusedPortMode = null;
  if (state.asmCurrentStep === 7) {
    state.activeTrackPieceIdx = 0;
  }

  const stepData = manifest.assembly_steps[state.asmCurrentStep - 1];

  document.getElementById("lbl-step-badge").textContent = `Step ${state.asmCurrentStep} / ${totalSteps}`;
  document.getElementById("asm-step-title").textContent = stepData.title;
  document.getElementById("asm-step-subtitle").textContent = stepData.subtitle;
  document.getElementById("asm-step-clearance").textContent = stepData.clearance_note;

  const ul = document.getElementById("asm-step-hardware");
  ul.innerHTML = "";
  stepData.hardware.forEach((h) => {
    const li = document.createElement("li");
    li.textContent = h;
    ul.appendChild(li);
  });

  const wiringCard = document.getElementById("asm-wiring-card");
  if (wiringCard) {
    const wInfo = STEP_WIRING_GUIDE[state.asmCurrentStep];
    if (wInfo) {
      wiringCard.classList.remove("hidden");
      wiringCard.innerHTML = `
        <div class="wiring-card-title">
          <span>${wInfo.title}</span>
          <span class="wiring-card-badge">${wInfo.badge}</span>
        </div>
        <div class="pinout-list">
          ${wInfo.rows
            .map(
              (r) => `
            <div class="pinout-row">
              <span class="wire-pill ${r.pillClass}">${r.pillText}</span>
              <div class="pinout-desc">${r.html}</div>
            </div>
          `
            )
            .join("")}
        </div>
      `;
    } else {
      wiringCard.classList.add("hidden");
      wiringCard.innerHTML = "";
    }
  }

  document.querySelectorAll(".elec-jump-btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.elecStep) === state.asmCurrentStep);
  });

  document.querySelectorAll(".step-dot").forEach((btn, idx) => {
    const s = idx + 1;
    btn.classList.toggle("current", s === state.asmCurrentStep);
    btn.classList.toggle("completed", s < state.asmCurrentStep);
  });

  if (animateCamera && stepData.camera_pos && stepData.camera_target) {
    camAnim = {
      targetPos: new THREE.Vector3(...stepData.camera_pos),
      targetLook: new THREE.Vector3(...stepData.camera_target),
      timeLeft: 0.75,
    };
  }

  applyExplodeAndVisibility();
  updatePieceConnectionUI();
  updateTrackInspectorUI(state.activeTrackPieceIdx);
}

function updateCameraTransition(dt) {
  if (!camAnim) return;
  camAnim.timeLeft -= dt;
  const alpha = Math.min(1.0, dt * 6.0);
  camera.position.lerp(camAnim.targetPos, alpha);
  controls.target.lerp(camAnim.targetLook, alpha);
  if (camAnim.timeLeft <= 0) {
    camAnim = null;
  }
}

function selectBuildPlate(plateIdx) {
  state.activePlateIndex = plateIdx;
  document.querySelectorAll(".plate-select-btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.plate) === plateIdx);
  });

  if (plateIdx === -1) {
    plateGroups.forEach((g, idx) => {
      g.visible = true;
      const col = idx % 4;
      const row = Math.floor(idx / 4);
      g.position.set((col - 1.5) * 324.0, (1.0 - row) * 324.0, 0);
    });
    camAnim = {
      targetPos: new THREE.Vector3(0, -1080, 860),
      targetLook: new THREE.Vector3(0, 0, 20),
      timeLeft: 0.7,
    };
  } else {
    plateGroups.forEach((g, idx) => {
      g.visible = idx === plateIdx;
      g.position.set(0, 0, 0);
    });
    camAnim = {
      targetPos: new THREE.Vector3(0, -290, 250),
      targetLook: new THREE.Vector3(0, 0, 20),
      timeLeft: 0.65,
    };
  }
}

function switchMode(newMode) {
  state.mode = newMode;
  document.querySelectorAll(".mode-tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === newMode);
  });
  document.querySelectorAll(".mode-panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${newMode}`);
  });

  if (newMode === "plates") {
    assembledRoot.visible = false;
    electronicsGroup.visible = false;
    guideLinesGroup.visible = false;
    bedGridGroup.visible = false;
    platesRoot.visible = true;
    renderer.localClippingEnabled = true;
    selectBuildPlate(state.activePlateIndex);
  } else {
    assembledRoot.visible = true;
    electronicsGroup.visible = newMode === "assembly" || state.showElectronics;
    guideLinesGroup.visible = true;
    bedGridGroup.visible = true;
    platesRoot.visible = false;
    renderer.localClippingEnabled = false;
    applyExplodeAndVisibility();

    if (newMode === "assembly") {
      setAssemblyStep(state.asmCurrentStep, true);
    } else {
      const vp = renderer.domElement.parentElement;
      const isP = vp.clientWidth / Math.max(1, vp.clientHeight) < 0.85;
      camAnim = {
        targetPos: isP ? new THREE.Vector3(540, -560, 410) : new THREE.Vector3(420, -430, 340),
        targetLook: new THREE.Vector3(0, 0, 225),
        timeLeft: 0.65,
      };
    }
  }
}

function initUI() {
  const sidePanel = document.getElementById("side-panel");
  const drawerBtn = document.getElementById("btn-mobile-drawer");
  const drawerLbl = document.getElementById("lbl-mobile-drawer");
  if (drawerBtn && sidePanel) {
    drawerBtn.addEventListener("click", () => {
      const isMin = sidePanel.classList.toggle("minimized");
      if (drawerLbl) {
        drawerLbl.textContent = isMin
          ? "▲ Expand Controls Panel"
          : "▼ Minimize Controls (Larger 3D View)";
      }
      setTimeout(onWindowResize, 260);
    });
  }

  // Mode Tabs
  document.querySelectorAll(".mode-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (sidePanel && sidePanel.classList.contains("minimized")) {
        sidePanel.classList.remove("minimized");
        if (drawerLbl) {
          drawerLbl.textContent = "▼ Minimize Controls (Larger 3D View)";
        }
        setTimeout(onWindowResize, 260);
      }
      switchMode(btn.dataset.mode);
    });
  });

  // Top Bar Quick Toggles
  document.getElementById("chk-xray").addEventListener("change", (e) => {
    state.xrayActive = e.target.checked;
    applyExplodeAndVisibility();
  });

  document.getElementById("chk-electronics").addEventListener("change", (e) => {
    state.showElectronics = e.target.checked;
    applyExplodeAndVisibility();
  });

  const chkTrackJoints = document.getElementById("chk-track-joints");
  if (chkTrackJoints) {
    chkTrackJoints.addEventListener("change", (e) => {
      state.showTrackJoints = e.target.checked;
      updateSimulation(0.0);
    });
  }

  document.getElementById("chk-follow-cam").addEventListener("change", (e) => {
    state.followMarbleCam = e.target.checked;
  });

  document.getElementById("btn-reset-cam").addEventListener("click", () => {
    state.followMarbleCam = false;
    document.getElementById("chk-follow-cam").checked = false;
    if (state.mode === "plates") {
      selectBuildPlate(state.activePlateIndex);
    } else {
      const vp = renderer.domElement.parentElement;
      const isP = vp.clientWidth / Math.max(1, vp.clientHeight) < 0.85;
      camAnim = {
        targetPos: isP ? new THREE.Vector3(540, -560, 410) : new THREE.Vector3(420, -430, 340),
        targetLook: new THREE.Vector3(0, 0, 225),
        timeLeft: 0.65,
      };
    }
  });

  // ESPHome Motor Toggle (M5Stack A092+C008) & Queue Test
  const pwrBtn = document.getElementById("btn-power-toggle");
  const pwrLbl = document.getElementById("lbl-power-status");
  const runBadge = document.getElementById("sim-run-badge");
  pwrBtn.addEventListener("click", () => {
    state.powerOn = !state.powerOn;
    pwrBtn.classList.toggle("active", state.powerOn);
    if (state.powerOn) {
      pwrBtn.textContent = "⚡ ESPHome Motor: ON — Click to Pause Auger & Test Bottom Queue";
      pwrLbl.textContent = "ON (Closed-Loop Active)";
      pwrLbl.className = "text-emerald";
      runBadge.textContent = "RUNNING";
    } else {
      pwrBtn.textContent = "⭕ ESPHome Motor: OFF — Marbles Queueing on Bottom Ramp";
      pwrLbl.textContent = "PAUSED (Queue Active)";
      pwrLbl.className = "text-crimson";
      runBadge.textContent = "PAUSED";
    }
  });

  // Auger RPM Slider
  const rpmSlider = document.getElementById("slider-rpm");
  const updateRpmUI = (val) => {
    state.augerRpm = Number(val);
    rpmSlider.value = String(state.augerRpm);
    const liftMmS = ((state.augerRpm / 60.0) * 46.0).toFixed(1);
    document.getElementById("lbl-auger-rpm").textContent = `${state.augerRpm} RPM (${liftMmS} mm/s lift)`;
  };
  rpmSlider.addEventListener("input", (e) => updateRpmUI(e.target.value));

  // Lighting Mode Buttons
  const lightNames = {
    rainbow: "🌈 Rainbow RGBIC Cascade",
    warm: "🍎 Crimson & Gold Halo",
    studio: "☀️ CAD Studio Daylight",
  };
  const setLightMode = (m) => {
    state.lightMode = m;
    document.querySelectorAll("[data-light]").forEach((b) =>
      b.classList.toggle("active", b.dataset.light === m)
    );
    document.getElementById("lbl-light-mode").textContent = lightNames[m] || m;
    applyExplodeAndVisibility();
    updateSimulation(0.0);
  };
  document.querySelectorAll("[data-light]").forEach((btn) => {
    btn.addEventListener("click", () => setLightMode(btn.dataset.light));
  });

  // Magic Wand Planet LED Controls
  const btnWandTapNext = document.getElementById("btn-wand-tap-next");
  if (btnWandTapNext) {
    btnWandTapNext.addEventListener("click", () => {
      if (planetLedActors.length > 0) {
        const target = planetLedActors[nextWandPlanetIdx % planetLedActors.length];
        nextWandPlanetIdx = (nextWandPlanetIdx + 1) % planetLedActors.length;
        triggerMagicWandOnPlanet(target.key);
      }
    });
  }
  const btnWandCycleAll = document.getElementById("btn-wand-cycle-all");
  if (btnWandCycleAll) {
    btnWandCycleAll.addEventListener("click", () => {
      allPlanetsModeIndex = (allPlanetsModeIndex + 1) % 4;
      planetLedActors.forEach((pl) => {
        pl.mode = allPlanetsModeIndex;
      });
      dynamicMarbles.forEach((m) => {
        m.ledMode = allPlanetsModeIndex;
      });
      const statusEl = document.getElementById("lbl-wand-status");
      if (statusEl) {
        statusEl.textContent = `14× ${LED_MODE_NAMES[allPlanetsModeIndex]}`;
      }
    });
  }

  // Quick Explode in Simulator
  document.getElementById("slider-sim-explode").addEventListener("input", (e) => {
    state.simExplodePct = Number(e.target.value);
    document.getElementById("lbl-sim-explode").textContent = `${state.simExplodePct}%`;
    applyExplodeAndVisibility();
  });

  // 3D Rigid-Body Physics Surface Preset Selector
  const selPhysPreset = document.getElementById("sel-phys-preset");
  if (selPhysPreset) {
    selPhysPreset.addEventListener("change", (e) => {
      const key = e.target.value;
      if (PHYSICS_PRESETS[key]) {
        state.physPreset = key;
        const p = PHYSICS_PRESETS[key];
        const lbl = document.getElementById("lbl-phys-preset");
        if (lbl) lbl.textContent = p.badge;
        gravLab.kappa = p.kappa;
        const selMarbleEl = document.getElementById("sel-grav-marble");
        if (selMarbleEl) selMarbleEl.value = String(p.kappa.toFixed(2));
        updateGravityLabUI();
      }
    });
  }

  // Newton Gravity Lab Controls (Gate Pair, Marble Inertia κ, Manual Stopwatch & Auto-Sim)
  const selGates = document.getElementById("sel-grav-gates");
  if (selGates) {
    selGates.addEventListener("change", (e) => {
      const [sId, eId] = e.target.value.split("-").map(Number);
      gravLab.startGate = sId;
      gravLab.endGate = eId;
      gravLab.trials = [];
      updateGravityLabUI();
    });
  }
  const selMarble = document.getElementById("sel-grav-marble");
  if (selMarble) {
    selMarble.addEventListener("change", (e) => {
      gravLab.kappa = Number(e.target.value);
      const lblK = document.getElementById("lbl-grav-kappa");
      if (lblK) {
        const labelMap = {
          "1.48": "κ = 1.48 (Y-Shape LED KC012)",
          "1.46": "κ = 1.46 (LED + M8 Nut)",
          "1.42": "κ = 1.42 (Steel Ball)",
          "1.54": "κ = 1.54 (Hollow PLA)",
        };
        lblK.textContent = labelMap[e.target.value] || `κ = ${gravLab.kappa}`;
      }
      updateGravityLabUI();
    });
  }
  const btnStopwatch = document.getElementById("btn-grav-stopwatch");
  const badgeGrav = document.getElementById("grav-lab-badge");
  if (btnStopwatch) {
    btnStopwatch.addEventListener("click", () => {
      if (!gravLab.manualRunning) {
        gravLab.manualRunning = true;
        gravLab.manualStartTime = performance.now();
        btnStopwatch.classList.add("active");
        if (badgeGrav) badgeGrav.textContent = "TIMING PHYSICAL...";
      } else {
        const dtSec = (performance.now() - gravLab.manualStartTime) / 1000.0;
        gravLab.manualRunning = false;
        btnStopwatch.classList.remove("active");
        btnStopwatch.textContent = "⏱️ Tap Start Gate (Physical)";
        if (badgeGrav) badgeGrav.textContent = gravLab.autoSim ? "AUTO-TIMING" : "MANUAL MODE";
        recordGravityTrial(dtSec, "Physical Stopwatch");
      }
    });
  }
  const btnGravAuto = document.getElementById("btn-grav-auto");
  if (btnGravAuto) {
    btnGravAuto.addEventListener("click", () => {
      gravLab.autoSim = !gravLab.autoSim;
      btnGravAuto.classList.toggle("active", gravLab.autoSim);
      btnGravAuto.textContent = gravLab.autoSim
        ? "🤖 Auto-Log 3D Sim: ON"
        : "🤖 Auto-Log 3D Sim: OFF";
      if (badgeGrav && !gravLab.manualRunning) {
        badgeGrav.textContent = gravLab.autoSim ? "AUTO-TIMING" : "MANUAL MODE";
      }
    });
  }
  const btnGravReset = document.getElementById("btn-grav-reset");
  if (btnGravReset) {
    btnGravReset.addEventListener("click", () => {
      gravLab.trials = [];
      gravLab.manualRunning = false;
      if (btnStopwatch) {
        btnStopwatch.classList.remove("active");
        btnStopwatch.textContent = "⏱️ Tap Start Gate (Physical)";
      }
      updateGravityLabUI();
    });
  }
  const inpGravDt = document.getElementById("inp-grav-dt");
  const btnGravLogDt = document.getElementById("btn-grav-log-dt");
  const logManualInputTrial = () => {
    if (!inpGravDt) return;
    const val = parseFloat(inpGravDt.value);
    if (Number.isFinite(val) && val > 0.05 && val < 60.0) {
      recordGravityTrial(val, "Phyphox / Manual Δt");
      inpGravDt.value = "";
    }
  };
  if (btnGravLogDt) {
    btnGravLogDt.addEventListener("click", logManualInputTrial);
  }
  if (inpGravDt) {
    inpGravDt.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        logManualInputTrial();
      }
    });
  }
  updateGravityLabUI();

  // Subsystem Filter Checkboxes
  const subList = document.getElementById("subsystem-toggles");
  Object.entries(SUBSYSTEM_LABELS).forEach(([key, label]) => {
    const row = document.createElement("div");
    row.className = "subsys-item";
    row.innerHTML = `
      <label>
        <input type="checkbox" checked data-subsys="${key}" />
        <span>${label}</span>
      </label>
      <button class="subsys-focus-btn" data-focus="${key}">Focus</button>
    `;
    row.querySelector("input").addEventListener("change", (e) => {
      subsystemVisibility[key] = e.target.checked;
      applyExplodeAndVisibility();
    });
    row.querySelector("button").addEventListener("click", () => focusSubsystem(key));
    subList.appendChild(row);
  });

  // Assembly Panel Controls
  const asmSlider = document.getElementById("slider-asm-explode");
  const setAsmExplode = (val) => {
    state.asmExplodePct = Number(val);
    asmSlider.value = String(state.asmExplodePct);
    document.getElementById("lbl-asm-explode").textContent =
      state.asmExplodePct === 0
        ? "0% Assembled"
        : `${state.asmExplodePct}% Exploded`;
    applyExplodeAndVisibility();
  };
  asmSlider.addEventListener("input", (e) => setAsmExplode(e.target.value));
  document.getElementById("btn-explode-0").addEventListener("click", () => setAsmExplode(0));
  document.getElementById("btn-explode-45").addEventListener("click", () => setAsmExplode(45));
  document.getElementById("btn-explode-100").addEventListener("click", () => setAsmExplode(100));

  document.getElementById("chk-ghost-future").addEventListener("change", (e) => {
    state.ghostFutureSteps = e.target.checked;
    applyExplodeAndVisibility();
  });

  // Step Dots (1..12)
  const totalSteps = manifest.assembly_steps.length;
  const dotsContainer = document.getElementById("step-dots");
  manifest.assembly_steps.forEach((s) => {
    const b = document.createElement("button");
    b.className = "step-dot";
    b.textContent = String(s.step);
    b.addEventListener("click", () => setAssemblyStep(s.step, true));
    dotsContainer.appendChild(b);
  });

  // Track Segment Connection Inspector (Seg 01 -> Seg 14 + Clip + First/Last Port Focus)
  const chkTrackAutoCam = document.getElementById("chk-track-autocam");
  if (chkTrackAutoCam) {
    chkTrackAutoCam.addEventListener("change", (e) => {
      state.trackAutoCam = e.target.checked;
    });
  }

  const chipsContainer = document.getElementById("track-seg-chips");
  if (chipsContainer) {
    TRACK_PIECE_SPECS.forEach((spec) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = `track-seg-chip ${spec.chipClass || ""}`;
      chip.dataset.pieceIdx = String(spec.pieceIdx);
      chip.textContent = spec.chipLabel;
      chip.title = spec.title;
      chip.addEventListener("click", () => {
        state.focusedPortMode = null;
        selectTrackPieceInStep7(spec.pieceIdx);
      });
      chipsContainer.appendChild(chip);
    });
  }

  const btnS01Port = document.getElementById("btn-focus-seg01-port");
  if (btnS01Port) {
    btnS01Port.addEventListener("click", () => {
      state.focusedPortMode = "start-port";
      selectTrackPieceInStep7(0, { pos: [-110, -195, 96], look: [4, -34, 56] });
    });
  }

  const btnS01Seam = document.getElementById("btn-focus-seg01-seam");
  if (btnS01Seam) {
    btnS01Seam.addEventListener("click", () => {
      state.focusedPortMode = "first-seam";
      selectTrackPieceInStep7(1, { pos: [-205, 125, 118], look: [-68, 40, 64] });
    });
  }

  const btnS14Seam = document.getElementById("btn-focus-seg14-seam");
  if (btnS14Seam) {
    btnS14Seam.addEventListener("click", () => {
      state.focusedPortMode = "last-seam";
      selectTrackPieceInStep7(14, { pos: [145, 145, 455], look: [32, 54, 406] });
    });
  }

  const btnS14Port = document.getElementById("btn-focus-seg14-port");
  if (btnS14Port) {
    btnS14Port.addEventListener("click", () => {
      state.focusedPortMode = "end-port";
      selectTrackPieceInStep7(14, { pos: [115, -185, 462], look: [0, -34, 432] });
    });
  }

  // Electronics Quick-Jump Buttons (Steps 1, 2, 8, 9)
  document.querySelectorAll(".elec-jump-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetStep = Number(btn.dataset.elecStep);
      state.showElectronics = true;
      const chkElec = document.getElementById("chk-electronics");
      if (chkElec) chkElec.checked = true;
      setAssemblyStep(targetStep, true);
    });
  });

  document.getElementById("btn-step-prev").addEventListener("click", () => {
    setAssemblyStep(state.asmCurrentStep - 1, true);
  });
  document.getElementById("btn-step-next").addEventListener("click", () => {
    setAssemblyStep(state.asmCurrentStep + 1, true);
  });

  // Piece-by-Piece Connection Controls (Prev Piece / Replay Step / Next Piece)
  const btnReplayStep = document.getElementById("btn-step-replay");
  if (btnReplayStep) {
    btnReplayStep.addEventListener("click", () => {
      state.stepAnimElapsed = 0.0;
      state.stepTargetMaxTime = Infinity;
      applyExplodeAndVisibility();
      updatePieceConnectionUI();
    });
  }

  const btnPieceNext = document.getElementById("btn-piece-next");
  if (btnPieceNext) {
    btnPieceNext.addEventListener("click", () => {
      const groups = getStepSubGroups(state.asmCurrentStep);
      // Find first piece group that hasn't finished connecting yet
      let targetGroup = groups.find((g) => state.stepAnimElapsed < g.endTime - 0.02);
      if (targetGroup) {
        state.stepAnimElapsed = targetGroup.subDelay;
        state.stepTargetMaxTime = targetGroup.endTime;
        applyExplodeAndVisibility();
        updatePieceConnectionUI();
      } else if (state.asmCurrentStep < totalSteps) {
        const nextGroups = getStepSubGroups(state.asmCurrentStep + 1);
        setAssemblyStep(state.asmCurrentStep + 1, true, nextGroups[0].endTime);
      }
    });
  }

  const btnPiecePrev = document.getElementById("btn-piece-prev");
  if (btnPiecePrev) {
    btnPiecePrev.addEventListener("click", () => {
      const groups = getStepSubGroups(state.asmCurrentStep);
      let activeIdx = 0;
      for (let i = 0; i < groups.length; i++) {
        if (state.stepAnimElapsed >= groups[i].subDelay + 0.02) {
          activeIdx = i;
        }
      }
      if (activeIdx > 0) {
        const prevG = groups[activeIdx - 1];
        state.stepAnimElapsed = prevG.subDelay;
        state.stepTargetMaxTime = prevG.endTime;
        applyExplodeAndVisibility();
        updatePieceConnectionUI();
      } else if (state.asmCurrentStep > 1) {
        const prevStepGroups = getStepSubGroups(state.asmCurrentStep - 1);
        const lastG = prevStepGroups[prevStepGroups.length - 1];
        setAssemblyStep(state.asmCurrentStep - 1, true, lastG.endTime);
        state.stepAnimElapsed = lastG.subDelay;
      } else {
        state.stepAnimElapsed = 0.0;
        state.stepTargetMaxTime = groups[0].endTime;
        applyExplodeAndVisibility();
        updatePieceConnectionUI();
      }
    });
  }

  let autoPlayTimer = null;
  const playBtn = document.getElementById("btn-step-play");
  playBtn.addEventListener("click", () => {
    if (autoPlayTimer) {
      clearInterval(autoPlayTimer);
      autoPlayTimer = null;
      playBtn.textContent = "▶ Auto-Play All Steps";
    } else {
      if (state.asmCurrentStep >= totalSteps) setAssemblyStep(1, true);
      else {
        state.stepAnimElapsed = 0.0;
        state.stepTargetMaxTime = Infinity;
      }
      playBtn.textContent = "⏸ Pause Tour";
      autoPlayTimer = setInterval(() => {
        const groups = getStepSubGroups(state.asmCurrentStep);
        const stepDur = groups[groups.length - 1].endTime + 0.6;
        if (state.stepAnimElapsed < stepDur) {
          return;
        }
        if (state.asmCurrentStep < totalSteps) {
          setAssemblyStep(state.asmCurrentStep + 1, true);
        } else {
          clearInterval(autoPlayTimer);
          autoPlayTimer = null;
          playBtn.textContent = "▶ Auto-Play All Steps";
        }
      }, 400);
    }
  });

  setAssemblyStep(1, false);

  // Plate Inspector Studio Lighting Preset & Exposure Controls
  const plateLightLabels = {
    studio: "☀️ High-Contrast Studio",
    detail: "🔍 Grazing Socket Detail",
    soft: "💡 Soft Shadowless",
  };
  document.querySelectorAll("[data-plate-light]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.plateLight;
      state.plateLightPreset = mode;
      document.querySelectorAll("[data-plate-light]").forEach((b) =>
        b.classList.toggle("active", b.dataset.plateLight === mode)
      );
      const lbl = document.getElementById("lbl-plate-light-mode");
      if (lbl) lbl.textContent = plateLightLabels[mode] || mode;
      updateSimulation(0.0);
    });
  });

  const sliderPlateExp = document.getElementById("slider-plate-exposure");
  if (sliderPlateExp) {
    sliderPlateExp.addEventListener("input", (e) => {
      state.plateExposurePct = Number(e.target.value);
      const lblExp = document.getElementById("lbl-plate-exposure");
      if (lblExp) lblExp.textContent = `${state.plateExposurePct}%`;
      updateSimulation(0.0);
    });
  }

  // Plate Selector List
  const plateList = document.getElementById("plate-selector-list");
  manifest.plates.forEach((p, idx) => {
    const btn = document.createElement("button");
    btn.className = `plate-select-btn ${idx === 0 ? "active" : ""}`;
    btn.dataset.plate = String(idx);
    btn.innerHTML = `<strong>${p.title}</strong><span>${p.meshes.length} pre-oriented parts @ Z = 0.00 mm</span>`;
    btn.addEventListener("click", () => selectBuildPlate(idx));
    plateList.appendChild(btn);
  });
  const allBtn = document.createElement("button");
  allBtn.className = "plate-select-btn";
  allBtn.dataset.plate = "-1";
  allBtn.innerHTML = `<strong>All 12 Build Plates (OrcaSlicer 4×3 Grid — 324 mm Stride)</strong><span>View complete GravMass_Tree_Ultimate_U1.3mf 2D layout</span>`;
  allBtn.addEventListener("click", () => selectBuildPlate(-1));
  plateList.appendChild(allBtn);

  // Slicer Z-Height Cross-Section Slider
  const sliceSlider = document.getElementById("slider-slice-z");
  const setSliceZ = (zVal) => {
    state.sliceZ = Number(zVal);
    sliceSlider.value = String(state.sliceZ);
    clipPlane.constant = state.sliceZ;
    const layerNum = Math.round(state.sliceZ / 0.2);
    document.getElementById("lbl-slice-z").textContent =
      state.sliceZ >= 219.5
        ? "Full Height (100%)"
        : `Z = ${state.sliceZ.toFixed(2)} mm (Layer ${layerNum} @ 0.20 mm)`;
  };
  sliceSlider.addEventListener("input", (e) => setSliceZ(e.target.value));
  document.querySelectorAll(".btn-pause-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      const z = Number(btn.dataset.z);
      setSliceZ(z);
      if (z < 5.0) {
        selectBuildPlate(10); // Plate 11 (Warm & Gas-Giant Planets)
      } else if (z < 30.0) {
        selectBuildPlate(8); // Plate 9 (Red Apple Marbles)
      }
    });
  });
}

function focusSubsystem(subsysKey) {
  const targets = {
    trunk_base: { pos: [210, -210, 110], look: [0, 0, 50] },
    trunk_mid: { pos: [-220, -220, 260], look: [0, 0, 225] },
    trunk_top: { pos: [210, -210, 410], look: [0, 0, 375] },
    auger_lower: { pos: [180, -180, 150], look: [0, 0, 120] },
    auger_upper: { pos: [180, -180, 350], look: [0, 0, 320] },
    clutch: { pos: [130, -130, 65], look: [0, 0, 37] },
    brackets: { pos: [280, -260, 230], look: [0, 0, 200] },
    track: { pos: [380, -380, 280], look: [0, 0, 220] },
    topper: { pos: [195, -195, 535], look: [0, 0, 482] },
    planets: { pos: [390, -370, 290], look: [0, 0, 230] },
    marbles: { pos: [340, -340, 280], look: [0, 0, 230] },
  };
  const t = targets[subsysKey];
  if (t) {
    if (
      subsysKey === "auger_lower" ||
      subsysKey === "auger_upper" ||
      subsysKey === "clutch"
    ) {
      state.xrayActive = true;
      document.getElementById("chk-xray").checked = true;
      applyExplodeAndVisibility();
    }
    camAnim = {
      targetPos: new THREE.Vector3(...t.pos),
      targetLook: new THREE.Vector3(...t.look),
      timeLeft: 0.65,
    };
  }
}

function triggerMagicWandOnPlanet(planetKey) {
  const pl = planetLedActors.find((p) => p.key === planetKey);
  if (!pl) return;

  // Cycle planet LED mode: 1 (Steady) -> 2 (Breathe) -> 3 (Flash) -> 0 (Off) -> 1
  pl.mode = (pl.mode + 1) % 4;
  const statusEl = document.getElementById("lbl-wand-status");
  if (statusEl) {
    statusEl.textContent = `${pl.name}: ${LED_MODE_NAMES[pl.mode]}`;
  }

  // Compute vector from the wand's star tip in assembly space (docked upright in the +30°
  // trunk_base Root-Flare Holster Socket at (45.03, 26.00, 101.1)) to just outside the target planet
  const starTipHome = new THREE.Vector3(45.03, 26.00, 101.1);
  const rad = (pl.deg * Math.PI) / 180.0;
  const radialDir = new THREE.Vector3(Math.cos(rad), Math.sin(rad), 0.0);
  const targetTipPos = pl.pos.clone().addScaledVector(radialDir, 12.0);
  wandTapAnim = {
    deltaVec: targetTipPos.sub(starTipHome),
    radialDir,
    elapsed: 0.0,
    duration: 0.95,
  };
}

function triggerMagicWandOnMarble(marbleIdx) {
  const m = dynamicMarbles[marbleIdx];
  if (!m) return;

  // Cycle marble LED mode: 1 (Steady) -> 2 (Breathe) -> 3 (Flash) -> 0 (Off) -> 1
  m.ledMode = (m.ledMode + 1) % 4;
  const statusEl = document.getElementById("lbl-wand-status");
  if (statusEl) {
    statusEl.textContent = `Marble #${marbleIdx + 1}: ${LED_MODE_NAMES[m.ledMode]}`;
  }

  const starTipHome = new THREE.Vector3(45.03, 26.00, 101.1);
  const mPos = m.group.position.clone();
  const radialDir = new THREE.Vector3(mPos.x, mPos.y, 0.0);
  if (radialDir.lengthSq() < 1.0) {
    radialDir.set(0.0, -1.0, 0.0);
  } else {
    radialDir.normalize();
  }
  const targetTipPos = mPos.addScaledVector(radialDir, 14.0);
  wandTapAnim = {
    deltaVec: targetTipPos.sub(starTipHome),
    radialDir,
    elapsed: 0.0,
    duration: 0.85,
  };
}

function setupRaycasterTooltip() {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  const tooltip = document.getElementById("part-tooltip");
  const canvas = renderer.domElement;
  let pointerDownPos = { x: 0, y: 0 };

  canvas.addEventListener("pointerdown", (e) => {
    pointerDownPos = { x: e.clientX, y: e.clientY };
  });

  const getVisibleInteractiveTargets = () => {
    if (state.mode === "plates") {
      return platesRoot.children.filter((c) => c.visible);
    }
    const list = [];
    assembledRoot.children.forEach((c) => {
      if (c.visible) list.push(c);
    });
    if (electronicsGroup && electronicsGroup.visible) {
      electronicsGroup.children.forEach((c) => {
        if (c.visible) list.push(c);
      });
    }
    if (trackJointsGroup && trackJointsGroup.visible) {
      trackJointsGroup.children.forEach((c) => {
        if (c.visible) list.push(c);
      });
    }
    return list;
  };

  canvas.addEventListener("pointerup", (e) => {
    if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 8) return;
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(getVisibleInteractiveTargets(), true);
    if (hits.length > 0) {
      const obj = hits[0].object;
      const label = obj.userData?.label || obj.parent?.userData?.label;
      if (label && e.pointerType === "touch") {
        tooltip.textContent = label;
        tooltip.classList.remove("hidden");
      }
      if (state.mode !== "plates") {
        const tpIdx =
          obj.userData?.track_piece_idx ??
          obj.parent?.userData?.track_piece_idx ??
          obj.parent?.parent?.userData?.track_piece_idx;
        if (typeof tpIdx === "number" && state.mode === "assembly") {
          state.focusedPortMode = null;
          selectTrackPieceInStep7(tpIdx);
          return;
        }
        const pKey = obj.userData?.planet_id || obj.parent?.userData?.planet_id;
        if (pKey) {
          triggerMagicWandOnPlanet(pKey);
        } else {
          const mIdx =
            obj.userData?.marble_idx ??
            obj.parent?.userData?.marble_idx ??
            obj.parent?.parent?.userData?.marble_idx;
          if (typeof mIdx === "number") {
            triggerMagicWandOnMarble(mIdx);
          }
        }
      }
    } else if (e.pointerType === "touch") {
      tooltip.classList.add("hidden");
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(getVisibleInteractiveTargets(), true);

    if (hits.length > 0) {
      let obj = hits[0].object;
      let label = obj.userData?.label || obj.parent?.userData?.label;
      if (label) {
        tooltip.textContent = label;
        tooltip.style.left = `${e.clientX - rect.left + 14}px`;
        tooltip.style.top = `${e.clientY - rect.top + 14}px`;
        tooltip.classList.remove("hidden");
        return;
      }
    }
    tooltip.classList.add("hidden");
  });

  canvas.addEventListener("pointerleave", () => {
    tooltip.classList.add("hidden");
  });
}

function onWindowResize() {
  const canvas = renderer.domElement;
  const viewport = canvas.parentElement;
  camera.aspect = viewport.clientWidth / viewport.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
}

init();
