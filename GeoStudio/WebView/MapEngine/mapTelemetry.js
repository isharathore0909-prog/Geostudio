// Map Telemetry and Viewport Tracking
let lastZoom = 5.0;
let moveStartTime = performance.now();
let isMoving = false;
let lastInteractionType = 'IDLE';
let currentFps = 60;
let frameCount = 0;
let lastFpsTime = performance.now();

function telemetryLoop(now) {
  frameCount++;
  const delta = now - lastFpsTime;
  if (delta >= 1000) {
    currentFps = Math.round((frameCount * 1000) / delta);
    frameCount = 0;
    lastFpsTime = now;
  }
  requestAnimationFrame(telemetryLoop);
}
requestAnimationFrame(telemetryLoop);

function getGpuHardwareInfo() {
  try {
    const testCanvas = document.createElement('canvas');
    const gl = testCanvas.getContext('webgl2') || testCanvas.getContext('webgl');
    if (!gl) return { renderer: 'Standard GPU Canvas', vendor: 'WebGL' };
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'DirectX/OpenGL WebGL2 Canvas';
    const vendor = ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : 'Hardware Accelerated';
    return { renderer, vendor, webgl2: !!testCanvas.getContext('webgl2') };
  } catch (e) {
    return { renderer: 'GPU WebGL Canvas', vendor: 'Hardware' };
  }
}

setTimeout(() => {
  const gpu = getGpuHardwareInfo();
  postToHost({ action: 'gpuInfo', gpuRenderer: gpu.renderer, gpuVendor: gpu.vendor });
}, 300);

function getActiveElementsDescription() {
  if (isPointCloudVisible && pointCloudBatch && pointCloudBatch.count > 0) return `${pointCloudBatch.count.toLocaleString()} Pts Quad`;
  if (isPointCloudVisible && pointCloudData && pointCloudData.length > 0) return `${pointCloudData.length.toLocaleString()} Pts Cloud`;
  if (activeRasterInfo) return `${activeRasterInfo.width || 4096}x${activeRasterInfo.height || 4096} Raster`;

  if (typeof map !== 'undefined' && map && map.getLayers) {
    const vLayers = map.getLayers().getArray().filter(l => l && l.get && l.get('type') === 'Vector' && (!l.getVisible || l.getVisible()));
    if (vLayers.length > 0) {
      const isGpu = vLayers.some(l => l.get('gpuAccelerated') || (typeof ol !== 'undefined' && ol.layer && ol.layer.VectorImage && l instanceof ol.layer.VectorImage));
      let totalFeats = 0;
      vLayers.forEach(l => {
        const src = l.getSource && l.getSource();
        if (src && src.getFeatures) totalFeats += src.getFeatures().length;
      });
      const featCountStr = totalFeats > 0 ? `${totalFeats.toLocaleString()} feats` : 'Vector';
      return isGpu ? `⚡ GPU Vector (${featCountStr})` : `Vector (${featCountStr})`;
    }
  }

  return 'Base Vector / Tiles';
}

function initTelemetryHandlers() {
  lastZoom = mapView.getZoom();
  map.on('movestart', function () {
    moveStartTime = performance.now();
    isMoving = true;
  });

  mapView.on('change:resolution', function () {
    const newZoom = mapView.getZoom();
    if (newZoom !== lastZoom) {
      lastInteractionType = newZoom > lastZoom ? 'ZOOM IN' : 'ZOOM OUT';
      lastZoom = newZoom;
    }
  });

  map.on('moveend', function () {
    isMoving = false;
    renderPointCloud();
    const redrawMs = Math.max(1, Math.round(performance.now() - moveStartTime));
    const currentZoom = mapView.getZoom() || 5.0;
    const activity = lastInteractionType !== 'IDLE' ? lastInteractionType : 'PAN';

    const centerLonLat = ol.proj.toLonLat(mapView.getCenter());

    postToHost({
      action: 'viewportTelemetry',
      activity: activity,
      zoom: currentZoom.toFixed(1),
      zoomNum: currentZoom,
      centerLon: centerLonLat[0],
      centerLat: centerLonLat[1],
      redrawMs: redrawMs,
      fps: currentFps,
      frameTimeMs: (redrawMs > 0 && redrawMs < 50 ? redrawMs / 8 : 1.6).toFixed(1),
      activeElements: getActiveElementsDescription()
    });

    setTimeout(() => { if (!isMoving) lastInteractionType = 'IDLE'; }, 900);

    if (activeRasterInfo) {
      clearTimeout(rasterDebounceTimer);
      rasterDebounceTimer = setTimeout(requestHighResRasterWindow, 60);
    }

    const requiresExtAttrs = (lidarColorMode === 'scan_angle' || lidarColorMode === 'return_num' || lidarColorMode === 'return_delta' || lidarColorMode === 'point_source_id' || lidarColorMode === 'withheld' || lidarColorMode === 'keypoint' || lidarColorMode === 'overlap');
    if (isPointCloudVisible && !requiresExtAttrs && (mapView.getZoom() >= 16.5) && ((pointCloudBatch && pointCloudBatch.count > 0) || (pointCloudData && pointCloudData.length > 0))) {
      clearTimeout(pointCloudDebounceTimer);
      pointCloudDebounceTimer = setTimeout(() => {
        const mapSize = map.getSize() || [window.innerWidth, window.innerHeight];
        const extent3857 = mapView.calculateExtent(mapSize);
        postToHost({ action: 'queryPointCloudViewport', bounds: extent3857 });
      }, 120);
    }
  });

  setInterval(() => {
    if (!isMoving) {
      postToHost({
        action: 'viewportTelemetry',
        activity: lastInteractionType,
        zoom: (mapView.getZoom() || 5.0).toFixed(1),
        redrawMs: 0,
        fps: currentFps,
        frameTimeMs: (1000 / Math.max(1, currentFps)).toFixed(1),
        activeElements: getActiveElementsDescription()
      });
    }
  }, 1000);
}

initTelemetryHandlers();
