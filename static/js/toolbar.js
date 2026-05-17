/* toolbar.js — Mode buttons, grid modal, reset */
(function () {
  'use strict';

  const { state, api, canvas } = window.App;

  /* ── Mode buttons ────────────────────────────────────────────── */
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => state.setMode(btn.dataset.mode));
  });

  /* ── Reset ───────────────────────────────────────────────────── */
  document.getElementById('btn-reset').addEventListener('click', async () => {
    if (!confirm('Clear the entire graph?')) return;
    try {
      const data = await api.resetGraph();
      state.setGraphData(data);
      state.setSelected(null);
      state.setEdgeSource(null);
    } catch (err) { console.warn(err); }
  });

  /* ── Grid modal ──────────────────────────────────────────────── */
  const overlay  = document.getElementById('modal-overlay');
  const rowsEl   = document.getElementById('grid-rows');
  const colsEl   = document.getElementById('grid-cols');
  const spacingEl= document.getElementById('grid-spacing');
  const preview  = document.getElementById('grid-preview');

  function openModal() {
    overlay.classList.remove('hidden');
    renderPreview();
  }

  function closeModal() {
    overlay.classList.add('hidden');
  }

  document.getElementById('btn-grid')    .addEventListener('click', openModal);
  document.getElementById('modal-close') .addEventListener('click', closeModal);
  document.getElementById('modal-cancel').addEventListener('click', closeModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });

  // Re-render preview on input change
  [rowsEl, colsEl, spacingEl].forEach(el =>
    el.addEventListener('input', renderPreview));

  function renderPreview() {
    const rows    = Math.max(2, Math.min(10, parseInt(rowsEl.value)    || 3));
    const cols    = Math.max(2, Math.min(10, parseInt(colsEl.value)    || 4));
    const spacing = Math.max(10, parseInt(spacingEl.value) || 100);
    const pad     = 14;
    const w       = preview.clientWidth  || 220;
    const h       = preview.clientHeight || 120;
    const gridW   = (cols - 1) * spacing;
    const gridH   = (rows - 1) * spacing;
    const scale   = Math.min((w - pad * 2) / gridW, (h - pad * 2) / gridH);
    const ox      = (w - gridW * scale) / 2;
    const oy      = (h - gridH * scale) / 2;

    let lines = '', circles = '';

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const x1 = ox + c * spacing * scale;
        const x2 = ox + (c + 1) * spacing * scale;
        const y  = oy + r * spacing * scale;
        lines += `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="var(--edge-stroke)" stroke-width="1.5"/>`;
      }
    }
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols; c++) {
        const x  = ox + c * spacing * scale;
        const y1 = oy + r * spacing * scale;
        const y2 = oy + (r + 1) * spacing * scale;
        lines += `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="var(--edge-stroke)" stroke-width="1.5"/>`;
      }
    }
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = ox + c * spacing * scale;
        const y = oy + r * spacing * scale;
        circles += `<circle cx="${x}" cy="${y}" r="3" fill="var(--vertex-fill)"/>`;
      }
    }

    preview.innerHTML = `<svg width="${w}" height="${h}">${lines}${circles}</svg>`;
  }

  document.getElementById('modal-insert').addEventListener('click', async () => {
    const rows    = Math.max(2, parseInt(rowsEl.value)    || 3);
    const cols    = Math.max(2, parseInt(colsEl.value)    || 4);
    const spacing = Math.max(10, parseInt(spacingEl.value) || 100);

    // Centre the grid on the current view
    const centre  = canvas.getViewCenter();
    const origin_x = centre.x - ((cols - 1) * spacing) / 2;
    const origin_y = centre.y - ((rows - 1) * spacing) / 2;

    closeModal();
    try {
      const data = await api.insertGrid(rows, cols, spacing, origin_x, origin_y);
      state.setGraphData(data);
      canvas.fitToContent();
    } catch (err) { console.warn(err); }
  });

  window.App.toolbar = {};
})();
