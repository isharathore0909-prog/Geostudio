// Host IPC Bridge: Receives messages from WPF C# and dispatches to map components
function handleHostMessage(msg) {
  if (!msg) return;
  if (typeof msg === 'string') {
    try { msg = JSON.parse(msg); } catch (e) { }
  }

  switch (msg.action) {
    case 'setTool':
      setTool(msg.tool);
      break;
    case 'zoomIn':
      mapView.animate({ zoom: mapView.getZoom() + 1, duration: 250 });
      break;
    case 'zoomOut':
      mapView.animate({ zoom: mapView.getZoom() - 1, duration: 250 });
      break;
    case 'zoomFull':
      mapView.animate({ center: ol.proj.fromLonLat([76.515, 24.762]), zoom: 6, duration: 400 });
      break;
    case 'zoomToExtent':
      if (msg.bounds) {
        const minX = Math.min(msg.bounds[0], msg.bounds[2]);
        const maxX = Math.max(msg.bounds[0], msg.bounds[2]);
        const minY = Math.min(msg.bounds[1], msg.bounds[3]);
        const maxY = Math.max(msg.bounds[1], msg.bounds[3]);
        if (minX >= -180 && maxX <= 180 && minY >= -90 && maxY <= 90) {
          const p1 = ol.proj.fromLonLat([minX, minY]);
          const p2 = ol.proj.fromLonLat([maxX, maxY]);
          mapView.fit([Math.min(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[0], p2[0]), Math.max(p1[1], p2[1])], { padding: [50, 50, 50, 50], duration: 800 });
        }
      }
      break;
    case 'refresh':
      map.render();
      renderPointCloud();
      break;
    case 'addRasterLayer':
      addRasterLayer(msg);
      break;
    case 'setTerrainShader':
      applyTerrainShader(msg.shader);
      break;
    case 'toggleSwipe':
      if (typeof toggleSwipe === 'function') {
        toggleSwipe(msg.active);
      }
      break;
    case 'setLidarColorBy':
      lidarColorMode = msg.colorBy;
      renderPointCloud();
      break;
    case 'updateClassification':
      if (pointCloudBatch && msg.classes) {
        pointCloudBatch.c = msg.classes;
      }
      if (msg.colorBy) {
        lidarColorMode = msg.colorBy;
      }
      renderPointCloud();
      break;
    case 'loadPointCloud':
      handleLoadPointCloud(msg);
      break;
    case 'updatePointCloud':
      if (msg.batch) {
        pointCloudBatch = msg.batch;
        pointCloudData = [];
      } else if (msg.points) {
        pointCloudData = msg.points;
        pointCloudBatch = null;
      }
      renderPointCloud();
      break;
    case 'setPointSize':
      userPointSize = parseFloat(msg.size) || 4.5;
      renderPointCloud();
      break;
    case 'clearMeasurements':
      measureSource.clear();
      document.querySelectorAll('.ol-tooltip-static').forEach(el => el.remove());
      break;
    case 'clearDigitized':
      vectorSource.clear();
      break;
    case 'clearAllLayers':
      handleClearAllLayers();
      break;
    case 'removeLayer':
      handleRemoveLayer(msg);
      break;
    case 'updateRasterOverview':
      handleUpdateRasterOverview(msg);
      break;
    case 'updateRasterWindow':
      handleUpdateRasterWindow(msg);
      break;
    case 'toggleLayer':
      handleToggleLayer(msg);
      break;
    case 'setLayerOpacity':
      handleSetLayerOpacity(msg);
      break;
    case 'addVectorLayer':
      handleAddVectorLayer(msg);
      break;
    case 'clearProfileLine':
      if (typeof clearProfileLine === 'function') clearProfileLine();
      break;
  }
}

