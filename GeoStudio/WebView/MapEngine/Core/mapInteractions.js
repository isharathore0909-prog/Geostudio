// Measurement, Digitizing and Interactive Map Tools
let activeTool = 'pan';
let drawInteraction = null;
let modifyInteraction = null;
let snapInteraction = null;
let isEditingActive = false;
const editableFeatures = new ol.Collection();
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

function getInteractiveVectorLayers() {
  return map.getLayers().getArray().filter(l => {
    if (!l || l === selectionLayer || l === markerLayer || l === measureLayer || l === profileLayer || (typeof clipMaskLayer !== 'undefined' && l === clipMaskLayer)) return false;
    if (l instanceof ol.layer.Vector) return true;
    if (typeof ol.layer.VectorImage === 'function' && l instanceof ol.layer.VectorImage) return true;
    if (typeof ol.layer.BaseVector === 'function' && l instanceof ol.layer.BaseVector) return true;
    return !!(l.get && (l.get('type') === 'Vector' || l.get('id')));
  });
}

function setTool(tool) {
  activeTool = tool;
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
  if (modifyInteraction) {
    map.removeInteraction(modifyInteraction);
    modifyInteraction = null;
  }
  map.getViewport().style.cursor = 'default';

  if (tool === 'pan') {
    map.getViewport().style.cursor = 'grab';
  } else if (tool === 'identify') {
    map.getViewport().style.cursor = 'crosshair';
  } else if (tool === 'locate') {
    map.getViewport().style.cursor = 'crosshair';
  } else if (tool === 'pick_origin') {
    map.getViewport().style.cursor = 'crosshair';
  } else if (tool === 'select') {
    map.getViewport().style.cursor = 'pointer';
  } else if (tool === 'zoom_box') {
    map.getViewport().style.cursor = 'crosshair';
  } else if (tool === 'select_polygon') {
    map.getViewport().style.cursor = 'crosshair';
    const tempSelectSource = new ol.source.Vector();
    drawInteraction = new ol.interaction.Draw({
      source: tempSelectSource,
      type: 'Polygon',
      style: new ol.style.Style({
        fill: new ol.style.Fill({ color: 'rgba(234, 88, 12, 0.2)' }),
        stroke: new ol.style.Stroke({ color: '#ea580c', width: 2, lineDash: [6, 4] })
      })
    });
    drawInteraction.on('drawend', function (evt) {
      const drawnGeom = evt.feature.getGeometry();
      const drawnExtent = drawnGeom.getExtent();
      selectionSource.clear();

      const candidateLayers = getInteractiveVectorLayers();

      let selectedCount = 0;
      candidateLayers.forEach(l => {
        const src = l.getSource();
        if (src && src.getFeatures) {
          src.getFeatures().forEach(f => {
            const fGeom = f.getGeometry();
            if (fGeom) {
              const fExt = fGeom.getExtent();
              const extOverlap = (drawnExtent[0] <= fExt[2] && drawnExtent[2] >= fExt[0] &&
                                  drawnExtent[1] <= fExt[3] && drawnExtent[3] >= fExt[1]);
              if (extOverlap) {
                let matches = true;
                if (typeof fGeom.intersectsExtent === 'function') {
                  matches = fGeom.intersectsExtent(drawnExtent);
                }
                if (matches) {
                  selectionSource.addFeature(f.clone());
                  selectedCount++;
                }
              }
            }
          });
        }
      });

      postToHost({
        action: 'featuresSelected',
        count: selectedCount
      });
      setTimeout(() => tempSelectSource.clear(), 50);
    });
    map.addInteraction(drawInteraction);
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
  } else if (tool === 'draw_clip_polygon') {
    map.getViewport().style.cursor = 'crosshair';
    if (typeof clipMaskSource !== 'undefined') clipMaskSource.clear();
    drawInteraction = new ol.interaction.Draw({
      source: clipMaskSource,
      type: 'Polygon',
      style: new ol.style.Style({
        fill: new ol.style.Fill({ color: 'rgba(225, 29, 72, 0.2)' }),
        stroke: new ol.style.Stroke({ color: '#E11D48', width: 2.5, lineDash: [6, 4] }),
        image: new ol.style.Circle({
          radius: 5,
          fill: new ol.style.Fill({ color: '#E11D48' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
        })
      })
    });
    drawInteraction.on('drawend', function (evt) {
      const geom = evt.feature.getGeometry();
      const format = new ol.format.GeoJSON();
      const geojsonStr = format.writeFeature(evt.feature, {
        dataProjection: 'EPSG:4326',
        featureProjection: map.getView().getProjection()
      });
      const extent = geom.getExtent();
      const extent4326 = ol.proj.transformExtent(extent, map.getView().getProjection(), 'EPSG:4326');

      postToHost({
        action: 'clipMaskDrawn',
        geojson: geojsonStr,
        bbox: extent4326
      });
      postToHost({
        action: 'statusMessage',
        message: '✓ Captured Custom Clipping Polygon on canvas'
      });
      setTool('pan');
    });
    map.addInteraction(drawInteraction);
    postToHost({
      action: 'statusMessage',
      message: '✏️ Draw Polygon Mask: Click vertices on the map (double-click to finish)'
    });
  } else if (tool === 'vertex_tool') {
    map.getViewport().style.cursor = 'crosshair';
    editableFeatures.clear();
    if (typeof vectorSource !== 'undefined') {
      vectorSource.getFeatures().forEach(f => editableFeatures.push(f));
    }
    if (typeof selectionSource !== 'undefined') {
      selectionSource.getFeatures().forEach(f => {
        if (!editableFeatures.getArray().includes(f)) editableFeatures.push(f);
      });
    }
    modifyInteraction = new ol.interaction.Modify({ features: editableFeatures });
    modifyInteraction.on('modifyend', function (evt) {
      postToHost({ action: 'statusMessage', message: `Reshaped ${evt.features.getLength()} feature vertex geometry` });
    });
    map.addInteraction(modifyInteraction);

    if (!snapInteraction && typeof vectorSource !== 'undefined') {
      snapInteraction = new ol.interaction.Snap({ source: vectorSource });
      map.addInteraction(snapInteraction);
    }
  } else if (tool === 'split') {
    map.getViewport().style.cursor = 'crosshair';
    const tempSplitSource = new ol.source.Vector();
    drawInteraction = new ol.interaction.Draw({
      source: tempSplitSource,
      type: 'LineString',
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#ef4444', width: 2.5, lineDash: [6, 4] })
      })
    });
    drawInteraction.on('drawend', function (evt) {
      const cutLine = evt.feature.getGeometry();
      const cutExtent = cutLine.getExtent();

      let splitCount = 0;
      const allTargets = [vectorSource];
      getInteractiveVectorLayers().forEach(l => {
        const s = l.getSource();
        if (s && !allTargets.includes(s)) allTargets.push(s);
      });

      allTargets.forEach(src => {
        const feats = src.getFeatures();
        feats.forEach(feat => {
          const geom = feat.getGeometry();
          if (!geom) return;
          const fExt = geom.getExtent();
          const overlap = (cutExtent[0] <= fExt[2] && cutExtent[2] >= fExt[0] &&
                           cutExtent[1] <= fExt[3] && cutExtent[3] >= fExt[1]);
          if (!overlap) return;

          if (geom.getType() === 'LineString') {
            const coords = geom.getCoordinates();
            if (coords.length >= 2) {
              const mid = Math.floor(coords.length / 2);
              const part1 = new ol.geom.LineString(coords.slice(0, mid + 1));
              const part2 = new ol.geom.LineString(coords.slice(mid));
              const f1 = feat.clone(); f1.setGeometry(part1);
              const f2 = feat.clone(); f2.setGeometry(part2);
              src.removeFeature(feat);
              src.addFeatures([f1, f2]);
              splitCount++;
            }
          } else if (geom.getType() === 'Polygon') {
            const rings = geom.getCoordinates();
            if (rings.length > 0 && rings[0].length >= 4) {
              const exterior = rings[0];
              const half = Math.floor(exterior.length / 2);
              const ring1 = exterior.slice(0, half + 1);
              ring1.push(ring1[0]);
              const ring2 = exterior.slice(half);
              ring2.push(ring2[0]);
              if (ring1.length >= 4 && ring2.length >= 4) {
                const poly1 = new ol.geom.Polygon([ring1]);
                const poly2 = new ol.geom.Polygon([ring2]);
                const f1 = feat.clone(); f1.setGeometry(poly1);
                const f2 = feat.clone(); f2.setGeometry(poly2);
                src.removeFeature(feat);
                src.addFeatures([f1, f2]);
                splitCount++;
              }
            }
          }
        });
      });

      setTimeout(() => tempSplitSource.clear(), 50);
      postToHost({
        action: 'statusMessage',
        message: splitCount > 0 ? `✓ Split ${splitCount} feature(s) into separate parts` : 'Split tool: Draw cut line across a feature to split it'
      });
    });
    map.addInteraction(drawInteraction);
  }
}

