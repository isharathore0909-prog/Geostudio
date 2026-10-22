// Raster Layer Manager (BigTIFF, GeoTIFF, Dynamic Viewport Streaming)
let activeRasterInfo = null;
let hiresRasterLayer = null;
let rasterDebounceTimer = null;

function requestHighResRasterWindow() {
  if (typeof isSwipeActive !== 'undefined' && isSwipeActive) return;
  if (!activeRasterInfo || !activeRasterInfo.filePath || !activeRasterInfo.bounds) return;

  const currentZoom = mapView.getZoom();
  if (currentZoom < 12) {
    if (hiresRasterLayer) hiresRasterLayer.setVisible(false);
    return;
  }
  if (hiresRasterLayer) hiresRasterLayer.setVisible(true);

  const mapSize = map.getSize() || [window.innerWidth, window.innerHeight];
  const mapExtent3857 = mapView.calculateExtent(mapSize);
  const mapExtent4326 = ol.proj.transformExtent(mapExtent3857, 'EPSG:3857', 'EPSG:4326');
  const rBounds = activeRasterInfo.bounds;

  if (mapExtent4326[2] < rBounds[0] || mapExtent4326[0] > rBounds[2] ||
    mapExtent4326[3] < rBounds[1] || mapExtent4326[1] > rBounds[3]) {
    return;
  }

  const spanX = mapExtent4326[2] - mapExtent4326[0];
  const spanY = mapExtent4326[3] - mapExtent4326[1];
  const padFactor = currentZoom >= 16 ? 0.05 : 0.12;
  const padX = spanX * padFactor;
  const padY = spanY * padFactor;
  const reqMinLon = Math.max(rBounds[0], mapExtent4326[0] - padX);
  const reqMaxLon = Math.min(rBounds[2], mapExtent4326[2] + padX);
  const reqMinLat = Math.max(rBounds[1], mapExtent4326[1] - padY);
  const reqMaxLat = Math.min(rBounds[3], mapExtent4326[3] + padY);

  const dpr = window.devicePixelRatio || 1;
  const screenW = Math.round((mapSize[0] || window.innerWidth) * dpr);
  const screenH = Math.round((mapSize[1] || window.innerHeight) * dpr);

  postToHost({
    action: 'requestRasterWindow',
    layerId: activeRasterInfo.id,
    filePath: activeRasterInfo.filePath,
    bounds: [reqMinLon, reqMinLat, reqMaxLon, reqMaxLat],
    screenW: screenW,
    screenH: screenH,
    zoom: currentZoom,
    shaderMode: activeRasterInfo.shaderMode || null,
    palette: activeRasterInfo.palette || null
  });
}

