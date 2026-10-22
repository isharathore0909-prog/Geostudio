// GeoStudio Core Map Engine Lifecycle & Viewport
const mapView = new ol.View({
  center: ol.proj.fromLonLat([76.515, 24.762]),
  zoom: 5,
  maxZoom: 22
});

const map = new ol.Map({
  target: 'map',
  layers: [satelliteLayer, cartoLayer, rasterLayer, vectorLayer, measureLayer, profileLayer],
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

initTelemetryHandlers();
