/* state.js — Central application state */
(function () {
  'use strict';

  window.App = window.App || {};

  const MODES = ['select', 'add-vertex', 'add-edge', 'delete'];

  const state = {
    /* Current interaction mode */
    mode: 'select',

    /* Full graph data from backend */
    graphData: { vertices: [], edges: [], faces: [] },

    /* Hover / selection */
    hovered:  null,   // { type: 'vertex'|'edge'|'face', id: number }
    selected: null,   // { type: 'vertex'|'edge'|'face', id: number }

    /* Add-edge mode: first vertex selected */
    edgeSource: null, // vertex id (number) or null

    /* Lookup maps — rebuilt when graphData changes */
    vertexMap: {},  // vid → vertex object
    edgeMap:   {},  // eid → edge object
    faceMap:   {},  // fid → face object

    /* ── Setters ─────────────────────────────────────────────────── */

    setMode(m) {
      if (!MODES.includes(m)) return;
      this.mode = m;
      this.edgeSource = null;
      this.hovered = null;
      this._emit('mode');
    },

    setGraphData(data) {
      this.graphData = data;
      this.vertexMap = Object.fromEntries(data.vertices.map(v => [v.id, v]));
      this.edgeMap   = Object.fromEntries(data.edges.map(e => [e.id, e]));
      this.faceMap   = Object.fromEntries(data.faces.map(f => [f.id, f]));
      this._emit('graph');
    },

    setHovered(h) {
      const prev = this.hovered;
      this.hovered = h;
      if (JSON.stringify(prev) !== JSON.stringify(h)) this._emit('hover');
    },

    setSelected(s) {
      this.selected = s;
      this._emit('select');
    },

    setEdgeSource(vid) {
      this.edgeSource = vid;
      this._emit('edgesource');
    },

    /* ── Event bus ───────────────────────────────────────────────── */

    _listeners: {},

    on(event, fn) {
      this._listeners[event] = this._listeners[event] || [];
      this._listeners[event].push(fn);
    },

    _emit(event) {
      (this._listeners[event] || []).forEach(fn => fn());
    },
  };

  window.App.state = state;
})();
