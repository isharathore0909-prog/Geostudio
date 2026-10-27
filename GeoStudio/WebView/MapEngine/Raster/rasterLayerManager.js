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
  if (hiresRasterLayer) {
    hiresRasterLayer.setVisible(true);
    if (activeRasterInfo && activeRasterInfo.opacity !== undefined) {
      hiresRasterLayer.setOpacity(activeRasterInfo.opacity);
    }
  }

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
  const initOpacity = (data.opacity !== undefined && data.opacity !== null) ? Number(data.opacity) : 1.0;

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
    isElevation: !!data.isElevation,
    opacity: initOpacity
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

  mapView.fit(extent, { padding: [50, 50, 50, 50], duration: 800 });

  if (imgUrl) {
    const overviewSource = new ol.source.ImageStatic({
      url: imgUrl,
      imageExtent: extent,
      projection: 'EPSG:3857',
      interpolate: true
    });

    overviewSource.on('imageloadend', function () {
      if (activeRasterInfo && activeRasterInfo.renderStartTime) {
        const canvasMs = Math.max(1, Math.round(performance.now() - activeRasterInfo.renderStartTime));
        const fileMs = activeRasterInfo.fileLoadMs || 0;
        postToHost({
          action: 'layerBenchmark',
          id: data.id,
          name: data.name,
          fileLoadMs: fileMs,
          canvasRenderMs: canvasMs,
          totalMs: fileMs + canvasMs,
          type: 'Raster'
        });
        activeRasterInfo.renderStartTime = null;
      }
      map.render();
    });

    const overviewLayer = new ol.layer.Image({
      source: overviewSource,
      opacity: initOpacity,
      zIndex: 7
    });
    overviewLayer.set('id', 'raster_img_' + data.id);
    overviewLayer.set('name', data.name);
    overviewLayer.set('type', 'Raster');
    map.addLayer(overviewLayer);
  }

  if (!hiresRasterLayer) {
    hiresRasterLayer = new ol.layer.Image({
      zIndex: 8,
      opacity: initOpacity
    });
    hiresRasterLayer.set('id', 'hires_viewport_layer');
    hiresRasterLayer.set('name', 'High-Res Dynamic Viewport');
    hiresRasterLayer.set('type', 'Raster');
    map.addLayer(hiresRasterLayer);
  } else {
    hiresRasterLayer.setOpacity(initOpacity);
  }

  map.on('moveend', function () {
    clearTimeout(rasterDebounceTimer);
    rasterDebounceTimer = setTimeout(requestHighResRasterWindow, 80);
  });
}

function updateRasterLayerStyle(data) {
  if (!data || !data.id) return;
  const targetId = 'raster_img_' + data.id;
  const layer = map.getLayers().getArray().find(l => l.get('id') === targetId);
  if (!layer) return;

  const newUrl = data.imageUrl || data.imageUri;
  if (newUrl) {
    const src = layer.getSource();
    const extent = src.getImageExtent();
    const newSource = new ol.source.ImageStatic({
      url: newUrl + '?t=' + performance.now(),
      imageExtent: extent,
      projection: 'EPSG:3857',
      interpolate: true
    });
    newSource.on('imageloadend', function () {
      map.render();
    });
    layer.setSource(newSource);
  }

  if (data.blendMode || data.filter !== undefined) {
    updateRasterLayerRendering(data);
  }

  if (activeRasterInfo && activeRasterInfo.id === data.id) {
    activeRasterInfo.shaderMode = data.shaderMode;
    activeRasterInfo.palette = data.palette;
    if (hiresRasterLayer) {
      requestHighResRasterWindow();
    }
  }
}

function applyTerrainShader(shaderMode) {
  const mode = (shaderMode || 'atlas').toLowerCase();
  const filters = {
    'slope': 'hue-rotate(90deg) saturate(220%) contrast(140%)',
    'aspect': 'invert(25%) hue-rotate(180deg) saturate(200%)',
    'hypsometric': 'saturate(250%) contrast(120%)'
  };
  updateRasterLayerRendering({ filter: filters[mode] || '' });
}

// ── Layer Compositing, Filters & Blend Modes (QGIS Layer Rendering) ──
let currentRasterBlendMode = 'source-over';
let currentRasterFilter = '';

function updateRasterLayerRendering(data) {
  if (!data) return;
  if (data.blendMode) {
    const k = data.blendMode.toLowerCase().replace(/\s+/g, '');
    const m = { normal: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', darken: 'darken', lighten: 'lighten', colordodge: 'color-dodge', colorburn: 'color-burn', hardlight: 'hard-light', softlight: 'soft-light', difference: 'difference', exclusion: 'exclusion' };
    currentRasterBlendMode = m[k] || 'source-over';
  }
  if (data.filter !== undefined) {
    currentRasterFilter = (data.filter && data.filter !== 'none') ? data.filter : '';
  }

  const rasterLayers = map.getLayers().getArray().filter(l => {
    const id = l.get('id') || '';
    return id.startsWith('raster_img_') || id === 'hires_viewport_layer';
  });

  rasterLayers.forEach(l => {
    l.un('prerender', rasterPreRender);
    l.un('postrender', rasterPostRender);
    if (currentRasterBlendMode !== 'source-over' || currentRasterFilter) {
      l.on('prerender', rasterPreRender);
      l.on('postrender', rasterPostRender);
    }
  });

  const canvases = document.querySelectorAll('.ol-layer canvas');
  canvases.forEach((c, idx) => {
    if (canvases.length === 1 || idx > 0) {
      c.style.mixBlendMode = currentRasterBlendMode !== 'source-over' ? currentRasterBlendMode : 'normal';
      c.style.filter = currentRasterFilter;
    }
  });

  map.render();
}

function applyLayerBlendMode(modeName) {
  updateRasterLayerRendering({ blendMode: modeName });
}

function rasterPreRender(event) {
  const ctx = event.context;
  if (!ctx) return;
  ctx.save();
  if (currentRasterBlendMode !== 'source-over') ctx.globalCompositeOperation = currentRasterBlendMode;
  if (currentRasterFilter) {
    try { ctx.filter = currentRasterFilter; } catch (e) {}
  }
}

function rasterPostRender(event) {
  const ctx = event.context;
  if (!ctx) return;
  ctx.restore();
}
