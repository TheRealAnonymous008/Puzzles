/**
 * constants.js
 * Shared layout and domain constants used across modules.
 */

export const CELL_SIZE   = 58;
export const CELL_RADIUS = 8;
export const PADDING     = 60;   // SVG padding so ghost border cells are never clipped
export const GHOST_EXTRA = 1;    // How many cells beyond the bounding box to show ghosts

export const PALETTE_DEFAULTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0];

// Color palette for endpoint (Start/End) symbols — indexed by color_id
export const ENDPOINT_COLORS = [
  '#ef4444', // 0 red
  '#3b82f6', // 1 blue
  '#22c55e', // 2 green
  '#f59e0b', // 3 amber
  '#a855f7', // 4 purple
  '#ec4899', // 5 pink
  '#06b6d4', // 6 cyan
  '#f97316', // 7 orange
  '#84cc16', // 8 lime
  '#14b8a6', // 9 teal
];