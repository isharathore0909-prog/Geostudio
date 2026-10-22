// Base Map Sources & Map Layers Definitions
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
