// Point Cloud Canvas Rendering Engine - High Performance Analytical & Classified LiDAR Renderer
const pcCanvas = document.getElementById('pointCloudCanvas');
const pcCtx = pcCanvas.getContext('2d');
let pointCloudData = [];
let pointCloudBatch = null;
let lidarColorMode = 'rgb_elev';
let userPointSize = 4.5;
let isPointCloudVisible = true;
let activePointCloudId = null;
let pcMinZ = 0;
let pcMaxZ = 1000;

function resizeCanvas() {
  if (typeof map === 'undefined') return;
  const viewport = map.getViewport();
  if (!viewport) return;
  pcCanvas.width = viewport.clientWidth;
  pcCanvas.height = viewport.clientHeight;
  renderPointCloud();
}
window.addEventListener('resize', resizeCanvas);
setTimeout(resizeCanvas, 200);

// ── Scientific Analytical Palettes (Uint32 ABGR format for fast Uint32Array blitting) ──
const turboPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  const r = Math.max(0, Math.min(1, 0.1357 + x * (4.6153 + x * (-42.6603 + x * (132.131 + x * (-152.9423 + x * 59.2863))))));
  const g = Math.max(0, Math.min(1, 0.0914 + x * (2.1941 + x * (4.8429 + x * (-14.1850 + x * (4.2773 + x * 2.8295))))));
  const b = Math.max(0, Math.min(1, 0.1067 + x * (12.5841 + x * (-86.8524 + x * (230.3101 + x * (-267.9254 + x * 113.8821))))));
  turboPalette[i] = (0xFF000000) | ((Math.round(b * 255) & 0xFF) << 16) | ((Math.round(g * 255) & 0xFF) << 8) | (Math.round(r * 255) & 0xFF);
}
const elevPalette = turboPalette;

const spectralPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  const r = Math.max(0, Math.min(1, 1.5 - Math.abs(4.0 * x - 3.0)));
  const g = Math.max(0, Math.min(1, 1.5 - Math.abs(4.0 * x - 2.0)));
  const b = Math.max(0, Math.min(1, 1.5 - Math.abs(4.0 * x - 1.0)));
  spectralPalette[i] = (0xFF000000) | ((Math.round(b * 255) & 0xFF) << 16) | ((Math.round(g * 255) & 0xFF) << 8) | (Math.round(r * 255) & 0xFF);
}

const plasmaPalette = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  const x = i / 255.0;
  const r = Math.max(0, Math.min(1, 0.05 + 0.9 * x));
  const g = Math.max(0, Math.min(1, 0.1 + 0.8 * Math.pow(x, 1.5)));
  const b = Math.max(0, Math.min(1, 0.5 + 0.5 * (1.0 - x)));
  plasmaPalette[i] = (0xFF000000) | ((Math.round(b * 255) & 0xFF) << 16) | ((Math.round(g * 255) & 0xFF) << 8) | (Math.round(r * 255) & 0xFF);
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
  2: hexToUint32('#D2A373'), // 2: Ground (Tan/Brown)
  3: hexToUint32('#84F0AB'), // 3: Low Veg (Mint)
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

