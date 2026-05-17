/* inspector.js — Right-panel inspector */
(function () {
  'use strict';

  const { state } = window.App;

  const elEmpty   = document.getElementById('inspector-empty');
  const elContent = document.getElementById('inspector-content');
  const elBadge   = document.getElementById('inspector-badge');
  const elStatV   = document.getElementById('stat-v');
  const elStatE   = document.getElementById('stat-e');
  const elStatF   = document.getElementById('stat-f');
  const elEuler   = document.getElementById('stat-euler');

  /* ── Public API ─────────────────────────────────────────────────── */

  function update(type, id) {
    const { graphData } = state;
    let html = '';

    if (type === 'vertex') {
      const v = graphData.vertices.find(v => v.id === id);
      if (!v) return clear();
      const adjChips = v.adjacent.map(nid =>
        `<span class="insp-chip" data-type="vertex" data-id="${nid}">#${nid}</span>`).join('');
      const incidentFaces = graphData.faces
        .filter(f => f.vertex_ids.includes(id))
        .map(f => `<span class="insp-chip" data-type="face" data-id="${f.id}">#${f.id}</span>`).join('');

      elBadge.textContent = 'VERTEX';
      elBadge.style.color = 'var(--accent-cyan)';
      html = `
        <div class="insp-type">Vertex</div>
        <div class="insp-id">#${v.id}</div>
        <div class="insp-divider"></div>
        <div class="insp-row"><span class="insp-label">X</span><span class="insp-value">${fmt(v.x)}</span></div>
        <div class="insp-row"><span class="insp-label">Y</span><span class="insp-value">${fmt(v.y)}</span></div>
        <div class="insp-row"><span class="insp-label">Degree</span><span class="insp-value accent-cyan">${v.degree}</span></div>
        ${v.adjacent.length ? `
        <div class="insp-section-title">Adjacent Vertices</div>
        <div class="insp-chips">${adjChips}</div>` : ''}
        ${incidentFaces ? `
        <div class="insp-section-title">Incident Faces</div>
        <div class="insp-chips">${incidentFaces}</div>` : ''}
      `;
    } else if (type === 'edge') {
      const e = graphData.edges.find(e => e.id === id);
      if (!e) return clear();
      const u = state.vertexMap[e.u_id];
      const v = state.vertexMap[e.v_id];
      const leftFaces  = graphData.faces.filter(f => cycleContains(f.vertex_ids, e.u_id, e.v_id));
      const rightFaces = graphData.faces.filter(f => cycleContains(f.vertex_ids, e.v_id, e.u_id));

      elBadge.textContent = 'EDGE';
      elBadge.style.color = 'var(--accent-amber)';
      html = `
        <div class="insp-type">Edge</div>
        <div class="insp-id">#${e.id}</div>
        <div class="insp-divider"></div>
        <div class="insp-row">
          <span class="insp-label">From</span>
          <span class="insp-value"><span class="insp-chip" data-type="vertex" data-id="${e.u_id}">#${e.u_id}</span></span>
        </div>
        <div class="insp-row">
          <span class="insp-label">To</span>
          <span class="insp-value"><span class="insp-chip" data-type="vertex" data-id="${e.v_id}">#${e.v_id}</span></span>
        </div>
        <div class="insp-row"><span class="insp-label">Length</span><span class="insp-value accent-amber">${fmt(e.length)}</span></div>
        ${u && v ? `
        <div class="insp-row"><span class="insp-label">Δx</span><span class="insp-value">${fmt(Math.abs(v.x - u.x))}</span></div>
        <div class="insp-row"><span class="insp-label">Δy</span><span class="insp-value">${fmt(Math.abs(v.y - u.y))}</span></div>` : ''}
        ${leftFaces.length ? `
        <div class="insp-section-title">Left Face (u→v)</div>
        <div class="insp-chips">${leftFaces.map(f => `<span class="insp-chip" data-type="face" data-id="${f.id}">#${f.id}</span>`).join('')}</div>` : ''}
        ${rightFaces.length ? `
        <div class="insp-section-title">Right Face (v→u)</div>
        <div class="insp-chips">${rightFaces.map(f => `<span class="insp-chip" data-type="face" data-id="${f.id}">#${f.id}</span>`).join('')}</div>` : ''}
      `;
    } else if (type === 'face') {
      const f = graphData.faces.find(f => f.id === id);
      if (!f) return clear();
      const vChips = f.vertex_ids.map(vid =>
        `<span class="insp-chip" data-type="vertex" data-id="${vid}">#${vid}</span>`).join('');

      elBadge.textContent = 'FACE';
      elBadge.style.color = 'var(--accent-green)';
      html = `
        <div class="insp-type">Face</div>
        <div class="insp-id">#${f.id}</div>
        <div class="insp-divider"></div>
        <div class="insp-row"><span class="insp-label">Vertices</span><span class="insp-value accent-cyan">${f.vertex_ids.length}</span></div>
        <div class="insp-row"><span class="insp-label">Edges</span><span class="insp-value">${f.edge_count}</span></div>
        <div class="insp-row"><span class="insp-label">Area</span><span class="insp-value accent-amber">${fmt(f.area)}</span></div>
        <div class="insp-section-title">Boundary Vertices</div>
        <div class="insp-chips">${vChips}</div>
      `;
    }

    if (html) {
      elEmpty.classList.add('hidden');
      elContent.classList.remove('hidden');
      elContent.innerHTML = html;
      elContent.querySelectorAll('.insp-chip[data-type]').forEach(chip => {
        chip.addEventListener('click', () => {
          const t = chip.dataset.type;
          const cid = parseInt(chip.dataset.id);
          state.setSelected({ type: t, id: cid });
          state.setHovered({ type: t, id: cid });
        });
      });
    }
  }

  function clear() {
    elEmpty.classList.remove('hidden');
    elContent.classList.add('hidden');
    elContent.innerHTML = '';
    elBadge.textContent = '';
  }

  function updateStats() {
    const { vertices, edges, faces } = state.graphData;
    const V = vertices.length, E = edges.length, F = faces.length;
    elStatV.textContent = V;
    elStatE.textContent = E;
    elStatF.textContent = F;
    // Euler characteristic: only meaningful for connected planar graphs
    const euler = V - E + F;
    elEuler.textContent = (V > 0) ? euler : '—';
  }

  /* ── Helpers ──────────────────────────────────────────────────── */

  function fmt(n) {
    return typeof n === 'number' ? n.toLocaleString('en', { maximumFractionDigits: 2 }) : n;
  }

  /** Returns true if the cycle contains edge u→v (consecutive in order). */
  function cycleContains(vertexIds, u, v) {
    const n = vertexIds.length;
    for (let i = 0; i < n; i++) {
      if (vertexIds[i] === u && vertexIds[(i + 1) % n] === v) return true;
    }
    return false;
  }

  /* ── Bind to state events ─────────────────────────────────────── */

  state.on('hover', () => {
    const h = state.hovered;
    if (h) update(h.type, h.id);
    else if (!state.selected) clear();
  });

  state.on('select', () => {
    const s = state.selected;
    if (s) update(s.type, s.id);
    else clear();
  });

  state.on('graph', () => {
    updateStats();
    // Refresh panel if currently showing stale data
    const h = state.hovered || state.selected;
    if (h) update(h.type, h.id);
  });

  window.App.inspector = { update, clear, updateStats };
})();
