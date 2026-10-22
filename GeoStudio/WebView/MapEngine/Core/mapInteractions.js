// Measurement, Digitizing and Interactive Map Tools
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
