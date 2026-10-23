// GeoStudio Core Map Engine Lifecycle & Viewport
const mapView = new ol.View({
  center: ol.proj.fromLonLat([76.515, 24.762]),
  zoom: 5,
  maxZoom: 22
});

const mapPopupElement = document.getElementById('mapPopup');
const mapPopupContent = document.getElementById('mapPopupContent');
const mapPopupCloser = document.getElementById('mapPopupCloser');

let mapPopupOverlay = null;
if (mapPopupElement) {
  mapPopupOverlay = new ol.Overlay({
    element: mapPopupElement,
    autoPan: {
      animation: {
        duration: 250
      }
    }
  });
  if (mapPopupCloser) {
    mapPopupCloser.onclick = function () {
      if (mapPopupOverlay) mapPopupOverlay.setPosition(undefined);
      mapPopupCloser.blur();
      return false;
    };
  }
}

const map = new ol.Map({
  target: 'map',
  layers: [satelliteLayer, cartoLayer, rasterLayer, vectorLayer, measureLayer, profileLayer, clipMaskLayer, selectionLayer, markerLayer],
  overlays: mapPopupOverlay ? [mapPopupOverlay] : [],
  view: mapView,
  controls: ol.control.defaults.defaults().extend([
    new ol.control.ScaleLine({ units: 'metric' })
  ])
});

map.on('postrender', renderPointCloud);

function postToHost(message) {
  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.postMessage(message);
  } else {
    console.log('[MapEngine -> Host]', message);
  }
}

let lastPointerMoveTime = 0;
map.on('pointermove', function (evt) {
  if (evt.dragging) return;
  const now = performance.now();
  if (now - lastPointerMoveTime < 40) return;
  lastPointerMoveTime = now;

  const coord = ol.proj.toLonLat(evt.coordinate);
  const lon = coord[0];
  const lat = coord[1];
  let elev = null;

  map.forEachFeatureAtPixel(evt.pixel, function (feature) {
    if (feature && feature.get('ELEV') !== undefined && feature.get('ELEV') !== null) {
      elev = Math.round(Number(feature.get('ELEV')));
      return true;
    }
  }, { hitTolerance: 3 });

  if (elev === null) {
    elev = Math.round(Math.abs(Math.sin(lon * 0.05) * Math.cos(lat * 0.05)) * 1250 + 120);
  }

  const resolution = mapView.getResolution();
  const scale = Math.round(resolution * 39.37 * 96 * 3.5);

  postToHost({
    action: 'pointerMove',
    lon: lon.toFixed(6),
    lat: lat.toFixed(6),
    elev: elev,
    scale: scale.toLocaleString()
  });
});

// Map Viewport Extent History (Undo / Redo)
const extentUndoStack = [];
const extentRedoStack = [];
let isNavigatingExtent = false;
let lastRecordedExtent = {
  center: [8517616.5, 2846875.5],
  zoom: 5
};

map.on('moveend', function () {
  const currentCenter = mapView.getCenter();
  const currentZoom = mapView.getZoom();
  if (!currentCenter) return;

  if (!isNavigatingExtent && lastRecordedExtent) {
    const distSq = Math.pow(currentCenter[0] - lastRecordedExtent.center[0], 2) + Math.pow(currentCenter[1] - lastRecordedExtent.center[1], 2);
    const zoomDiff = Math.abs(currentZoom - lastRecordedExtent.zoom);

    if (distSq > 10000 || zoomDiff > 0.15) {
      extentUndoStack.push({
        center: lastRecordedExtent.center.slice(),
        zoom: lastRecordedExtent.zoom
      });
      if (extentUndoStack.length > 50) extentUndoStack.shift();
      extentRedoStack.length = 0;
    }
  }

  lastRecordedExtent = {
    center: currentCenter.slice(),
    zoom: currentZoom
  };
  isNavigatingExtent = false;
});

function undoMapAction() {
  if (typeof vectorSource !== 'undefined' && vectorSource.getFeatures().length > 0 && typeof activeTool !== 'undefined' && activeTool.startsWith('digitize')) {
    const feats = vectorSource.getFeatures();
    vectorSource.removeFeature(feats[feats.length - 1]);
    postToHost({ action: 'statusMessage', message: `Undid digitized feature (${feats.length - 1} remaining)` });
    return;
  }

  if (extentUndoStack.length > 0) {
    isNavigatingExtent = true;
    extentRedoStack.push({
      center: mapView.getCenter().slice(),
      zoom: mapView.getZoom()
    });
    const target = extentUndoStack.pop();
    lastRecordedExtent = target;
    mapView.animate({
      center: target.center,
      zoom: target.zoom,
      duration: 350
    });
    const cLonLat = ol.proj.toLonLat(target.center);
    postToHost({
      action: 'statusMessage',
      message: `Navigated to previous extent: Lat ${cLonLat[1].toFixed(4)}°, Lon ${cLonLat[0].toFixed(4)}° (Zoom ${target.zoom.toFixed(1)}x)`
    });
  } else {
    postToHost({ action: 'statusMessage', message: 'No previous map extent in history' });
  }
}

function redoMapAction() {
  if (extentRedoStack.length > 0) {
    isNavigatingExtent = true;
    extentUndoStack.push({
      center: mapView.getCenter().slice(),
      zoom: mapView.getZoom()
    });
    const target = extentRedoStack.pop();
    lastRecordedExtent = target;
    mapView.animate({
      center: target.center,
      zoom: target.zoom,
      duration: 350
    });
    const cLonLat = ol.proj.toLonLat(target.center);
    postToHost({
      action: 'statusMessage',
      message: `Navigated to next extent: Lat ${cLonLat[1].toFixed(4)}°, Lon ${cLonLat[0].toFixed(4)}° (Zoom ${target.zoom.toFixed(1)}x)`
    });
  } else {
    postToHost({ action: 'statusMessage', message: 'No forward map extent in history' });
  }
}

if (typeof initTelemetryHandlers === 'function') {
  initTelemetryHandlers();
}
