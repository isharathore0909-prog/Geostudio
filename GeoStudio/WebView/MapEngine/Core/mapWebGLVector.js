// GeoStudio Hardware-Accelerated WebGL Vector Engine (100% Offline)
// Directly renders massive polygon and line GeoJSON datasets on the GPU via WebGL shaders.

(function () {
  'use strict';

  let glCanvas = null;
  let gl = null;
  let polyProgram = null;
  let lineProgram = null;
  let polyAttribs = null;
  let lineAttribs = null;
  let polyUniforms = null;
  let lineUniforms = null;

  // Registry of loaded WebGL vector layers: layerId -> { polyVbo, polyCount, lineVbo, lineCount, originX, originY, visible, opacity, zIndex }
  const webGlDatasets = new Map();

  function initWebGL() {
    if (gl) return true;
    glCanvas = document.createElement('canvas');
    gl = glCanvas.getContext('webgl2', { alpha: true, antialias: true, premultipliedAlpha: true }) ||
         glCanvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: true });

    if (!gl) {
      console.warn('[WebGL Vector] WebGL not supported on this platform, falling back to Canvas.');
      return false;
    }

    // Vertex Shader: high-precision GPU matrix transformation
    const vsSource = `
      attribute vec2 a_position;
      attribute vec4 a_color;
      uniform mat4 u_matrix;
      varying vec4 v_color;
      void main() {
        gl_Position = u_matrix * vec4(a_position, 0.0, 1.0);
        v_color = a_color;
      }
    `;

    // Fragment Shader: premultiplied alpha for correct canvas compositing and smooth transparency
    const fsSource = `
      precision mediump float;
      varying vec4 v_color;
      uniform float u_opacity;
      void main() {
        float a = v_color.a * u_opacity;
        gl_FragColor = vec4(v_color.rgb * a, a);
      }
    `;

    polyProgram = createProgram(gl, vsSource, fsSource);
    lineProgram = createProgram(gl, vsSource, fsSource);
    if (!polyProgram || !lineProgram) return false;

    polyAttribs = {
      position: gl.getAttribLocation(polyProgram, 'a_position'),
      color: gl.getAttribLocation(polyProgram, 'a_color')
    };
    polyUniforms = {
      matrix: gl.getUniformLocation(polyProgram, 'u_matrix'),
      opacity: gl.getUniformLocation(polyProgram, 'u_opacity')
    };

    lineAttribs = {
      position: gl.getAttribLocation(lineProgram, 'a_position'),
      color: gl.getAttribLocation(lineProgram, 'a_color')
    };
    lineUniforms = {
      matrix: gl.getUniformLocation(lineProgram, 'u_matrix'),
      opacity: gl.getUniformLocation(lineProgram, 'u_opacity')
    };

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    return true;
  }

  function createShader(glCtx, type, source) {
    const shader = glCtx.createShader(type);
    glCtx.shaderSource(shader, source);
    glCtx.compileShader(shader);
    if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
      console.error('[WebGL Shader Error]', glCtx.getShaderInfoLog(shader));
      glCtx.deleteShader(shader);
      return null;
    }
    return shader;
  }

  function createProgram(glCtx, vs, fs) {
    const vShader = createShader(glCtx, glCtx.VERTEX_SHADER, vs);
    const fShader = createShader(glCtx, glCtx.FRAGMENT_SHADER, fs);
    if (!vShader || !fShader) return null;

    const prog = glCtx.createProgram();
    glCtx.attachShader(prog, vShader);
    glCtx.attachShader(prog, fShader);
    glCtx.linkProgram(prog);
    if (!glCtx.getProgramParameter(prog, glCtx.LINK_STATUS)) {
      console.error('[WebGL Link Error]', glCtx.getProgramInfoLog(prog));
      return null;
    }
    return prog;
  }

  function parseHexColor(colorStr, defaultAlpha) {
    let r = 16 / 255, g = 185 / 255, b = 129 / 255, a = defaultAlpha !== undefined ? defaultAlpha : 1.0;
    if (!colorStr) return [r, g, b, a];
    colorStr = colorStr.trim();
    if (colorStr.startsWith('#')) {
      let hex = colorStr.substring(1);
      if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
      if (hex.length >= 6) {
        r = parseInt(hex.substring(0, 2), 16) / 255.0;
        g = parseInt(hex.substring(2, 4), 16) / 255.0;
        b = parseInt(hex.substring(4, 6), 16) / 255.0;
      }
    } else if (colorStr.startsWith('rgb')) {
      const parts = colorStr.match(/[\d.]+/g);
      if (parts && parts.length >= 3) {
        r = parseFloat(parts[0]) / 255.0;
        g = parseFloat(parts[1]) / 255.0;
        b = parseFloat(parts[2]) / 255.0;
        if (parts.length >= 4) a = parseFloat(parts[3]);
      }
    }
    return [r, g, b, a];
  }

  // Triangulates GeoJSON and uploads vertices directly to GPU VBO buffers
  function uploadGeoJsonToGpu(layerId, geoJsonObj, defaultColorHex) {
    if (!initWebGL()) return false;
    if (!geoJsonObj || !geoJsonObj.features) return false;

    const features = geoJsonObj.features;
    if (features.length === 0) return false;

    // Use dataset center as relative origin to preserve 32-bit float GPU precision
    let originX = 0, originY = 0;
    let sampleCount = 0;
    for (let i = 0; i < Math.min(features.length, 100); i++) {
      const g = features[i].geometry;
      if (!g || !g.coordinates) continue;
      let coord = null;
      if (g.type === 'Polygon' && g.coordinates[0] && g.coordinates[0][0]) coord = g.coordinates[0][0];
      else if (g.type === 'MultiPolygon' && g.coordinates[0] && g.coordinates[0][0] && g.coordinates[0][0][0]) coord = g.coordinates[0][0][0];
      else if (g.type === 'LineString' && g.coordinates[0]) coord = g.coordinates[0];
      if (coord && typeof coord[0] === 'number') {
        const p = ol.proj.fromLonLat([coord[0], coord[1]]);
        originX += p[0];
        originY += p[1];
        sampleCount++;
      }
    }
    if (sampleCount > 0) {
      originX /= sampleCount;
      originY /= sampleCount;
    }

    const polyVerts = []; // [x, y, r, g, b, a]
    const lineVerts = []; // [x, y, r, g, b, a]

    for (let fIdx = 0; fIdx < features.length; fIdx++) {
      const feat = features[fIdx];
      const geom = feat.geometry;
      if (!geom || !geom.coordinates) continue;

      const props = feat.properties || {};
      const fillColorStr = props.fillColor || props.color || defaultColorHex || '#3b82f6';
      const strokeColorStr = props.strokeColor || '#0f172a';
      const [pr, pg, pb, pa] = parseHexColor(fillColorStr, 0.95);
      const [lr, lg, lb, la] = parseHexColor(strokeColorStr, 1.0);

      const type = geom.type;

      if (type === 'Polygon') {
        triangulatePolygon(geom.coordinates, originX, originY, pr, pg, pb, pa, polyVerts, lr, lg, lb, la, lineVerts);
      } else if (type === 'MultiPolygon') {
        for (let m = 0; m < geom.coordinates.length; m++) {
          triangulatePolygon(geom.coordinates[m], originX, originY, pr, pg, pb, pa, polyVerts, lr, lg, lb, la, lineVerts);
        }
      } else if (type === 'LineString') {
        processLineString(geom.coordinates, originX, originY, lr, lg, lb, la, lineVerts);
      } else if (type === 'MultiLineString') {
        for (let m = 0; m < geom.coordinates.length; m++) {
          processLineString(geom.coordinates[m], originX, originY, lr, lg, lb, la, lineVerts);
        }
      }
    }

    // Upload to WebGL buffers
    let polyVbo = null, polyCount = 0;
    if (polyVerts.length > 0) {
      polyVbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, polyVbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(polyVerts), gl.STATIC_DRAW);
      polyCount = polyVerts.length / 6;
    }

    let lineVbo = null, lineCount = 0;
    if (lineVerts.length > 0) {
      lineVbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, lineVbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(lineVerts), gl.STATIC_DRAW);
      lineCount = lineVerts.length / 6;
    }

    // Clean up old VBOs if layer reloaded while preserving current opacity / visibility
    let currentOpacity = 1.0;
    let currentVisible = true;
    if (webGlDatasets.has(layerId)) {
      const old = webGlDatasets.get(layerId);
      if (old.polyVbo) gl.deleteBuffer(old.polyVbo);
      if (old.lineVbo) gl.deleteBuffer(old.lineVbo);
      if (old.opacity !== undefined) currentOpacity = old.opacity;
      if (old.visible !== undefined) currentVisible = old.visible;
    }

    webGlDatasets.set(layerId, {
      polyVbo: polyVbo,
      polyCount: polyCount,
      lineVbo: lineVbo,
      lineCount: lineCount,
      originX: originX,
      originY: originY,
      visible: currentVisible,
      opacity: currentOpacity,
      zIndex: 12
    });

    return true;
  }

  function triangulatePolygon(rings, originX, originY, r, g, b, a, polyVerts, lr, lg, lb, la, lineVerts) {
    if (!rings || rings.length === 0 || rings[0].length < 3) return;

    // Convert rings to flat coordinates and hole indices
    const flat = [];
    const holeIndices = [];
    let vertIndex = 0;

    for (let rIdx = 0; rIdx < rings.length; rIdx++) {
      const ring = rings[rIdx];
      if (rIdx > 0) holeIndices.push(vertIndex);

      for (let i = 0; i < ring.length; i++) {
        const pt = ol.proj.fromLonLat([ring[i][0], ring[i][1]]);
        flat.push(pt[0] - originX, pt[1] - originY);
        vertIndex++;

        // Add boundary wireframe segment
        if (i > 0) {
          const prev = ol.proj.fromLonLat([ring[i - 1][0], ring[i - 1][1]]);
          lineVerts.push(
            prev[0] - originX, prev[1] - originY, lr, lg, lb, la,
            pt[0] - originX, pt[1] - originY, lr, lg, lb, la
          );
        }
      }
    }

    if (typeof window.earcut !== 'function') return;
    const indices = window.earcut(flat, holeIndices, 2);

    for (let i = 0; i < indices.length; i++) {
      const idx = indices[i] * 2;
      polyVerts.push(flat[idx], flat[idx + 1], r, g, b, a);
    }
  }

  function processLineString(coords, originX, originY, r, g, b, a, lineVerts) {
    if (!coords || coords.length < 2) return;
    for (let i = 1; i < coords.length; i++) {
      const p1 = ol.proj.fromLonLat([coords[i - 1][0], coords[i - 1][1]]);
      const p2 = ol.proj.fromLonLat([coords[i][0], coords[i][1]]);
      lineVerts.push(
        p1[0] - originX, p1[1] - originY, r, g, b, a,
        p2[0] - originX, p2[1] - originY, r, g, b, a
      );
    }
  }

  // Pure WebGL GPU Render Pass called inside OpenLayers Frame Loop
  function renderWebGLVectorLayers(frameState) {
    if (!gl || webGlDatasets.size === 0) return null;

    const width = frameState.size[0] * frameState.pixelRatio;
    const height = frameState.size[1] * frameState.pixelRatio;

    if (glCanvas.width !== width || glCanvas.height !== height) {
      glCanvas.width = width;
      glCanvas.height = height;
      gl.viewport(0, 0, width, height);
    }

    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    const viewState = frameState.viewState;
    const center = viewState.center;
    const res = viewState.resolution;
    const rotation = viewState.rotation || 0;

    const sx = 2.0 / (frameState.size[0] * res);
    const sy = 2.0 / (frameState.size[1] * res);
    const cosR = Math.cos(-rotation);
    const sinR = Math.sin(-rotation);

    webGlDatasets.forEach((dataset, layerId) => {
      if (!dataset.visible || dataset.opacity <= 0) return;

      const dx = dataset.originX - center[0];
      const dy = dataset.originY - center[1];

      // Build 4x4 matrix converting relative world coords directly to WebGL NDC [-1, 1]
      const matrix = new Float32Array([
        sx * cosR, -sy * sinR, 0, 0,
        sx * sinR,  sy * cosR, 0, 0,
        0,          0,         1, 0,
        (dx * cosR - dy * sinR) * sx, (dx * sinR + dy * cosR) * sy, 0, 1
      ]);

      // 1. Draw Polygons
      if (dataset.polyCount > 0 && dataset.polyVbo) {
        gl.useProgram(polyProgram);
        gl.uniformMatrix4fv(polyUniforms.matrix, false, matrix);
        gl.uniform1f(polyUniforms.opacity, dataset.opacity);

        gl.bindBuffer(gl.ARRAY_BUFFER, dataset.polyVbo);
        gl.enableVertexAttribArray(polyAttribs.position);
        gl.vertexAttribPointer(polyAttribs.position, 2, gl.FLOAT, false, 24, 0);

        gl.enableVertexAttribArray(polyAttribs.color);
        gl.vertexAttribPointer(polyAttribs.color, 4, gl.FLOAT, false, 24, 8);

        gl.drawArrays(gl.TRIANGLES, 0, dataset.polyCount);
      }

      // 2. Draw Boundaries & Drainage Lines
      if (dataset.lineCount > 0 && dataset.lineVbo) {
        gl.useProgram(lineProgram);
        gl.uniformMatrix4fv(lineUniforms.matrix, false, matrix);
        gl.uniform1f(lineUniforms.opacity, dataset.opacity);

        gl.bindBuffer(gl.ARRAY_BUFFER, dataset.lineVbo);
        gl.enableVertexAttribArray(lineAttribs.position);
        gl.vertexAttribPointer(lineAttribs.position, 2, gl.FLOAT, false, 24, 0);

        gl.enableVertexAttribArray(lineAttribs.color);
        gl.vertexAttribPointer(lineAttribs.color, 4, gl.FLOAT, false, 24, 8);

        gl.drawArrays(gl.LINES, 0, dataset.lineCount);
      }
    });

    return glCanvas;
  }

  // Create native OpenLayers Layer wrapping the GPU WebGL renderer
  function createOpenLayersWebGLLayer() {
    return new ol.layer.Layer({
      render: function (frameState) {
        return renderWebGLVectorLayers(frameState);
      },
      zIndex: 15
    });
  }

  // Public WebGL Vector API for MapEngine
  window.GeoStudioWebGLVector = {
    init: initWebGL,
    upload: uploadGeoJsonToGpu,
    createLayer: createOpenLayersWebGLLayer,
    hasLayer: (id) => webGlDatasets.has(id),
    setLayerVisibility: (id, visible) => {
      const d = webGlDatasets.get(id);
      if (d) d.visible = !!visible;
      if (typeof map !== 'undefined' && map) map.render();
    },
    setLayerOpacity: (id, opacity) => {
      const d = webGlDatasets.get(id);
      if (d) {
        const val = parseFloat(opacity);
        d.opacity = isNaN(val) ? 1.0 : Math.max(0, Math.min(1, val));
      }
      if (typeof map !== 'undefined' && map) map.render();
    },
    removeLayer: (id) => {
      if (webGlDatasets.has(id)) {
        const d = webGlDatasets.get(id);
        if (gl) {
          if (d.polyVbo) gl.deleteBuffer(d.polyVbo);
          if (d.lineVbo) gl.deleteBuffer(d.lineVbo);
        }
        webGlDatasets.delete(id);
      }
    }
  };
})();
