/**
 * palette.js
 * Unified palette: numbers + endpoint colours/role are all symbols.
 * In edit mode it places the selected symbol; in play mode it picks a value.
 */

import { PALETTE_DEFAULTS, ENDPOINT_COLORS } from './constants.js';
import { appState }  from './state.js';

// ── Number buttons ─────────────────────────────────────────────────────────

export function buildNumberPalette() {
  const container = document.getElementById('symbol-palette');
  if (!container) return;
  container.innerHTML = PALETTE_DEFAULTS.map(v => `
    <button class="palette-btn ${v === appState.selectedValue && !appState.eraseMode && appState.paletteType === 'number' ? 'selected' : ''}"
            id="palette-btn-${v}"
            data-value="${v}">${v}</button>
  `).join('');
}

export function selectPaletteValue(v) {
  appState.update({ selectedValue: v, eraseMode: false, paletteType: 'number' });
  document.getElementById('palette-erase-btn')?.classList.remove('selected');
  document.querySelectorAll('.palette-btn').forEach(b => b.classList.remove('selected'));
  document.getElementById(`palette-btn-${v}`)?.classList.add('selected');
  // deselect any endpoint colour
  document.querySelectorAll('.ep-color-btn').forEach(b => b.classList.remove('selected'));

  if (PALETTE_DEFAULTS.includes(v)) {
    const inp = document.getElementById('palette-custom-input');
    if (inp) inp.value = '';
  }

  switchToPlaceTool();
  updateToolbarBadge();
}

export function onCustomPaletteInput(raw) {
  const v = parseInt(raw, 10);
  if (isNaN(v)) return;
  appState.update({ selectedValue: v, eraseMode: false, paletteType: 'number' });
  document.getElementById('palette-erase-btn')?.classList.remove('selected');
  document.querySelectorAll('.palette-btn').forEach(b => b.classList.remove('selected'));
  document.querySelectorAll('.ep-color-btn').forEach(b => b.classList.remove('selected'));
  switchToPlaceTool();
  updateToolbarBadge();
}

// ── Endpoint colour / role ─────────────────────────────────────────────────

export function buildEndpointPalette() {
  const container = document.getElementById('endpoint-palette');
  if (!container) return;

  container.innerHTML = ENDPOINT_COLORS.map((color, i) => `
    <button class="ep-color-btn ${i === appState.endpointColorId && appState.paletteType === 'endpoint' && !appState.eraseMode ? 'selected' : ''}"
            data-color-id="${i}"
            style="background:${color}; border-color:${color}">
      ${i}
    </button>
  `).join('');

  updateEndpointRoleUI();
}

function updateEndpointRoleUI() {
  document.getElementById('ep-role-start')?.classList.toggle('active', appState.endpointRole === 'start');
  document.getElementById('ep-role-end')?.classList.toggle('active',   appState.endpointRole === 'end');
}

export function selectEndpointColor(colorId) {
  appState.update({ endpointColorId: colorId, paletteType: 'endpoint', eraseMode: false });
  document.getElementById('palette-erase-btn')?.classList.remove('selected');
  document.querySelectorAll('.palette-btn').forEach(b => b.classList.remove('selected'));
  document.querySelectorAll('.ep-color-btn').forEach(b => {
    b.classList.toggle('selected', parseInt(b.dataset.colorId) === colorId);
  });
  switchToPlaceTool();
  updateToolbarBadge();
}

export function selectEndpointRole(role) {
  appState.update({ endpointRole: role });
  updateEndpointRoleUI();
}

// ── Erase mode ─────────────────────────────────────────────────────────────

export function selectErase() {
  appState.update({ eraseMode: true, paletteType: 'number' });
  document.getElementById('palette-erase-btn')?.classList.add('selected');
  document.querySelectorAll('.palette-btn').forEach(b => b.classList.remove('selected'));
  document.querySelectorAll('.ep-color-btn').forEach(b => b.classList.remove('selected'));
  const inp = document.getElementById('palette-custom-input');
  if (inp) inp.value = '';
  if (appState.mode === 'edit') {
    const lineTools = ['draw-line', 'erase-line'];
    if (!lineTools.includes(appState.activeTool)) {
      appState.update({ activeTool: 'erase-symbol' });
      syncToolButtons();
    }
  }
  updateToolbarBadge();
}

// ── Helper ─────────────────────────────────────────────────────────────────

function switchToPlaceTool() {
  // Only switch if we are in edit mode and NOT already using a line tool
  if (appState.mode !== 'edit') return;
  const lineTools = ['draw-line', 'erase-line'];
  if (lineTools.includes(appState.activeTool)) return;   // leave line tool alone
  if (appState.activeTool !== 'place-symbol') {
    appState.update({ activeTool: 'place-symbol' });
    syncToolButtons();
  }
}
// ── Tool button sync (for edit tools) ─────────────────────────────────────

export function syncToolButtons() {
  const tool = appState.activeTool;
  ['add-cell', 'remove-cell', 'draw-line', 'erase-line'].forEach(id => {
    document.getElementById(`tool-${id}`)?.classList.toggle('active', id === tool);
  });
}

// ── Toolbar badge ──────────────────────────────────────────────────────────

export function updateToolbarBadge() {
  const badge   = document.getElementById('toolbar-val-badge');
  const numEl   = document.getElementById('toolbar-val-num');
  const toolLbl = document.getElementById('toolbar-tool-label');
  if (!badge || !numEl || !toolLbl) return;

  const { mode, activeTool, eraseMode, selectedValue, paletteType, endpointRole, endpointColorId } = appState;

  if (mode === 'edit') {
    if (activeTool === 'add-cell')      { badge.style.display='none'; toolLbl.textContent='Add Cell'; }
    else if (activeTool === 'remove-cell') { badge.style.display='none'; toolLbl.textContent='Delete Cell'; }
    else if (activeTool === 'draw-line')   { badge.style.display='none'; toolLbl.textContent='Draw Line'; }
    else if (activeTool === 'erase-line')  { badge.style.display='none'; toolLbl.textContent='Erase Line'; }
    else if (activeTool === 'place-symbol') {
      badge.style.display = '';
      if (paletteType === 'endpoint') {
        const roleLetter = endpointRole === 'start' ? 'S' : 'E';
        numEl.textContent = `${roleLetter}${endpointColorId}`;
        toolLbl.textContent = 'Place Symbol';
      } else {
        numEl.textContent = selectedValue;
        toolLbl.textContent = 'Place Symbol';
      }
    }
    else if (activeTool === 'erase-symbol') { badge.style.display='none'; toolLbl.textContent='Erase Symbol'; }
    else { badge.style.display='none'; toolLbl.textContent=activeTool; }
  } else {
    // play mode – only numbers matter
    if (activeTool === 'draw-line')  { badge.style.display='none'; toolLbl.textContent='Draw Line'; }
    else if (activeTool === 'erase-line') { badge.style.display='none'; toolLbl.textContent='Erase Line'; }
    else if (eraseMode) { badge.style.display='none'; toolLbl.textContent='Erase Value'; }
    else {
      badge.style.display = '';
      numEl.textContent = selectedValue;
      toolLbl.textContent = 'Set Value';
    }
  }
}