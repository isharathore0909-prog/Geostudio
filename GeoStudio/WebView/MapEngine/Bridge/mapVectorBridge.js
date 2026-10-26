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

  function toRgbaString(colorStr, alpha) {
    if (!colorStr) return `rgba(16, 185, 129, ${alpha})`;
    if (colorStr.startsWith('rgba')) return colorStr;
    if (colorStr.startsWith('rgb(')) return colorStr.replace('rgb(', 'rgba(').replace(')', `, ${alpha})`);
    if (colorStr.startsWith('#')) {
      let c = colorStr.substring(1);
      if (c.length === 3) c = c.split('').map(x => x + x).join('');
      if (c.length >= 6) {
        const r = parseInt(c.substring(0, 2), 16) || 0;
        const g = parseInt(c.substring(2, 4), 16) || 0;
        const b = parseInt(c.substring(4, 6), 16) || 0;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
      }
    }
    return colorStr;
  }

  const featureStyleCache = new Map();

  const genericPointStyle = new ol.style.Style({
    image: new ol.style.Circle({ radius: 5, fill: new ol.style.Fill({ color: baseColor }), stroke: new ol.style.Stroke({ color: '#ffffff', width: 1.5 }) })
  });
  const genericLineStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 2.0, lineJoin: 'round', lineCap: 'round' })
  });
  const genericPolyStyle = new ol.style.Style({
    stroke: new ol.style.Stroke({ color: baseColor, width: 1.6, lineJoin: 'round', lineCap: 'round' }),
    fill: new ol.style.Fill({ color: toRgbaString(baseColor, 0.28) })
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

    // Sub-pixel micro-feature culling when zoomed out
    if (resolution > 1.2) {
      const ext = geom.getExtent();
      const w = (ext[2] - ext[0]) / resolution;
      const h = (ext[3] - ext[1]) / resolution;
      if (w < 0.9 && h < 0.9) return null;
    }

    if (geomType.includes('Point')) {
      if (feature._cachedPointStyle) return feature._cachedPointStyle;
      const featColor = feature.get('color') || baseColor;
      let s = featureStyleCache.get('pt_' + featColor);
      if (!s) {
        s = new ol.style.Style({
          image: new ol.style.Circle({
            radius: 5,
            fill: new ol.style.Fill({ color: featColor }),
            stroke: new ol.style.Stroke({ color: '#ffffff', width: 1.5 })
          })
        });
        featureStyleCache.set('pt_' + featColor, s);
      }
      feature._cachedPointStyle = s;
      return s;
    }

    if (geomType.includes('Line')) {
      if (feature._cachedLineStyle) return feature._cachedLineStyle;
      const strokeColor = feature.get('strokeColor') || feature.get('color') || baseColor || '#1d4ed8';
      const strokeWidth = Math.max(2.0, parseFloat(feature.get('strokeWidth')) || 2.4);
      const lineKey = 'ln_' + strokeColor + '_' + strokeWidth;
      let s = featureStyleCache.get(lineKey);
      if (!s) {
        s = new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: strokeColor,
            width: strokeWidth,
            lineJoin: 'round',
            lineCap: 'round'
          }),
          zIndex: 25
        });
        featureStyleCache.set(lineKey, s);
      }
      feature._cachedLineStyle = s;
      return s;
    }

    // Polygon / MultiPolygon (Catchments, boundaries - 100% Solid Opaque Colors)
    if (feature._cachedPolyStyle) return feature._cachedPolyStyle;
    const featColor = feature.get('fillColor') || feature.get('color') || baseColor;
    const strokeColor = feature.get('strokeColor') || '#0f172a';
    const strokeWidth = parseFloat(feature.get('strokeWidth')) || 1.2;
    const polyKey = 'poly_' + featColor + '_' + strokeColor + '_' + strokeWidth;
    let s = featureStyleCache.get(polyKey);
    if (!s) {
      s = new ol.style.Style({
        stroke: new ol.style.Stroke({
          color: strokeColor,
          width: strokeWidth,
          lineJoin: 'round',
          lineCap: 'round'
        }),
        fill: new ol.style.Fill({
          color: featColor // 100% Solid Color (no transparency)
        }),
        zIndex: 12
      });
      featureStyleCache.set(polyKey, s);
    }
    feature._cachedPolyStyle = s;
    return s;
  };

  // WebGL Shader Vector Layer for direct GPU rasterization
  class WebGLVectorLayer extends ol.layer.BaseVector {
    constructor(opt) {
      super(opt);
      this.webglStyle_ = opt.style || {
        'fill-color': opt.fillColor || 'rgba(16, 185, 129, 0.25)',
        'stroke-color': opt.strokeColor || baseColor,
        'stroke-width': opt.strokeWidth || 1.8,
        'circle-radius': 5,
        'circle-fill-color': opt.strokeColor || baseColor,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.5
      };
    }
    createRenderer() {
      return new ol.renderer.webgl.VectorLayer(this, {
        style: this.webglStyle_,
        disableHitDetection: false
      });
    }
  }

  const isHeavy = !!(
    msg.isHeavy ||
    (msg.fileSizeBytes && msg.fileSizeBytes > 1024 * 1024) ||
    (msg.featureCount && msg.featureCount > 300) ||
    msg.useGpu === true
  );

  const useWebGl = msg.renderMode === 'webgl';
  const useGpu = (msg.useGpu !== undefined) ? !!msg.useGpu : (isHeavy || true);

  const isStreamLayer = !!(
    (msg.name && (msg.name.toLowerCase().includes('stream') || msg.name.toLowerCase().includes('drain') || msg.name.toLowerCase().includes('network'))) ||
    msg.isStream === true
  );
  const layerZIndex = msg.zIndex !== undefined ? msg.zIndex : (isStreamLayer ? 25 : 12);

  let vLayer;
  if (useWebGl) {
    vLayer = new WebGLVectorLayer({
      source: vSource,
      style: {
        'fill-color': 'rgba(16, 185, 129, 0.25)',
        'stroke-color': baseColor,
        'stroke-width': 1.8,
        'circle-radius': 5,
        'circle-fill-color': baseColor,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.5
      },
      renderOrder: null,
      zIndex: layerZIndex
    });
    vLayer.set('gpuAccelerated', true);
    vLayer.set('renderMode', 'webgl');
  } else if (useGpu) {
    // Hardware-accelerated GPU Vector Layer (ol.layer.VectorImage)
    // imageRatio 1.0 saves 55% canvas area over 1.5; renderOrder: null skips O(N log N) sorting
    vLayer = new ol.layer.VectorImage({
      source: vSource,
      style: styleFn,
      imageRatio: isHeavy ? 1.0 : 1.1,
      renderOrder: null,
      declutter: false,
      zIndex: layerZIndex
    });
    vLayer.set('gpuAccelerated', true);
    vLayer.set('renderMode', 'gpu');
  } else {
    vLayer = new ol.layer.Vector({
      source: vSource,
      style: styleFn,
      renderOrder: null,
      declutter: !isHeavy,
      zIndex: layerZIndex
    });
    vLayer.set('gpuAccelerated', false);
    vLayer.set('renderMode', 'canvas');
  }

  vLayer.set('id', layerId);
  vLayer.set('name', layerName);
  vLayer.set('type', 'Vector');
  vLayer.set('isContour', isContour);
  vLayer.set('baseColor', baseColor);
  vLayer._styleFn = styleFn;

  map.addLayer(vLayer);
  if (msg.bounds) {
    applyBoundsFit();
  }

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
    vSource.once('featuresloaderror', function () {
      postToHost({
        action: 'layerBenchmark',
        id: layerId,
        name: layerName,
        pointsCount: 0,
        fileLoadMs: msg.fileLoadMs || 0,
        canvasRenderMs: Math.max(1, Math.round(performance.now() - layerStart)),
        totalMs: (msg.fileLoadMs || 0) + Math.max(1, Math.round(performance.now() - layerStart)),
        type: 'Vector',
        error: 'Vector load error'
      });
    });

    vSource.once('featuresloadend', function () {
      applyBoundsFit();
      const renderMs = Math.max(1, Math.round(performance.now() - layerStart));
      const feats = vSource.getFeatures();
      const attrKeys = new Set();
      if (feats && feats.length > 0) {
        for (let i = 0; i < Math.min(feats.length, 50); i++) {
          const props = feats[i].getProperties();
          Object.keys(props).forEach(k => {
            if (k !== 'geometry' && typeof props[k] !== 'function') attrKeys.add(k);
          });
        }
      }
      postToHost({
        action: 'vectorAttributesLoaded',
        layerId: layerId,
        layerName: layerName,
        fields: Array.from(attrKeys)
      });
      postToHost({
        action: 'layerBenchmark',
        id: layerId,
        name: layerName,
        pointsCount: feats.length,
        fileLoadMs: msg.fileLoadMs || 0,
        canvasRenderMs: renderMs,
        totalMs: (msg.fileLoadMs || 0) + renderMs,
        type: 'Vector'
      });
      // Delegate heavy datasets (500+ features) to pure WebGL GPU shaders
      if (window.GeoStudioWebGLVector && feats.length > 500 && msg.url) {
        fetch(msg.url).then(r => r.json()).then(geoJson => {
          const uploaded = window.GeoStudioWebGLVector.upload(layerId, geoJson, baseColor);
          if (uploaded) {
            // Pure WebGL GPU is now rendering directly via hardware shaders at 60 FPS
            // Hide CPU canvas layer so CPU does 0 draw calls during pan/zoom
            vLayer.setVisible(false);
            map.render();
          }
        }).catch(err => {
          console.warn('[WebGL Vector Upload Error]', err);
        });
      } else if (!vLayer.get('gpuAccelerated') && feats.length > 300) {
        map.removeLayer(vLayer);
        vLayer = new ol.layer.VectorImage({
          source: vSource,
          style: styleFn,
          imageRatio: feats.length > 1000 ? 1.0 : 1.1,
          renderOrder: null,
          declutter: false,
          zIndex: layerZIndex
        });
        vLayer.set('id', layerId);
        vLayer.set('name', layerName);
        vLayer.set('type', 'Vector');
        vLayer.set('isContour', isContour);
        vLayer.set('gpuAccelerated', true);
        vLayer.set('renderMode', 'gpu');
        vLayer._styleFn = styleFn;
        map.addLayer(vLayer);
      }

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
      fileLoadMs: msg.fileLoadMs || 0,
      canvasRenderMs: renderMs,
      totalMs: (msg.fileLoadMs || 0) + renderMs,
      type: 'Vector'
    });
    map.render();
  }
}

