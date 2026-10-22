// LiDAR Classification & Analytical Legends Management
const LIDAR_LEGENDS = {
  classification: {
    icon: '🏷️', title: 'LiDAR: Classification', type: 'swatches', subtext: 'ASPRS Standard Classes',
    items: [
      { color: '#94A3B8', label: '0: Unclassified' }, { color: '#D2A373', label: '2: Ground' },
      { color: '#84F0AB', label: '3: Low Veg' }, { color: '#22C55E', label: '4: Med Veg' },
      { color: '#15803D', label: '5: High Veg' }, { color: '#EF4444', label: '6: Building' },
      { color: '#0284C7', label: '9: Water' }, { color: '#F97316', label: '14: Conductor' }
    ]
  },
  elevation: {
    icon: '🏔️', title: 'LiDAR: Elevation (Z)', type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4662d8, #28bbec, #a2fc3c, #fb8022, #7a0403)',
    minLabel: () => `${(typeof pcMinZ === 'number' && !isNaN(pcMinZ)) ? pcMinZ.toFixed(1) : 0}m`,
    midLabel: () => `${(typeof pcMinZ === 'number' && typeof pcMaxZ === 'number' && !isNaN(pcMinZ) && !isNaN(pcMaxZ)) ? ((pcMinZ + pcMaxZ) / 2).toFixed(1) : 'Mid'}m`,
    maxLabel: () => `${(typeof pcMaxZ === 'number' && !isNaN(pcMaxZ)) ? pcMaxZ.toFixed(1) : 100}m`,
    subtext: 'Continuous Turbo Spectrum'
  },
  rgb_elev: {
    icon: '🏔️', title: 'RGB / Elevation Hybrid', type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4582f4, #29efa2, #f2ca3a, #e23812, #7a0403)',
    minLabel: () => `${(typeof pcMinZ === 'number' && !isNaN(pcMinZ)) ? pcMinZ.toFixed(1) : 0}m`,
    midLabel: () => 'Ortho RGB',
    maxLabel: () => `${(typeof pcMaxZ === 'number' && !isNaN(pcMaxZ)) ? pcMaxZ.toFixed(1) : 100}m`,
    subtext: 'True Color Photo + Elevation'
  },
  intensity: {
    icon: '💡', title: 'LiDAR: Intensity', type: 'ramp',
    gradient: 'linear-gradient(to right, #000000, #555555, #aaaaaa, #ffffff)',
    minLabel: '0 (Low Return)', midLabel: '128', maxLabel: '255 (High Return)',
    subtext: 'NIR Surface Reflectance'
  },
  return_num: {
    icon: '🔄', title: 'Return Number', type: 'swatches', subtext: 'Canopy Pulse Penetration',
    items: [
      { color: '#10B981', label: '1st Return (Canopy Top)' },
      { color: '#3B82F6', label: '2nd Return (Mid Branch)' },
      { color: '#F59E0B', label: '3rd Return (Understory)' },
      { color: '#EF4444', label: '4th Return (Deep)' },
      { color: '#8B5CF6', label: '5+ Return (Ground)' }
    ]
  },
  hag: {
    icon: '📏', title: 'Height Above Ground (HAG)', type: 'ramp',
    gradient: 'linear-gradient(to right, #30123b, #4582f4, #29efa2, #f2ca3a, #e23812)',
    minLabel: '0.0 m (Ground)', midLabel: '15.0 m', maxLabel: '35.0+ m (Canopy)',
    subtext: 'Normalized Height Above Earth'
  },
  scan_angle: {
    icon: '📐', title: 'Scan Angle', type: 'ramp',
    gradient: 'linear-gradient(to right, #9e0142, #d53e4f, #f46d43, #fdae61, #fee08b, #ffffbf, #e6f598, #abdda4, #66c2a5, #3288bd, #5e4fa2)',
    minLabel: '-35° (Left)', midLabel: '0° (Nadir)', maxLabel: '+35° (Right)',
    subtext: 'Sensor Off-Nadir Angle'
  },
  point_source_id: {
    icon: '✈️', title: 'Point Source ID', type: 'swatches', subtext: 'Flight Strip Swaths',
    items: [
      { color: '#3B82F6', label: 'Flight Strip A' }, { color: '#10B981', label: 'Flight Strip B' },
      { color: '#F59E0B', label: 'Flight Strip C' }, { color: '#EC4899', label: 'Flight Strip D' },
      { color: '#8B5CF6', label: 'Flight Strip E' }, { color: '#06B6D4', label: 'Flight Strip F' }
    ]
  },
  source_layer: {
    icon: '🗂️', title: 'Source Layer / Tile', type: 'swatches', subtext: 'Source LAS File / Tile ID',
    items: [
      { color: '#6366F1', label: 'LAS Tile 1' }, { color: '#EC4899', label: 'LAS Tile 2' },
      { color: '#14B8A6', label: 'LAS Tile 3' }, { color: '#F97316', label: 'LAS Tile 4' }
    ]
  },
  segment: {
    icon: '🧩', title: 'Segment / Cluster', type: 'swatches', subtext: 'Planar & Structure Clusters',
    items: [
      { color: '#EF4444', label: 'Cluster 1' }, { color: '#F59E0B', label: 'Cluster 2' },
      { color: '#10B981', label: 'Cluster 3' }, { color: '#3B82F6', label: 'Cluster 4' },
      { color: '#8B5CF6', label: 'Cluster 5' }, { color: '#06B6D4', label: 'Cluster 6' }
    ]
  },
  point_index: {
    icon: '⏱️', title: 'Point Index / Time', type: 'ramp',
    gradient: 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)',
    minLabel: 'Start of Survey', midLabel: 'Mid', maxLabel: 'End of Survey',
    subtext: 'GPS Time Chronological Order'
  },
  cir: {
    icon: '🌿', title: 'CIR (Color Infrared)', type: 'swatches', subtext: 'False-Color Infrared Composite',
    items: [
      { color: '#EF4444', label: 'Vegetation (NIR High)' }, { color: '#94A3B8', label: 'Bare Soil / Sand' },
      { color: '#38BDF8', label: 'Pavement / Concrete' }, { color: '#0F172A', label: 'Water & Shadow' }
    ]
  },
  ndvi: {
    icon: '🌱', title: 'NDVI (Vegetation Index)', type: 'ramp',
    gradient: 'linear-gradient(to right, #dc2626, #f59e0b, #eab308, #84cc16, #22c55e, #15803d)',
    minLabel: '-1.0 (Non-Veg)', midLabel: '0.0 (Soil)', maxLabel: '+1.0 (Dense Foliage)',
    subtext: 'Chlorophyll Density & Vigour'
  },
  ndwi: {
    icon: '💧', title: 'NDWI (Water Index)', type: 'ramp',
    gradient: 'linear-gradient(to right, #f1f5f9, #bae6fd, #38bdf8, #0284c7, #0369a1)',
    minLabel: 'Dry Land', midLabel: 'Moist Soil', maxLabel: 'Open Water',
    subtext: 'Surface Water & Soil Moisture'
  },
  point_density: {
    icon: '📊', title: 'Point Density (pts/m²)', type: 'ramp',
    gradient: 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)',
    minLabel: 'Low (< 5)', midLabel: '25 pts', maxLabel: 'High (> 60 pts/m²)',
    subtext: 'Laser Pulses per Square Meter'
  },
  withheld: {
    icon: '🚫', title: 'Withheld Flag', type: 'swatches', subtext: 'Sensor Noise & Outlier Filter',
    items: [
      { color: '#10B981', label: 'Valid Survey Point' },
      { color: '#EF4444', label: 'Withheld Point (Noise)' }
    ]
  },
  keypoint: {
    icon: '⭐', title: 'Model Key Point Flag', type: 'swatches', subtext: 'Critical DTM Terrain Vertices',
    items: [
      { color: '#64748B', label: 'Standard Pulse' },
      { color: '#F59E0B', label: 'Model Key Point' }
    ]
  },
  overlap: {
    icon: '🔄', title: 'Flight Line Overlap Flag', type: 'swatches', subtext: 'Cross-Swath Overlap Coverage',
    items: [
      { color: '#3B82F6', label: 'Single Strip Coverage' },
      { color: '#EC4899', label: 'Overlap Zone (Multi-Strip)' }
    ]
  },
  return_delta: {
    icon: '↕️', title: 'Return Height Delta', type: 'swatches', subtext: 'Canopy Multi-Pulse Penetration',
    items: [
      { color: '#D2A373', label: 'Single Return (Ground Surface)' },
      { color: '#38BDF8', label: 'Multi-Return Depth (> 1.5m)' }
    ]
  },
  rgb: {
    icon: '🎨', title: 'LiDAR True Color RGB', type: 'swatches', subtext: 'UAV Photogrammetric Camera Bands',
    items: [
      { color: '#3B82F6', label: 'True Color Ortho Photogrammetry' }
    ]
  }
};

