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
    case 'undo':
    case 'previousExtent':
      if (typeof undoMapAction === 'function') undoMapAction();
      break;
    case 'redo':
    case 'nextExtent':
      if (typeof redoMapAction === 'function') redoMapAction();
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
    case 'setBlendMode':
      if (typeof applyLayerBlendMode === 'function') {
        applyLayerBlendMode(msg.mode);
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
    case 'toggleEditing':
      if (typeof handleToggleEditing === 'function') handleToggleEditing(msg.active);
      break;
    case 'setSnappingTolerance':
      if (typeof handleSetSnappingTolerance === 'function') handleSetSnappingTolerance(msg.tolerance);
      break;
    case 'getCanvasExtent':
      if (map && map.getView) {
        const curExt = map.getView().calculateExtent(map.getSize());
        const curExt4326 = ol.proj.transformExtent(curExt, map.getView().getProjection(), 'EPSG:4326');
        postToHost({
          action: 'canvasExtentReady',
          bbox: curExt4326
        });
      }
      break;
    case 'clearClipMask':
      if (typeof clipMaskSource !== 'undefined') clipMaskSource.clear();
      break;
    case 'undoVertex':
      if (typeof handleUndoVertex === 'function') handleUndoVertex();
      break;
    case 'deleteSelectedFeature':
      if (typeof handleDeleteSelectedFeature === 'function') handleDeleteSelectedFeature();
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
    case 'toggleLayerGpu':
      if (typeof handleToggleLayerGpu === 'function') handleToggleLayerGpu(msg);
      break;
    case 'clearProfileLine':
      if (typeof clearProfileLine === 'function') clearProfileLine();
      break;
    case 'goToCoord':
      if (typeof msg.lon === 'number' && typeof msg.lat === 'number') {
        const c = ol.proj.fromLonLat([msg.lon, msg.lat]);
        mapView.animate({ center: c, zoom: msg.zoom || 13, duration: 600 });
        markerSource.clear();
        const pin = new ol.Feature({
          geometry: new ol.geom.Point(c),
          label: msg.label || `(${msg.lat.toFixed(4)}°, ${msg.lon.toFixed(4)}°)`
        });
        markerSource.addFeature(pin);
      }
      break;
    case 'setCenterZoom':
      if (typeof msg.lon === 'number' && typeof msg.lat === 'number') {
        mapView.animate({
          center: ol.proj.fromLonLat([msg.lon, msg.lat]),
          zoom: msg.zoom || mapView.getZoom(),
          duration: 350
        });
      }
      break;
    case 'clearSelection':
      if (typeof selectionSource !== 'undefined') selectionSource.clear();
      if (mapPopupOverlay) mapPopupOverlay.setPosition(undefined);
      break;
    case 'zoomToSelected':
      if (typeof selectionSource !== 'undefined' && selectionSource.getFeatures().length > 0) {
        mapView.fit(selectionSource.getExtent(), { padding: [60, 60, 60, 60], duration: 500 });
      }
      break;
    case 'clearMarkers':
      if (typeof markerSource !== 'undefined') markerSource.clear();
      if (mapPopupOverlay) mapPopupOverlay.setPosition(undefined);
      break;
    case 'selectByAttribute':
      if (typeof selectionSource !== 'undefined') {
        selectionSource.clear();
        let matched = 0;
        const key = (msg.key || '').trim();
        const op = msg.op || '=';
        const rawVal = (msg.value !== undefined && msg.value !== null) ? String(msg.value).trim() : '';
        const targetLayerId = msg.layerId;
        const isVectorLayer = (l) => {
          if (!l || l === selectionLayer || l === markerLayer || l === measureLayer || l === profileLayer) return false;
          if (l instanceof ol.layer.Vector) return true;
          if (typeof ol.layer.VectorImage === 'function' && l instanceof ol.layer.VectorImage) return true;
          if (typeof ol.layer.BaseVector === 'function' && l instanceof ol.layer.BaseVector) return true;
          return !!(l.get && (l.get('type') === 'Vector' || l.get('id')));
        };
        const vectorLayers = map.getLayers().getArray().filter(l => 
          isVectorLayer(l) &&
          (!targetLayerId || l.get('id') === targetLayerId || l.get('id') === 'vector_' + targetLayerId)
        );
        vectorLayers.forEach(l => {
          const src = l.getSource();
          if (src && src.getFeatures) {
            src.getFeatures().forEach(f => {
              let val = f.get(key);
              if (val === undefined || val === null) {
                const props = f.getProperties();
                const matchedKey = Object.keys(props).find(k => k.toLowerCase() === key.toLowerCase());
                if (matchedKey) val = props[matchedKey];
              }
              if (val !== undefined && val !== null) {
                let isMatch = false;
                const sVal = String(val).trim().toLowerCase();
                const sRaw = rawVal.toLowerCase();
                if (op === '=' && sVal === sRaw) isMatch = true;
                else if (op === '!=' && sVal !== sRaw) isMatch = true;
                else if (op === 'contains' && sVal.includes(sRaw)) isMatch = true;
                else if (op === '>' && Number(val) > Number(rawVal)) isMatch = true;
                else if (op === '<' && Number(val) < Number(rawVal)) isMatch = true;
                else if (op === '>=' && Number(val) >= Number(rawVal)) isMatch = true;
                else if (op === '<=' && Number(val) <= Number(rawVal)) isMatch = true;

                if (isMatch) {
                  selectionSource.addFeature(f.clone());
                  matched++;
                }
              }
            });
          }
        });
        if (matched > 0) {
          mapView.fit(selectionSource.getExtent(), { padding: [60, 60, 60, 60], duration: 500 });
        }
        postToHost({ action: 'selectByAttributeResult', count: matched, key: key, value: rawVal });
      }
      break;
    case 'getVectorFeatures':
      const featList = [];
      const isVec = (l) => {
        if (!l || l === selectionLayer || l === markerLayer || l === measureLayer || l === profileLayer) return false;
        if (l instanceof ol.layer.Vector) return true;
        if (typeof ol.layer.VectorImage === 'function' && l instanceof ol.layer.VectorImage) return true;
        if (typeof ol.layer.BaseVector === 'function' && l instanceof ol.layer.BaseVector) return true;
        return !!(l.get && l.get('type') === 'Vector');
      };
      const vLayers = map.getLayers().getArray().filter(isVec);
      vLayers.forEach(l => {
        const src = l.getSource();
        const lName = (l.get && (l.get('name') || (l.get('properties') && l.get('properties').name))) || 'Vector Layer';
        if (src && src.getFeatures) {
          src.getFeatures().forEach((f, idx) => {
            const p = Object.assign({}, f.getProperties());
            delete p.geometry;
            p['_id'] = idx + 1;
            p['_layer'] = lName;
            featList.push(p);
          });
        }
      });
      postToHost({ action: 'vectorFeaturesData', features: featList });
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