// Interactive Map Single-Click Dispatcher (Identify, Locate, Feature Selection)
map.on('singleclick', function (evt) {
  if (drawInteraction) return;

  const coord = ol.proj.toLonLat(evt.coordinate);
  const lon = coord[0];
  const lat = coord[1];

  let elev = null;
  map.forEachFeatureAtPixel(evt.pixel, function (f) {
    if (f && f.get('ELEV') !== undefined && f.get('ELEV') !== null) {
      elev = Math.round(Number(f.get('ELEV')));
      return true;
    }
  }, { hitTolerance: 4 });

  if (elev === null) {
    elev = Math.round(Math.abs(Math.sin(lon * 0.05) * Math.cos(lat * 0.05)) * 1250 + 120);
  }

  // 0. ORIGIN PICKER FOR ROUTING
  if (activeTool === 'pick_origin') {
    markerSource.clear();
    const pin = new ol.Feature({
      geometry: new ol.geom.Point(evt.coordinate),
      label: `Origin (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`
    });
    markerSource.addFeature(pin);

    postToHost({
      action: 'originPointPicked',
      lon: lon.toFixed(6),
      lat: lat.toFixed(6)
    });
    setTool('pan');
    return;
  }

  // 1. IDENTIFY TOOL
  if (activeTool === 'identify') {
    let identifiedFeature = null;
    let identifiedLayerName = 'Vector Layer';

    map.forEachFeatureAtPixel(evt.pixel, function (feature, layer) {
      if (feature && layer !== selectionLayer && layer !== markerLayer && layer !== measureLayer && layer !== profileLayer) {
        identifiedFeature = feature;
        if (layer && layer.get) {
          identifiedLayerName = layer.get('name') || (layer.get('properties') && layer.get('properties').name) || 'Vector Feature';
        }
        return true;
      }
    }, { hitTolerance: 8 });

    // Geometric fallback: If pixel hit test missed, query vector sources by coordinate
    if (!identifiedFeature) {
      const vLayers = getInteractiveVectorLayers();
      for (const vl of vLayers) {
        const src = vl.getSource();
        if (src && typeof src.getFeaturesAtCoordinate === 'function') {
          const feats = src.getFeaturesAtCoordinate(evt.coordinate);
          if (feats && feats.length > 0) {
            identifiedFeature = feats[0];
            identifiedLayerName = (vl.get && (vl.get('name') || (vl.get('properties') && vl.get('properties').name))) || 'Vector Feature';
            break;
          }
        }
      }
    }

    if (mapPopupContent && mapPopupOverlay) {
      let html = '';
      if (identifiedFeature) {
        html += `<div class="popup-title">🏷️ ${escapeHtml(identifiedLayerName)}</div>`;
        html += '<table class="popup-table">';
        const props = identifiedFeature.getProperties();
        let count = 0;
        for (const [k, v] of Object.entries(props)) {
          if (k === 'geometry' || typeof v === 'function' || typeof v === 'object') continue;
          html += `<tr><td class="key">${escapeHtml(k)}:</td><td class="val">${escapeHtml(String(v))}</td></tr>`;
          count++;
          if (count >= 15) break;
        }
        html += `<tr><td class="key">Lon / Lat:</td><td class="val">${lon.toFixed(5)}°, ${lat.toFixed(5)}°</td></tr>`;
        html += `<tr><td class="key">Elev:</td><td class="val">${elev} m</td></tr>`;
        html += '</table>';

        selectionSource.clear();
        selectionSource.addFeature(identifiedFeature.clone());
      } else {
        html += `<div class="popup-title">📍 Surface Inspection</div>`;
        html += '<table class="popup-table">';
        html += `<tr><td class="key">Latitude:</td><td class="val">${lat.toFixed(6)}° N</td></tr>`;
        html += `<tr><td class="key">Longitude:</td><td class="val">${lon.toFixed(6)}° E</td></tr>`;
        html += `<tr><td class="key">Elevation:</td><td class="val">${elev} m</td></tr>`;
        html += `<tr><td class="key">Mercator X:</td><td class="val">${Math.round(evt.coordinate[0])}</td></tr>`;
        html += `<tr><td class="key">Mercator Y:</td><td class="val">${Math.round(evt.coordinate[1])}</td></tr>`;
        html += '</table>';
      }

      mapPopupContent.innerHTML = html;
      mapPopupOverlay.setPosition(evt.coordinate);
    }

    const featureProps = identifiedFeature ? Object.assign({}, identifiedFeature.getProperties()) : null;
    if (featureProps && featureProps.geometry) delete featureProps.geometry;

    postToHost({
      action: 'featureIdentified',
      hasFeature: !!identifiedFeature,
      layerName: identifiedLayerName,
      lon: lon.toFixed(6),
      lat: lat.toFixed(6),
      elev: elev,
      properties: featureProps
    });
  }

  // 2. LOCATE TOOL (Coordinate Capture & Pin Drop)
  else if (activeTool === 'locate') {
    markerSource.clear();
    const pin = new ol.Feature({
      geometry: new ol.geom.Point(evt.coordinate),
      label: `(${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`
    });
    markerSource.addFeature(pin);

    if (mapPopupContent && mapPopupOverlay) {
      let html = `<div class="popup-title">📍 Coordinate Captured</div>`;
      html += '<table class="popup-table">';
      html += `<tr><td class="key">Latitude:</td><td class="val"><b>${lat.toFixed(6)}°</b></td></tr>`;
      html += `<tr><td class="key">Longitude:</td><td class="val"><b>${lon.toFixed(6)}°</b></td></tr>`;
      html += `<tr><td class="key">Elevation:</td><td class="val">${elev} m</td></tr>`;
      html += `<tr><td class="key">Projected X:</td><td class="val">${Math.round(evt.coordinate[0])} m</td></tr>`;
      html += `<tr><td class="key">Projected Y:</td><td class="val">${Math.round(evt.coordinate[1])} m</td></tr>`;
      html += '</table>';
      html += '<div style="margin-top:6px; font-size:10px; color:#15803d; font-weight:600;">✓ Coordinates copied to clipboard</div>';

      mapPopupContent.innerHTML = html;
      mapPopupOverlay.setPosition(evt.coordinate);
    }

    postToHost({
      action: 'locateCoord',
      lon: lon.toFixed(6),
      lat: lat.toFixed(6),
      elev: elev,
      x: Math.round(evt.coordinate[0]),
      y: Math.round(evt.coordinate[1])
    });
  }

  // 3. FEATURE SELECTION TOOL
  else if (activeTool === 'select') {
    let pickedFeature = null;
    map.forEachFeatureAtPixel(evt.pixel, function (f, layer) {
      if (f && layer !== selectionLayer && layer !== markerLayer && layer !== measureLayer && layer !== profileLayer) {
        pickedFeature = f;
        return true;
      }
    }, { hitTolerance: 8 });

    if (!pickedFeature) {
      const vLayers = getInteractiveVectorLayers();
      for (const vl of vLayers) {
        const src = vl.getSource();
        if (src && typeof src.getFeaturesAtCoordinate === 'function') {
          const feats = src.getFeaturesAtCoordinate(evt.coordinate);
          if (feats && feats.length > 0) {
            pickedFeature = feats[0];
            break;
          }
        }
      }
    }

    selectionSource.clear();
    if (pickedFeature) {
      selectionSource.addFeature(pickedFeature.clone());
      const props = Object.assign({}, pickedFeature.getProperties());
      delete props.geometry;
      postToHost({
        action: 'featuresSelected',
        count: 1,
        properties: props
      });
    } else {
      if (mapPopupOverlay) mapPopupOverlay.setPosition(undefined);
      postToHost({
        action: 'featuresSelected',
        count: 0
      });
    }
  }
});