function updateLidarLegendWidget(mode) {
  const widget = document.getElementById('lidarLegendWidget');
  if (!widget) return;

  const hasData = (pointCloudBatch && pointCloudBatch.count > 0) || (pointCloudData && pointCloudData.length > 0);
  if (!hasData || !isPointCloudVisible) {
    widget.style.display = 'none';
    return;
  }

  const key = (mode || lidarColorMode || 'classification').toLowerCase();
  const cfg = LIDAR_LEGENDS[key] || LIDAR_LEGENDS['classification'];

  const shaderWidget = document.getElementById('shaderScaleWidget');
  widget.style.top = (shaderWidget && shaderWidget.style.display !== 'none') ? '108px' : '8px';

  const iconEl = document.getElementById('lidarLegendIcon');
  const titleEl = document.getElementById('lidarLegendTitle');
  const contentEl = document.getElementById('lidarLegendContent');
  const subtextEl = document.getElementById('lidarLegendSubtext');

  if (iconEl) iconEl.textContent = cfg.icon;
  if (titleEl) titleEl.textContent = cfg.title;
  if (subtextEl) subtextEl.textContent = cfg.subtext;

  if (contentEl) {
    if (cfg.type === 'swatches') {
      let html = '<div class="lidar-swatch-grid">';
      for (const item of cfg.items) {
        html += `<div class="lidar-swatch-item">
          <div class="lidar-swatch-box" style="background: ${item.color};"></div>
          <span>${item.label}</span>
        </div>`;
      }
      html += '</div>';
      contentEl.innerHTML = html;
    } else if (cfg.type === 'ramp') {
      const minTxt = typeof cfg.minLabel === 'function' ? cfg.minLabel() : cfg.minLabel;
      const midTxt = typeof cfg.midLabel === 'function' ? cfg.midLabel() : cfg.midLabel;
      const maxTxt = typeof cfg.maxLabel === 'function' ? cfg.maxLabel() : cfg.maxLabel;

      contentEl.innerHTML = `
        <div class="lidar-ramp-container">
          <div class="lidar-ramp-bar" style="background: ${cfg.gradient};"></div>
          <div class="lidar-ramp-ticks">
            <span>${minTxt}</span>
            <span>${midTxt}</span>
            <span>${maxTxt}</span>
          </div>
        </div>
      `;
    }
  }

  widget.style.display = 'block';
}

(function initLidarLegendEvents() {
  function setup() {
    const header = document.getElementById('lidarLegendHeader');
    const widget = document.getElementById('lidarLegendWidget');
    const toggleBtn = document.getElementById('lidarLegendToggle');
    if (!header || !widget || !toggleBtn) {
      setTimeout(setup, 100);
      return;
    }
    header.addEventListener('click', function () {
      widget.classList.toggle('collapsed');
      toggleBtn.textContent = widget.classList.contains('collapsed') ? '▸' : '▾';
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
