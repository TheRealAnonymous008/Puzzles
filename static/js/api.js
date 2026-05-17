/* api.js — All backend fetch calls */
(function () {
  'use strict';

  window.App = window.App || {};

  const BASE = '/api';

  async function request(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  window.App.api = {
    getGraph:    ()              => request('GET',    '/graph'),
    resetGraph:  ()              => request('POST',   '/reset'),
    addVertex:   (x, y)         => request('POST',   '/vertices', { x, y }),
    removeVertex:(vid)           => request('DELETE', `/vertices/${vid}`),
    addEdge:     (u_id, v_id)   => request('POST',   '/edges', { u_id, v_id }),
    removeEdge:  (eid)           => request('DELETE', `/edges/${eid}`),
    insertGrid:  (rows, cols, spacing, origin_x, origin_y) =>
      request('POST', '/templates/grid', { rows, cols, spacing, origin_x, origin_y }),
  };
})();
