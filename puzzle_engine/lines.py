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
# Convert a cell edge to the two vertices it lies on
# ---------------------------------------------------------------------------

def cell_edge_to_vertices(edge: Edge) -> List[VertexCoord]:
    """Return the two vertices that form the shared border of two adjacent cells."""
    a, b = edge
    if a[0] == b[0]:          # horizontal adjacency → vertical edge
        row = a[0]
        col_left = min(a[1], b[1])
        return [(row, col_left), (row + 1, col_left)]
    else:                     # vertical adjacency → horizontal edge
        col = a[1]
        row_top = min(a[0], b[0])
        return [(row_top, col), (row_top, col + 1)]


# ---------------------------------------------------------------------------
# Vertex‑line graph (vertices connected by drawn lines)
# ---------------------------------------------------------------------------

def build_vertex_line_graph(state: "PuzzleState") -> Dict[VertexCoord, List[VertexCoord]]:
    """
    Build a graph of vertices connected by drawn cell edges.
    Each vertex maps to a list of adjacent vertices reachable via one line edge.
    """
    graph = defaultdict(list)
    for edge in state.lines:
        v1, v2 = cell_edge_to_vertices(edge)
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