function renderPointCloud() {
  if (typeof map === 'undefined') return;
  const viewport = map.getViewport();
  const currentWidth = viewport ? viewport.clientWidth : window.innerWidth;
  const currentHeight = viewport ? viewport.clientHeight : window.innerHeight;
  if (currentWidth > 0 && currentHeight > 0 && (pcCanvas.width !== currentWidth || pcCanvas.height !== currentHeight)) {
    pcCanvas.width = currentWidth;
    pcCanvas.height = currentHeight;
  }

  const width = pcCanvas.width;
  const height = pcCanvas.height;
  if (width <= 0 || height <= 0) return;

  if (!isPointCloudVisible) {
    pcCtx.clearRect(0, 0, width, height);
    return;
  }

  const hasBatch = pointCloudBatch && pointCloudBatch.count > 0;
  const hasPoints = pointCloudData && pointCloudData.length > 0;
  if (!hasBatch && !hasPoints) {
    pcCtx.clearRect(0, 0, width, height);
    return;
  }

  const count = hasBatch ? pointCloudBatch.count : pointCloudData.length;
  const imgData = pcCtx.createImageData(width, height);
  const buf32 = new Uint32Array(imgData.data.buffer);
  const zRange = Math.max(1, pcMaxZ - pcMinZ);

  const mapSize = map.getSize() || [width, height];
  const extent = mapView.calculateExtent(mapSize);
  const minExtentX = extent[0];
  const maxExtentY = extent[3];
  const invRes = 1.0 / mapView.getResolution();

  let radius = 0;
  let threshold = 0;
  if (userPointSize >= 3.0) {
    radius = 2;
    threshold = 5;
  } else if (userPointSize >= 1.5) {
    radius = 1;
    threshold = 2;
  }

  const batch = pointCloudBatch;
  const pts = pointCloudData;

  const rBytes = hasBatch ? decodeBuffer(batch.r) : null;
  const gBytes = hasBatch ? decodeBuffer(batch.g) : null;
  const bBytes = hasBatch ? decodeBuffer(batch.b) : null;
  const cBytes = hasBatch ? decodeBuffer(batch.c) : null;
  const iBytes = hasBatch ? decodeBuffer(batch.i) : null;
  const rnBytes = hasBatch ? decodeBuffer(batch.rn) : null;
  const nrBytes = hasBatch ? decodeBuffer(batch.nr) : null;
  const saBytes = hasBatch ? decodeBuffer(batch.sa) : null;
  const psRaw = hasBatch ? decodeBuffer(batch.ps) : null;
  const psU16 = psRaw ? new Uint16Array(psRaw.buffer, psRaw.byteOffset, Math.floor(psRaw.byteLength / 2)) : null;
  const flBytes = hasBatch ? decodeBuffer(batch.fl) : null;
  const nirBytes = hasBatch ? decodeBuffer(batch.nir) : null;

  const fileHasRgb = hasBatch ? (batch.hasRgb === true || (rBytes !== null && rBytes.length > 0)) : (pts[0] && pts[0].r !== undefined);

  const firstX = hasBatch ? (batch.x && batch.x[0]) : (pts[0] && (pts[0].x !== undefined ? pts[0].x : pts[0].X));
  const isDegree = firstX !== undefined && Math.abs(firstX) <= 180;
  const originShift = 20037508.342789244;
  const toMercX = originShift / 180.0;
  const toMercYFactor = originShift / Math.PI;

  const xs = hasBatch ? batch.x : null;
  const ys = hasBatch ? batch.y : null;
  const zs = hasBatch ? batch.z : null;

  // Pre-calculate density grid if Point Density mode is active
  let densityGrid = null;
  const cellShift = 5; // 32x32 pixel cells
  const gridW = (width >> cellShift) + 1;
  const gridH = (height >> cellShift) + 1;
  if (lidarColorMode === 'point_density') {
    densityGrid = new Uint16Array(gridW * gridH);
    for (let i = 0; i < count; i++) {
      const x = hasBatch ? xs[i] : (pts[i].x !== undefined ? pts[i].x : pts[i].X);
      const y = hasBatch ? ys[i] : (pts[i].y !== undefined ? pts[i].y : pts[i].Y);
      if (x === undefined || y === undefined) continue;
      let mx, my;
      if (isDegree) {
        mx = x * toMercX;
        const latRad = y * 0.017453292519943295;
        my = toMercYFactor * Math.log((1 + Math.sin(latRad)) / (1 - Math.sin(latRad))) * 0.5;
      } else {
        mx = x; my = y;
      }
      const px = ((mx - minExtentX) * invRes) | 0;
      const py = ((maxExtentY - my) * invRes) | 0;
      const gx = px >> cellShift;
      const gy = py >> cellShift;
      if (gx >= 0 && gx < gridW && gy >= 0 && gy < gridH) {
        densityGrid[gy * gridW + gx]++;
      }
    }
  }

  for (let i = 0; i < count; i++) {
    let x, y, z, intensity, classification, pr, pg, pb;

    if (hasBatch) {
      x = xs[i];
      y = ys[i];
      z = zs ? zs[i] : pcMinZ;
      intensity = iBytes ? iBytes[i] : (batch.i ? batch.i[i] : 128);
      classification = cBytes ? cBytes[i] : (batch.c ? batch.c[i] : 2);
      pr = rBytes ? rBytes[i] : undefined;
      pg = gBytes ? gBytes[i] : undefined;
      pb = bBytes ? bBytes[i] : undefined;
    } else {
      const pt = pts[i];
      x = pt.x !== undefined ? pt.x : pt.X;
      y = pt.y !== undefined ? pt.y : pt.Y;
      z = pt.z !== undefined ? pt.z : pt.Z;
      intensity = pt.intensity !== undefined ? pt.intensity : pt.Intensity;
      classification = pt.classification !== undefined ? pt.classification : pt.Classification;
      pr = pt.r !== undefined ? pt.r : pt.R;
      pg = pt.g !== undefined ? pt.g : pt.G;
      pb = pt.b !== undefined ? pt.b : pt.B;
    }

    if (x === undefined || y === undefined) continue;

    let mx, my;
    if (isDegree) {
      mx = x * toMercX;
      const latRad = y * 0.017453292519943295;
      const sinLat = Math.sin(latRad);
      my = toMercYFactor * Math.log((1 + sinLat) / (1 - sinLat)) * 0.5;
    } else {
      mx = x;
      my = y;
    }

    const px = ((mx - minExtentX) * invRes) | 0;
    const py = ((maxExtentY - my) * invRes) | 0;

    if (px < -radius || px >= width + radius || py < -radius || py >= height + radius) continue;

    const normZ = Math.min(255, Math.max(0, Math.round(((z - pcMinZ) / zRange) * 255)));
    let pixelColor = defaultPointColor;

    switch (lidarColorMode) {
      case 'rgb':
      case 'rgb_elev':
        if (fileHasRgb && pr !== undefined && pg !== undefined && pb !== undefined) {
          pixelColor = (0xFF000000) | ((pb & 0xFF) << 16) | ((pg & 0xFF) << 8) | (pr & 0xFF);
        } else {
          pixelColor = turboPalette[normZ];
        }
        break;

      case 'elevation':
        pixelColor = turboPalette[normZ];
        break;

      case 'intensity':
        {
          const val = Math.min(255, Math.max(0, intensity ? (intensity > 255 ? intensity >> 8 : intensity) : 128));
          pixelColor = (0xFF000000) | (val << 16) | (val << 8) | val;
        }
        break;

      case 'classification':
        pixelColor = classColorMap[classification] || 0xFFE0D3C9;
        break;

      case 'return_num':
        {
          const rn = rnBytes ? rnBytes[i] : 1;
          if (rn === 1) pixelColor = hexToUint32('#10B981');       // Emerald (1st)
          else if (rn === 2) pixelColor = hexToUint32('#3B82F6');  // Blue (2nd)
          else if (rn === 3) pixelColor = hexToUint32('#F59E0B');  // Amber (3rd)
          else if (rn === 4) pixelColor = hexToUint32('#EF4444');  // Red (4th)
          else pixelColor = hexToUint32('#8B5CF6');                // Purple (5+)
        }
        break;

      case 'hag':
        {
          const normHag = Math.min(255, Math.max(0, Math.round(((z - pcMinZ) / Math.min(35.0, zRange)) * 255)));
          pixelColor = turboPalette[normHag];
        }
        break;

      case 'scan_angle':
        {
          const saDeg = saBytes ? (saBytes[i] - 128) : 0;
          const normSa = Math.min(255, Math.max(0, Math.round(((saDeg + 35) / 70.0) * 255)));
          pixelColor = spectralPalette[normSa];
        }
        break;

      case 'point_source_id':
        {
          const psId = psU16 ? psU16[i] : 1;
          pixelColor = categoricalColor(psId);
        }
        break;

      case 'source_layer':
        {
          const psId = psU16 ? psU16[i] : 1;
          pixelColor = categoricalColor(psId ^ 0xAA);
        }
        break;

      case 'segment':
        {
          const segId = ((((px >> 4) * 31) ^ ((py >> 4) * 17) ^ (classification * 11)) & 0xFFFF);
          pixelColor = categoricalColor(segId);
        }
        break;

      case 'point_index':
        {
          const normIdx = Math.min(255, Math.max(0, Math.round((i / Math.max(1, count - 1)) * 255)));
          pixelColor = plasmaPalette[normIdx];
        }
        break;

      case 'cir':
        {
          let rCIR, gCIR, bCIR;
          if (nirBytes) {
            rCIR = nirBytes[i];
            gCIR = pr !== undefined ? pr : intensity;
            bCIR = pg !== undefined ? pg : intensity;
          } else {
            rCIR = intensity;
            gCIR = (fileHasRgb && pr !== undefined) ? pr : intensity;
            bCIR = (fileHasRgb && pg !== undefined) ? pg : Math.round(intensity * 0.7);
          }
          pixelColor = (0xFF000000) | ((bCIR & 0xFF) << 16) | ((gCIR & 0xFF) << 8) | (rCIR & 0xFF);
        }
        break;

      case 'ndvi':
        {
          const gVal = (fileHasRgb && pg !== undefined) ? pg : intensity;
          const rVal = (fileHasRgb && pr !== undefined) ? pr : Math.round(intensity * 0.75);
          const ndviVal = (gVal - rVal) / Math.max(1, gVal + rVal);
          const normNdvi = Math.min(255, Math.max(0, Math.round((ndviVal + 1) * 0.5 * 255)));
          pixelColor = ndviPalette[normNdvi];
        }
        break;

      case 'ndwi':
        {
          const normNdwi = (classification === 9) ? 255 : Math.min(255, Math.max(0, 255 - normZ));
          pixelColor = bluesPalette[normNdwi];
        }
        break;

      case 'point_density':
        {
          const gx = px >> cellShift;
          const gy = py >> cellShift;
          const c = (densityGrid && gx >= 0 && gx < gridW && gy >= 0 && gy < gridH) ? densityGrid[gy * gridW + gx] : 1;
          const normDens = Math.min(255, Math.max(0, Math.round((c / 250.0) * 255)));
          pixelColor = turboPalette[normDens];
        }
        break;

      case 'withheld':
        {
          const isWithheld = flBytes ? ((flBytes[i] & 0x01) !== 0) : false;
          pixelColor = isWithheld ? hexToUint32('#EF4444') : hexToUint32('#10B981');
        }
        break;

      case 'keypoint':
        {
          const isKeypoint = flBytes ? ((flBytes[i] & 0x02) !== 0 || classification === 8) : (classification === 8);
          pixelColor = isKeypoint ? hexToUint32('#F59E0B') : hexToUint32('#64748B');
        }
        break;

      case 'overlap':
        {
          const isOverlap = flBytes ? ((flBytes[i] & 0x04) !== 0 || classification === 12) : (classification === 12);
          pixelColor = isOverlap ? hexToUint32('#EC4899') : hexToUint32('#3B82F6');
        }
        break;

      case 'return_delta':
        {
          const numRet = nrBytes ? nrBytes[i] : 1;
          pixelColor = numRet > 1 ? hexToUint32('#38BDF8') : hexToUint32('#D2A373');
        }
        break;

      default:
        pixelColor = turboPalette[normZ];
        break;
    }

    if (radius === 0) {
      if (px >= 0 && px < width && py >= 0 && py < height) {
        buf32[py * width + px] = pixelColor;
      }
    } else if (radius === 1) {
      if (px >= 0 && px < width - 1 && py >= 0 && py < height - 1) {
        const row0 = py * width + px;
        buf32[row0] = pixelColor;
        buf32[row0 + 1] = pixelColor;
        buf32[row0 + width] = pixelColor;
        buf32[row0 + width + 1] = pixelColor;
      }
    } else {
      for (let dy = -radius; dy <= radius; dy++) {
        const ny = py + dy;
        if (ny < 0 || ny >= height) continue;
        const rowOffset = ny * width;
        for (let dx = -radius; dx <= radius; dx++) {
          if (dx * dx + dy * dy > threshold) continue;
          const nx = px + dx;
          if (nx >= 0 && nx < width) {
            buf32[rowOffset + nx] = pixelColor;
          }
        }
      }
    }
  }

  pcCtx.putImageData(imgData, 0, 0);
  updateLidarLegendWidget(lidarColorMode);
}