function handleLoadPointCloud(msg) {
  const pcStart = performance.now();
  activePointCloudId = msg.id || 'pointcloud_layer';
  isPointCloudVisible = true;
  pcCanvas.style.opacity = '1.0';
  if (msg.colorMode) lidarColorMode = msg.colorMode;
  if (msg.pointSize) userPointSize = parseFloat(msg.pointSize) || 4.5;
  if (msg.batch) { pointCloudBatch = msg.batch; pointCloudData = []; }
  else if (msg.points) { pointCloudData = msg.points; pointCloudBatch = null; }
  if (msg.minZ !== undefined && msg.maxZ !== undefined) { pcMinZ = msg.minZ; pcMaxZ = msg.maxZ; }

  if (msg.bounds) {
    const minX = Math.min(msg.bounds[0], msg.bounds[2]), maxX = Math.max(msg.bounds[0], msg.bounds[2]);
    const minY = Math.min(msg.bounds[1], msg.bounds[3]), maxY = Math.max(msg.bounds[1], msg.bounds[3]);
    if (Math.abs(minX) <= 180 && Math.abs(maxX) <= 180 && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90) {
      const p1 = ol.proj.fromLonLat([minX, minY]), p2 = ol.proj.fromLonLat([maxX, maxY]);
      mapView.fit([Math.min(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[0], p2[0]), Math.max(p1[1], p2[1])], { padding: [50, 50, 50, 50], duration: 400 });
    } else {
      mapView.fit([minX, minY, maxX, maxY], { padding: [50, 50, 50, 50], duration: 400 });
    }
  } else if (msg.center) {
    const isDeg = Math.abs(msg.center.x) <= 180 && Math.abs(msg.center.y) <= 90;
    mapView.animate({ center: isDeg ? ol.proj.fromLonLat([msg.center.x, msg.center.y]) : [msg.center.x, msg.center.y], zoom: 17, duration: 400 });
  }

  renderPointCloud();
  setTimeout(renderPointCloud, 100);
  setTimeout(renderPointCloud, 450);
  const pcCanvasMs = Math.max(1, Math.round(performance.now() - pcStart));
  const pcFileMs = msg.fileLoadMs || 0;
  const totalPoints = msg.totalPoints || (pointCloudBatch ? pointCloudBatch.count : (pointCloudData ? pointCloudData.length : 0));
  postToHost({
    action: 'layerBenchmark', id: msg.id || 'pointcloud_layer', name: msg.name || 'ASPRS Point Cloud',
    fileLoadMs: pcFileMs, canvasRenderMs: pcCanvasMs, totalMs: pcFileMs + pcCanvasMs, pointsCount: totalPoints, type: 'PointCloud'
  });
}

function handleClearAllLayers() {
  pointCloudBatch = null; pointCloudData = []; activePointCloudId = null;
  clearTimeout(pointCloudDebounceTimer);
  pcCtx.clearRect(0, 0, pcCanvas.width, pcCanvas.height);
  activeRasterInfo = null;
  clearTimeout(rasterDebounceTimer);
  if (hiresRasterLayer) { hiresRasterLayer.setVisible(false); hiresRasterLayer.setSource(null); }
  rasterSource.clear();
  map.getLayers().getArray().filter(l => (l.get('id') || '').startsWith('raster_img_')).forEach(l => map.removeLayer(l));
  vectorSource.clear();
  measureSource.clear();
  document.querySelectorAll('.ol-tooltip-static').forEach(el => el.remove());
  cartoLayer.setVisible(true);
  satelliteLayer.setVisible(true);
  if (typeof hideShaderScaleWidget === 'function') hideShaderScaleWidget();
  const lWidget = document.getElementById('lidarLegendWidget');
  if (lWidget) lWidget.style.display = 'none';
  if (typeof clearProfileLine === 'function') clearProfileLine();
  map.render();
}

function handleRemoveLayer(msg) {
  if (msg.id === activePointCloudId || msg.type === 'PointCloud') {
    pointCloudBatch = null; pointCloudData = []; activePointCloudId = null;
    clearTimeout(pointCloudDebounceTimer);
    pcCtx.clearRect(0, 0, pcCanvas.width, pcCanvas.height);
    const lWidget = document.getElementById('lidarLegendWidget');
    if (lWidget) lWidget.style.display = 'none';
  }
  map.getLayers().getArray().filter(l => l.get('id') === 'raster_img_' + msg.id || l.get('id') === msg.id).forEach(l => map.removeLayer(l));
  if (activeRasterInfo && (activeRasterInfo.id === msg.id || msg.type === 'Raster')) {
    activeRasterInfo = null;
    clearTimeout(rasterDebounceTimer);
    if (hiresRasterLayer) { hiresRasterLayer.setVisible(false); hiresRasterLayer.setSource(null); }
    rasterSource.clear();
    if (typeof hideShaderScaleWidget === 'function') hideShaderScaleWidget();
  }
  if (msg.id === 'vector_active' || msg.type === 'Vector') {
    vectorSource.clear();
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => map.removeLayer(l));
  }
  if (msg.id === 'osm_basemap' || msg.type === 'Basemap') { cartoLayer.setVisible(false); satelliteLayer.setVisible(false); }
  map.getLayers().getArray().filter(l => l.get('id') === msg.id).forEach(l => map.removeLayer(l));
  map.render();
}

