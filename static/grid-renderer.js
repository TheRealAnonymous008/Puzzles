/**
 * grid-renderer.js
 * Responsible for building the SVG representation of the puzzle grid.
 * No inline event handlers – interaction is handled via delegation in main.js.
 */

import { CELL_SIZE, CELL_RADIUS, PADDING, GHOST_EXTRA, ENDPOINT_COLORS } from './constants.js';
import { appState } from './state.js';

// ── Coordinate helpers ──────────────────────────────────────────────────────

/** Convert grid column index to SVG x of cell top‑left. */
function cx(col, gMinC) {
  return PADDING + (col - gMinC) * CELL_SIZE;
}

/** Convert grid row index to SVG y of cell top‑left. */
function cy(row, gMinR) {
  return PADDING + (row - gMinR) * CELL_SIZE;
}

/** Cell center x. */
function ccx(col, gMinC) { return cx(col, gMinC) + CELL_SIZE / 2; }

/** Cell center y. */
function ccy(row, gMinR) { return cy(row, gMinR) + CELL_SIZE / 2; }

export function cellKey(r, c) { return `${r},${c}`; }

// ── Bounding‑box calculation ───────────────────────────────────────────────

function computeBounds(cells) {
  if (!cells.length) {
    // Default seed area so there's always somewhere to click on an empty grid
    return { minR: 0, minC: 0, maxR: 2, maxC: 2 };
  }
  return {
    minR: Math.min(...cells.map(([r]) => r)),
    minC: Math.min(...cells.map(([, c]) => c)),
    maxR: Math.max(...cells.map(([r]) => r)),
    maxC: Math.max(...cells.map(([, c]) => c)),
  };
}

// ── Edge helper ────────────────────────────────────────────────────────────

/**
 * Returns { x1, y1, x2, y2 } for the shared edge line between two
 * orthogonally adjacent cells. The line runs exactly along the border.
 */
function edgeCoords(r1, c1, r2, c2, gMinR, gMinC) {
  if (r1 === r2) {
    // Horizontal adjacency → vertical edge
    const colL = Math.min(c1, c2);
    const x = cx(colL, gMinC) + CELL_SIZE;
    const y1 = cy(r1, gMinR);
    const y2 = y1 + CELL_SIZE;
    return { x1: x, y1, x2: x, y2 };
  } else {
    // Vertical adjacency → horizontal edge
    const rowTop = Math.min(r1, r2);
    const y = cy(rowTop, gMinR) + CELL_SIZE;
    const x1 = cx(c1, gMinC);
    const x2 = x1 + CELL_SIZE;
    return { x1, y1: y, x2, y2: y };
  }
}

// ── Vertex helpers ─────────────────────────────────────────────────────────

/**
 * Convert a vertex (row, col) in grid‑intersection coordinates to SVG point.
 * Vertex (r,c) corresponds to the top‑left corner of cell (r,c).
 */
function vertexToSvg(vr, vc, gMinR, gMinC) {
  return {
    x: cx(vc, gMinC),
    y: cy(vr, gMinR)
  };
}

/**
 * Given SVG coordinates, return the nearest grid vertex [vr, vc].
 */
export function svgPosToVertex(svgX, svgY) {
  const svg = document.getElementById('grid-svg');
  if (!svg) return null;
  const gMinR = svg._gMinR ?? 0;
  const gMinC = svg._gMinC ?? 0;
  const colVertex = Math.round((svgX - PADDING) / CELL_SIZE) + gMinC;
  const rowVertex = Math.round((svgY - PADDING) / CELL_SIZE) + gMinR;
  return [rowVertex, colVertex];
}

/**
 * Given two adjacent vertices (one step orthogonal), return the two cells
 * that share the edge they form, or null if the edge is not between two active cells.
 */
function edgeVerticesToCells(vr1, vc1, vr2, vc2) {
  if (vr1 === vr2 && Math.abs(vc1 - vc2) === 1) {
    const r = vr1;
    const c = Math.min(vc1, vc2);
    return [[r-1, c], [r, c]];
  }
  if (vc1 === vc2 && Math.abs(vr1 - vr2) === 1) {
    const r = Math.min(vr1, vr2);
    const c = vc1;
    return [[r, c-1], [r, c]];
  }
  return null;
}

// ── SVG fragment builders ─────────────────────────────────────────────────

function ghostCell(r, c, gMinR, gMinC, isClickable) {
  const x = cx(c, gMinC), y = cy(r, gMinR);
  const cursor = isClickable ? 'pointer' : 'default';
  const opacity = isClickable ? '1' : '0.3';
  return `
    <rect data-ghost="1" data-row="${r}" data-col="${c}"
          x="${x + 2}" y="${y + 2}"
          width="${CELL_SIZE - 4}" height="${CELL_SIZE - 4}" rx="${CELL_RADIUS}"
          fill="#16161e" stroke="#2a2a40" stroke-width="1" stroke-dasharray="5,3"
          opacity="${opacity}" cursor="${cursor}"/>
    <text x="${x + CELL_SIZE / 2}" y="${y + CELL_SIZE / 2 + 6}"
          text-anchor="middle" fill="#2e2e50" font-size="18"
          pointer-events="none" opacity="${opacity}">+</text>
  `;
}

