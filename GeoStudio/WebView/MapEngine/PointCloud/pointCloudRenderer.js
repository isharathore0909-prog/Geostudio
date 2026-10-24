// Point Cloud Canvas Rendering Execution Loop
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

  const master = window.initialLidarBatch || batch || {};
  const isMasterSameLength = master && master.count === count;
  const rBytes = hasBatch ? (batch.r || (isMasterSameLength ? master.r : null)) : null;
  const gBytes = hasBatch ? (batch.g || (isMasterSameLength ? master.g : null)) : null;
  const bBytes = hasBatch ? (batch.b || (isMasterSameLength ? master.b : null)) : null;
  const cBytes = hasBatch ? (batch.c || (isMasterSameLength ? master.c : null)) : null;
  const iBytes = hasBatch ? (batch.i || (isMasterSameLength ? master.i : null)) : null;
  const rnBytes = hasBatch ? (batch.rn || (isMasterSameLength ? master.rn : null)) : null;
  const nrBytes = hasBatch ? (batch.nr || (isMasterSameLength ? master.nr : null)) : null;
  const saBytes = hasBatch ? (batch.sa || (isMasterSameLength ? master.sa : null)) : null;
  const psRaw = hasBatch ? (batch.ps || (isMasterSameLength ? master.ps : null)) : null;
  const flBytes = hasBatch ? (batch.fl || (isMasterSameLength ? master.fl : null)) : null;
  const nirBytes = hasBatch ? (batch.nir || (isMasterSameLength ? master.nir : null)) : null;
  const tBytes = hasBatch ? (batch.t || (isMasterSameLength ? master.t : null)) : null;

  const fileHasRgb = hasBatch ? (batch.hasRgb === true || (rBytes !== null && rBytes.length > 0)) : (pts[0] && pts[0].r !== undefined);

  const firstX = hasBatch ? (batch.x && batch.x[0]) : (pts[0] && (pts[0].x !== undefined ? pts[0].x : pts[0].X));
  const isDegree = firstX !== undefined && Math.abs(firstX) <= 180;
  const originShift = 20037508.342789244;
  const toMercX = originShift / 180.0;
  const toMercYFactor = originShift / Math.PI;

  const xs = hasBatch ? batch.x : null;
  const ys = hasBatch ? batch.y : null;
  const zs = hasBatch ? batch.z : null;

  let densityGrid = null;
  const cellShift = 5;
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

    let mercX, mercY;
    if (isDegree) {
      mercX = x * toMercX;
      const latRad = y * 0.017453292519943295;
      mercY = toMercYFactor * Math.log((1 + Math.sin(latRad)) / (1 - Math.sin(latRad))) * 0.5;
    } else {
      mercX = x;
      mercY = y;
    }

    const px = ((mercX - minExtentX) * invRes) | 0;
    const py = ((maxExtentY - mercY) * invRes) | 0;

    if (px < -2 || px >= width + 2 || py < -2 || py >= height + 2) continue;

    const normZ = Math.min(255, Math.max(0, Math.round(((z - pcMinZ) / zRange) * 255)));
    let color = defaultPointColor;

    switch (lidarColorMode) {
      case 'rgb':
      case 'rgb_elev':
        if (fileHasRgb && pr !== undefined && pg !== undefined && pb !== undefined) {
          color = (0xFF000000) | ((pb & 0xFF) << 16) | ((pg & 0xFF) << 8) | (pr & 0xFF);
        } else {
          color = turboPalette[normZ];
        }
        break;
      case 'elevation':
        color = turboPalette[normZ];
        break;
      case 'intensity':
        {
          const val = Math.min(255, Math.max(0, intensity ? (intensity > 255 ? intensity >> 8 : intensity) : 128));
          color = (0xFF000000) | (val << 16) | (val << 8) | val;
        }
        break;
      case 'classification':
        color = classColorMap[classification] || 0xFFE0D3C9;
        break;
      case 'return_num':
        {
          const rn = rnBytes ? rnBytes[i] : 1;
          if (rn === 1) color = hexToUint32('#10B981');
          else if (rn === 2) color = hexToUint32('#3B82F6');
          else if (rn === 3) color = hexToUint32('#F59E0B');
          else if (rn === 4) color = hexToUint32('#EF4444');
          else color = hexToUint32('#8B5CF6');
        }
        break;
      case 'hag':
        {
          const normHag = Math.min(255, Math.max(0, Math.round(((z - pcMinZ) / Math.min(35.0, zRange)) * 255)));
          color = turboPalette[normHag];
        }
        break;
      case 'scan_angle':
        {
          const saVal = (saBytes && i < saBytes.length) ? (saBytes[i] - 128) : 0;
          const normSa = Math.min(255, Math.max(0, Math.round(((saVal + 35) / 70.0) * 255)));
          color = spectralPalette[normSa];
        }
        break;
      case 'point_source_id':
        {
          const psVal = (psRaw && (i * 2 + 1) < psRaw.length) ? (psRaw[i * 2] | (psRaw[i * 2 + 1] << 8)) : 1;
          color = categoricalColor(psVal);
        }
        break;
      case 'source_layer':
        {
          const psVal = (psRaw && (i * 2 + 1) < psRaw.length) ? (psRaw[i * 2] | (psRaw[i * 2 + 1] << 8)) : 1;
          color = categoricalColor(psVal ^ 0xAA);
        }
        break;
      case 'segment':
        color = categoricalColor(((((px >> 4) * 31) ^ ((py >> 4) * 17) ^ (classification * 11)) & 0xFFFF));
        break;
      case 'point_index':
        {
          const normIdx = (tBytes && i < tBytes.length) ? tBytes[i] : Math.min(255, Math.max(0, Math.round((i / Math.max(1, count - 1)) * 255)));
          color = plasmaPalette[normIdx];
        }
        break;
      case 'cir':
        {
          let rCIR = nirBytes ? nirBytes[i] : intensity;
          let gCIR = (fileHasRgb && pr !== undefined) ? pr : intensity;
          let bCIR = (fileHasRgb && pg !== undefined) ? pg : Math.round(intensity * 0.7);
          color = (0xFF000000) | ((bCIR & 0xFF) << 16) | ((gCIR & 0xFF) << 8) | (rCIR & 0xFF);
        }
        break;
      case 'ndvi':
        {
          const gVal = (fileHasRgb && pg !== undefined) ? pg : intensity;
          const rVal = (fileHasRgb && pr !== undefined) ? pr : Math.round(intensity * 0.75);
          const ndviVal = (gVal - rVal) / Math.max(1, gVal + rVal);
          const normNdvi = Math.min(255, Math.max(0, Math.round((ndviVal + 1) * 0.5 * 255)));
          color = ndviPalette[normNdvi];
        }
        break;
      case 'ndwi':
        {
          const normNdwi = (classification === 9) ? 255 : Math.min(255, Math.max(0, 255 - normZ));
          color = bluesPalette[normNdwi];
        }
        break;
      case 'point_density':
        {
          const gx = px >> cellShift;
          const gy = py >> cellShift;
          const c = (densityGrid && gx >= 0 && gx < gridW && gy >= 0 && gy < gridH) ? densityGrid[gy * gridW + gx] : 1;
          color = turboPalette[Math.min(255, Math.max(0, Math.round((c / 250.0) * 255)))];
        }
        break;
      case 'withheld':
        color = (flBytes && (flBytes[i] & 0x01) !== 0) ? hexToUint32('#EF4444') : hexToUint32('#10B981');
        break;
      case 'keypoint':
        color = ((flBytes && (flBytes[i] & 0x02) !== 0) || classification === 8) ? hexToUint32('#F59E0B') : hexToUint32('#64748B');
        break;
      case 'overlap':
        color = ((flBytes && (flBytes[i] & 0x04) !== 0) || classification === 12) ? hexToUint32('#EC4899') : hexToUint32('#3B82F6');
        break;
      case 'return_delta':
        {
          const nrVal = (nrBytes && i < nrBytes.length) ? nrBytes[i] : 1;
          color = (nrVal > 1) ? hexToUint32('#38BDF8') : hexToUint32('#D2A373');
        }
        break;
      default:
        color = classColorMap[classification] || defaultPointColor;
        break;
    }

    if (radius === 0) {
      if (px >= 0 && px < width && py >= 0 && py < height) {
        buf32[py * width + px] = color;
      }
    } else {
      for (let dy = -radius; dy <= radius; dy++) {
        const ny = py + dy;
        if (ny < 0 || ny >= height) continue;
        const rowOff = ny * width;
        for (let dx = -radius; dx <= radius; dx++) {
          if (dx * dx + dy * dy <= threshold) {
            const nx = px + dx;
            if (nx >= 0 && nx < width) {
              buf32[rowOff + nx] = color;
            }
          }
        }
      }
    }
  }

  pcCtx.putImageData(imgData, 0, 0);
  if (typeof updateLidarLegendWidget === 'function') {
    updateLidarLegendWidget(lidarColorMode);
  }
}