function addRasterLayer(data) {
  if (!data || !data.bounds) return;

  const renderStart = performance.now();
  const imgUrl = data.imageUrl || data.imageUri;

  activeRasterInfo = {
    id: data.id,
    name: data.name,
    filePath: data.filePath,
    bounds: data.bounds,
    width: data.width,
    height: data.height,
    hasOverview: !!imgUrl,
    renderStartTime: renderStart,
    fileLoadMs: data.fileLoadMs || 0,
    shaderMode: data.shaderMode || null,
    palette: data.palette || null,
    minElev: (data.minElev !== undefined && data.minElev !== null) ? Number(data.minElev) : null,
    maxElev: (data.maxElev !== undefined && data.maxElev !== null) ? Number(data.maxElev) : null,
    isElevation: !!data.isElevation
  };

  if (data.isElevation || data.shaderMode || (data.minElev !== undefined && data.minElev !== null)) {
    updateShaderScaleWidget(data.shaderMode || 'atlas', data.palette, data.minElev, data.maxElev);
  }

  const minX = data.bounds[0];
  const minY = data.bounds[1];
  const maxX = data.bounds[2];
  const maxY = data.bounds[3];

  let extent;
  if (Math.abs(minX) <= 180 && Math.abs(maxX) <= 180 && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90) {
    const p1 = ol.proj.fromLonLat([minX, minY]);
    const p2 = ol.proj.fromLonLat([maxX, maxY]);
    extent = [
      Math.min(p1[0], p2[0]),
      Math.min(p1[1], p2[1]),
      Math.max(p1[0], p2[0]),
      Math.max(p1[1], p2[1])
    ];
  } else {
    extent = [
      Math.min(minX, maxX),
      Math.min(minY, maxY),
      Math.max(minX, maxX),
      Math.max(minY, maxY)
    ];
  }

  rasterSource.clear();

  if (imgUrl) {
    const existingLayers = map.getLayers().getArray().filter(l => l.get('id') === 'raster_img_' + data.id);
    existingLayers.forEach(l => map.removeLayer(l));

    const imageSource = new ol.source.ImageStatic({
      url: imgUrl,
      imageExtent: extent,
      projection: 'EPSG:3857',
      interpolate: true
    });

    imageSource.on('imageloadend', function () {
      const canvasMs = Math.max(1, Math.round(performance.now() - renderStart));
      const fileMs = data.fileLoadMs || 0;
      postToHost({
        action: 'layerBenchmark',
        id: data.id,
        name: data.name,
        fileLoadMs: fileMs,
        canvasRenderMs: canvasMs,
        totalMs: fileMs + canvasMs,
        type: 'Raster'
      });
      map.render();
    });

    imageSource.on('imageloaderror', function (e) {
      console.warn('[MapEngine] Overview imageloaderror, triggering high-res viewport request', e);
      requestHighResRasterWindow();
    });

    const imageLayer = new ol.layer.Image({
      properties: { id: 'raster_img_' + data.id, name: data.name },
      source: imageSource,
      opacity: 1.0,
      zIndex: 7
    });
    map.addLayer(imageLayer);
  }

  if (!hiresRasterLayer) {
    hiresRasterLayer = new ol.layer.Image({
      properties: { id: 'raster_hires_layer' },
      zIndex: 10,
      opacity: 1.0
    });
    map.addLayer(hiresRasterLayer);
  } else {
    hiresRasterLayer.setSource(null);
  }

  mapView.fit(extent, {
    padding: [50, 50, 50, 50],
    duration: 350
  });

  if (mapView.getZoom() >= 12) {
    setTimeout(requestHighResRasterWindow, 50);
    setTimeout(requestHighResRasterWindow, 400);
  }
}

function applyTerrainShader(mode) {
  const canvasEl = map.getViewport().querySelector('canvas');
  if (!canvasEl) return;
  if (mode === 'hillshade') {
    canvasEl.style.filter = 'contrast(160%) brightness(90%) drop-shadow(2px 2px 3px rgba(0,0,0,0.4))';
  } else if (mode === 'slope') {
    canvasEl.style.filter = 'hue-rotate(90deg) saturate(220%) contrast(140%)';
  } else if (mode === 'aspect') {
    canvasEl.style.filter = 'invert(25%) hue-rotate(180deg) saturate(200%)';
  } else if (mode === 'hypsometric') {
    canvasEl.style.filter = 'saturate(250%) contrast(120%)';
  } else {
    canvasEl.style.filter = 'none';
  }
}

