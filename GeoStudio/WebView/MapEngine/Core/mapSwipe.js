// Swipe Comparison Layer Interaction
let isSwipeActive = false;
let swipeFraction = 0.5;
let swipeInverted = false;
let swipeInitialized = false;

function initSwipeInteraction() {
  if (swipeInitialized) return;
  const container = document.getElementById('swipeContainer');
  const handle = document.getElementById('swipeHandle');
  const line = document.getElementById('swipeLine');
  const btnExit = document.getElementById('btnExitSwipe');
  const btnSwap = document.getElementById('btnSwapSwipe');
  if (!container || !handle) return;
  swipeInitialized = true;

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
  let activePointerId = null;

  function updatePosition(clientX) {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;
    const rect = mapEl.getBoundingClientRect();
    const x = Math.max(10, Math.min(rect.width - 10, clientX - rect.left));
    swipeFraction = x / rect.width;
    container.style.left = (swipeFraction * 100) + '%';
    map.render();
  }

  function onPointerDown(e) {
    dragging = true;
    activePointerId = e.pointerId;
    try {
      if (typeof e.target.setPointerCapture === 'function') {
        e.target.setPointerCapture(e.pointerId);
      }
    } catch (err) {}
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    updatePosition(e.clientX);
    e.preventDefault();
    e.stopPropagation();
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
      if (activePointerId !== null) {
        try {
          if (e.target && typeof e.target.releasePointerCapture === 'function') {
            e.target.releasePointerCapture(activePointerId);
          }
        } catch (err) {}
        activePointerId = null;
      }
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      e.preventDefault();
      e.stopPropagation();
    }
  }

  handle.addEventListener('pointerdown', onPointerDown);
  if (line) line.addEventListener('pointerdown', onPointerDown);

  window.addEventListener('pointermove', onPointerMove, { passive: false });
  window.addEventListener('pointerup', onPointerUp, { passive: false });
  window.addEventListener('pointercancel', onPointerUp);

  window.addEventListener('resize', function () {
    if (isSwipeActive) {
      const c = document.getElementById('swipeContainer');
      if (c) c.style.left = (swipeFraction * 100) + '%';
      if (typeof map !== 'undefined' && map) map.render();
    }
  });
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

  if (container) {
    container.style.display = isSwipeActive ? 'block' : 'none';
    if (isSwipeActive) {
      if (typeof swipeFraction !== 'number' || isNaN(swipeFraction)) {
        swipeFraction = 0.5;
      }
      container.style.left = (swipeFraction * 100) + '%';
    }
  }
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
  if (!canvas) return;
  const canvasW = canvas.width;
  const canvasH = canvas.height;

  let scaleX = 1;
  let scaleY = 1;
  let offsetX = 0;
  let offsetY = 0;

  if (typeof ctx.getTransform === 'function') {
    try {
      const m = ctx.getTransform();
      scaleX = m.a || 1;
      scaleY = m.d || 1;
      offsetX = m.e || 0;
      offsetY = m.f || 0;
    } catch (err) {}
  } else {
    scaleX = canvasW / mapSize[0];
    scaleY = canvasH / mapSize[1];
  }

  const screenSplitX = canvasW * swipeFraction;
  const xSplit = (screenSplitX - offsetX) / scaleX;
  const xLeft = (0 - offsetX) / scaleX;
  const xRight = (canvasW - offsetX) / scaleX;
  const yTop = (0 - offsetY) / scaleY;
  const yBottom = (canvasH - offsetY) / scaleY;

  ctx.save();
  ctx.beginPath();
  if (!swipeInverted) {
    ctx.rect(xLeft, yTop, xSplit - xLeft, yBottom - yTop);
  } else {
    ctx.rect(xSplit, yTop, xRight - xSplit, yBottom - yTop);
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