function setPointCloud(points) {
  pointCloudData = points || [];
  renderPointCloud();
}

// ── LiDAR Dynamic Map Legend ──────────────────────────────────────────────────
const LIDAR_LEGENDS = {
  classification: {
    icon: '🏷️',
    title: 'ASPRS Classification',
    type: 'swatches',
    subtext: 'ASPRS Standard Feature Classes',
    items: [
      { color: '#D2A373', label: 'Ground (Class 2)' },
      { color: '#84F0AB', label: 'Low Veg (Class 3)' },
      { color: '#22C55E', label: 'Med Veg (Class 4)' },
      { color: '#15803D', label: 'Canopy (Class 5)' },
      { color: '#EF4444', label: 'Building (Class 6)' },
      { color: '#0284C7', label: 'Water (Class 9)' },
      { color: '#F59E0B', label: 'Keypoint (Class 8)' },
      { color: '#94A3B8', label: 'Unclassified (0/1)' }
    ]
  },
  elevation: {
    icon: '⛰️',
    title: 'Elevation (Z Height)',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4582f4, #29efa2, #f2ca3a, #e23812, #7a0403)',
    minLabel: () => `${(typeof pcMinZ === 'number' && !isNaN(pcMinZ)) ? pcMinZ.toFixed(1) : 0} m`,
    midLabel: () => `${(typeof pcMinZ === 'number' && typeof pcMaxZ === 'number' && !isNaN(pcMinZ) && !isNaN(pcMaxZ)) ? ((pcMinZ + pcMaxZ) / 2).toFixed(1) : 'Mid'} m`,
    maxLabel: () => `${(typeof pcMaxZ === 'number' && !isNaN(pcMaxZ)) ? pcMaxZ.toFixed(1) : 100} m`,
    subtext: 'Continuous Turbo Spectrum'
  },
  rgb_elev: {
    icon: '🏔️',
    title: 'RGB / Elevation Hybrid',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4582f4, #29efa2, #f2ca3a, #e23812, #7a0403)',
    minLabel: () => `${(typeof pcMinZ === 'number' && !isNaN(pcMinZ)) ? pcMinZ.toFixed(1) : 0} m`,
    midLabel: () => 'Ortho RGB',
    maxLabel: () => `${(typeof pcMaxZ === 'number' && !isNaN(pcMaxZ)) ? pcMaxZ.toFixed(1) : 100} m`,
    subtext: 'True Color Photo + Elevation'
  },
  intensity: {
    icon: '💡',
    title: 'Laser Intensity',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #000000, #475569, #94a3b8, #ffffff)',
    minLabel: '0 (Low)',
    midLabel: '128',
    maxLabel: '255 (High Reflectance)',
    subtext: 'Laser Pulse Amplitude'
  },
  return_num: {
    icon: '🔄',
    title: 'Return Number',
    type: 'swatches',
    subtext: 'Canopy Pulse Penetration',
    items: [
      { color: '#10B981', label: '1st Return (Canopy Top)' },
      { color: '#3B82F6', label: '2nd Return (Mid Branch)' },
      { color: '#F59E0B', label: '3rd Return (Understory)' },
      { color: '#EF4444', label: '4th Return (Deep)' },
      { color: '#8B5CF6', label: '5+ Return (Ground)' }
    ]
  },
  hag: {
    icon: '📏',
    title: 'Height Above Ground (HAG)',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4582f4, #29efa2, #f2ca3a, #e23812)',
    minLabel: '0.0 m (Ground)',
    midLabel: '15.0 m',
    maxLabel: '35.0+ m (Canopy)',
    subtext: 'Normalized Height Above Earth'
  },
  scan_angle: {
    icon: '📐',
    title: 'Scan Angle',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #9e0142, #d53e4f, #f46d43, #fdae61, #fee08b, #ffffbf, #e6f598, #abdda4, #66c2a5, #3288bd, #5e4fa2)',
    minLabel: '-35° (Left)',
    midLabel: '0° (Nadir)',
    maxLabel: '+35° (Right)',
    subtext: 'Sensor Off-Nadir Angle'
  },
  point_source_id: {
    icon: '✈️',
    title: 'Point Source ID',
    type: 'swatches',
    subtext: 'Individual Flight Strip Swaths',
    items: [
      { color: '#3B82F6', label: 'Flight Strip A' },
      { color: '#10B981', label: 'Flight Strip B' },
      { color: '#F59E0B', label: 'Flight Strip C' },
      { color: '#EC4899', label: 'Flight Strip D' },
      { color: '#8B5CF6', label: 'Flight Strip E' },
      { color: '#06B6D4', label: 'Flight Strip F' }
    ]
  },
  source_layer: {
    icon: '🗂️',
    title: 'Source Layer / Tile',
    type: 'swatches',
    subtext: 'Source LAS File / Tile ID',
    items: [
      { color: '#6366F1', label: 'LAS Tile 1' },
      { color: '#EC4899', label: 'LAS Tile 2' },
      { color: '#14B8A6', label: 'LAS Tile 3' },
      { color: '#F97316', label: 'LAS Tile 4' }
    ]
  },
  segment: {
    icon: '🧩',
    title: 'Segment / Cluster',
    type: 'swatches',
    subtext: 'Planar & Structure Clusters',
    items: [
      { color: '#EF4444', label: 'Cluster 1' },
      { color: '#F59E0B', label: 'Cluster 2' },
      { color: '#10B981', label: 'Cluster 3' },
      { color: '#3B82F6', label: 'Cluster 4' },
      { color: '#8B5CF6', label: 'Cluster 5' },
      { color: '#06B6D4', label: 'Cluster 6' }
    ]
  },
  point_index: {
    icon: '⏱️',
    title: 'Point Index / Time',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)',
    minLabel: 'Start of Survey',
    midLabel: 'Mid',
    maxLabel: 'End of Survey',
    subtext: 'GPS Time Chronological Order'
  },
  cir: {
    icon: '🌿',
    title: 'CIR (Color Infrared)',
    type: 'swatches',
    subtext: 'False-Color Infrared Composite',
    items: [
      { color: '#EF4444', label: 'Vegetation (NIR High)' },
      { color: '#94A3B8', label: 'Bare Soil / Sand' },
      { color: '#38BDF8', label: 'Pavement / Concrete' },
      { color: '#0F172A', label: 'Water & Shadow' }
    ]
  },
  ndvi: {
    icon: '🌱',
    title: 'NDVI (Vegetation Index)',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #dc2626, #f59e0b, #eab308, #84cc16, #22c55e, #15803d)',
    minLabel: '-1.0 (Non-Veg)',
    midLabel: '0.0 (Soil)',
    maxLabel: '+1.0 (Dense Foliage)',
    subtext: 'Chlorophyll Density & Vigour'
  },
  ndwi: {
    icon: '💧',
    title: 'NDWI (Water Index)',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #f1f5f9, #bae6fd, #38bdf8, #0284c7, #0369a1)',
    minLabel: 'Dry Land',
    midLabel: 'Moist Soil',
    maxLabel: 'Open Water',
    subtext: 'Surface Water & Soil Moisture'
  },
  point_density: {
    icon: '📊',
    title: 'Point Density (pts/m²)',
    type: 'ramp',
    gradient: 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)',
    minLabel: 'Low (< 5)',
    midLabel: '25 pts',
    maxLabel: 'High (> 60 pts/m²)',
    subtext: 'Laser Pulses per Square Meter'
  },
  withheld: {
    icon: '🚫',
    title: 'Withheld Flag',
    type: 'swatches',
    subtext: 'Sensor Noise & Outlier Filter',
    items: [
      { color: '#10B981', label: 'Valid Survey Point' },
      { color: '#EF4444', label: 'Withheld Point (Noise)' }
    ]
  },
  keypoint: {
    icon: '⭐',
    title: 'Model Key Point Flag',
    type: 'swatches',
    subtext: 'Critical DTM Terrain Vertices',
    items: [
      { color: '#64748B', label: 'Standard Pulse' },
      { color: '#F59E0B', label: 'Model Key Point' }
    ]
  },
  overlap: {
    icon: '🔄',
    title: 'Flight Line Overlap Flag',
    type: 'swatches',
    subtext: 'Cross-Swath Overlap Coverage',
    items: [
      { color: '#3B82F6', label: 'Single Strip Coverage' },
      { color: '#EC4899', label: 'Overlap Zone (Multi-Strip)' }
    ]
  },
  return_delta: {
    icon: '↕️',
    title: 'Return Height Delta',
    type: 'swatches',
    subtext: 'Canopy Multi-Pulse Penetration',
    items: [
      { color: '#D2A373', label: 'Single Return (Ground Surface)' },
      { color: '#38BDF8', label: 'Multi-Return Depth (> 1.5m)' }
    ]
  },
  rgb: {
    icon: '🎨',
    title: 'LiDAR True Color RGB',
    type: 'swatches',
    subtext: 'UAV Photogrammetric Camera Bands',
    items: [
      { color: '#3B82F6', label: 'True Color Ortho Photogrammetry' }
    ]
  }
};

