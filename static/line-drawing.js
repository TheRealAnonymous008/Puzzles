// line-drawing.js
import { eventToSvgPos, svgPosToVertex, cellKey, renderGrid } from './grid-renderer.js';
import { appState } from './state.js';
import { api } from './api.js';

export function initLineDrawing(svg) {
  svg.addEventListener('mousedown', onMouseDown);
  svg.addEventListener('mousemove', onMouseMove);
  svg.addEventListener('mouseup',   onMouseUp);
  window.addEventListener('mouseup', onMouseUp);
  svg.addEventListener('dragstart',  e => e.preventDefault());
}

function isActiveCell(r, c) {
  const cells = appState.puzzle?.grid?.cells || [];
  return cells.some(([cr, cc]) => cr === r && cc === c);
}

function isDrawLineTool() {
  return appState.activeTool === 'draw-line';
}

/**
 * Build the graph of valid edges (vertex to vertex) from active cells.
 * Returns an adjacency Map: vertex key -> list of neighbor vertex keys.
 */
function buildVertexGraph() {
  const cells = appState.puzzle?.grid?.cells || [];
  const activeSet = new Set(cells.map(([r,c]) => cellKey(r,c)));
  const graph = new Map();

  function vertexKey(vr, vc) { return `${vr},${vc}`; }

  for (const [r, c] of cells) {
    // All four corners of this cell
    const corners = [[r, c], [r, c+1], [r+1, c], [r+1, c+1]];
    // Add all potential edges between corners that are adjacent
    // Horizontal edge between (r,c) and (r,c+1) if both cells above/below are active
    const edge1 = [[r,c], [r,c+1]];   // top horizontal
    const edge2 = [[r+1,c], [r+1,c+1]]; // bottom horizontal
    const edge3 = [[r,c], [r+1,c]];   // left vertical
    const edge4 = [[r,c+1], [r+1,c+1]]; // right vertical

    const edges = [edge1, edge2, edge3, edge4];
    for (const [v1, v2] of edges) {
      const [vr1, vc1] = v1, [vr2, vc2] = v2;
      // Check if edge separates two active cells
      const cellsForEdge = edgeVerticesToCells(vr1, vc1, vr2, vc2);
      if (!cellsForEdge) continue;
      const [cellA, cellB] = cellsForEdge;
      if (!activeSet.has(cellKey(cellA[0],cellA[1])) || !activeSet.has(cellKey(cellB[0],cellB[1]))) continue;

      const k1 = vertexKey(vr1, vc1);
      const k2 = vertexKey(vr2, vc2);
      if (!graph.has(k1)) graph.set(k1, []);
      if (!graph.get(k1).includes(k2)) graph.get(k1).push(k2);
      if (!graph.has(k2)) graph.set(k2, []);
      if (!graph.get(k2).includes(k1)) graph.get(k2).push(k1);
    }
  }
  return graph;
}

/**
 * Helper: convert two adjacent vertices to the two cells they separate.
 * Same logic as in grid-renderer.js (copied here for independence).
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

function findVertexPath(startVertex, endVertex, graph) {
  const startKey = `${startVertex[0]},${startVertex[1]}`;
  const endKey = `${endVertex[0]},${endVertex[1]}`;
  if (startKey === endKey) return [startVertex];

  const queue = [[startVertex]];
  const visited = new Set([startKey]);

  while (queue.length) {
    const path = queue.shift();
    const [vr, vc] = path[path.length - 1];
    const currentKey = `${vr},${vc}`;
    const neighbors = graph.get(currentKey) || [];
    for (const nKey of neighbors) {
      if (!visited.has(nKey)) {
        const [nr, nc] = nKey.split(',').map(Number);
        const newPath = [...path, [nr, nc]];
        if (nKey === endKey) return newPath;
        visited.add(nKey);
        queue.push(newPath);
      }
    }
  }
  return null; // no path
}

function onMouseDown(e) {
  if (!isDrawLineTool()) return;
  if (e.button !== 0) return;

  const [x, y] = eventToSvgPos(e);
  const vertex = svgPosToVertex(x, y);
  if (!vertex) return;

  const [vr, vc] = vertex;
  // Verify this vertex belongs to at least one active cell (graph will tell)
  const graph = buildVertexGraph();
  if (!graph.has(`${vr},${vc}`)) return; // vertex not on valid edge

  appState.update({
    dragState: {
      active: true,
      vertexPath: [[vr, vc]],
    }
  });
  e.preventDefault();
}

function onMouseMove(e) {
  const ds = appState.dragState;
  if (!ds?.active || !isDrawLineTool()) return;

  const [x, y] = eventToSvgPos(e);
  const vertex = svgPosToVertex(x, y);
  if (!vertex) return;
  const [vr, vc] = vertex;
  const last = ds.vertexPath[ds.vertexPath.length - 1];
  if (last[0] === vr && last[1] === vc) return;

  const graph = buildVertexGraph();
  const pathToNew = findVertexPath(last, [vr, vc], graph);
  if (!pathToNew || pathToNew.length < 2) return;

  // Remove duplicate start vertex (already in existing path)
  const segment = pathToNew.slice(1);
  // Check for backtracking: if the segment's first vertex is the second-last of current path
  if (ds.vertexPath.length >= 2) {
    const secondLast = ds.vertexPath[ds.vertexPath.length - 2];
    if (segment.length >= 1 && segment[0][0] === secondLast[0] && segment[0][1] === secondLast[1]) {
      // Backtrack: pop the last vertex
      appState.update({
        dragState: {
          active: true,
          vertexPath: ds.vertexPath.slice(0, -1),
        }
      });
      renderGrid();
      return;
    }
  }

  // Check that we are not revisiting a vertex already in the path (except the last)
  const existingSet = new Set(ds.vertexPath.map(([r,c]) => `${r},${c}`));
  for (const [sr, sc] of segment) {
    if (existingSet.has(`${sr},${sc}`)) return; // cycle not allowed
  }

  const newPath = [...ds.vertexPath, ...segment];
  appState.update({
    dragState: {
      active: true,
      vertexPath: newPath,
    }
  });
  renderGrid();
}

async function onMouseUp(e) {
  const ds = appState.dragState;
  if (!ds?.active) return;

  appState.update({ dragState: null });

  if (!isDrawLineTool() || !ds.vertexPath || ds.vertexPath.length < 2) return;

  // Commit each edge of the vertex path
  for (let i = 0; i < ds.vertexPath.length - 1; i++) {
    const [vr1, vc1] = ds.vertexPath[i];
    const [vr2, vc2] = ds.vertexPath[i+1];
    const cells = edgeVerticesToCells(vr1, vc1, vr2, vc2);
    if (!cells) continue;
    const [cellA, cellB] = cells;
    // both cells must still be active (could have been deleted during drag? unlikely)
    if (!isActiveCell(cellA[0], cellA[1]) || !isActiveCell(cellB[0], cellB[1])) continue;
    try {
      await api.addLineSegment(cellA[0], cellA[1], cellB[0], cellB[1]);
    } catch (err) {
      console.error('Failed to add line segment', err);
    }
  }

  const updated = await api.getState();
  appState.update({ puzzle: updated });
}