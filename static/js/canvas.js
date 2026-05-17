/* canvas.js — SVG-based graph canvas rendering and interactions */
(function () {
  'use strict';

  const { state, api } = window.App;

  /* ── Constants ─────────────────────────────────────────────────── */
  const VERTEX_R     = 7;    // vertex circle radius (graph units)
  const VERTEX_HIT_R = 14;   // invisible hit area radius
  const ZOOM_MIN     = 0.08;
  const ZOOM_MAX     = 20;
  const ZOOM_STEP    = 0.12;

  /* ── State ─────────────────────────────────────────────────────── */
  let svg, container;
  let layers = {};
  let viewBox = { x: -450, y: -350, w: 900, h: 700 };
  let isPanning = false;
  let panStart  = null;
  let ghostVertex = null;
  let ghostLine   = null;
  let mouseGraphPos = { x: 0, y: 0 };

  /* ── Initialisation ──────────────────────────────────────────────*/
  function init() {
    svg       = document.getElementById('graph-svg');
    container = document.getElementById('canvas-container');
    layers = {
      faces:       document.getElementById('faces-layer'),
      edges:       document.getElementById('edges-layer'),
      vertices:    document.getElementById('vertices-layer'),
      interaction: document.getElementById('interaction-layer'),
    };

    // Ghost vertex circle
    ghostVertex = makeSVG('circle', { id: 'ghost-vertex', r: VERTEX_R });
    ghostVertex.style.display = 'none';
    layers.interaction.appendChild(ghostVertex);

    // Ghost line for add-edge mode
    ghostLine = makeSVG('line', { id: 'ghost-line' });
    ghostLine.style.display = 'none';
    layers.interaction.appendChild(ghostLine);

    setupEvents();
    applyViewBox();
  }

  /* ── Events ─────────────────────────────────────────────────────*/
  function setupEvents() {
    svg.addEventListener('wheel',     onWheel,     { passive: false });
    svg.addEventListener('mousedown', onMouseDown);
    svg.addEventListener('mousemove', onMouseMove);
    svg.addEventListener('mouseup',   onMouseUp);
    svg.addEventListener('mouseleave',onMouseLeave);
    svg.addEventListener('click',     onClick);
    svg.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('keydown', onKeyDown);

    // Zoom buttons
    document.getElementById('zoom-in') .addEventListener('click', () => zoom(0.8));
    document.getElementById('zoom-out').addEventListener('click', () => zoom(1.25));
    document.getElementById('btn-fit') .addEventListener('click', fitToContent);
  }

  /* ── ViewBox helpers ─────────────────────────────────────────── */
  function applyViewBox() {
    const { x, y, w, h } = viewBox;
    svg.setAttribute('viewBox', `${x} ${y} ${w} ${h}`);
    updateZoomLabel();
  }

  function updateZoomLabel() {
    const svgW = svg.clientWidth || 800;
    const pct = Math.round((svgW / viewBox.w) * 100);
    document.getElementById('zoom-level').textContent = `${pct}%`;
  }

  function screenToGraph(clientX, clientY) {
    const rect = svg.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    return {
      x: viewBox.x + (px / rect.width)  * viewBox.w,
      y: viewBox.y + (py / rect.height) * viewBox.h,
    };
  }

  function zoom(factor, pivotX, pivotY) {
    const newW = viewBox.w * factor;
    const newH = viewBox.h * factor;
    const svgW = svg.clientWidth  || 800;
    const svgH = svg.clientHeight || 600;
    const scale = svgW / viewBox.w;
    if ((svgW / newW) < ZOOM_MIN || (svgW / newW) > ZOOM_MAX) return;

    const gx = pivotX !== undefined ? pivotX : viewBox.x + viewBox.w / 2;
    const gy = pivotY !== undefined ? pivotY : viewBox.y + viewBox.h / 2;

    viewBox.x = gx - (gx - viewBox.x) * factor;
    viewBox.y = gy - (gy - viewBox.y) * factor;
    viewBox.w = newW;
    viewBox.h = newH;
    applyViewBox();
  }

  function fitToContent() {
    const verts = state.graphData.vertices;
    if (verts.length === 0) {
      viewBox = { x: -450, y: -350, w: 900, h: 700 };
      applyViewBox();
      return;
    }
    const xs = verts.map(v => v.x), ys = verts.map(v => v.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = Math.max(80, Math.max(maxX - minX, maxY - minY) * 0.25);
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    const svgW = svg.clientWidth  || 800;
    const svgH = svg.clientHeight || 600;
    const neededW = (maxX - minX) + pad * 2;
    const neededH = (maxY - minY) + pad * 2;
    const scaleF = Math.min(svgW / neededW, svgH / neededH);
    viewBox.w = svgW / scaleF;
    viewBox.h = svgH / scaleF;
    viewBox.x = cx - viewBox.w / 2;
    viewBox.y = cy - viewBox.h / 2;
    applyViewBox();
  }

  /* ── Pan ─────────────────────────────────────────────────────── */
  function onWheel(e) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? (1 + ZOOM_STEP) : (1 - ZOOM_STEP);
    const g = screenToGraph(e.clientX, e.clientY);
    zoom(factor, g.x, g.y);
  }

  function onMouseDown(e) {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      // Middle-click or Alt+drag → pan
      isPanning = true;
      panStart  = { cx: e.clientX, cy: e.clientY, vx: viewBox.x, vy: viewBox.y };
      svg.style.cursor = 'grabbing';
      e.preventDefault();
    } else if (e.button === 0 && isBackground(e.target)) {
      // Left-click on background → may start pan in select mode
      if (state.mode === 'select') {
        isPanning = true;
        panStart  = { cx: e.clientX, cy: e.clientY, vx: viewBox.x, vy: viewBox.y };
        svg.style.cursor = 'grabbing';
      }
    }
  }

  function onMouseMove(e) {
    const g = screenToGraph(e.clientX, e.clientY);
    mouseGraphPos = g;
    updateStatusCoords(g);

    if (isPanning && panStart) {
      const rect = svg.getBoundingClientRect();
      const dx = (e.clientX - panStart.cx) / rect.width  * viewBox.w;
      const dy = (e.clientY - panStart.cy) / rect.height * viewBox.h;
      viewBox.x = panStart.vx - dx;
      viewBox.y = panStart.vy - dy;
      applyViewBox();
      return;
    }

    updateGhosts(g);
  }

  function onMouseUp(e) {
    if (isPanning) {
      isPanning = false;
      panStart  = null;
      svg.style.cursor = '';
    }
  }

  function onMouseLeave() {
    isPanning   = false;
    panStart    = null;
    svg.style.cursor = '';
    hideGhosts();
    state.setHovered(null);
  }

  /* ── Ghosts ─────────────────────────────────────────────────── */
  function updateGhosts(g) {
    if (state.mode === 'add-vertex') {
      ghostVertex.setAttribute('cx', g.x);
      ghostVertex.setAttribute('cy', g.y);
      ghostVertex.style.display = '';
      ghostLine.style.display = 'none';
    } else if (state.mode === 'add-edge' && state.edgeSource !== null) {
      const src = state.vertexMap[state.edgeSource];
      if (src) {
        ghostLine.setAttribute('x1', src.x);
        ghostLine.setAttribute('y1', src.y);
        ghostLine.setAttribute('x2', g.x);
        ghostLine.setAttribute('y2', g.y);
        ghostLine.style.display = '';
      }
      ghostVertex.style.display = 'none';
    } else {
      hideGhosts();
    }
  }

  function hideGhosts() {
    ghostVertex.style.display = 'none';
    ghostLine.style.display   = 'none';
  }

  /* ── Click dispatch ─────────────────────────────────────────── */
  function onClick(e) {
    if (e.button !== 0) return;
    if (isPanning) return; // was a pan drag, not a click

    const el  = e.target.closest('[data-type]');
    const g   = screenToGraph(e.clientX, e.clientY);
    const typ = el ? el.dataset.type : null;
    const id  = el ? parseInt(el.dataset.id) : null;

    switch (state.mode) {
      case 'select':     handleClickSelect(typ, id, e);  break;
      case 'add-vertex': handleClickAddVertex(g);         break;
      case 'add-edge':   handleClickAddEdge(typ, id, g); break;
      case 'delete':     handleClickDelete(typ, id);      break;
    }
  }

  function handleClickSelect(type, id, e) {
    if (!type) {
      state.setSelected(null);
    } else {
      state.setSelected({ type, id });
    }
  }

  async function handleClickAddVertex(g) {
    try {
      const data = await api.addVertex(g.x, g.y);
      state.setGraphData(data);
    } catch (err) { console.warn(err); }
  }

  async function handleClickAddEdge(type, id, g) {
    if (type === 'vertex') {
      if (state.edgeSource === null) {
        // First click: select source vertex
        state.setEdgeSource(id);
        updateHints();
      } else if (state.edgeSource === id) {
        // Clicked same vertex: cancel
        state.setEdgeSource(null);
        updateHints();
      } else {
        // Second click: add edge
        try {
          const data = await api.addEdge(state.edgeSource, id);
          state.setGraphData(data);
        } catch (err) { console.warn(err); }
        state.setEdgeSource(null);
        updateHints();
      }
    } else {
      // Clicked non-vertex: cancel
      if (state.edgeSource !== null) {
        state.setEdgeSource(null);
        updateHints();
      }
    }
  }

  async function handleClickDelete(type, id) {
    if (!type || id === null) return;
    try {
      let data;
      if (type === 'vertex') data = await api.removeVertex(id);
      else if (type === 'edge') data = await api.removeEdge(id);
      else return; // faces can't be directly deleted
      if (state.selected && state.selected.type === type && state.selected.id === id) {
        state.setSelected(null);
      }
      state.setGraphData(data);
    } catch (err) { console.warn(err); }
  }

  function onKeyDown(e) {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key.toLowerCase();
    if (k === 's')      state.setMode('select');
    else if (k === 'v') state.setMode('add-vertex');
    else if (k === 'e') state.setMode('add-edge');
    else if (k === 'd') state.setMode('delete');
    else if (k === 'escape') {
      state.setEdgeSource(null);
      state.setSelected(null);
      updateHints();
    } else if (k === 'f') fitToContent();
  }

  /* ── Hit detection helpers ───────────────────────────────────── */
  function isBackground(el) {
    return el === svg || el.id === 'canvas-bg';
  }

  /* ── Hover wiring ────────────────────────────────────────────── */
  function wireHover(group, type, id) {
    group.addEventListener('mouseenter', (e) => {
      e.stopPropagation();
      state.setHovered({ type, id });
      applySVGHover(type, id, true);
    });
    group.addEventListener('mouseleave', (e) => {
      e.stopPropagation();
      state.setHovered(null);
      applySVGHover(type, id, false);
    });
  }

  function applySVGHover(type, id, on) {
    const el = svg.querySelector(`[data-type="${type}"][data-id="${id}"]`)?.closest('.vertex-group, .edge-group, .face-poly');
    if (el) el.classList.toggle('hovered', on);
  }

  /* ── Rendering ───────────────────────────────────────────────── */
  function render(data) {
    const { vertices, edges, faces } = data;
    const { selected, edgeSource, mode } = state;

    // ── Faces
    layers.faces.innerHTML = '';
    faces.forEach(face => {
      const verts = face.vertex_ids.map(vid => state.vertexMap[vid]).filter(Boolean);
      if (verts.length < 3) return;
      const pts = verts.map(v => `${v.x},${v.y}`).join(' ');
      const poly = makeSVG('polygon', {
        class: 'face-poly',
        points: pts,
        'data-type': 'face',
        'data-id': face.id,
      });
      const isSelected = selected && selected.type === 'face' && selected.id === face.id;
      if (isSelected) poly.classList.add('selected');
      poly.addEventListener('mouseenter', (e) => { e.stopPropagation(); state.setHovered({ type: 'face', id: face.id }); poly.classList.add('hovered'); });
      poly.addEventListener('mouseleave', (e) => { e.stopPropagation(); state.setHovered(null); poly.classList.remove('hovered'); });
      poly.addEventListener('click', (e) => { e.stopPropagation(); if (state.mode === 'select') state.setSelected({ type: 'face', id: face.id }); });
      layers.faces.appendChild(poly);
    });

    // ── Edges
    layers.edges.innerHTML = '';
    edges.forEach(edge => {
      const u = state.vertexMap[edge.u_id], v = state.vertexMap[edge.v_id];
      if (!u || !v) return;
      const g = makeSVG('g', { class: 'edge-group', 'data-type': 'edge', 'data-id': edge.id });

      const line = makeSVG('line', {
        class: 'edge-line',
        x1: u.x, y1: u.y, x2: v.x, y2: v.y,
      });
      const hit = makeSVG('line', {
        class: 'edge-hit',
        x1: u.x, y1: u.y, x2: v.x, y2: v.y,
        'data-type': 'edge', 'data-id': edge.id,
      });

      const isSelected = selected && selected.type === 'edge' && selected.id === edge.id;
      if (isSelected) g.classList.add('selected');

      g.appendChild(line);
      g.appendChild(hit);

      g.addEventListener('mouseenter', (e) => {
        e.stopPropagation();
        state.setHovered({ type: 'edge', id: edge.id });
        g.classList.add(mode === 'delete' ? 'delete-hover' : 'hovered');
      });
      g.addEventListener('mouseleave', (e) => {
        e.stopPropagation();
        state.setHovered(null);
        g.classList.remove('hovered', 'delete-hover');
      });
      layers.edges.appendChild(g);
    });

    // ── Vertices
    layers.vertices.innerHTML = '';
    vertices.forEach(vertex => {
      const g = makeSVG('g', {
        class: 'vertex-group',
        'data-type': 'vertex',
        'data-id': vertex.id,
      });

      const circle = makeSVG('circle', {
        class: 'vertex-circle',
        cx: vertex.x, cy: vertex.y, r: VERTEX_R,
      });
      const hit = makeSVG('circle', {
        class: 'vertex-hit',
        cx: vertex.x, cy: vertex.y, r: VERTEX_HIT_R,
        'data-type': 'vertex', 'data-id': vertex.id,
      });

      g.appendChild(circle);
      g.appendChild(hit);

      const isPending = state.edgeSource === vertex.id;
      const isSelected = selected && selected.type === 'vertex' && selected.id === vertex.id;

      if (isPending)  g.classList.add('pending');
      if (isSelected) g.classList.add('selected');

      g.addEventListener('mouseenter', (e) => {
        e.stopPropagation();
        state.setHovered({ type: 'vertex', id: vertex.id });
        g.classList.add(mode === 'delete' ? 'delete-hover' : 'hovered');
      });
      g.addEventListener('mouseleave', (e) => {
        e.stopPropagation();
        state.setHovered(null);
        g.classList.remove('hovered', 'delete-hover');
      });
      layers.vertices.appendChild(g);
    });

    updateCanvasHint(vertices.length);
    updateHints();
  }

  /* ── UI hints ────────────────────────────────────────────────── */
  function updateCanvasHint(vertexCount) {
    const hint = document.getElementById('canvas-hint');
    if (vertexCount === 0) {
      hint.classList.remove('hidden');
      hint.innerHTML = 'Press <strong>V</strong> to add vertices<br>or use <strong>Grid</strong> to insert a template';
    } else {
      hint.classList.add('hidden');
    }
  }

  function updateHints() {
    const el = document.getElementById('status-hint');
    const { mode, edgeSource } = state;
    const hints = {
      'select':     'Click a vertex, edge, or face to inspect it · Drag to pan',
      'add-vertex': 'Click anywhere to place a vertex · Esc to cancel',
      'add-edge':   edgeSource !== null
                      ? `Source #${edgeSource} selected · Click another vertex to connect · Esc to cancel`
                      : 'Click a vertex to select the edge source',
      'delete':     'Click a vertex or edge to delete it',
    };
    el.textContent = hints[mode] || '';
  }

  function updateStatusCoords(g) {
    document.getElementById('status-coords').textContent =
      `x: ${g.x.toFixed(1)}  y: ${g.y.toFixed(1)}`;
  }

  /* ── SVG helper ──────────────────────────────────────────────── */
  function makeSVG(tag, attrs = {}) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
  }

  /* ── Public surface ──────────────────────────────────────────── */
  function getViewCenter() {
    return { x: viewBox.x + viewBox.w / 2, y: viewBox.y + viewBox.h / 2 };
  }

  /* ── Bind to state ────────────────────────────────────────────── */
  state.on('graph',      () => render(state.graphData));
  state.on('mode',       () => {
    hideGhosts();
    render(state.graphData);
    // Update mode button UI
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === state.mode);
    });
    document.getElementById('status-mode').textContent = `MODE: ${state.mode.toUpperCase().replace('-', ' ')}`;
    updateHints();
  });
  state.on('edgesource', () => {
    render(state.graphData);
    updateHints();
    updateGhosts(mouseGraphPos);
  });
  state.on('select',     () => render(state.graphData));

  window.App.canvas = { init, render, fitToContent, getViewCenter };
})();
