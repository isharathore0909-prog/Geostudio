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
      if (window.initialLidarBatch && (!pointCloudBatch || !pointCloudBatch.sa || !pointCloudBatch.rn)) {
        pointCloudBatch = window.initialLidarBatch;
      }
      renderPointCloud();
      break;
    case 'updateClassification':
      const decodedClasses = decodeBuffer(msg.classes);
      if (pointCloudBatch && decodedClasses) {
        pointCloudBatch.c = decodedClasses;
      }
      if (window.initialLidarBatch && decodedClasses) {
        window.initialLidarBatch.c = decodedClasses;
      }
      if (msg.colorBy) {
        lidarColorMode = msg.colorBy;
      }
      renderPointCloud();
      if (typeof updateLidarLegendWidget === 'function') {
        updateLidarLegendWidget(lidarColorMode);
      }
      break;
    case 'loadPointCloud':
      handleLoadPointCloud(msg);
      break;
    case 'updatePointCloud':
      if (msg.batch && msg.batch.count > 0) {
        const requiresExtAttrs = (lidarColorMode === 'scan_angle' || lidarColorMode === 'return_num' || lidarColorMode === 'return_delta' || lidarColorMode === 'point_source_id' || lidarColorMode === 'withheld' || lidarColorMode === 'keypoint' || lidarColorMode === 'overlap');
        if (!requiresExtAttrs || msg.batch.sa) {
          const keys = ['r', 'g', 'b', 'c', 'i', 'rn', 'nr', 'sa', 'ps', 'fl', 'nir'];
          for (let k = 0; k < keys.length; k++) {
            const key = keys[k];
            if (msg.batch[key]) msg.batch[key] = decodeBuffer(msg.batch[key]);
          }
          pointCloudBatch = msg.batch;
          pointCloudData = [];
        }
      } else if (msg.points) {
        pointCloudData = msg.points;
        pointCloudBatch = null;
      }
      renderPointCloud();
      if (typeof updateLidarLegendWidget === 'function') {
        updateLidarLegendWidget(lidarColorMode);
      }
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
