/**
 * main.js
 * Application entry point. Wires together UI events, state, and rendering.
 */

import { api } from './api.js';
import { appState } from './state.js';
import { renderGrid, svgPosToCell, eventToSvgPos, cellKey } from './grid-renderer.js';
import { initLineDrawing } from './line-drawing.js';
import {
  buildNumberPalette,
  selectPaletteValue,
  onCustomPaletteInput,
  selectErase,
  updateToolbarBadge,
  syncToolButtons,
  buildEndpointPalette,
  selectEndpointColor,
  selectEndpointRole
} from './palette.js';

// ── State listener: re-render whenever state changes ───────────────────
appState.subscribe(() => {
  renderGrid();
  renderRulesList();
  renderViolations();
  updateStatus();
  updateToolbarBadge();
  syncToolButtons();
  // show/hide mode-dependent sections
  document.getElementById('edit-tools').style.display = appState.mode === 'edit' ? '' : 'none';
  document.getElementById('rules-section').style.display = appState.mode === 'edit' ? '' : 'none';
  document.getElementById('play-actions').style.display = appState.mode === 'play' ? '' : 'none';
  document.getElementById('play-banner').style.display = appState.mode === 'play' ? '' : 'none';
  document.getElementById('status-mode').textContent = appState.mode === 'edit' ? 'Edit' : 'Play';
  document.getElementById('palette-heading').textContent = appState.mode === 'edit' ? 'Symbol' : 'Input Value';
  document.getElementById('endpoint-palette').parentElement.style.display = appState.mode === 'edit' ? '' : 'none';
  document.querySelector('.ep-role-row').style.display = appState.mode === 'edit' ? '' : 'none';
  // placement target buttons active state
  document.querySelectorAll('.target-btn').forEach(b => {
    b.classList.toggle('active', b.id === `target-${appState.placementTarget}`);
  });
  if (appState.activeTool !== 'draw-line' && appState.dragState) {
    appState.update({ dragState: null });
  }
});

// ── Helper: refresh full puzzle from server ─────────────────────────────
async function refresh(data) {
  if (!data || data.error) {
    if (data?.error) console.error(data.error);
    return;
  }
  appState.update({ puzzle: data });
}

// ── Load initial data ──────────────────────────────────────────────────
async function load() {
  const data = await api.getState();
  const schema = await api.rulesRegistry();
  appState.update({ rulesSchema: schema });
  refresh(data);
  buildNumberPalette();
  buildEndpointPalette();
  buildRuleSelect();
  // sync mode buttons
  document.getElementById('btn-edit').classList.toggle('active', appState.mode === 'edit');
  document.getElementById('btn-play').classList.toggle('active', appState.mode === 'play');
}

// ── Cell click handler (modified for placement target) ──────────────────
async function onCellClick(r, c) {
  const puzzle = appState.puzzle;
  const key = cellKey(r, c);
  const isActive = (puzzle?.grid?.cells || []).some(([cr, cc]) => cr === r && cc === c);

  if (appState.mode === 'edit') {
    if (appState.eraseMode) {
      // erase any symbol on the cell if it exists
      if (isActive && puzzle.symbols?.[`c:${key}`]) {
        refresh(await api.removeSymbol(r, c));
      }
    } else if (appState.activeTool === 'place-symbol' && appState.placementTarget === 'cell') {
      if (isActive) {
        if (appState.paletteType === 'endpoint') {
          refresh(await api.placeSymbol(r, c, 'endpoint', {
            role: appState.endpointRole,
            color_id: appState.endpointColorId
          }));
        } else {
          refresh(await api.placeSymbol(r, c, 'number', { value: appState.selectedValue }));
        }
      }
    } else if (appState.activeTool === 'add-cell') {
      if (!isActive) refresh(await api.addCell(r, c));
    } else if (appState.activeTool === 'remove-cell') {
      if (isActive) refresh(await api.removeCell(r, c));
    }
  } else { // play mode
    if (!isActive) return;
    const isFixed = puzzle.symbols?.[`c:${key}`] !== undefined;
    if (isFixed) return;

    if (appState.eraseMode) {
      refresh(await api.clearPlayerValue(r, c));
    } else {
      const existing = puzzle.player_values?.[key];
      if (existing === appState.selectedValue) {
        refresh(await api.clearPlayerValue(r, c));
      } else {
        refresh(await api.setPlayerValue(r, c, appState.selectedValue));
      }
    }
  }
  showInspector(r, c);
}

