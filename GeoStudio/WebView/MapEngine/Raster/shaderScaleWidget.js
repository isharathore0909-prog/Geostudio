// Dynamic Shader / Elevation Scale Legend Widget
const SHADER_SCALES = {
  'atlas': {
    title: 'Elevation',
    unit: 'm',
    icon: '🏔️',
    gradient: 'linear-gradient(to right, rgb(0,0,255) 0%, rgb(0,212,255) 8%, rgb(0,184,40) 18%, rgb(15,166,25) 45%, rgb(96,200,0) 70%, rgb(255,214,0) 82%, rgb(255,102,0) 92%, rgb(204,0,0) 100%)',
    subtext: 'Global Mapper Atlas (3D Shaded Relief)',
    isElevation: true
  },
  'terrain': {
    title: 'Elevation (Terrain)',
    unit: 'm',
    icon: '⛰️',
    gradient: 'linear-gradient(to right, rgb(25,104,40) 0%, rgb(63,162,53) 15%, rgb(140,198,69) 30%, rgb(229,223,99) 48%, rgb(221,162,70) 65%, rgb(180,90,36) 78%, rgb(125,63,31) 88%, rgb(150,144,140) 96%, rgb(255,255,255) 100%)',
    subtext: 'Global Mapper Earth Tones (3D Relief)',
    isElevation: true
  },
  'viridis': {
    title: 'Elevation (Viridis)',
    unit: 'm',
    icon: '📊',
    gradient: 'linear-gradient(to right, rgb(68,1,84) 0%, rgb(59,82,139) 25%, rgb(33,145,140) 50%, rgb(94,201,98) 75%, rgb(253,231,37) 100%)',
    subtext: 'Scientific Viridis Colormap (3D)',
    isElevation: true
  },
  'magma': {
    title: 'Elevation (Magma)',
    unit: 'm',
    icon: '🔥',
    gradient: 'linear-gradient(to right, rgb(0,0,4) 0%, rgb(81,18,124) 25%, rgb(183,55,121) 50%, rgb(252,137,97) 75%, rgb(252,253,191) 100%)',
    subtext: 'High-Contrast Magma Colormap (3D)',
    isElevation: true
  },
  'slope': {
    title: 'Slope Angle',
    unit: '°',
    icon: '📐',
    gradient: 'linear-gradient(to right, rgb(34,197,94) 0%, rgb(132,204,22) 15%, rgb(234,179,8) 35%, rgb(249,115,22) 60%, rgb(239,68,68) 100%)',
    minLabel: '0° Flat',
    midLabel: '20° Moderate',
    maxLabel: '45°+ Cliff',
    subtext: 'Terrain Inclination Steepness',
    isElevation: false
  },
  'aspect': {
    title: 'Aspect (Direction)',
    unit: '',
    icon: '🧭',
    gradient: 'linear-gradient(to right, rgb(227,26,28) 0%, rgb(255,127,0) 6.25%, rgb(255,255,51) 18.75%, rgb(77,175,74) 31.25%, rgb(55,126,184) 43.75%, rgb(152,78,163) 56.25%, rgb(247,129,191) 68.75%, rgb(166,86,40) 81.25%, rgb(227,26,28) 100%)',
    minLabel: '0° N',
    midLabel: '180° S',
    maxLabel: '360° N',
    subtext: 'Azimuth Compass Facing Direction',
    isElevation: false
  },
  'hillshade': {
    title: 'Shaded Relief',
    unit: '',
    icon: '☀️',
    gradient: 'linear-gradient(to right, rgb(15,15,20) 0%, rgb(128,128,128) 50%, rgb(255,255,255) 100%)',
    minLabel: 'Shadow',
    midLabel: 'Midtone',
    maxLabel: 'Sunlit',
    subtext: 'Multi-directional Hillshade (315° Az / 45° Alt)',
    isElevation: false
  },
  'tri': {
    title: 'TRI (Ruggedness)',
    unit: '',
    icon: '🪨',
    gradient: 'linear-gradient(to right, rgb(34,197,94) 0%, rgb(234,179,8) 35%, rgb(239,68,68) 70%, rgb(147,51,234) 100%)',
    minLabel: 'Level (0)',
    midLabel: 'Moderate',
    maxLabel: 'Highly Rugged',
    subtext: 'Terrain Ruggedness Index (Riley et al.)',
    isElevation: false
  },
  'tpi': {
    title: 'TPI (Position)',
    unit: '',
    icon: '📊',
    gradient: 'linear-gradient(to right, rgb(0,100,255) 0%, rgb(0,212,255) 25%, rgb(34,197,94) 50%, rgb(255,214,0) 75%, rgb(204,0,0) 100%)',
    minLabel: 'Valley / Pit',
    midLabel: 'Planar / Slope',
    maxLabel: 'Ridge / Peak',
    subtext: 'Topographic Position Index',
    isElevation: false
  },
  'twi': {
    title: 'TWI (Wetness Index)',
    unit: '',
    icon: '💧',
    gradient: 'linear-gradient(to right, rgb(245,235,200) 0%, rgb(210,225,170) 20%, rgb(120,198,121) 40%, rgb(65,182,196) 65%, rgb(34,94,168) 85%, rgb(8,29,88) 100%)',
    minLabel: 'Dry Crest',
    midLabel: 'Moist Slope',
    maxLabel: 'Saturated Channel',
    subtext: 'Hydrological Topographic Wetness',
    isElevation: false
  },
  'curvature': {
    title: 'Curvature (Morphology)',
    unit: '',
    icon: '🌐',
    gradient: 'linear-gradient(to right, rgb(215,48,39) 0%, rgb(252,141,89) 25%, rgb(240,240,240) 50%, rgb(145,191,219) 75%, rgb(69,117,180) 100%)',
    minLabel: 'Convex (+)',
    midLabel: 'Planar (0.0)',
    maxLabel: 'Concave (-)',
    subtext: 'Surface Curvature Profile',
    isElevation: false
  }
};

