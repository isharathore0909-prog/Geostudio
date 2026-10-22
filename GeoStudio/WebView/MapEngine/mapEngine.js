// GeoStudio Core Map Engine
const cartoSource = new ol.source.XYZ({
  url: 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
  maxZoom: 20,
  crossOrigin: 'anonymous'
});
const cartoLayer = new ol.layer.Tile({
  properties: { id: 'osm_basemap', name: 'Global Basemap' },
  source: cartoSource,
  visible: false
});

const esriSatelliteSource = new ol.source.XYZ({
  url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  maxZoom: 19,
  crossOrigin: 'anonymous'
});
const satelliteLayer = new ol.layer.Tile({
  properties: { id: 'satellite_basemap', name: 'Esri Satellite' },
  source: esriSatelliteSource,
  visible: false
});

cartoSource.on('tileloaderror', function () { if (!navigator.onLine) cartoLayer.setVisible(false); });
esriSatelliteSource.on('tileloaderror', function () { if (!navigator.onLine) satelliteLayer.setVisible(false); });
if (typeof navigator !== 'undefined' && navigator.onLine === false) {
  cartoLayer.setVisible(false);
  satelliteLayer.setVisible(false);
}
window.addEventListener('offline', function () {
  cartoLayer.setVisible(false);
  satelliteLayer.setVisible(false);
});

const rasterSource = new ol.source.Vector({ wrapX: false });
const rasterLayer = new ol.layer.Vector({
  properties: { id: 'raster_layers', name: 'Raster Layers' },
  source: rasterSource,
  zIndex: 6
});

const vectorSource = new ol.source.Vector({ wrapX: false });
const vectorLayer = new ol.layer.Vector({
  properties: { id: 'vector_active', name: 'Digitized Layer' },
  source: vectorSource,
  style: new ol.style.Style({
    fill: new ol.style.Fill({ color: 'rgba(59, 130, 246, 0.25)' }),
    stroke: new ol.style.Stroke({ color: '#2563eb', width: 2.5 }),
    image: new ol.style.Circle({
      radius: 6,
      fill: new ol.style.Fill({ color: '#2563eb' }),
      stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
    })
  }),
  zIndex: 10
});

const measureSource = new ol.source.Vector();
const measureLayer = new ol.layer.Vector({
  source: measureSource,
  style: new ol.style.Style({
    fill: new ol.style.Fill({ color: 'rgba(234, 88, 12, 0.2)' }),
    stroke: new ol.style.Stroke({ color: '#ea580c', lineDash: [8, 4], width: 2.5 }),
    image: new ol.style.Circle({
      radius: 5,
      fill: new ol.style.Fill({ color: '#ea580c' }),
      stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
    })
  }),
  zIndex: 15
});

const profileSource = new ol.source.Vector({ wrapX: false });
const profileLayer = new ol.layer.Vector({
  properties: { id: 'elevation_profile_layer', name: 'Elevation Profile' },
  source: profileSource,
  style: function () {
    return [
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#ffffff', width: 6 })
      }),
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#0284c7', width: 3.5, lineDash: [8, 4] }),
        image: new ol.style.Circle({
          radius: 6,
          fill: new ol.style.Fill({ color: '#0284c7' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
        })
      })
    ];
  },
  zIndex: 20
});

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

let activeTool = 'pan';
let drawInteraction = null;
let measureTooltipElement = null;
let measureTooltip = null;

function createMeasureTooltip() {
  if (measureTooltipElement && measureTooltipElement.parentNode) {
    measureTooltipElement.parentNode.removeChild(measureTooltipElement);
  }
  measureTooltipElement = document.createElement('div');
  measureTooltipElement.className = 'ol-tooltip ol-tooltip-measure';
  measureTooltip = new ol.Overlay({
    element: measureTooltipElement,
    offset: [0, -15],
    positioning: 'bottom-center',
    stopEvent: false
  });
  map.addOverlay(measureTooltip);
}