// ── Inspector display ──────────────────────────────────────────────────
function showInspector(r, c) {
  const key = cellKey(r, c);
  const sym = appState.puzzle?.symbols?.[`c:${key}`];  // use prefixed key
  const pv  = appState.puzzle?.player_values?.[key];
  document.getElementById('inspector').innerHTML = `
    <div style="font-family:'DM Mono',monospace;margin-bottom:4px;color:var(--accent2)">Cell (${r}, ${c})</div>
    <div class="inspector-row"><span class="lbl">Given:</span> <span class="val" style="color:var(--accent)">${sym ? `${sym.symbol_type} = ${sym.value ?? ''}` : '—'}</span></div>
    <div class="inspector-row"><span class="lbl">Player val:</span> <span class="val" style="color:var(--success)">${pv !== undefined && pv !== null ? pv : '—'}</span></div>
  `;
}

// ── Mode switching ─────────────────────────────────────────────────────
function setMode(m) {
  appState.update({ mode: m, activeTool: m === 'edit' ? 'draw-line' : 'place-symbol', placementTarget: 'cell' });
  playbackReset();
}

// ── Tool selection ─────────────────────────────────────────────────────
function setTool(t) {
  appState.update({ activeTool: t });
  if (t === 'erase-symbol') {
    appState.update({ eraseMode: true });
  } else if (t === 'place-symbol') {
    // do not turn off eraseMode here; palette selection will handle it
  }
}

// ── Palette UI wiring ──────────────────────────────────────────────────
document.getElementById('symbol-palette').addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const v = parseInt(btn.dataset.value);
  if (!isNaN(v)) selectPaletteValue(v);
});

document.getElementById('palette-custom-input').addEventListener('input', (e) => {
  onCustomPaletteInput(e.target.value);
});

document.getElementById('palette-erase-btn').addEventListener('click', selectErase);

// ── Endpoint palette events ──────────────────────────────────────
document.getElementById('endpoint-palette').addEventListener('click', (e) => {
  const btn = e.target.closest('.ep-color-btn');
  if (!btn) return;
  const colorId = parseInt(btn.dataset.colorId);
  if (!isNaN(colorId)) selectEndpointColor(colorId);
});

document.getElementById('ep-role-start').addEventListener('click', () => selectEndpointRole('start'));
document.getElementById('ep-role-end').addEventListener('click', () => selectEndpointRole('end'));
document.getElementById('ep-role-both').addEventListener('click', () => selectEndpointRole('both'));

// ── Placement target buttons ────────────────────────────────────────
document.getElementById('target-cell').addEventListener('click', () => {
  appState.update({ placementTarget: 'cell' });
  if (appState.mode === 'edit') {
    setTool(appState.eraseMode ? 'erase-symbol' : 'place-symbol');
  }
});

document.getElementById('target-vertex').addEventListener('click', () => {
  appState.update({ placementTarget: 'vertex' });
  if (appState.mode === 'edit') {
    setTool(appState.eraseMode ? 'erase-symbol' : 'place-symbol');
  }
});

document.getElementById('target-edge').addEventListener('click', () => {
  appState.update({ placementTarget: 'edge' });
  if (appState.mode === 'edit') {
    setTool(appState.eraseMode ? 'erase-symbol' : 'place-symbol');
  }
});

// ── Tool buttons ───────────────────────────────────────────────────────
document.getElementById('tool-add-cell').addEventListener('click', () => setTool('add-cell'));
document.getElementById('tool-remove-cell').addEventListener('click', () => setTool('remove-cell'));
document.getElementById('tool-draw-line').addEventListener('click', () => setTool('draw-line'));
document.getElementById('tool-erase-line').addEventListener('click', () => setTool('erase-line'));