function updateLidarLegendWidget(mode) {
  const widget = document.getElementById('lidarLegendWidget');
  if (!widget) return;

  const hasData = (pointCloudBatch && pointCloudBatch.count > 0) || (pointCloudData && pointCloudData.length > 0);
  if (!hasData || !isPointCloudVisible) {
    widget.style.display = 'none';
    return;
  }

  const key = (mode || lidarColorMode || 'classification').toLowerCase();
  const cfg = LIDAR_LEGENDS[key] || LIDAR_LEGENDS['classification'];

  // Offset below raster scale widget if both are visible
  const shaderWidget = document.getElementById('shaderScaleWidget');
  if (shaderWidget && shaderWidget.style.display !== 'none') {
    widget.style.top = '108px';
  } else {
    widget.style.top = '8px';
  }

  const iconEl = document.getElementById('lidarLegendIcon');
  const titleEl = document.getElementById('lidarLegendTitle');
  const contentEl = document.getElementById('lidarLegendContent');
  const subtextEl = document.getElementById('lidarLegendSubtext');

  if (iconEl) iconEl.textContent = cfg.icon;
  if (titleEl) titleEl.textContent = cfg.title;
  if (subtextEl) subtextEl.textContent = cfg.subtext;

  if (contentEl) {
    if (cfg.type === 'swatches') {
      let html = '<div class="lidar-swatch-grid">';
      for (const item of cfg.items) {
        html += `<div class="lidar-swatch-item">
          <div class="lidar-swatch-box" style="background: ${item.color};"></div>
          <span>${item.label}</span>
        </div>`;
      }
      html += '</div>';
      contentEl.innerHTML = html;
    } else if (cfg.type === 'ramp') {
      const minTxt = typeof cfg.minLabel === 'function' ? cfg.minLabel() : cfg.minLabel;
      const midTxt = typeof cfg.midLabel === 'function' ? cfg.midLabel() : cfg.midLabel;
      const maxTxt = typeof cfg.maxLabel === 'function' ? cfg.maxLabel() : cfg.maxLabel;

      contentEl.innerHTML = `
        <div class="lidar-ramp-container">
          <div class="lidar-ramp-bar" style="background: ${cfg.gradient};"></div>
          <div class="lidar-ramp-ticks">
            <span>${minTxt}</span>
            <span>${midTxt}</span>
            <span>${maxTxt}</span>
          </div>
        </div>
      `;
    }
  }

  widget.style.display = 'block';
}

// Attach collapse / expand toggle listener
(function initLidarLegendEvents() {
  function setup() {
    const header = document.getElementById('lidarLegendHeader');
    const widget = document.getElementById('lidarLegendWidget');
    const toggleBtn = document.getElementById('lidarLegendToggle');
    if (!header || !widget || !toggleBtn) {
      setTimeout(setup, 100);
      return;
    }
    header.addEventListener('click', function () {
      widget.classList.toggle('collapsed');
      toggleBtn.textContent = widget.classList.contains('collapsed') ? '▸' : '▾';
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();