function setTool(tool) {
  activeTool = tool;
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
  map.getViewport().style.cursor = 'default';

  if (tool === 'pan') {
    map.getViewport().style.cursor = 'grab';
  } else if (tool === 'measure_distance') {
    map.getViewport().style.cursor = 'crosshair';
    createMeasureTooltip();
    drawInteraction = new ol.interaction.Draw({
      source: measureSource,
      type: 'LineString',
      style: new ol.style.Style({ stroke: new ol.style.Stroke({ color: '#ea580c', lineDash: [6, 4], width: 2.5 }) })
    });
    setupMeasureEvents(drawInteraction, 'LineString');
    map.addInteraction(drawInteraction);
  } else if (tool === 'measure_area') {
    map.getViewport().style.cursor = 'crosshair';
    createMeasureTooltip();
    drawInteraction = new ol.interaction.Draw({
      source: measureSource,
      type: 'Polygon',
      style: new ol.style.Style({
        fill: new ol.style.Fill({ color: 'rgba(234, 88, 12, 0.25)' }),
        stroke: new ol.style.Stroke({ color: '#ea580c', lineDash: [6, 4], width: 2.5 })
      })
    });
    setupMeasureEvents(drawInteraction, 'Polygon');
    map.addInteraction(drawInteraction);
  } else if (tool === 'digitize_point') {
    map.getViewport().style.cursor = 'crosshair';
    drawInteraction = new ol.interaction.Draw({ source: vectorSource, type: 'Point' });
    setupDigitizeEvents(drawInteraction, 'Point');
    map.addInteraction(drawInteraction);
  } else if (tool === 'digitize_line') {
    map.getViewport().style.cursor = 'crosshair';
    drawInteraction = new ol.interaction.Draw({ source: vectorSource, type: 'LineString' });
    setupDigitizeEvents(drawInteraction, 'LineString');
    map.addInteraction(drawInteraction);
  } else if (tool === 'digitize_polygon') {
    map.getViewport().style.cursor = 'crosshair';
    drawInteraction = new ol.interaction.Draw({ source: vectorSource, type: 'Polygon' });
    setupDigitizeEvents(drawInteraction, 'Polygon');
    map.addInteraction(drawInteraction);
  } else if (tool === 'elevation_profile') {
    map.getViewport().style.cursor = 'crosshair';
    drawInteraction = new ol.interaction.Draw({
      source: profileSource,
      type: 'LineString',
      maxPoints: 2,
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#0284c7', width: 3.5, lineDash: [8, 4] }),
        image: new ol.style.Circle({
          radius: 6,
          fill: new ol.style.Fill({ color: '#0284c7' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
        })
      })
    });
    drawInteraction.on('drawstart', function() {
      profileSource.clear();
    });
    drawInteraction.on('drawend', function(evt) {
      const geom = evt.feature.getGeometry();
      const coords3857 = geom.getCoordinates();
      if (coords3857.length >= 2) {
        const pt1 = ol.proj.toLonLat(coords3857[0]);
        const pt2 = ol.proj.toLonLat(coords3857[coords3857.length - 1]);
        postToHost({
          action: 'profileLineDrawn',
          p1: { lon: pt1[0], lat: pt1[1] },
          p2: { lon: pt2[0], lat: pt2[1] }
        });
      }
    });
    map.addInteraction(drawInteraction);
  }
}

function clearProfileLine() {
  if (typeof profileSource !== 'undefined' && profileSource) {
    profileSource.clear();
  }
  if (typeof vectorSource !== 'undefined' && vectorSource) {
    const toRemove = [];
    vectorSource.forEachFeature(function(f) {
      const g = f.getGeometry();
      if (g && g.getType() === 'LineString' && g.getCoordinates().length === 2) {
        toRemove.push(f);
      }
    });
    toRemove.forEach(function(f) {
      vectorSource.removeFeature(f);
    });
  }
  if (activeTool === 'elevation_profile') {
    setTool('pan');
  }
  map.render();
}

let isSwipeActive = false;
let swipeFraction = 0.5;
let swipeInverted = false;

function initSwipeInteraction() {
  const container = document.getElementById('swipeContainer');
  const btnExit = document.getElementById('btnExitSwipe');
  const btnSwap = document.getElementById('btnSwapSwipe');
  if (!container) return;

  if (btnExit) {
    btnExit.onclick = function(e) {
      e.stopPropagation();
      toggleSwipe(false);
    };
  }

  if (btnSwap) {
    btnSwap.onclick = function(e) {
      e.stopPropagation();
      swipeInverted = !swipeInverted;
      updateSwipeBadgeText();
      map.render();
    };
  }

  let dragging = false;

  function onPointerDown(e) {
    if (e.button !== undefined && e.button !== 0) return;
    dragging = true;
    try { container.setPointerCapture(e.pointerId); } catch(err){}
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
    e.stopPropagation();
  }

  function updatePosition(clientX) {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;
    const rect = mapEl.getBoundingClientRect();
    const x = Math.max(10, Math.min(rect.width - 10, clientX - rect.left));
    swipeFraction = x / rect.width;
    container.style.left = (swipeFraction * 100) + '%';
    map.render();
  }

  function onPointerMove(e) {
    if (!dragging) return;
    updatePosition(e.clientX);
    e.preventDefault();
    e.stopPropagation();
  }

  function onPointerUp(e) {
    if (dragging) {
      dragging = false;
      try { container.releasePointerCapture(e.pointerId); } catch(err){}
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      e.preventDefault();
      e.stopPropagation();
    }
  }

  container.addEventListener('pointerdown', onPointerDown);
  container.addEventListener('mousedown', onPointerDown);
  window.addEventListener('pointermove', onPointerMove, { passive: false });
  window.addEventListener('mousemove', onPointerMove, { passive: false });
  window.addEventListener('pointerup', onPointerUp, { passive: false });
  window.addEventListener('mouseup', onPointerUp, { passive: false });
  window.addEventListener('pointercancel', onPointerUp);
}

