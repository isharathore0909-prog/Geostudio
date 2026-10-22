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
      properties: { id: 'raster_img_' + data.id, name: data.name },
      source: overviewSource,
      opacity: 1.0,
      zIndex: 7
    });
    map.addLayer(overviewLayer);
  }

  if (!hiresRasterLayer) {
    hiresRasterLayer = new ol.layer.Image({
      properties: { id: 'hires_viewport_layer', name: 'High-Res Dynamic Viewport' },
      zIndex: 8
    });
    map.addLayer(hiresRasterLayer);
  }

  map.on('moveend', function () {
    clearTimeout(rasterDebounceTimer);
    rasterDebounceTimer = setTimeout(requestHighResRasterWindow, 80);
  });
}

function applyTerrainShader(shaderMode) {
  const mode = (shaderMode || 'atlas').toLowerCase();
  const rasterLayerEl = map.getLayers().getArray().find(l => (l.get('id') || '').startsWith('raster_img_'));
  if (!rasterLayerEl) return;

  const canvasEl = document.querySelector('.ol-layer canvas');
  if (!canvasEl) return;

  if (mode === 'slope') {
    canvasEl.style.filter = 'hue-rotate(90deg) saturate(220%) contrast(140%)';
  } else if (mode === 'aspect') {
    canvasEl.style.filter = 'invert(25%) hue-rotate(180deg) saturate(200%)';
  } else if (mode === 'hypsometric') {
    canvasEl.style.filter = 'saturate(250%) contrast(120%)';
  } else {
    canvasEl.style.filter = 'none';
  }
}