function handleUpdateRasterOverview(msg) {
  const url = msg.imageUrl || msg.imageUri;
  const bounds = msg.bounds || (activeRasterInfo ? activeRasterInfo.bounds : null);
  if (!url || !bounds) return;

  if (activeRasterInfo) {
    activeRasterInfo.hasOverview = true;
    activeRasterInfo.renderStartTime = performance.now();
    if (msg.shaderMode !== undefined) activeRasterInfo.shaderMode = msg.shaderMode;
    if (msg.palette !== undefined) activeRasterInfo.palette = msg.palette;
    if (msg.minElev !== undefined && msg.minElev !== null) activeRasterInfo.minElev = Number(msg.minElev);
    if (msg.maxElev !== undefined && msg.maxElev !== null) activeRasterInfo.maxElev = Number(msg.maxElev);
  }

  const sMode = msg.shaderMode || (activeRasterInfo ? activeRasterInfo.shaderMode : 'atlas');
  const sPal = msg.palette !== undefined ? msg.palette : (activeRasterInfo ? activeRasterInfo.palette : null);
  const sMin = (msg.minElev !== undefined && msg.minElev !== null) ? Number(msg.minElev) : (activeRasterInfo ? activeRasterInfo.minElev : null);
  const sMax = (msg.maxElev !== undefined && msg.maxElev !== null) ? Number(msg.maxElev) : (activeRasterInfo ? activeRasterInfo.maxElev : null);
  if (typeof updateShaderScaleWidget === 'function') {
    updateShaderScaleWidget(sMode, sPal, sMin, sMax);
  }

  const rMinX = bounds[0], rMinY = bounds[1], rMaxX = bounds[2], rMaxY = bounds[3];
  let fullExt = (Math.abs(rMinX) <= 180 && Math.abs(rMaxX) <= 180 && Math.abs(rMinY) <= 90 && Math.abs(rMaxY) <= 90)
    ? [Math.min(ol.proj.fromLonLat([rMinX, rMinY])[0], ol.proj.fromLonLat([rMaxX, rMaxY])[0]), Math.min(ol.proj.fromLonLat([rMinX, rMinY])[1], ol.proj.fromLonLat([rMaxX, rMaxY])[1]), Math.max(ol.proj.fromLonLat([rMinX, rMinY])[0], ol.proj.fromLonLat([rMaxX, rMaxY])[0]), Math.max(ol.proj.fromLonLat([rMinX, rMinY])[1], ol.proj.fromLonLat([rMaxX, rMaxY])[1])]
    : [Math.min(rMinX, rMaxX), Math.min(rMinY, rMaxY), Math.max(rMinX, rMaxX), Math.max(rMinY, rMaxY)];

  const targetId = msg.id || (activeRasterInfo ? activeRasterInfo.id : 'default');
  const existingLayer = map.getLayers().getArray().find(l => l.get('id') === 'raster_img_' + targetId);
  const layerName = msg.name || (existingLayer ? existingLayer.get('name') : null) || (activeRasterInfo ? activeRasterInfo.name : 'DEM');
  const zIdx = existingLayer ? existingLayer.getZIndex() : 7;
  const opac = existingLayer ? existingLayer.getOpacity() : 1.0;

  map.getLayers().getArray().filter(l => l.get('id') === 'raster_img_' + targetId).forEach(l => map.removeLayer(l));

  if (hiresRasterLayer) {
    hiresRasterLayer.setVisible(false);
    hiresRasterLayer.setSource(null);
  }

  const overviewSource = new ol.source.ImageStatic({ url: url, imageExtent: fullExt, projection: 'EPSG:3857', interpolate: true });
  overviewSource.on('imageloadend', function () {
    if (activeRasterInfo && activeRasterInfo.renderStartTime) {
      const canvasMs = Math.max(1, Math.round(performance.now() - activeRasterInfo.renderStartTime));
      const fileMs = activeRasterInfo.fileLoadMs || 0;
      postToHost({ action: 'layerBenchmark', id: targetId, name: layerName, fileLoadMs: fileMs, canvasRenderMs: canvasMs, totalMs: fileMs + canvasMs, type: 'Raster' });
      activeRasterInfo.renderStartTime = null;
    }
    if (typeof isSwipeActive !== 'undefined' && isSwipeActive) {
      toggleSwipe(true);
    }
    map.render();
  });

  const newImgLayer = new ol.layer.Image({ properties: { id: 'raster_img_' + targetId, name: layerName }, source: overviewSource, opacity: opac, zIndex: zIdx });
  map.addLayer(newImgLayer);

  if (mapView.getZoom() >= 12) {
    clearTimeout(rasterDebounceTimer);
    rasterDebounceTimer = setTimeout(requestHighResRasterWindow, 60);
  }
}