function updateSwipeBadgeText() {
  const lbl = document.getElementById('swipeLabel');
  if (!lbl) return;
  const rasterLayers = map.getLayers().getArray().filter(l => (l.get('id') || '').startsWith('raster_img_'));
  if (rasterLayers.length >= 2) {
    const topLayer = rasterLayers[rasterLayers.length - 1];
    const bottomLayer = rasterLayers[rasterLayers.length - 2];
    const topName = topLayer.get('name') || 'Top Layer';
    const bottomName = bottomLayer.get('name') || 'Base Layer';
    if (!swipeInverted) {
      lbl.textContent = `◀ ${topName} | ${bottomName} ▶`;
    } else {
      lbl.textContent = `◀ ${bottomName} | ${topName} ▶`;
    }
  }
}

function toggleSwipe(forceState) {
  isSwipeActive = typeof forceState === 'boolean' ? forceState : !isSwipeActive;
  const container = document.getElementById('swipeContainer');
  const badge = document.getElementById('swipeBadge');
  if (container) container.style.display = isSwipeActive ? 'block' : 'none';
  if (badge) badge.style.display = isSwipeActive ? 'flex' : 'none';

  if (typeof hiresRasterLayer !== 'undefined' && hiresRasterLayer) {
    hiresRasterLayer.setVisible(!isSwipeActive);
  }

  const rasterLayers = map.getLayers().getArray().filter(l => (l.get('id') || '').startsWith('raster_img_'));
  rasterLayers.forEach(l => {
    l.un('prerender', swipePreRender);
    l.un('postrender', swipePostRender);
  });

  if (isSwipeActive && rasterLayers.length >= 2) {
    const topLayer = rasterLayers[rasterLayers.length - 1];
    const bottomLayer = rasterLayers[rasterLayers.length - 2];
    topLayer.setVisible(true);
    bottomLayer.setVisible(true);
    updateSwipeBadgeText();

    topLayer.on('prerender', swipePreRender);
    topLayer.on('postrender', swipePostRender);
  }
  map.render();
}

function swipePreRender(event) {
  if (!isSwipeActive) return;
  const ctx = event.context;
  if (!ctx) return;
  const mapSize = map.getSize();
  if (!mapSize) return;

  const canvas = ctx.canvas;
  const canvasW = canvas ? canvas.width : mapSize[0];
  const canvasH = canvas ? canvas.height : mapSize[1];

  let scaleX = 1;
  let scaleY = 1;
  if (typeof ctx.getTransform === 'function') {
    const m = ctx.getTransform();
    scaleX = m.a || 1;
    scaleY = m.d || 1;
  } else {
    scaleX = canvasW / mapSize[0];
    scaleY = canvasH / mapSize[1];
  }

  const clipW = (canvasW / scaleX) * swipeFraction;
  const clipH = canvasH / scaleY;

  ctx.save();
  ctx.beginPath();
  if (!swipeInverted) {
    ctx.rect(0, 0, clipW, clipH);
  } else {
    ctx.rect(clipW, 0, (canvasW / scaleX) - clipW, clipH);
  }
  ctx.clip();
}

function swipePostRender(event) {
  if (!isSwipeActive) return;
  const ctx = event.context;
  if (ctx) ctx.restore();
}

window.addEventListener('DOMContentLoaded', initSwipeInteraction);
setTimeout(initSwipeInteraction, 200);

function setupMeasureEvents(draw, type) {
  let listener;
  draw.on('drawstart', function (evt) {
    const sketch = evt.feature;
    let tooltipCoord = evt.coordinate;
    listener = sketch.getGeometry().on('change', function (evt) {
      const geom = evt.target;
      let output;
      if (type === 'Polygon') {
        const area = ol.sphere.getArea(geom);
        output = area > 1000000 ? (area / 1000000).toFixed(2) + ' km²' : Math.round(area).toLocaleString() + ' m²';
        tooltipCoord = geom.getInteriorPoint().getCoordinates();
      } else {
        const length = ol.sphere.getLength(geom);
        output = length > 1000 ? (length / 1000).toFixed(2) + ' km' : Math.round(length).toLocaleString() + ' m';
        tooltipCoord = geom.getLastCoordinate();
      }
      measureTooltipElement.innerHTML = output;
      measureTooltip.setPosition(tooltipCoord);
    });
  });
  draw.on('drawend', function () {
    measureTooltipElement.className = 'ol-tooltip ol-tooltip-static';
    measureTooltip.setOffset([0, -7]);
    ol.Observable.unByKey(listener);
    createMeasureTooltip();
  });
}

function setupDigitizeEvents(draw, type) {
  draw.on('drawend', function () {
    postToHost({
      action: 'digitizedFeature',
      type: type,
      count: vectorSource.getFeatures().length + 1
    });
  });
}

initTelemetryHandlers();
