/* main.js — App initialisation */
(function () {
  'use strict';

  const { state, api, canvas } = window.App;

  async function boot() {
    // Initialise canvas (sets up SVG, events)
    canvas.init();

    // Load initial graph state
    try {
      const data = await api.getGraph();
      state.setGraphData(data);
    } catch (err) {
      console.error('Failed to load initial graph:', err);
    }

    // Trigger mode render to set initial toolbar state
    state._emit('mode');
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