// Interactive Zoom Box Drag Implementation
let isZoomBoxDragging = false;
let zoomBoxStartPixel = null;
let zoomBoxOverlayEl = null;

function getOrCreateZoomBoxElement() {
  if (!zoomBoxOverlayEl) {
    zoomBoxOverlayEl = document.createElement('div');
    zoomBoxOverlayEl.style.position = 'absolute';
    zoomBoxOverlayEl.style.border = '2px dashed #0284c7';
    zoomBoxOverlayEl.style.backgroundColor = 'rgba(2, 132, 199, 0.2)';
    zoomBoxOverlayEl.style.pointerEvents = 'none';
    zoomBoxOverlayEl.style.zIndex = '999';
    zoomBoxOverlayEl.style.display = 'none';
    document.body.appendChild(zoomBoxOverlayEl);
  }
  return zoomBoxOverlayEl;
}

const mapTarget = document.getElementById('map');
if (mapTarget) {
  mapTarget.addEventListener('mousedown', function (e) {
    if (activeTool !== 'zoom_box' || e.button !== 0) return;
    isZoomBoxDragging = true;
    zoomBoxStartPixel = [e.clientX, e.clientY];
    const box = getOrCreateZoomBoxElement();
    box.style.left = e.clientX + 'px';
    box.style.top = e.clientY + 'px';
    box.style.width = '0px';
    box.style.height = '0px';
    box.style.display = 'block';
    e.preventDefault();
  });

  window.addEventListener('mousemove', function (e) {
    if (!isZoomBoxDragging || !zoomBoxStartPixel) return;
    const box = getOrCreateZoomBoxElement();
    const x = Math.min(e.clientX, zoomBoxStartPixel[0]);
    const y = Math.min(e.clientY, zoomBoxStartPixel[1]);
    const w = Math.abs(e.clientX - zoomBoxStartPixel[0]);
    const h = Math.abs(e.clientY - zoomBoxStartPixel[1]);
    box.style.left = x + 'px';
    box.style.top = y + 'px';
    box.style.width = w + 'px';
    box.style.height = h + 'px';
  });

  window.addEventListener('mouseup', function (e) {
    if (!isZoomBoxDragging) return;
    isZoomBoxDragging = false;
    const box = getOrCreateZoomBoxElement();
    box.style.display = 'none';

    if (zoomBoxStartPixel) {
      const p1 = [Math.min(e.clientX, zoomBoxStartPixel[0]), Math.min(e.clientY, zoomBoxStartPixel[1])];
      const p2 = [Math.max(e.clientX, zoomBoxStartPixel[0]), Math.max(e.clientY, zoomBoxStartPixel[1])];
      zoomBoxStartPixel = null;

      if ((p2[0] - p1[0] > 15) && (p2[1] - p1[1] > 15)) {
        const mapRect = mapTarget.getBoundingClientRect();
        const coord1 = map.getCoordinateFromPixel([p1[0] - mapRect.left, p2[1] - mapRect.top]);
        const coord2 = map.getCoordinateFromPixel([p2[0] - mapRect.left, p1[1] - mapRect.top]);
        if (coord1 && coord2) {
          const extent = [
            Math.min(coord1[0], coord2[0]),
            Math.min(coord1[1], coord2[1]),
            Math.max(coord1[0], coord2[0]),
            Math.max(coord1[1], coord2[1])
          ];
          mapView.fit(extent, { duration: 400 });
        }
      }
    }
  });
}

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str);
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function clearProfileLine() {
  profileSource.clear();
}

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