// ── Mode buttons ───────────────────────────────────────────────────────
document.getElementById('btn-edit').addEventListener('click', () => setMode('edit'));
document.getElementById('btn-play').addEventListener('click', () => setMode('play'));

// ── Quick grid ─────────────────────────────────────────────────────────
document.getElementById('make-rect-btn').addEventListener('click', async () => {
  const rows = parseInt(document.getElementById('dim-rows').value) || 4;
  const cols = parseInt(document.getElementById('dim-cols').value) || 4;
  const newState = {
    grid: { cells: [] },
    symbols: {},
    rules: [],
    player_values: {},
    metadata: {}
  };
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) newState.grid.cells.push([r, c]);
  refresh(await api.loadState(newState));
});

// ── Import / Export ────────────────────────────────────────────────────
document.getElementById('export-btn').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(appState.puzzle, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'puzzle.json';
  a.click();
});

document.getElementById('import-btn').addEventListener('click', () => {
  document.getElementById('import-file').click();
});

document.getElementById('import-file').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (ev) => {
    try {
      const parsed = JSON.parse(ev.target.result);
      refresh(await api.loadState(parsed.state || parsed));
    } catch (err) {
      alert('Invalid JSON: ' + err.message);
    }
  };
  reader.readAsText(file);
  e.target.value = '';
});

// ── Clear all player values ────────────────────────────────────────────
document.getElementById('clear-values-btn').addEventListener('click', async () => {
  refresh(await api.clearAllPlayerValues());
  playbackReset();
});

document.getElementById('clear-all-play-btn').addEventListener('click', async () => {
  refresh(await api.clearAllPlayerValues());
  playbackReset();
});

// ── Validate ───────────────────────────────────────────────────────────
document.getElementById('validate-btn').addEventListener('click', async () => {
  const result = await api.validate();
  if (appState.puzzle) {
    const updated = { ...appState.puzzle, violations: result.violations, is_solved: result.is_solved };
    refresh(updated);
  }
  if (result.is_solved) alert('🎉 Puzzle solved! All rules satisfied.');
});

// ── SVG interaction (click for cells, vertices, edges, lines) ──────────
document.getElementById('grid-svg').addEventListener('click', async (e) => {
  // If we clicked a line element while in erase-line mode, handle that first
  const line = e.target.closest('line[data-line-from-row]');
  if (line && appState.mode === 'edit' && appState.activeTool === 'erase-line') {
    const fromRow = parseInt(line.dataset.lineFromRow);
    const fromCol = parseInt(line.dataset.lineFromCol);
    const toRow = parseInt(line.dataset.lineToRow);
    const toCol = parseInt(line.dataset.lineToCol);
    if (!isNaN(fromRow) && !isNaN(toRow)) {
      api.removeLineSegment(fromRow, fromCol, toRow, toCol)
        .then(() => api.getState())
        .then(refresh);
      return;
    }
  }

  // Vertex click
  const vertexEl = e.target.closest('[data-vertex-row]');
  if (vertexEl && appState.mode === 'edit') {
    const vr = parseInt(vertexEl.dataset.vertexRow);
    const vc = parseInt(vertexEl.dataset.vertexCol);
    if (appState.eraseMode) {
      refresh(await api.removeVertexSymbol(vr, vc));
    } else if (appState.activeTool === 'place-symbol' && appState.placementTarget === 'vertex') {
      if (appState.paletteType === 'endpoint') {
        refresh(await api.placeVertexSymbol(vr, vc, 'endpoint', {
          role: appState.endpointRole,
          color_id: appState.endpointColorId
        }));
      } else {
        refresh(await api.placeVertexSymbol(vr, vc, 'number', { value: appState.selectedValue }));
      }
    }
    return;
  }

  // Edge click
  const edgeEl = e.target.closest('[data-edge-from-row]');
  if (edgeEl && appState.mode === 'edit') {
    const fr = parseInt(edgeEl.dataset.edgeFromRow);
    const fc = parseInt(edgeEl.dataset.edgeFromCol);
    const tr = parseInt(edgeEl.dataset.edgeToRow);
    const tc = parseInt(edgeEl.dataset.edgeToCol);
    if (appState.eraseMode) {
      refresh(await api.removeEdgeSymbol(fr, fc, tr, tc));
    } else if (appState.activeTool === 'place-symbol' && appState.placementTarget === 'edge') {
      if (appState.paletteType === 'endpoint') {
        refresh(await api.placeEdgeSymbol(fr, fc, tr, tc, 'endpoint', {
          role: appState.endpointRole,
          color_id: appState.endpointColorId
        }));
      } else {
        refresh(await api.placeEdgeSymbol(fr, fc, tr, tc, 'number', { value: appState.selectedValue }));
      }
    }
    return;
  }

  // Cell click: try to get row/col from data-* attributes on a rect
  const rect = e.target.closest('rect[data-row]');
  if (rect) {
    const r = parseInt(rect.dataset.row);
    const c = parseInt(rect.dataset.col);
    if (!isNaN(r) && !isNaN(c)) {
      onCellClick(r, c);
      return;
    }
  }

  // Fallback to coordinate-based lookup (for ghost cells or background clicks)
  const [x, y] = eventToSvgPos(e);
  const cell = svgPosToCell(x, y);
  if (cell) onCellClick(cell[0], cell[1]);
});