function activeCell(r, c, gMinR, gMinC, { isViol, isSolveHL, symData, playerVal }) {
  const x = cx(c, gMinC), y = cy(r, gMinR);

  let fill = '#1e1e26', stroke = '#2e2e38', sw = '1.5';
  if (symData?.symbol_type === 'endpoint') {
    const color = ENDPOINT_COLORS[symData.color_id % ENDPOINT_COLORS.length];
    fill   = color + '22';
    stroke = color;
    sw     = '2.5';
  } else if (isViol)   { fill = '#2a1414'; stroke = '#f87171'; sw = '2'; }
  else if (isSolveHL)  { fill = '#1a1a30'; stroke = '#7c6af7'; sw = '2'; }

  let html = `
    <rect data-row="${r}" data-col="${c}"
          x="${x + 2}" y="${y + 2}"
          width="${CELL_SIZE - 4}" height="${CELL_SIZE - 4}" rx="${CELL_RADIUS}"
          fill="${fill}" stroke="${stroke}" stroke-width="${sw}" cursor="pointer"/>
  `;

  let label = null, labelColor = '#e8e8f0', labelWeight = 'normal';

  if (isSolveHL) {
    label       = String(appState.solveOverlay[cellKey(r, c)]);
    labelColor  = '#9580ff';
    labelWeight = '500';
  } else if (symData?.symbol_type === 'endpoint') {
    const color = ENDPOINT_COLORS[symData.color_id % ENDPOINT_COLORS.length];
    const letter = symData.role === 'start' ? 'S' : 'E';
    const cx_ = x + CELL_SIZE / 2, cy_ = y + CELL_SIZE / 2;
    html += `
      <circle cx="${cx_}" cy="${cy_}" r="16" fill="${color}" pointer-events="none"/>
      <text x="${cx_}" y="${cy_ + 5}" text-anchor="middle" fill="#fff"
            font-size="14" font-family="DM Mono, monospace" font-weight="700"
            pointer-events="none">${letter}</text>
    `;
    label = null;
  } else if (symData?.symbol_type === 'number') {
    label       = String(symData.value ?? '');
    labelColor  = '#a78bfa';
    labelWeight = '600';
  } else if (playerVal !== undefined && playerVal !== null) {
    label      = String(playerVal);
    labelColor = isViol ? '#f87171' : '#4ade80';
  }

  if (label !== null) {
    const fs = label.length > 2 ? 14 : 22;
    html += `
      <text x="${x + CELL_SIZE / 2}" y="${y + CELL_SIZE / 2 + 7}"
            text-anchor="middle" fill="${labelColor}"
            font-size="${fs}" font-family="DM Mono, monospace"
            font-weight="${labelWeight}" pointer-events="none">${label}</text>
    `;
  }

  // Coord hint
  html += `
    <text x="${x + 5}" y="${y + 12}" fill="#2a2a40" font-size="8"
          font-family="DM Mono, monospace" pointer-events="none">${r},${c}</text>
  `;

  return html;
}

function lineSegments(lines, gMinR, gMinC, symbols) {
  if (!lines?.length) return '';

  // Build color lookup from endpoint symbols
  const cellColor = {};
  if (symbols) {
    for (const [key, sym] of Object.entries(symbols)) {
      if (sym.symbol_type === 'endpoint') {
        cellColor[key] = ENDPOINT_COLORS[sym.color_id % ENDPOINT_COLORS.length];
      }
    }
  }

  // BFS to assign color to every line cell
  const adj = {};
  for (const [[r1,c1],[r2,c2]] of lines) {
    const k1 = cellKey(r1,c1), k2 = cellKey(r2,c2);
    (adj[k1] = adj[k1] || []).push(k2);
    (adj[k2] = adj[k2] || []).push(k1);
  }

  const assignedColor = { ...cellColor };
  const queue = Object.keys(cellColor);
  const visited = new Set(queue);
  while (queue.length) {
    const cur = queue.shift();
    const color = assignedColor[cur];
    for (const nb of (adj[cur] || [])) {
      if (!visited.has(nb)) {
        visited.add(nb);
        assignedColor[nb] = color;
        queue.push(nb);
      }
    }
  }

  let html = '';
  const isLineTool = (appState.mode === 'edit' &&
    (appState.activeTool === 'erase-line' || appState.activeTool === 'draw-line'));

  for (const [[r1,c1],[r2,c2]] of lines) {
    const key1 = cellKey(r1,c1);
    const color = assignedColor[key1] || '#7c6af7';
    const { x1, y1, x2, y2 } = edgeCoords(r1, c1, r2, c2, gMinR, gMinC);

    html += `
      <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
            stroke="${color}" stroke-width="10" stroke-linecap="butt"
            opacity="0.55"
            pointer-events="${isLineTool ? 'auto' : 'none'}"
            data-line-from-row="${r1}" data-line-from-col="${c1}"
            data-line-to-row="${r2}" data-line-to-col="${c2}"
            style="cursor:${isLineTool ? 'pointer' : 'inherit'}"/>
      <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
            stroke="${color}" stroke-width="5" stroke-linecap="butt"
            opacity="0.9"
            pointer-events="${isLineTool ? 'auto' : 'none'}"
            data-line-from-row="${r1}" data-line-from-col="${c1}"
            data-line-to-row="${r2}" data-line-to-col="${c2}"
            style="cursor:${isLineTool ? 'pointer' : 'inherit'}"/>
    `;
  }
  return html;
}

