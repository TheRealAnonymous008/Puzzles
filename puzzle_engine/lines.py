"""
Line-drawing helpers: adjacency, endpoint collection, vertex mapping.
These functions are used by the line‑related rules.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.symbol import EndpointSymbol

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from puzzle_engine.puzzle import PuzzleState

# Type aliases
Edge = Tuple[CellCoord, CellCoord]
VertexCoord = Tuple[int, int]


# ---------------------------------------------------------------------------
# Basic adjacency from drawn lines (cell‑to‑cell)
# ---------------------------------------------------------------------------

def build_adjacency(state: "PuzzleState") -> Dict[CellCoord, List[CellCoord]]:
    """Build cell adjacency map from the drawn lines."""
    adj: Dict[CellCoord, List[CellCoord]] = defaultdict(list)
    for a, b in state.lines:
        adj[a].append(b)
        adj[b].append(a)
    return adj


# ---------------------------------------------------------------------------
# Convert a cell edge to the two vertices it lies on (CORRECTED)
# ---------------------------------------------------------------------------

def cell_edge_to_vertices(edge: Edge) -> List[VertexCoord]:
    """
    Return the two vertices that form the shared border of two adjacent cells.
    Works for both orthogonal directions.
    """
    a, b = edge
    r1, c1 = a
    r2, c2 = b
    if r1 == r2:
        # horizontal adjacency → shared VERTICAL edge
        row = r1
        col_right = max(c1, c2)          # the column of the shared border
        return [(row, col_right), (row + 1, col_right)]
    else:
        # vertical adjacency → shared HORIZONTAL edge
        col = c1
        row_bottom = max(r1, r2)         # the row of the shared border
        return [(row_bottom, col), (row_bottom, col + 1)]


# ---------------------------------------------------------------------------
# Vertex‑line graph (vertices connected by drawn lines)
# ---------------------------------------------------------------------------

def build_vertex_line_graph(state: "PuzzleState") -> Dict[VertexCoord, List[VertexCoord]]:
    graph = defaultdict(list)
    for v1, v2 in state.lines:          # now vertex edges
        graph[v1].append(v2)
        graph[v2].append(v1)
    return graph

# ---------------------------------------------------------------------------
# Endpoint collection (cells + vertices, grouped by color_id and role)
# ---------------------------------------------------------------------------

def collect_endpoints(state: "PuzzleState") -> Dict[int, Dict[str, List[CellCoord]]]:
    """
    DEPRECATED – returns only cell endpoints.
    Kept for backward compatibility with older rules.
    """
    result: Dict[int, Dict[str, List[CellCoord]]] = defaultdict(lambda: {"start": [], "end": []})
    for cell, sym in state.symbols.items():
        if isinstance(sym, EndpointSymbol):
            result[sym.color_id][sym.role].append(cell)
    return result


def get_all_endpoints(state: "PuzzleState") -> Dict[int, Dict[str, List]]:
    """
    Return { color_id: {"start": [...], "end": [...], "both": [...]} }
    Each entry is either a CellCoord (cell symbol) or a VertexCoord (vertex symbol).
    """
    result: Dict[int, Dict[str, List]] = defaultdict(lambda: {"start": [], "end": [], "both": []})
    # cell endpoints
    for cell, sym in state.symbols.items():
        if isinstance(sym, EndpointSymbol):
            result[sym.color_id][sym.role].append(cell)
    # vertex endpoints
    for vertex, sym in state.vertex_symbols.items():
        if isinstance(sym, EndpointSymbol):
            result[sym.color_id][sym.role].append(vertex)
    return result