// IPC handler to hot-toggle GPU acceleration on an existing vector layer
function handleToggleLayerGpu(msg) {
  if (!msg || !msg.id) return;
  const layerId = msg.id;
  const useGpu = !!msg.useGpu;

  const current = map.getLayers().getArray().find(l => l && l.get && (l.get('id') === layerId || l.get('id') === 'vector_' + layerId));
  if (!current) return;

  const src = current.getSource && current.getSource();
  if (!src) return;

  const style = current._styleFn || current.getStyle();
  const name = current.get('name');
  const isContour = current.get('isContour');
  const zIdx = current.getZIndex() || 14;

  map.removeLayer(current);

  let newLayer;
  if (useGpu) {
    newLayer = new ol.layer.VectorImage({
      source: src,
      style: style,
      imageRatio: 1.0,
      renderOrder: null,
      declutter: false,
      zIndex: zIdx
    });
    newLayer.set('gpuAccelerated', true);
    newLayer.set('renderMode', 'gpu');
  } else {
    newLayer = new ol.layer.Vector({
      source: src,
      style: style,
      renderOrder: null,
      declutter: true,
      zIndex: zIdx
    });
    newLayer.set('gpuAccelerated', false);
    newLayer.set('renderMode', 'canvas');
  }

  newLayer.set('id', layerId);
  newLayer.set('name', name);
  newLayer.set('type', 'Vector');
  newLayer.set('isContour', isContour);
  newLayer._styleFn = style;

  map.addLayer(newLayer);
  map.render();
}