// ==========================================
// Dynamic Shader / Elevation Scale Legend Widget
// Positioned directly beside the Zoom [+] [-] controls
// ==========================================
const SHADER_SCALES = {
  'atlas': {
    title: 'Elevation',
    unit: 'm',
    icon: '🏔️',
    gradient: 'linear-gradient(to right, rgb(0,0,255) 0%, rgb(0,212,255) 8%, rgb(0,184,40) 18%, rgb(15,166,25) 45%, rgb(96,200,0) 70%, rgb(255,214,0) 82%, rgb(255,102,0) 92%, rgb(204,0,0) 100%)',
    subtext: 'Global Mapper Atlas (3D Shaded Relief)',
    isElevation: true
  },
  'terrain': {
    title: 'Elevation (Terrain)',
    unit: 'm',
    icon: '⛰️',
    gradient: 'linear-gradient(to right, rgb(25,104,40) 0%, rgb(63,162,53) 15%, rgb(140,198,69) 30%, rgb(229,223,99) 48%, rgb(221,162,70) 65%, rgb(180,90,36) 78%, rgb(125,63,31) 88%, rgb(150,144,140) 96%, rgb(255,255,255) 100%)',
    subtext: 'Global Mapper Earth Tones (3D Relief)',
    isElevation: true
  },
  'viridis': {
    title: 'Elevation (Viridis)',
    unit: 'm',
    icon: '📊',
    gradient: 'linear-gradient(to right, rgb(68,1,84) 0%, rgb(59,82,139) 25%, rgb(33,145,140) 50%, rgb(94,201,98) 75%, rgb(253,231,37) 100%)',
    subtext: 'Scientific Viridis Colormap (3D)',
    isElevation: true
  },
  'magma': {
    title: 'Elevation (Magma)',
    unit: 'm',
    icon: '🔥',
    gradient: 'linear-gradient(to right, rgb(0,0,4) 0%, rgb(81,18,124) 25%, rgb(183,55,121) 50%, rgb(252,137,97) 75%, rgb(252,253,191) 100%)',
    subtext: 'High-Contrast Magma Colormap (3D)',
    isElevation: true
  },
  'slope': {
    title: 'Slope Angle',
    unit: '°',
    icon: '📐',
    gradient: 'linear-gradient(to right, rgb(34,197,94) 0%, rgb(132,204,22) 15%, rgb(234,179,8) 35%, rgb(249,115,22) 60%, rgb(239,68,68) 100%)',
    minLabel: '0° Flat',
    midLabel: '20° Moderate',
    maxLabel: '45°+ Cliff',
    subtext: 'Terrain Inclination Steepness',
    isElevation: false
  },
  'aspect': {
    title: 'Aspect (Direction)',
    unit: '',
    icon: '🧭',
    gradient: 'linear-gradient(to right, rgb(227,26,28) 0%, rgb(255,127,0) 6.25%, rgb(255,255,51) 18.75%, rgb(77,175,74) 31.25%, rgb(55,126,184) 43.75%, rgb(152,78,163) 56.25%, rgb(247,129,191) 68.75%, rgb(166,86,40) 81.25%, rgb(227,26,28) 100%)',
    minLabel: '0° N',
    midLabel: '180° S',
    maxLabel: '360° N',
    subtext: 'Azimuth Compass Facing Direction',
    isElevation: false
  },
  'hillshade': {
    title: 'Shaded Relief',
    unit: '',
    icon: '☀️',
    gradient: 'linear-gradient(to right, rgb(15,15,20) 0%, rgb(128,128,128) 50%, rgb(255,255,255) 100%)',
    minLabel: 'Shadow',
    midLabel: 'Midtone',
    maxLabel: 'Sunlit',
    subtext: 'Multi-directional Hillshade (315° Az / 45° Alt)',
    isElevation: false
  },
  'tri': {
    title: 'TRI (Ruggedness)',
    unit: '',
    icon: '🪨',
    gradient: 'linear-gradient(to right, rgb(34,197,94) 0%, rgb(234,179,8) 35%, rgb(239,68,68) 70%, rgb(147,51,234) 100%)',
    minLabel: 'Level (0)',
    midLabel: 'Moderate',
    maxLabel: 'Highly Rugged',
    subtext: 'Terrain Ruggedness Index (Riley et al.)',
    isElevation: false
  },
  'tpi': {
    title: 'TPI (Position)',
    unit: '',
    icon: '📊',
    gradient: 'linear-gradient(to right, rgb(0,100,255) 0%, rgb(0,212,255) 25%, rgb(34,197,94) 50%, rgb(255,214,0) 75%, rgb(204,0,0) 100%)',
    minLabel: 'Valley / Pit',
    midLabel: 'Planar / Slope',
    maxLabel: 'Ridge / Peak',
    subtext: 'Topographic Position Index',
    isElevation: false
  },
  'twi': {
    title: 'TWI (Wetness Index)',
    unit: '',
    icon: '💧',
    gradient: 'linear-gradient(to right, rgb(245,235,200) 0%, rgb(210,225,170) 20%, rgb(120,198,121) 40%, rgb(65,182,196) 65%, rgb(34,94,168) 85%, rgb(8,29,88) 100%)',
    minLabel: 'Dry Crest',
    midLabel: 'Moist Slope',
    maxLabel: 'Saturated Channel',
    subtext: 'Hydrological Topographic Wetness',
    isElevation: false
  },
  'curvature': {
    title: 'Curvature (Morphology)',
    unit: '',
    icon: '🌐',
    gradient: 'linear-gradient(to right, rgb(215,48,39) 0%, rgb(252,141,89) 25%, rgb(240,240,240) 50%, rgb(145,191,219) 75%, rgb(69,117,180) 100%)',
    minLabel: 'Convex (+)',
    midLabel: 'Planar (0.0)',
    maxLabel: 'Concave (-)',
    subtext: 'Surface Curvature Profile',
    isElevation: false
  }
};