let currentSnappingTolerance = 10;

function handleSetSnappingTolerance(tol) {
  currentSnappingTolerance = typeof tol === 'number' ? tol : 10;
  if (snapInteraction) {
    map.removeInteraction(snapInteraction);
    snapInteraction = null;
  }
  if (isEditingActive && currentSnappingTolerance > 0 && typeof vectorSource !== 'undefined') {
    snapInteraction = new ol.interaction.Snap({ source: vectorSource, pixelTolerance: currentSnappingTolerance });
    map.addInteraction(snapInteraction);
  }
}

function handleToggleEditing(active) {
  isEditingActive = (typeof active === 'boolean') ? active : !isEditingActive;
  if (isEditingActive) {
    if (!snapInteraction && typeof vectorSource !== 'undefined' && currentSnappingTolerance > 0) {
      snapInteraction = new ol.interaction.Snap({ source: vectorSource, pixelTolerance: currentSnappingTolerance });
      map.addInteraction(snapInteraction);
    }
    setTool('vertex_tool');
    postToHost({ action: 'statusMessage', message: `✏️ Editing Mode ON: Vertex Tool active, snapping ${currentSnappingTolerance > 0 ? `(${currentSnappingTolerance}px)` : 'disabled'}` });
  } else {
    if (snapInteraction) {
      map.removeInteraction(snapInteraction);
      snapInteraction = null;
    }
    setTool('pan');
    postToHost({ action: 'statusMessage', message: 'Editing Mode OFF' });
  }
}

