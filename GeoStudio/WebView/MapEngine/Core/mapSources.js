// Base Map Sources & Map Layers Definitions (Removed)
const cartoSource = null;
const cartoLayer = null;
const esriSatelliteSource = null;
const satelliteLayer = null;

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
  style: function (feature) {
    const styles = [
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#ffffff', width: 6 })
      }),
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#0284c7', width: 3.5, lineDash: [8, 4] })
      })
    ];
    if (feature && feature.getGeometry) {
      const geom = feature.getGeometry();
      if (geom && typeof geom.getCoordinates === 'function') {
        const coords = geom.getCoordinates();
        if (Array.isArray(coords) && coords.length >= 2) {
          styles.push(new ol.style.Style({
            geometry: new ol.geom.Point(coords[0]),
            image: new ol.style.Circle({
              radius: 7,
              fill: new ol.style.Fill({ color: '#0284c7' }),
              stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
            }),
            text: new ol.style.Text({
              text: 'A',
              font: 'bold 11px sans-serif',
              fill: new ol.style.Fill({ color: '#ffffff' }),
              offsetY: -14
            })
          }));
          styles.push(new ol.style.Style({
            geometry: new ol.geom.Point(coords[coords.length - 1]),
            image: new ol.style.Circle({
              radius: 7,
              fill: new ol.style.Fill({ color: '#0284c7' }),
              stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
            }),
            text: new ol.style.Text({
              text: 'B',
              font: 'bold 11px sans-serif',
              fill: new ol.style.Fill({ color: '#ffffff' }),
              offsetY: -14
            })
          }));
        }
      }
    }
    return styles;
  },
  zIndex: 20
});

const clipMaskSource = new ol.source.Vector({ wrapX: false });
const clipMaskLayer = new ol.layer.Vector({
  properties: { id: 'clip_mask_layer', name: 'Clipping Mask' },
  source: clipMaskSource,
  style: new ol.style.Style({
    fill: new ol.style.Fill({ color: 'rgba(225, 29, 72, 0.2)' }),
    stroke: new ol.style.Stroke({ color: '#E11D48', width: 2.5, lineDash: [6, 4] })
  }),
  zIndex: 35
});

// Interactive Feature Selection Source & Layer
const selectionSource = new ol.source.Vector({ wrapX: false });
const selectionLayer = new ol.layer.Vector({
  properties: { id: 'selection_layer', name: 'Selection' },
  source: selectionSource,
  style: function () {
    return [
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#ffffff', width: 5 }),
        fill: new ol.style.Fill({ color: 'rgba(249, 115, 22, 0.35)' })
      }),
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#ea580c', width: 2.5 }),
        image: new ol.style.Circle({
          radius: 7,
          fill: new ol.style.Fill({ color: '#ea580c' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 2.5 })
        })
      })
    ];
  },
  zIndex: 35
});

// Interactive Pin & Coordinate Markers Layer
const markerSource = new ol.source.Vector({ wrapX: false });
const markerLayer = new ol.layer.Vector({
  properties: { id: 'marker_layer', name: 'Map Markers' },
  source: markerSource,
  style: function (feat) {
    const text = feat.get('label') || '';
    return [
      new ol.style.Style({
        image: new ol.style.Circle({
          radius: 8,
          fill: new ol.style.Fill({ color: '#dc2626' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 2.5 })
        }),
        text: text ? new ol.style.Text({
          text: text,
          offsetY: -18,
          font: 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fill: new ol.style.Fill({ color: '#0f172a' }),
          stroke: new ol.style.Stroke({ color: '#ffffff', width: 3 }),
          backgroundFill: new ol.style.Fill({ color: 'rgba(255, 255, 255, 0.95)' }),
          padding: [3, 6, 2, 6]
        }) : null
      })
    ];
  },
  zIndex: 40
});