function updateShaderScaleWidget(shaderMode, palette, minElev, maxElev) {
  const widget = document.getElementById('shaderScaleWidget');
  if (!widget) return;

  if (typeof activeRasterInfo !== 'undefined' && activeRasterInfo && activeRasterInfo.visible === false) {
    widget.style.display = 'none';
    return;
  }

  const key = (shaderMode || 'atlas').toLowerCase();
  const palKey = (palette || '').toLowerCase();

  let cfg = SHADER_SCALES[key];
  if (!cfg && palKey) {
    if (palKey.includes('terrain')) cfg = SHADER_SCALES['terrain'];
    else if (palKey.includes('viridis')) cfg = SHADER_SCALES['viridis'];
    else if (palKey.includes('magma')) cfg = SHADER_SCALES['magma'];
  }
  if (!cfg) cfg = SHADER_SCALES['atlas'];

  const iconEl = document.getElementById('shaderScaleIcon');
  const titleEl = document.getElementById('shaderScaleTitle');
  const barEl = document.getElementById('shaderScaleBar');
  const minEl = document.getElementById('shaderScaleMin');
  const midEl = document.getElementById('shaderScaleMid');
  const maxEl = document.getElementById('shaderScaleMax');
  const subtextEl = document.getElementById('shaderScaleSubtext');

  if (iconEl) iconEl.textContent = cfg.icon;
  if (titleEl) titleEl.textContent = cfg.title;
  if (barEl) barEl.style.background = cfg.gradient;
  if (subtextEl) subtextEl.textContent = cfg.subtext;

  if (cfg.isElevation) {
    const minVal = minElev !== undefined && minElev !== null ? minElev : (activeRasterInfo ? activeRasterInfo.minElev : null);
    const maxVal = maxElev !== undefined && maxElev !== null ? maxElev : (activeRasterInfo ? activeRasterInfo.maxElev : null);

    if (minVal !== null && maxVal !== null && !isNaN(minVal) && !isNaN(maxVal)) {
      const midVal = (minVal + maxVal) / 2.0;
      if (minEl) minEl.textContent = `${minVal.toFixed(1)} ${cfg.unit}`;
      if (midEl) midEl.textContent = `${midVal.toFixed(1)} ${cfg.unit}`;
      if (maxEl) maxEl.textContent = `${maxVal.toFixed(1)} ${cfg.unit}`;
    } else {
      if (minEl) minEl.textContent = `-- ${cfg.unit}`;
      if (midEl) midEl.textContent = `-- ${cfg.unit}`;
      if (maxEl) maxEl.textContent = `-- ${cfg.unit}`;
    }
  } else {
    if (minEl) minEl.textContent = cfg.minLabel || '';
    if (midEl) midEl.textContent = cfg.midLabel || '';
    if (maxEl) maxEl.textContent = cfg.maxLabel || '';
  }

  widget.style.display = 'block';
}

function hideShaderScaleWidget() {
  const widget = document.getElementById('shaderScaleWidget');
  if (widget) widget.style.display = 'none';
}

(function initShaderScaleEvents() {
  function setup() {
    const header = document.getElementById('shaderScaleHeader');
    const widget = document.getElementById('shaderScaleWidget');
    const toggleBtn = document.getElementById('shaderScaleToggle');
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
