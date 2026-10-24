// IPC Bridge Handlers for Raster Overview and Viewport Window Updates
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

  const targetId = msg.id || (activeRasterInfo ? activeRasterInfo.id : 'default');
  const existingLayer = map.getLayers().getArray().find(l => {
    const lid = l.get('id');
    return lid === 'raster_img_' + targetId || lid === targetId;
  });
  const isVis = existingLayer ? existingLayer.getVisible() : (activeRasterInfo ? (activeRasterInfo.visible !== false) : true);

  if (activeRasterInfo) {
    activeRasterInfo.hasOverview = true;
    activeRasterInfo.visible = isVis;
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

  if (isVis && typeof updateShaderScaleWidget === 'function') {
    updateShaderScaleWidget(sMode, sPal, sMin, sMax);
  } else if (!isVis && typeof hideShaderScaleWidget === 'function') {
    hideShaderScaleWidget();
  }

  const rMinX = bounds[0], rMinY = bounds[1], rMaxX = bounds[2], rMaxY = bounds[3];
  let fullExt = (Math.abs(rMinX) <= 180 && Math.abs(rMaxX) <= 180 && Math.abs(rMinY) <= 90 && Math.abs(rMaxY) <= 90)
    ? [Math.min(ol.proj.fromLonLat([rMinX, rMinY])[0], ol.proj.fromLonLat([rMaxX, rMaxY])[0]), Math.min(ol.proj.fromLonLat([rMinX, rMinY])[1], ol.proj.fromLonLat([rMaxX, rMaxY])[1]), Math.max(ol.proj.fromLonLat([rMinX, rMinY])[0], ol.proj.fromLonLat([rMaxX, rMaxY])[0]), Math.max(ol.proj.fromLonLat([rMinX, rMinY])[1], ol.proj.fromLonLat([rMaxX, rMaxY])[1])]
    : [Math.min(rMinX, rMaxX), Math.min(rMinY, rMaxY), Math.max(rMinX, rMaxX), Math.max(rMinY, rMaxY)];

  const layerName = msg.name || (existingLayer ? existingLayer.get('name') : null) || (activeRasterInfo ? activeRasterInfo.name : 'DEM');
  const zIdx = existingLayer ? existingLayer.getZIndex() : 7;
  const opac = (activeRasterInfo && activeRasterInfo.opacity !== undefined)
    ? activeRasterInfo.opacity
    : (existingLayer ? existingLayer.getOpacity() : 1.0);

  map.getLayers().getArray().filter(l => l.get('id') === 'raster_img_' + targetId || l.get('id') === targetId).forEach(l => map.removeLayer(l));

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

  const newImgLayer = new ol.layer.Image({ source: overviewSource, opacity: opac, zIndex: zIdx, visible: isVis });
  newImgLayer.set('id', 'raster_img_' + targetId);
  newImgLayer.set('name', layerName);
  newImgLayer.set('type', 'Raster');
  newImgLayer.setVisible(isVis);
  map.addLayer(newImgLayer);

  if (mapView.getZoom() >= 12 && isVis) {
    clearTimeout(rasterDebounceTimer);
    rasterDebounceTimer = setTimeout(requestHighResRasterWindow, 60);
  }
}

function handleUpdateRasterWindow(msg) {
  if (!msg.imageUrl || !msg.bounds) return;
  if (activeRasterInfo && activeRasterInfo.visible === false) return;
  const currentOpacity = (msg.opacity !== undefined && msg.opacity !== null)
    ? parseFloat(msg.opacity)
    : ((activeRasterInfo && activeRasterInfo.opacity !== undefined) ? activeRasterInfo.opacity : 1.0);

  if (!hiresRasterLayer) {
    hiresRasterLayer = new ol.layer.Image({ properties: { id: 'raster_hires_layer' }, zIndex: 10, opacity: currentOpacity });
    hiresRasterLayer.set('id', 'raster_hires_layer');
    hiresRasterLayer.set('type', 'Raster');
    map.addLayer(hiresRasterLayer);
  } else {
    hiresRasterLayer.setOpacity(currentOpacity);
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
  hiresRasterLayer.setOpacity(currentOpacity);
  map.render();
}