// Right-click to remove symbol (edit mode only, on active cells)
document.getElementById('grid-svg').addEventListener('contextmenu', async (e) => {
  e.preventDefault();  // suppress browser context menu

  if (appState.mode !== 'edit') return;

  // Try to get cell from a rect element under the cursor
  const rect = e.target.closest('rect[data-row]');
  let r, c;
  if (rect) {
    r = parseInt(rect.dataset.row);
    c = parseInt(rect.dataset.col);
  } else {
    // Fallback to coordinate lookup
    const [x, y] = eventToSvgPos(e);
    const cell = svgPosToCell(x, y);
    if (!cell) return;
    [r, c] = cell;
  }

  const key = cellKey(r, c);
  const isActive = (appState.puzzle?.grid?.cells || []).some(
    ([cr, cc]) => cr === r && cc === c
  );
  const symKey = `c:${key}`;
  if (isActive && appState.puzzle?.symbols?.[symKey]) {
    refresh(await api.removeSymbol(r, c));
  }
});

// Hover inspector via mousemove
document.getElementById('grid-svg').addEventListener('mousemove', (e) => {
  const rect = e.target.closest('rect[data-row]');
  if (rect) {
    const r = parseInt(rect.dataset.row);
    const c = parseInt(rect.dataset.col);
    if (!isNaN(r) && !isNaN(c)) {
      showInspector(r, c);
      return;
    }
  }
  // Fallback coordinate lookup for hover
  const [x, y] = eventToSvgPos(e);
  const cell = svgPosToCell(x, y);
  if (cell && appState.puzzle) {
    const [r, c] = cell;
    const isActive = (appState.puzzle.grid?.cells || []).some(([cr, cc]) => cr === r && cc === c);
    if (isActive) showInspector(r, c);
  }
});

// ── Rules UI ───────────────────────────────────────────────────────────
function buildRuleSelect() {
  const sel = document.getElementById('rule-type-select');
  sel.innerHTML = (appState.rulesSchema || []).map(r =>
    `<option value="${r.rule_type}">${r.rule_type}</option>`
  ).join('');
  onRuleTypeChange();
}

function onRuleTypeChange() {
  const sel = document.getElementById('rule-type-select');
  const schema = (appState.rulesSchema || []).find(r => r.rule_type === sel.value);
  const desc = document.getElementById('rule-schema-desc');
  const area = document.getElementById('rule-params-area');
  desc.textContent = schema?.description || '';
  if (!schema?.param_schema || !Object.keys(schema.param_schema).length) {
    area.innerHTML = '';
    return;
  }
  area.innerHTML = Object.entries(schema.param_schema).map(([k, v]) => `
    <div class="param-row">
      <label>${k}</label>
      <input type="text" id="param-${k}" placeholder="${v.description || ''}" value="${v.default !== undefined && v.default !== null ? v.default : ''}" title="${v.description || ''}">
    </div>
  `).join('');
}