function dragPreviewLine(gMinR, gMinC) {
  const ds = appState.dragState;
  if (!ds?.active || !ds.vertexPath || ds.vertexPath.length < 2) return '';
  const path = ds.vertexPath;
  let html = '';

  for (let i = 0; i < path.length - 1; i++) {
    const [vr1, vc1] = path[i];
    const [vr2, vc2] = path[i + 1];
    const cells = edgeVerticesToCells(vr1, vc1, vr2, vc2);
    if (!cells) continue;
    const [cellA, cellB] = cells;
    const activeSet = new Set(
      (appState.puzzle?.grid?.cells || []).map(([r, c]) => cellKey(r, c))
    );
    // Draw preview if at least one side is active
    if (
      !activeSet.has(cellKey(cellA[0], cellA[1])) &&
      !activeSet.has(cellKey(cellB[0], cellB[1]))
    )
      continue;
  }
  return html;
}

// ── Main render function ──────────────────────────────────────────────────

export function renderGrid(dragState = null) {
  const svg = document.getElementById('grid-svg');
  if (!svg || !appState.puzzle) return;

  const puzzle  = appState.puzzle;
  const cells   = puzzle.grid?.cells || [];
  const mode    = appState.mode;
  const tool    = appState.activeTool;

  const { minR, minC, maxR, maxC } = computeBounds(cells);

  const gMinR = minR - GHOST_EXTRA;
  const gMinC = minC - GHOST_EXTRA;
  const gMaxR = maxR + GHOST_EXTRA;
  const gMaxC = maxC + GHOST_EXTRA;

  const svgW = (gMaxC - gMinC + 1) * CELL_SIZE + PADDING * 2;
  const svgH = (gMaxR - gMinR + 1) * CELL_SIZE + PADDING * 2;

  svg.setAttribute('width',  svgW);
  svg.setAttribute('height', svgH);

  const activeCells = new Set(cells.map(([r, c]) => cellKey(r, c)));
  const violations  = puzzle.violations || [];
  const violCells   = new Set(violations.flatMap(v =>
    v.cells.map(cell => cellKey(cell[0], cell[1]))
  ));

  let html = `
    <defs>
      <pattern id="dot-bg" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
        <circle cx="10" cy="10" r="1" fill="#2e2e38" opacity="0.4"/>
      </pattern>
    </defs>
    <rect width="${svgW}" height="${svgH}" fill="url(#dot-bg)"/>
  `;

  // Ghost cells
  if (mode === 'edit') {
    const isAddTool = (tool === 'add-cell');
    for (let r = gMinR; r <= gMaxR; r++) {
      for (let c = gMinC; c <= gMaxC; c++) {
        if (activeCells.has(cellKey(r, c))) continue;
        const adjacent = [[r-1,c],[r+1,c],[r,c-1],[r,c+1]]
          .some(([ar, ac]) => activeCells.has(cellKey(ar, ac)));
        if (cells.length > 0 && !adjacent) continue;
        html += ghostCell(r, c, gMinR, gMinC, isAddTool);
      }
    }
  }

  // Active cells
  for (const [r, c] of cells) {
    const key     = cellKey(r, c);
    const symData = puzzle.symbols?.[key];
    html += activeCell(r, c, gMinR, gMinC, {
      isViol:    violCells.has(key),
      isSolveHL: appState.solveOverlay.hasOwnProperty(key),
      symData,
      playerVal: puzzle.player_values?.[key],
    });
  }

  // Drawn lines (edges)
  html += lineSegments(puzzle.lines, gMinR, gMinC, puzzle.symbols);

  // Drag preview (vertex‑based)
  html += dragPreviewLine(gMinR, gMinC);


  svg.innerHTML = html;
  svg._gMinR = gMinR;
  svg._gMinC = gMinC;
}

// ── Coordinate conversion utilities ───────────────────────────────────────

export function svgPosToCell(svgX, svgY) {
  const svg = document.getElementById('grid-svg');
  if (!svg) return null;
  const gMinR = svg._gMinR ?? 0;
  const gMinC = svg._gMinC ?? 0;
  const col = Math.floor((svgX - PADDING) / CELL_SIZE) + gMinC;
  const row = Math.floor((svgY - PADDING) / CELL_SIZE) + gMinR;
  return [row, col];
}

export function eventToSvgPos(evt) {
  const svg = document.getElementById('grid-svg');
  try {
    const pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return [0, 0];
    const svgPt = pt.matrixTransform(ctm.inverse());
    return [svgPt.x, svgPt.y];
  } catch (e) {
    console.warn('eventToSvgPos failed', e);
    return [0, 0];
  }
}