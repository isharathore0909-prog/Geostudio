// IPC Bridge Handlers for Vector Datasets and Contour Styling
function handleAddVectorLayer(msg) {
  if (!msg.id) return;
  const layerStart = performance.now();
  const layerId = msg.id;
  const layerName = msg.name || 'Vector Dataset';
  const isContour = !!msg.isContour;
  const baseColor = msg.color || (isContour ? '#D97706' : '#10B981');

  map.getLayers().getArray().filter(l => l.get('id') === layerId || l.get('id') === 'vector_' + layerId).forEach(l => map.removeLayer(l));

  const vSource = new ol.source.Vector({
    url: msg.url,
    format: new ol.format.GeoJSON()
  });

  const indexStroke = new ol.style.Stroke({ color: '#78350F', width: 2.4, lineJoin: 'round', lineCap: 'round' });
  const intermediateStroke = new ol.style.Stroke({ color: baseColor, width: 1.2, lineJoin: 'round', lineCap: 'round' });

  const indexBaseStyle = new ol.style.Style({ stroke: indexStroke });
  const intermediateStyle = new ol.style.Style({ stroke: intermediateStroke });

  const genericPointStyle = new ol.style.Style({
    image: new ol.style.Circle({ radius: 5, fill: new ol.style.Fill({ color: baseColor }), stroke: new ol.style.Stroke({ color: '#ffffff', width: 1.5 }) })
  });
  const genericLineStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 2.0, lineJoin: 'round', lineCap: 'round' })
  });
  const genericPolyStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 2.0, lineJoin: 'round', lineCap: 'round' }),
    fill: new ol.style.Fill({ color: 'rgba(16, 185, 129, 0.25)' })
  });

  const labelCache = new Map();
  const rawInterval = parseFloat(msg.interval) || 10;
  const indexStep = rawInterval <= 1 ? 5 : (rawInterval <= 2 ? 10 : (rawInterval <= 5 ? 25 : (rawInterval <= 10 ? 50 : rawInterval * 5)));

  const styleFn = function (feature, resolution) {
    const geom = feature.getGeometry();
    if (!geom) return null;
    const geomType = geom.getType();

    if (isContour || feature.get('ELEV') !== undefined) {
      const elev = feature.get('ELEV');
      if (elev === undefined || elev === null) return intermediateStyle;

      const elevNum = Math.round(Number(elev) * 10) / 10;
      const isIndex = (Math.abs(elevNum % indexStep) < 0.05) || (Math.abs(elevNum % 5) < 0.05);

      const lineLen = geom.getLength ? geom.getLength() : 0;
      const screenLen = resolution > 0 ? (lineLen / resolution) : 0;

      const showLabel = (isIndex && screenLen > 70 && resolution < 50) || (!isIndex && screenLen > 180 && resolution < 4);

      if (showLabel) {
        const cacheKey = (isIndex ? 'idx_' : 'int_') + elevNum;
        let cached = labelCache.get(cacheKey);
        if (!cached) {
          cached = new ol.style.Style({
            stroke: isIndex ? indexStroke : intermediateStroke,
            text: new ol.style.Text({
              text: elevNum + ' m',
              font: isIndex ? 'bold 11px Inter, -apple-system, sans-serif' : '10px Inter, -apple-system, sans-serif',
              fill: new ol.style.Fill({ color: isIndex ? '#451a03' : '#7c2d12' }),
              stroke: new ol.style.Stroke({ color: '#ffffff', width: 2.5 }),
              placement: 'line',
              repeat: 1000,
              overflow: false,
              maxAngle: Math.PI / 4
            })
          });
          labelCache.set(cacheKey, cached);
        }
        return cached;
      }

      return isIndex ? indexBaseStyle : intermediateStyle;
    }

    if (geomType.includes('Point')) return genericPointStyle;
    if (geomType.includes('Line')) return genericLineStyle;
    return genericPolyStyle;
  };

  const LayerClass = (typeof ol.layer.VectorImage === 'function') ? ol.layer.VectorImage : ol.layer.Vector;
  const vLayer = new LayerClass({
    properties: {
      id: layerId,
      name: layerName,
      type: 'Vector',
      isContour: isContour
    },
    source: vSource,
    style: styleFn,
    declutter: true,
    imageRatio: 1.5,
    zIndex: 14
  });

  map.addLayer(vLayer);

  function applyBoundsFit() {
    if (msg.bounds) {
      const minX = Math.min(msg.bounds[0], msg.bounds[2]);
      const maxX = Math.max(msg.bounds[0], msg.bounds[2]);
      const minY = Math.min(msg.bounds[1], msg.bounds[3]);
      const maxY = Math.max(msg.bounds[1], msg.bounds[3]);
      if (Math.abs(minX) <= 180 && Math.abs(maxX) <= 180 && Math.abs(minY) <= 90 && Math.abs(maxY) <= 90) {
        const p1 = ol.proj.fromLonLat([minX, minY]);
        const p2 = ol.proj.fromLonLat([maxX, maxY]);
        mapView.fit([Math.min(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[0], p2[0]), Math.max(p1[1], p2[1])], { padding: [50, 50, 50, 50], duration: 500 });
        return;
      }
    }
    const ext = vSource.getExtent();
    if (ext && !ol.extent.isEmpty(ext) && isFinite(ext[0])) {
      mapView.fit(ext, { padding: [50, 50, 50, 50], duration: 500 });
    }
  }

  if (msg.url) {
    vSource.once('featuresloadend', function () {
      applyBoundsFit();
      const renderMs = Math.max(1, Math.round(performance.now() - layerStart));
      postToHost({
        action: 'layerBenchmark',
        id: layerId,
        name: layerName,
        pointsCount: vSource.getFeatures().length,
        canvasRenderMs: renderMs,
        totalMs: renderMs,
        type: 'Vector'
      });
      map.render();
    });
  } else {
    applyBoundsFit();
    const renderMs = Math.max(1, Math.round(performance.now() - layerStart));
    postToHost({
      action: 'layerBenchmark',
      id: layerId,
      name: layerName,
      pointsCount: vSource.getFeatures().length,
      canvasRenderMs: renderMs,
      totalMs: renderMs,
      type: 'Vector'
    });
    map.render();
  }
}