document.getElementById('rule-type-select').addEventListener('change', onRuleTypeChange);

document.getElementById('add-rule-btn').addEventListener('click', async () => {
  const sel = document.getElementById('rule-type-select');
  const schema = (appState.rulesSchema || []).find(r => r.rule_type === sel.value);
  const params = {};
  if (schema?.param_schema) {
    for (const [k] of Object.entries(schema.param_schema)) {
      const el = document.getElementById(`param-${k}`);
      if (!el) continue;
      const raw = el.value.trim();
      if (raw === '' || raw === 'null') { params[k] = null; continue; }
      if (/^-?\d+$/.test(raw)) { params[k] = parseInt(raw); }
      else { try { params[k] = JSON.parse(raw); } catch { params[k] = raw; } }
    }
  }
  refresh(await api.addRule(sel.value, params));
});

function renderRulesList() {
  const el = document.getElementById('rules-list');
  const rules = appState.puzzle?.rules || [];
  if (!rules.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--muted)">No rules yet.</div>';
    return;
  }
  el.innerHTML = rules.map((r, i) => `
    <div class="rule-item">
      <div class="rule-label">
        <div class="rule-type-badge">${r.rule_type}</div>
        <div class="rule-description">${r.description || JSON.stringify(r.params)}</div>
      </div>
      <button class="rule-del" data-index="${i}" title="Remove rule">✕</button>
    </div>
  `).join('');
  el.querySelectorAll('.rule-del').forEach(btn => {
    btn.addEventListener('click', async () => {
      const i = parseInt(btn.dataset.index);
      refresh(await api.removeRule(i));
    });
  });
}

// ── Violations ─────────────────────────────────────────────────────────
function renderViolations() {
  const el = document.getElementById('violations-list');
  const viols = appState.puzzle?.violations || [];
  if (!viols.length) {
    el.innerHTML = appState.puzzle?.is_solved
      ? '<div class="ok-badge">✓ No violations</div>'
      : '<div style="font-size:12px;color:var(--muted)">—</div>';
    return;
  }
  el.innerHTML = viols.map(v => `<div class="viol-item">⚠ ${v.message}</div>`).join('');
}

// ── Status bar ─────────────────────────────────────────────────────────
function updateStatus() {
  const puzzle = appState.puzzle;
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');
  const viols = puzzle?.violations || [];
  document.getElementById('status-cells').textContent = puzzle?.grid?.cells?.length ?? 0;
  document.getElementById('status-rules').textContent = puzzle?.rules?.length ?? 0;
  if (!puzzle?.rules?.length) { dot.className = 'dot'; txt.textContent = 'No rules'; }
  else if (viols.length)      { dot.className = 'dot red'; txt.textContent = `${viols.length} violation(s)`; }
  else if (puzzle?.is_solved) { dot.className = 'dot green'; txt.textContent = 'Solved ✓'; }
  else                         { dot.className = 'dot purple'; txt.textContent = 'In progress'; }
}

// ── Collapse toggles ───────────────────────────────────────────────────
document.querySelectorAll('.collapse-header').forEach(header => {
  header.addEventListener('click', () => {
    const targetId = header.id.replace('-collapse-header', '-body');
    const body = document.getElementById(targetId);
    if (!body) return;
    const isOpen = !body.classList.contains('closed');
    body.classList.toggle('closed', isOpen);
    const arrow = document.getElementById(targetId.replace('-body', '-arrow'));
    if (arrow) arrow.textContent = isOpen ? '▼' : '▲';
  });
});