function handleUpdateRasterWindow(msg) {
  if (!msg.imageUrl || !msg.bounds) return;
  if (!hiresRasterLayer) {
    hiresRasterLayer = new ol.layer.Image({ properties: { id: 'raster_hires_layer' }, zIndex: 10, opacity: 1.0 });
    map.addLayer(hiresRasterLayer);
  }
  const minX = Math.min(msg.bounds[0], msg.bounds[2]), maxX = Math.max(msg.bounds[0], msg.bounds[2]);
  const minY = Math.min(msg.bounds[1], msg.bounds[3]), maxY = Math.max(msg.bounds[1], msg.bounds[3]);
  let hiresExtent = (Math.abs(minX) <= 180 && Math.abs(maxX) <= 180 && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90)
    ? [Math.min(ol.proj.fromLonLat([minX, minY])[0], ol.proj.fromLonLat([maxX, maxY])[0]), Math.min(ol.proj.fromLonLat([minX, minY])[1], ol.proj.fromLonLat([maxX, maxY])[1]), Math.max(ol.proj.fromLonLat([minX, minY])[0], ol.proj.fromLonLat([maxX, maxY])[0]), Math.max(ol.proj.fromLonLat([minX, minY])[1], ol.proj.fromLonLat([maxX, maxY])[1])]
    : [minX, minY, maxX, maxY];

  const hiresSource = new ol.source.ImageStatic({ url: msg.imageUrl, imageExtent: hiresExtent, projection: 'EPSG:3857', interpolate: true });
  hiresSource.on('imageloadend', function () {
    if (activeRasterInfo && activeRasterInfo.renderStartTime) {
      const canvasMs = Math.max(1, Math.round(performance.now() - activeRasterInfo.renderStartTime));
      const fileMs = activeRasterInfo.fileLoadMs || 0;
      postToHost({ action: 'layerBenchmark', id: activeRasterInfo.id, name: activeRasterInfo.name, fileLoadMs: fileMs, canvasRenderMs: canvasMs, totalMs: fileMs + canvasMs, type: 'Raster' });
      activeRasterInfo.renderStartTime = null;
    }
    map.render();
  });
  hiresRasterLayer.setSource(hiresSource);
  hiresRasterLayer.setVisible(true);
  map.render();
}

function handleToggleLayer(msg) {
  if (msg.id === 'osm_basemap' || msg.type === 'Basemap') {
    cartoLayer.setVisible(msg.visible); satelliteLayer.setVisible(msg.visible);
  } else if (msg.id === activePointCloudId || msg.type === 'PointCloud') {
    isPointCloudVisible = !!msg.visible;
    if (!isPointCloudVisible) pcCtx.clearRect(0, 0, pcCanvas.width, pcCanvas.height); else renderPointCloud();
  } else if (msg.id === 'vector_active' || msg.type === 'Vector') {
    vectorLayer.setVisible(msg.visible);
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => l.setVisible(msg.visible));
  } else {
    const rImg = map.getLayers().getArray().find(l => l.get('id') === 'raster_img_' + msg.id);
    if (rImg) rImg.setVisible(msg.visible);
    if (activeRasterInfo && msg.id === activeRasterInfo.id && hiresRasterLayer) hiresRasterLayer.setVisible(msg.visible);
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => l.setVisible(msg.visible));
  }
}

