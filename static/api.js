/**
 * api.js
 * Thin wrapper around fetch for all server communication.
 * Every function returns the parsed JSON response.
 */

async function _fetch(url, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return res.json();
}

export const api = {
  // ── State ──────────────────────────────────────────────────
  getState:   ()           => _fetch('/api/state'),
  loadState:  (state)      => _fetch('/api/load', 'POST', { state }),
  exportState: ()          => _fetch('/api/export'),

  // ── Grid ───────────────────────────────────────────────────
  addCell:    (row, col)   => _fetch('/api/grid/add_cell',    'POST', { row, col }),
  removeCell: (row, col)   => _fetch('/api/grid/remove_cell', 'POST', { row, col }),

  // ── Symbols ────────────────────────────────────────────────
  symbolsRegistry: ()      => _fetch('/api/symbols/registry'),
  placeSymbol: (row, col, symbol_type, params) =>
    _fetch('/api/symbol/place', 'POST', { row, col, symbol_type, ...params }),
  removeSymbol: (row, col) => _fetch('/api/symbol/remove', 'POST', { row, col }),

  // ── Rules ──────────────────────────────────────────────────
  rulesRegistry: ()                    => _fetch('/api/rules/registry'),
  addRule:    (rule_type, params)      => _fetch('/api/rule/add',    'POST', { rule_type, params }),
  removeRule: (index)                  => _fetch('/api/rule/remove', 'POST', { index }),

  // ── Player values ──────────────────────────────────────────
  setPlayerValue:   (row, col, value)  => _fetch('/api/player/set_value',   'POST', { row, col, value }),
  clearPlayerValue: (row, col)         => _fetch('/api/player/clear_value', 'POST', { row, col }),
  clearAllPlayerValues: ()             => _fetch('/api/player/clear_all',   'POST', {}),
  validate: ()                         => _fetch('/api/player/validate',     'POST', {}),

  // ── Lines ──────────────────────────────────────────────────
  addLineSegment: (from_row, from_col, to_row, to_col) =>
    _fetch('/api/lines/add_segment',    'POST', { from_row, from_col, to_row, to_col }),
  removeLineSegment: (from_row, from_col, to_row, to_col) =>
    _fetch('/api/lines/remove_segment', 'POST', { from_row, from_col, to_row, to_col }),
  clearLines: ()  => _fetch('/api/lines/clear', 'POST', {}),

  // ── Solver ─────────────────────────────────────────────────
  solve: (domain, maxSolutions) =>
    _fetch(`/api/solve?domain=${encodeURIComponent(domain)}&max_solutions=${maxSolutions}`),
};