// ── Solver ─────────────────────────────────────────────────────────────
document.getElementById('run-solver-btn').addEventListener('click', async () => {
  playbackReset();
  const maxSols = document.getElementById('solver-max').value;
  const result = await api.solve('', maxSols);   // domain is ignored by the server now
  appState.update({ solveResult: result });

  document.getElementById('solve-stats').innerHTML = `
    <div class="solve-stat"><span class="lbl">Has solution</span>
      <span class="val ${result.has_solution ? 'yes' : 'no'}">${result.has_solution ? 'Yes' : 'No'}</span></div>
    <div class="solve-stat"><span class="lbl">Solutions found</span>
      <span class="val ${result.solution_count === 1 ? 'unique' : ''}">${result.solution_count}${result.solution_count >= parseInt(maxSols) ? '+' : ''}</span></div>
    <div class="solve-stat"><span class="lbl">Unique</span>
      <span class="val ${result.is_unique ? 'unique' : 'no'}">${result.is_unique ? 'Yes ✓' : 'No'}</span></div>
    <div class="solve-stat"><span class="lbl">Nodes searched</span>
      <span class="val">${result.searched_nodes.toLocaleString()}</span></div>
  `;

  const solveResDiv = document.getElementById('solve-result');
  solveResDiv.style.display = 'block';   // always show result panel

  // Show solution lines if they exist
  const linesListDiv = document.getElementById('solution-lines');
  if (result.lines && result.lines.length > 0) {
    linesListDiv.innerHTML = `<h3 style="font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:4px">Solution Lines</h3>
      <ol style="margin:0;padding-left:18px;font-size:11px;">
        ${result.lines.map(([a, b]) => `<li>(${a[0]},${a[1]}) ↔ (${b[0]},${b[1]})</li>`).join('')}
      </ol>`;
    linesListDiv.style.display = 'block';
  } else {
    linesListDiv.style.display = 'none';
  }

  // If there's a solve path (cell assignments), we still show playback, but now it's unused.
  // We'll hide playback controls entirely since the solver no longer gives cell paths.
  document.getElementById('solve-path-controls').style.display = 'none';
});

function renderSolvePath(path) {
  document.getElementById('solve-path-list').innerHTML = path.map((step, i) => `
    <div class="solve-step" id="step-${i}">${i + 1}. (${step.cell[0]},${step.cell[1]}) ← <b>${step.value}</b></div>
  `).join('');
  document.getElementById('path-slider').max = path.length - 1;
  document.getElementById('path-slider').value = path.length - 1;
  document.getElementById('step-counter').textContent = `${path.length} / ${path.length}`;
  document.querySelectorAll('.solve-step').forEach(el => {
    el.addEventListener('click', () => setPlaybackStep(parseInt(el.id.split('-')[1])));
  });
}

function setPlaybackStep(idx) {
  const result = appState.solveResult;
  if (!result?.solve_path?.length) return;
  const path = result.solve_path;
  idx = Math.max(0, Math.min(idx, path.length - 1));
  appState.update({ playbackIdx: idx });
  document.getElementById('path-slider').value = idx;
  document.getElementById('step-counter').textContent = `${idx + 1} / ${path.length}`;
  document.querySelectorAll('.solve-step').forEach((el, i) => el.classList.toggle('current', i === idx));

  const overlay = {};
  path.slice(0, idx + 1).forEach(step => {
    overlay[cellKey(step.cell[0], step.cell[1])] = step.value;
  });
  appState.update({ solveOverlay: overlay });
}

function playbackReset() {
  appState.update({ playbackIdx: -1, solveOverlay: {}, solveResult: null });
  document.getElementById('solve-path-list').innerHTML = '';
  document.getElementById('solve-result').style.display = 'none';
  document.getElementById('step-counter').textContent = '0 / 0';
}

document.getElementById('playback-prev').addEventListener('click', () => {
  const cur = appState.playbackIdx < 0 ? (appState.solveResult?.solve_path?.length || 0) - 1 : appState.playbackIdx;
  setPlaybackStep(cur - 1);
});
document.getElementById('playback-next').addEventListener('click', () => {
  const cur = appState.playbackIdx < 0 ? (appState.solveResult?.solve_path?.length || 0) - 1 : appState.playbackIdx;
  setPlaybackStep(cur + 1);
});
document.getElementById('playback-reset').addEventListener('click', playbackReset);
document.getElementById('path-slider').addEventListener('input', (e) => {
  setPlaybackStep(parseInt(e.target.value));
});

// ── Boot ────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  load().then(() => {
    // After first render, attach line‑drawing events to the SVG
    initLineDrawing(document.getElementById('grid-svg'));
  });
});