// IPC Bridge Handlers for General Layer Management & Point Cloud Loading
function handleLoadPointCloud(msg) {
  const pcStart = performance.now();
  activePointCloudId = msg.id || 'pointcloud_layer';
  isPointCloudVisible = true;
  pcCanvas.style.opacity = '1.0';
  if (msg.colorMode) lidarColorMode = msg.colorMode;
  if (msg.pointSize) userPointSize = parseFloat(msg.pointSize) || 4.5;
  if (msg.batch) {
    pointCloudBatch = msg.batch;
    const keys = ['r', 'g', 'b', 'c', 'i', 'rn', 'nr', 'sa', 'ps', 'fl', 'nir', 't'];
    for (let k = 0; k < keys.length; k++) {
      const key = keys[k];
      if (pointCloudBatch[key]) pointCloudBatch[key] = decodeBuffer(pointCloudBatch[key]);
    }
    window.initialLidarBatch = pointCloudBatch;
    pointCloudData = [];
  }
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

function handleToggleLayer(msg) {
  const isVis = !!msg.visible;
  if (msg.id === 'osm_basemap' || msg.type === 'Basemap') {
    cartoLayer.setVisible(isVis);
    satelliteLayer.setVisible(isVis);
  } else if (msg.id === activePointCloudId || msg.type === 'PointCloud' || (msg.id && msg.id.startsWith('pc_'))) {
    isPointCloudVisible = isVis;
    const lWidget = document.getElementById('lidarLegendWidget');
    if (!isPointCloudVisible) {
      pcCtx.clearRect(0, 0, pcCanvas.width, pcCanvas.height);
      if (lWidget) lWidget.style.display = 'none';
    } else {
      renderPointCloud();
      if (typeof updateLidarLegendWidget === 'function') {
        updateLidarLegendWidget(lidarColorMode);
      }
    }
  } else if (msg.id === 'vector_active' || msg.type === 'Vector') {
    vectorLayer.setVisible(isVis);
    map.getLayers().getArray().filter(l => l.get('id') === msg.id || l.get('id') === 'vector_' + msg.id).forEach(l => l.setVisible(isVis));
  } else {
    // Raster / DEM / DSM layers
    if (activeRasterInfo && (msg.id === activeRasterInfo.id || msg.type === 'Raster')) {
      activeRasterInfo.visible = isVis;
      if (hiresRasterLayer) hiresRasterLayer.setVisible(isVis);
    }

    map.getLayers().getArray().forEach(l => {
      const lid = l.get('id') || '';
      if (lid === msg.id || lid === 'raster_img_' + msg.id || lid === 'hires_viewport_layer' || lid === 'raster_hires_layer') {
        l.setVisible(isVis);
      }
    });

    if (!isVis) {
      if (typeof hideShaderScaleWidget === 'function') hideShaderScaleWidget();
    } else {
      if (typeof updateShaderScaleWidget === 'function') updateShaderScaleWidget();
    }

    // Refresh LiDAR legend position if both or one are visible
    if (isPointCloudVisible && typeof updateLidarLegendWidget === 'function') {
      updateLidarLegendWidget(lidarColorMode);
    }
  }
  map.render();
}

function handleSetLayerOpacity(msg) {
  const opacity = parseFloat(msg.opacity);
  if (isNaN(opacity)) return;
  const clampedOpacity = Math.max(0, Math.min(1, opacity));

  const isRaster = (msg.type === 'Raster' || msg.type === 'Elevation' || (activeRasterInfo && activeRasterInfo.id === msg.id));
  if (isRaster) {
    if (activeRasterInfo) {
      activeRasterInfo.opacity = clampedOpacity;
    }
    if (typeof hiresRasterLayer !== 'undefined' && hiresRasterLayer) {
      hiresRasterLayer.setOpacity(clampedOpacity);
    }
  }

  if (msg.id === 'osm_basemap' || msg.id === 'satellite_basemap' || msg.type === 'Basemap') {
    if (typeof cartoLayer !== 'undefined' && cartoLayer) cartoLayer.setOpacity(clampedOpacity);
    if (typeof satelliteLayer !== 'undefined' && satelliteLayer) satelliteLayer.setOpacity(clampedOpacity);
  } else if (msg.id === activePointCloudId || msg.type === 'PointCloud' || (msg.id && msg.id.startsWith('pc_'))) {
    if (typeof pcCanvas !== 'undefined' && pcCanvas) {
      pcCanvas.style.opacity = String(clampedOpacity);
    }
  } else {
    if (msg.id === 'vector_active' || (!msg.id && msg.type === 'Vector')) {
      if (typeof vectorLayer !== 'undefined' && vectorLayer) vectorLayer.setOpacity(clampedOpacity);
    }
    map.getLayers().getArray().forEach(l => {
      const lid = l.get('id') || '';
      const lType = l.get('type') || '';
      if (lid === msg.id ||
          lid === 'raster_img_' + msg.id ||
          lid === 'vector_' + msg.id ||
          (isRaster && (lid === 'hires_viewport_layer' || lid === 'raster_hires_layer' || lid.startsWith('raster_img_'))) ||
          (!msg.id && msg.type && lType === msg.type)) {
        l.setOpacity(clampedOpacity);
      }
    });
  }
  map.render();
}
