// Swipe Comparison Layer Interaction
let isSwipeActive = false;
let swipeFraction = 0.5;
let swipeInverted = false;

function initSwipeInteraction() {
  const container = document.getElementById('swipeContainer');
  const handle = document.getElementById('swipeHandle');
  const btnExit = document.getElementById('btnExitSwipe');
  const btnSwap = document.getElementById('btnSwapSwipe');
  if (!container || !handle) return;

  if (btnExit) {
    btnExit.onclick = function (e) {
      e.stopPropagation();
      toggleSwipe(false);
    };
  }

  if (btnSwap) {
    btnSwap.onclick = function (e) {
      e.stopPropagation();
      swipeInverted = !swipeInverted;
      updateSwipeBadgeText();
      map.render();
    };
  }

  let dragging = false;

  function onPointerDown(e) {
    dragging = true;
    try { container.setPointerCapture(e.pointerId); } catch(err){}
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    updatePosition(e.clientX);
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
