/**
 * state.js
 * Central reactive store for all UI state.
 * Modules import { appState } and call appState.update() to change state,
 * which triggers registered listeners.
 */

const _listeners = [];

export const appState = {
  // ── Server-synced ──────────────────────────────────────────
  puzzle: null,          // Full puzzle state from server
  // ── Controls ────────────────────────────────────────────────
  dragState: null,   // line drawing preview: { path: [[r,c],...], usedKeys: Set } or null
  // ── Editor ─────────────────────────────────────────────────
  mode: 'edit',          // 'edit' | 'play'
  activeTool: 'add-cell', // 'add-cell' | 'remove-cell' | 'place-symbol' | 'erase-symbol' | 'draw-line' | 'erase-line'

  // ── Palette ────────────────────────────────────────────────
  selectedValue: 1,       // Currently chosen palette number
  eraseMode: false,       // true = palette is in symbol-erase mode
  paletteType: 'number',  // 'number' | 'endpoint'

  // ── Endpoint placement (edit mode) ─────────────────────────
  endpointRole: 'start',  // 'start' | 'end'
  endpointColorId: 0,     // integer color index

  // ── Placement target (new) ─────────────────────────────────
  placementTarget: 'cell', // 'cell' | 'vertex' | 'edge'

  // ── Solver playback ────────────────────────────────────────
  solveResult: null,
  playbackIdx: -1,        // -1 = show full solution; >=0 = step index
  solveOverlay: {},       // cellKey -> value  (highlighted cells from solver)

  // ── Rule schema from server ────────────────────────────────
  rulesSchema: [],

  /**
   * Update one or more state keys and notify all listeners.
   * @param {Object} patch - plain object with keys to update
   */
  update(patch) {
    Object.assign(this, patch);
    _listeners.forEach(fn => fn(this));
  },

  /**
   * Register a listener function called whenever state changes.
   * Returns an unsubscribe function.
   */
  subscribe(fn) {
    _listeners.push(fn);
    return () => {
      const i = _listeners.indexOf(fn);
      if (i >= 0) _listeners.splice(i, 1);
    };
  },
};