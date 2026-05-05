"""
Line-drawing rules for endpoint (Start/End) puzzle types.

These rules operate on PuzzleState.lines and PuzzleState.symbols
rather than PuzzleState.player_values.

Rules
-----
LineConnectsEndpointsRule
    Every Start cell must be reachable from exactly one End cell of the
    same color_id via the drawn lines, and vice versa.

NoLineOverlapRule
    No cell may be an interior node of more than one distinct line path
    (i.e. have line-degree > 2), and no cell may appear in line segments
    of two different colors.
    Endpoint cells (Start/End) must have exactly 1 line connection.
    Interior cells must have exactly 2 line connections (pass-through).

AllEndpointsConnectedRule
    All endpoint pairs must be fully connected (convenience wrapper that
    also checks completeness — no partially drawn lines).
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Optional, Set

from puzzle_engine.grid import CellCoord
from puzzle_engine.symbol import EndpointSymbol

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from puzzle_engine.puzzle import PuzzleState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_adjacency(state: "PuzzleState") -> Dict[CellCoord, List[CellCoord]]:
    """Build adjacency map from the drawn lines."""
    adj: Dict[CellCoord, List[CellCoord]] = defaultdict(list)
    for a, b in state.lines:
        adj[a].append(b)
        adj[b].append(a)
    return adj


def collect_endpoints(state: "PuzzleState") -> Dict[int, Dict[str, List[CellCoord]]]:
    """
    Return { color_id: {"start": [...], "end": [...]} } from symbols.
    """
    result: Dict[int, Dict[str, List[CellCoord]]] = defaultdict(lambda: {"start": [], "end": []})
    for cell, sym in state.symbols.items():
        if isinstance(sym, EndpointSymbol):
            result[sym.color_id][sym.role].append(cell)
    return result


def trace_path(start: CellCoord, adj: Dict[CellCoord, List[CellCoord]],
                endpoints: Set[CellCoord]) -> Optional[List[CellCoord]]:
    """
    Follow the unique path from `start` through the line network.
    Returns the ordered list of cells from start to the other endpoint,
    or None if the path branches or forms a loop.
    """
    path = [start]
    prev = None
    current = start
    while True:
        neighbors = [n for n in adj.get(current, []) if n != prev]
        if len(neighbors) == 0:
            # Dead end — return path as-is (may be an endpoint)
            return path
        if len(neighbors) > 1:
            return None  # Branches — invalid
        nxt = neighbors[0]
        if nxt in path:
            return None  # Loop
        path.append(nxt)
        prev, current = current, nxt
        if current in endpoints:
            return path  # Reached another endpoint