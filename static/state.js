/**
 * state.js
 * Central reactive store for all UI state.
 * Modules import { appState } and call appState.update() to change state,
 * which triggers registered listeners.
 */

const _listeners = [];

export const appState = {
  // ── Server-synced ──────────────────────────────────────────
  puzzle: null,
  // ── Controls ────────────────────────────────────────────────
  dragState: null,
  // ── Editor ─────────────────────────────────────────────────
  mode: 'edit',
  activeTool: 'draw-line',
  // ── Palette ────────────────────────────────────────────────
  selectedValue: 1,
  eraseMode: false,
  paletteType: 'number',
  // ── Endpoint placement (edit mode) ─────────────────────────
  endpointRole: 'start',
  endpointColorId: 0,
  placementTarget: 'cell',
  symbolsSchema: [],
  // ── Solver playback ────────────────────────────────────────
  solveResult: null,
  playbackIdx: -1,
  solveOverlay: {},
  solveLines: null,            
  // ── Rule schema from server ────────────────────────────────
  rulesSchema: [],

  update(patch) {
    Object.assign(this, patch);
    _listeners.forEach(fn => fn(this));
  },

  subscribe(fn) {
    _listeners.push(fn);
    return () => {
      const i = _listeners.indexOf(fn);
      if (i >= 0) _listeners.splice(i, 1);
    };
  },
};