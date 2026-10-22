// Point Cloud Canvas Manager - Lifecycle & State
const pcCanvas = document.getElementById('pointCloudCanvas');
const pcCtx = pcCanvas.getContext('2d');
let pointCloudData = [];
let pointCloudBatch = null;
let lidarColorMode = 'rgb_elev';
let userPointSize = 4.5;
let isPointCloudVisible = true;
let activePointCloudId = null;
let pcMinZ = 0;
let pcMaxZ = 1000;
let pointCloudDebounceTimer = null;

function resizeCanvas() {
  if (typeof map === 'undefined') return;
  const viewport = map.getViewport();
  if (!viewport) return;
  pcCanvas.width = viewport.clientWidth;
  pcCanvas.height = viewport.clientHeight;
  renderPointCloud();
}
window.addEventListener('resize', resizeCanvas);
setTimeout(resizeCanvas, 200);
