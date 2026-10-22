// Scientific Analytical Palettes for LiDAR Rendering (Uint32 ABGR format for fast Uint32Array blitting)
const turboPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  const r = Math.max(0, Math.min(1, 0.1357 + x * (4.6153 + x * (-42.6603 + x * (132.131 + x * (-152.9423 + x * 59.2863))))));
  const g = Math.max(0, Math.min(1, 0.0914 + x * (2.1941 + x * (4.8429 + x * (-14.1850 + x * (4.2773 + x * 2.8295))))));
  const b = Math.max(0, Math.min(1, 0.1067 + x * (12.5841 + x * (-86.8524 + x * (230.3101 + x * (-267.9254 + x * 113.8821))))));
  turboPalette[i] = (0xFF000000) | ((Math.round(b * 255) & 0xFF) << 16) | ((Math.round(g * 255) & 0xFF) << 8) | (Math.round(r * 255) & 0xFF);
}
const elevPalette = turboPalette;

const SPECTRAL_STOPS = [
  [0.0, 158, 1, 66],     // #9e0142 (-35° Red)
  [0.1, 213, 62, 79],    // #d53e4f
  [0.2, 244, 109, 67],   // #f46d43
  [0.3, 253, 174, 97],   // #fdae61
  [0.4, 254, 224, 139],  // #fee08b
  [0.5, 255, 255, 191],  // #ffffbf (0° Nadir Yellow)
  [0.6, 230, 245, 152],  // #e6f598
  [0.7, 171, 221, 164],  // #abdda4
  [0.8, 102, 194, 165],  // #66c2a5
  [0.9, 50, 136, 189],   // #3288bd
  [1.0, 94, 79, 162]     // #5e4fa2 (+35° Blue)
];
const spectralPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const t = i / 255.0;
  let idx = 0;
  while (idx < SPECTRAL_STOPS.length - 2 && t > SPECTRAL_STOPS[idx + 1][0]) {
    idx++;
  }
  const s0 = SPECTRAL_STOPS[idx];
  const s1 = SPECTRAL_STOPS[idx + 1];
  const u = Math.max(0, Math.min(1, (t - s0[0]) / (s1[0] - s0[0])));
  const r = Math.round(s0[1] + u * (s1[1] - s0[1]));
  const g = Math.round(s0[2] + u * (s1[2] - s0[2]));
  const b = Math.round(s0[3] + u * (s1[3] - s0[3]));
  spectralPalette[i] = (0xFF000000) | ((b & 0xFF) << 16) | ((g & 0xFF) << 8) | (r & 0xFF);
}

const PLASMA_STOPS = [
  [0.00, 13, 8, 135],    // #0d0887 (Deep Blue / Start)
  [0.20, 106, 0, 168],   // #6a00a8 (Purple)
  [0.40, 177, 42, 144],  // #b12a90 (Magenta)
  [0.60, 225, 100, 98],  // #e16462 (Coral)
  [0.80, 252, 166, 54],  // #fca636 (Orange/Gold)
  [1.00, 240, 249, 33]   // #f0f921 (Bright Yellow / End)
];
const plasmaPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const t = i / 255.0;
  let idx = 0;
  while (idx < PLASMA_STOPS.length - 2 && t > PLASMA_STOPS[idx + 1][0]) {
    idx++;
  }
  const s0 = PLASMA_STOPS[idx];
  const s1 = PLASMA_STOPS[idx + 1];
  const u = Math.max(0, Math.min(1, (t - s0[0]) / (s1[0] - s0[0])));
  const r = Math.round(s0[1] + u * (s1[1] - s0[1]));
  const g = Math.round(s0[2] + u * (s1[2] - s0[2]));
  const b = Math.round(s0[3] + u * (s1[3] - s0[3]));
  plasmaPalette[i] = (0xFF000000) | ((b & 0xFF) << 16) | ((g & 0xFF) << 8) | (r & 0xFF);
}

const ndviPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  let r, g, b;
  if (x < 0.35) {
    const t = x / 0.35;
    r = 180 + t * 40; g = 100 + t * 60; b = 60 + t * 20;
  } else if (x < 0.6) {
    const t = (x - 0.35) / 0.25;
    r = 220 - t * 100; g = 160 + t * 60; b = 80 - t * 40;
  } else {
    const t = (x - 0.6) / 0.4;
    r = 120 - t * 100; g = 220 + t * 20; b = 40 + t * 20;
  }
  ndviPalette[i] = (0xFF000000) | ((Math.round(b) & 0xFF) << 16) | ((Math.round(g) & 0xFF) << 8) | (Math.round(r) & 0xFF);
}

const bluesPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  const r = Math.round(240 - 220 * x);
  const g = Math.round(245 - 120 * x);
  const b = Math.round(255 - 20 * (1 - x));
  bluesPalette[i] = (0xFF000000) | ((b & 0xFF) << 16) | ((g & 0xFF) << 8) | (r & 0xFF);
}

function hexToUint32(hex) {
  const c = parseInt(hex.replace('#', ''), 16);
  const r = (c >> 16) & 0xFF;
  const g = (c >> 8) & 0xFF;
  const b = c & 0xFF;
  return (0xFF000000) | (b << 16) | (g << 8) | r;
}

const CATEGORICAL_HEXES = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#EC4899', '#F97316'];
function categoricalColor(val) {
  const hex = CATEGORICAL_HEXES[Math.abs(val | 0) % CATEGORICAL_HEXES.length];
  return hexToUint32(hex);
}

// ASPRS Standard Classification Palette
const classColorMap = {
  0: hexToUint32('#94A3B8'), // 0: Never Classified / Unclassified (Slate)
  1: hexToUint32('#CBD5E1'), // 1: Unassigned
  2: hexToUint32('#D4A373'), // 2: Ground (Light Brown / Tan)
  3: hexToUint32('#86EFAC'), // 3: Low Veg (Mint)
  4: hexToUint32('#22C55E'), // 4: Med Veg (Green)
  5: hexToUint32('#15803D'), // 5: High Veg / Canopy (Forest Green)
  6: hexToUint32('#EF4444'), // 6: Building / Rooftops (Crimson Red)
  7: hexToUint32('#8B7464'), // 7: Low Point / Noise
  8: hexToUint32('#F59E0B'), // 8: Model Keypoint (Amber)
  9: hexToUint32('#0284C7'), // 9: Water (Sky Blue)
  10: hexToUint32('#A855F7'), // 10: Rail (Magenta)
  11: hexToUint32('#475569'), // 11: Road Surface (Asphalt)
  12: hexToUint32('#EC4899'), // 12: Overlap (Pink)
  13: hexToUint32('#EAB308'), // 13: Wire - Guard (Yellow)
  14: hexToUint32('#F97316'), // 14: Wire - Conductor (Orange)
  15: hexToUint32('#84CC16'), // 15: Transmission Tower (Lime)
  17: hexToUint32('#78716C'), // 17: Bridge Deck (Stone)
  18: hexToUint32('#06B6D4')  // 18: High Noise (Cyan)
};
const defaultPointColor = hexToUint32('#94A3B8');

function decodeBuffer(buf) {
  if (!buf) return null;
  if (typeof buf === 'string') {
    const s = atob(buf);
    const bytes = new Uint8Array(s.length);
    for (let k = 0; k < s.length; k++) bytes[k] = s.charCodeAt(k);
    return bytes;
  }
  return buf;
}