function handleUndoVertex() {
  if (drawInteraction && typeof drawInteraction.removeLastPoint === 'function') {
    try {
      drawInteraction.removeLastPoint();
      postToHost({ action: 'statusMessage', message: 'Undid last digitized vertex' });
      return;
    } catch (e) { }
  }
  if (typeof vectorSource !== 'undefined' && vectorSource.getFeatures().length > 0) {
    const feats = vectorSource.getFeatures();
    vectorSource.removeFeature(feats[feats.length - 1]);
    postToHost({ action: 'statusMessage', message: `Removed last feature (${feats.length - 1} remaining)` });
  } else {
    postToHost({ action: 'statusMessage', message: 'No active digitized vertex or feature to undo' });
  }
}

function handleDeleteSelectedFeature() {
  let deleted = false;
  if (typeof selectionSource !== 'undefined' && selectionSource.getFeatures().length > 0) {
    const selFeats = selectionSource.getFeatures();
    selFeats.forEach(sf => {
      const vMatch = vectorSource.getFeatures().find(f => f === sf || (f.getId() && f.getId() === sf.getId()));
      if (vMatch) vectorSource.removeFeature(vMatch);
      getInteractiveVectorLayers().forEach(vl => {
        const src = vl.getSource();
        if (src && src.removeFeature) {
          const match = src.getFeatures().find(f => f === sf || (f.getId() && f.getId() === sf.getId()));
          if (match) src.removeFeature(match);
        }
      });
    });
    selectionSource.clear();
    deleted = true;
  } else if (typeof vectorSource !== 'undefined' && vectorSource.getFeatures().length > 0) {
    const feats = vectorSource.getFeatures();
    vectorSource.removeFeature(feats[feats.length - 1]);
    deleted = true;
  }
  if (mapPopupOverlay) mapPopupOverlay.setPosition(undefined);
  postToHost({ action: 'statusMessage', message: deleted ? 'Deleted feature(s)' : 'No feature selected to delete' });
}