function handleSetLayerOpacity(msg) {
  if (msg.id === 'osm_basemap' || msg.type === 'Basemap') {
    cartoLayer.setOpacity(msg.opacity); satelliteLayer.setOpacity(msg.opacity);
  } else if (msg.id === activePointCloudId || msg.type === 'PointCloud') {
    pcCanvas.style.opacity = msg.opacity;
  } else if (msg.id === 'vector_active' || msg.type === 'Vector') {
    vectorLayer.setOpacity(msg.opacity);
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => l.setOpacity(msg.opacity));
  } else {
    const rImg = map.getLayers().getArray().find(l => l.get('id') === 'raster_img_' + msg.id);
    if (rImg) rImg.setOpacity(msg.opacity);
    if (activeRasterInfo && msg.id === activeRasterInfo.id && hiresRasterLayer) hiresRasterLayer.setOpacity(msg.opacity);
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => l.setOpacity(msg.opacity));
  }
}

function handleAddVectorLayer(msg) {
  if (!msg || !msg.id) return;
  const layerStart = performance.now();
  const layerId = msg.id;
  const layerName = msg.name || 'Vector Layer';
  const isContour = !!msg.isContour;
  const baseColor = msg.color || (isContour ? '#d97706' : '#10b981');

  // Remove existing instance if present
  map.getLayers().getArray()
    .filter(l => l.get('id') === layerId || l.get('id') === 'vector_' + layerId)
    .forEach(l => map.removeLayer(l));

  let vSource;
  const geojsonFormat = new ol.format.GeoJSON();

  if (msg.url) {
    vSource = new ol.source.Vector({
      url: msg.url,
      format: geojsonFormat
    });
  } else if (msg.geojson) {
    try {
      const geoData = typeof msg.geojson === 'string' ? JSON.parse(msg.geojson) : msg.geojson;
      const feats = geojsonFormat.readFeatures(geoData, {
        featureProjection: 'EPSG:3857',
        dataProjection: 'EPSG:4326'
      });
      vSource = new ol.source.Vector({ features: feats });
    } catch (err) {
      console.error('[MapEngine] Error parsing GeoJSON data:', err);
      return;
    }
  } else {
    return;
  }

  // Ultra-high-performance pre-cached styles (zero allocation during zoom/pan)
  // Round joins and caps eliminate sharp corner spikes and provide smooth, organic topographic lines
  const intermediateStroke = new ol.style.Stroke({
    color: baseColor,
    width: 0.9,
    lineJoin: 'round',
    lineCap: 'round'
  });
  const intermediateStyle = new ol.style.Style({ stroke: intermediateStroke });

  const indexStroke = new ol.style.Stroke({
    color: '#9a3412',
    width: 1.6,
    lineJoin: 'round',
    lineCap: 'round'
  });
  const indexBaseStyle = new ol.style.Style({ stroke: indexStroke });

  const genericPointStyle = new ol.style.Style({
    image: new ol.style.Circle({
      radius: 5,
      fill: new ol.style.Fill({ color: baseColor }),
      stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
    })
  });
  const genericLineStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 2.0, lineJoin: 'round', lineCap: 'round' })
  });
  const genericPolyStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 2.0, lineJoin: 'round', lineCap: 'round' }),
    fill: new ol.style.Fill({ color: 'rgba(16, 185, 129, 0.25)' })
  });

  const labelCache = new Map();
  // Determine index interval (e.g. every 5th contour or multiple of 5m/10m/50m)
  const rawInterval = parseFloat(msg.interval) || 10;
  const indexStep = rawInterval <= 1 ? 5 : (rawInterval <= 2 ? 10 : (rawInterval <= 5 ? 25 : (rawInterval <= 10 ? 50 : rawInterval * 5)));

  // Dynamic styling with zero heap allocations during zoom/pan
  const styleFn = function (feature, resolution) {
    const geom = feature.getGeometry();
    if (!geom) return null;
    const geomType = geom.getType();

    if (isContour || feature.get('ELEV') !== undefined) {
      const elev = feature.get('ELEV');
      if (elev === undefined || elev === null) return intermediateStyle;

      const elevNum = Math.round(Number(elev) * 10) / 10;
      const isIndex = (Math.abs(elevNum % indexStep) < 0.05) || (Math.abs(elevNum % 5) < 0.05);

      // Check on-screen pixel length to prevent cluttering on micro-segments
      const lineLen = geom.getLength ? geom.getLength() : 0;
      const screenLen = resolution > 0 ? (lineLen / resolution) : 0;

      // Index contours show labels when screen length is at least 70px
      // Intermediate contours show labels when zoomed in close (resolution < 4) and line is prominent (> 180px)
      const showLabel = (isIndex && screenLen > 70 && resolution < 50) || (!isIndex && screenLen > 180 && resolution < 4);

      if (showLabel) {
        const cacheKey = (isIndex ? 'idx_' : 'int_') + elevNum;
        let cached = labelCache.get(cacheKey);
        if (!cached) {
          cached = new ol.style.Style({
            stroke: isIndex ? indexStroke : intermediateStroke,
            text: new ol.style.Text({
              text: elevNum + ' m',
              font: isIndex ? 'bold 11px Inter, -apple-system, sans-serif' : '10px Inter, -apple-system, sans-serif',
              fill: new ol.style.Fill({ color: isIndex ? '#451a03' : '#7c2d12' }),
              stroke: new ol.style.Stroke({ color: '#ffffff', width: 2.5 }),
              placement: 'line',
              repeat: 1000,
              overflow: false,
              maxAngle: Math.PI / 4
            })
          });
          labelCache.set(cacheKey, cached);
        }
        return cached;
      }

      return isIndex ? indexBaseStyle : intermediateStyle;
    }

    if (geomType.includes('Point')) return genericPointStyle;
    if (geomType.includes('Line')) return genericLineStyle;
    return genericPolyStyle;
  };

  // Use VectorImage for off-screen canvas raster caching: 60 FPS silky smooth zoom/pan with zero lag
  const LayerClass = (typeof ol.layer.VectorImage === 'function') ? ol.layer.VectorImage : ol.layer.Vector;
  const vLayer = new LayerClass({
    properties: {
      id: layerId,
      name: layerName,
      type: 'Vector',
      isContour: isContour
    },
    source: vSource,
    style: styleFn,
    declutter: true,
    imageRatio: 1.5,
    zIndex: 14
  });

  map.addLayer(vLayer);

  function applyBoundsFit() {
    if (msg.bounds) {
      const minX = Math.min(msg.bounds[0], msg.bounds[2]);
      const maxX = Math.max(msg.bounds[0], msg.bounds[2]);
      const minY = Math.min(msg.bounds[1], msg.bounds[3]);
      const maxY = Math.max(msg.bounds[1], msg.bounds[3]);
      if (Math.abs(minX) <= 180 && Math.abs(maxX) <= 180 && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90) {
        const p1 = ol.proj.fromLonLat([minX, minY]);
        const p2 = ol.proj.fromLonLat([maxX, maxY]);
        mapView.fit([Math.min(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[0], p2[0]), Math.max(p1[1], p2[1])], { padding: [50, 50, 50, 50], duration: 500 });
        return;
      }
    }
    const ext = vSource.getExtent();
    if (ext && !ol.extent.isEmpty(ext) && isFinite(ext[0])) {
      mapView.fit(ext, { padding: [50, 50, 50, 50], duration: 500 });
    }
  }

  if (msg.url) {
    vSource.once('featuresloadend', function () {
      applyBoundsFit();
      const renderMs = Math.max(1, Math.round(performance.now() - layerStart));
      postToHost({
        action: 'layerBenchmark',
        id: layerId,
        name: layerName,
        pointsCount: vSource.getFeatures().length,
        canvasRenderMs: renderMs,
        totalMs: renderMs,
        type: 'Vector'
      });
      map.render();
    });
  } else {
    applyBoundsFit();
    const renderMs = Math.max(1, Math.round(performance.now() - layerStart));
    postToHost({
      action: 'layerBenchmark',
      id: layerId,
      name: layerName,
      pointsCount: vSource.getFeatures().length,
      canvasRenderMs: renderMs,
      totalMs: renderMs,
      type: 'Vector'
    });
    map.render();
  }
}

window.addEventListener('message', function (e) { handleHostMessage(e.data); });
if (window.chrome && window.chrome.webview) {
  window.chrome.webview.addEventListener('message', function (e) { handleHostMessage(e.data); });
}
let isReadyNotified = false;
function notifyReady() {
  if (isReadyNotified) return;
  isReadyNotified = true;
  postToHost({ action: 'ready' });
}

if (typeof map !== 'undefined' && map && map.once) {
  map.once('rendercomplete', function () {
    requestAnimationFrame(() => {
      notifyReady();
    });
  });
  setTimeout(notifyReady, 250);
} else {
  setTimeout(notifyReady, 100);
}