function updateShaderScaleWidget(mode, palette, minElev, maxElev) {
  const widget = document.getElementById('shaderScaleWidget');
  if (!widget) return;

  if (!mode && activeRasterInfo) {
    mode = activeRasterInfo.shaderMode || 'atlas';
    palette = palette || activeRasterInfo.palette;
    if ((minElev === undefined || minElev === null) && activeRasterInfo.minElev !== null) {
      minElev = activeRasterInfo.minElev;
    }
    if ((maxElev === undefined || maxElev === null) && activeRasterInfo.maxElev !== null) {
      maxElev = activeRasterInfo.maxElev;
    }
  }

  if (!mode) mode = 'atlas';

  const normalizedMode = (mode || 'atlas').toLowerCase();
  const normalizedPal = (palette || '').toUpperCase();

  let cfg = SHADER_SCALES[normalizedMode];
  if (normalizedMode === 'atlas' || normalizedMode === 'terrain') {
    if (normalizedPal.includes('VIRIDIS')) cfg = SHADER_SCALES['viridis'];
    else if (normalizedPal.includes('MAGMA')) cfg = SHADER_SCALES['magma'];
    else if (normalizedPal.includes('TERRAIN') || normalizedMode === 'terrain') cfg = SHADER_SCALES['terrain'];
    else cfg = SHADER_SCALES['atlas'];
  }

  if (!cfg) cfg = SHADER_SCALES['atlas'];

  const iconEl = document.getElementById('shaderScaleIcon');
  const titleEl = document.getElementById('shaderScaleTitle');
  const barEl = document.getElementById('shaderScaleBar');
  const minEl = document.getElementById('shaderScaleMin');
  const midEl = document.getElementById('shaderScaleMid');
  const maxEl = document.getElementById('shaderScaleMax');
  const subtextEl = document.getElementById('shaderScaleSubtext');

  if (iconEl) iconEl.textContent = cfg.icon;
  if (barEl) barEl.style.background = cfg.gradient;
  if (subtextEl) subtextEl.textContent = cfg.subtext;

  if (cfg.isElevation) {
    const hasElevRange = minElev !== undefined && minElev !== null && maxElev !== undefined && maxElev !== null && (minElev !== 0 || maxElev !== 0);
    if (hasElevRange) {
      const minVal = parseFloat(minElev);
      const maxVal = parseFloat(maxElev);
      const midVal = (minVal + maxVal) / 2;
      if (minEl) minEl.textContent = `${minVal.toFixed(1)} m`;
      if (midEl) midEl.textContent = `${midVal.toFixed(1)} m`;
      if (maxEl) maxEl.textContent = `${maxVal.toFixed(1)} m`;
      if (titleEl) titleEl.textContent = `${cfg.title} (${minVal.toFixed(0)} - ${maxVal.toFixed(0)}m)`;
    } else {
      if (titleEl) titleEl.textContent = cfg.title;
      if (minEl) minEl.textContent = 'Min Elev';
      if (midEl) midEl.textContent = 'Mid';
      if (maxEl) maxEl.textContent = 'Max Elev';
    }
  } else {
    if (titleEl) titleEl.textContent = cfg.title;
    if (minEl) minEl.textContent = cfg.minLabel;
    if (midEl) midEl.textContent = cfg.midLabel;
    if (maxEl) maxEl.textContent = cfg.maxLabel;
  }

  widget.style.display = 'block';
  widget.classList.remove('collapsed');
  const toggleBtn = document.getElementById('shaderScaleToggle');
  if (toggleBtn) toggleBtn.textContent = '▾';

  // Highlight pulse animation
  widget.classList.remove('shader-scale-pulse');
  void widget.offsetWidth;
  widget.classList.add('shader-scale-pulse');
}

function hideShaderScaleWidget() {
  const widget = document.getElementById('shaderScaleWidget');
  if (widget) widget.style.display = 'none';
}

function initShaderScaleWidget() {
  const widget = document.getElementById('shaderScaleWidget');
  const header = document.getElementById('shaderScaleHeader');
  const toggleBtn = document.getElementById('shaderScaleToggle');
  if (!widget || !header) return;

  function toggleCollapse(e) {
    if (e) e.stopPropagation();
    const isCollapsed = widget.classList.toggle('collapsed');
    if (toggleBtn) toggleBtn.textContent = isCollapsed ? '▸' : '▾';
  }

  header.addEventListener('click', toggleCollapse);
  if (toggleBtn) toggleBtn.addEventListener('click', toggleCollapse);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initShaderScaleWidget);
} else {
  initShaderScaleWidget();
}

