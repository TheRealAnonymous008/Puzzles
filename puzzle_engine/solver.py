"""
Solver module: path‑based backtracking line solver for PuzzleState.
Works on the vertex graph, handles boundary edges, and respects
degree & connectivity constraints automatically.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.puzzle import PuzzleState
from puzzle_engine.symbol import EndpointSymbol

Vertex = Tuple[int, int]
Edge = Tuple[CellCoord, CellCoord]          # cell‑pair edge
VertexEdge = Tuple[Vertex, Vertex]          # internal vertex‑pair edge


@dataclass
class SolveResult:
    solution_count: int = 0
    first_solution: Optional[Dict[CellCoord, Any]] = None
    solve_path: List[Tuple[CellCoord, Any]] = field(default_factory=list)
    searched_nodes: int = 0
    first_lines: Optional[Set[Edge]] = None

    @property
    def is_unique(self) -> bool:
        return self.solution_count == 1

    @property
    def has_solution(self) -> bool:
        return self.solution_count > 0

    def to_dict(self) -> dict:
        d = {
            "solution_count": self.solution_count,
            "has_solution": self.has_solution,
            "is_unique": self.is_unique,
            "searched_nodes": self.searched_nodes,
            "first_solution": (
                {f"{r},{c}": v for (r, c), v in self.first_solution.items()}
                if self.first_solution else None
            ),
            "solve_path": [],       # not used for line solving
        }
        if self.first_lines is not None:
            d["lines"] = [
                [[a[0], a[1]], [b[0], b[1]]] for a, b in sorted(self.first_lines)
            ]
        else:
            d["lines"] = []
        return d


class Solver:
    """Backtracking line solver that places lines on the vertex graph."""

    def __init__(self, max_solutions: int = 2) -> None:
        self.max_solutions = max_solutions

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def solve(self, state: PuzzleState) -> SolveResult:
        result = SolveResult()

        # 1. Build vertex graph and all possible edges
        vgraph, vertex_edges_list = self._build_vertex_graph(state)
        # 2. Extract endpoints per colour, expand cell endpoints to concrete vertices
        color_terminals = self._extract_terminals(state)
        if not color_terminals:
            result.searched_nodes = 1
            if state.is_solved():
                result.solution_count = 1
                result.first_solution = dict(state.player_values)
                result.first_lines = set(state.lines)
            return result

        # 3. For each colour, list all possible assignments of corner choices
        #    for cell endpoints, yielding (starts, ends, self_loops) as concrete vertices.
        assignments_per_color = []
        for color, terminals in color_terminals.items():
            assignments = list(self._generate_assignments(terminals))
            if not assignments:
                # No possible way to assign corners – unsolvable
                return result
            assignments_per_color.append((color, assignments))

        # 4. Iterate over all combinations of assignments across colours
        colors_assignments = [assignments_per_color]  # list of (color, [assignments])
        # We'll do a product over the assignment lists.
        for combo in product(*[a for _, a in assignments_per_color]):
            # Build a fresh state of used vertices / edges
            used_edges: Set[VertexEdge] = set()
            vertex_degrees: Dict[Vertex, int] = defaultdict(int)
            # Track colour of each interior vertex (to prevent mixing)
            vertex_colour: Dict[Vertex, int] = {}

            # For each colour in this combo
            success = True
            for (color, _), (starts, ends, self_loops) in zip(assignments_per_color, combo):
                # For this colour, we need to connect starts to ends and handle self_loops.
                # We'll pair up starts and ends and try to find disjoint paths.
                if not self._solve_color(vgraph, starts, ends, self_loops,
                                         used_edges, vertex_degrees, vertex_colour, color):
                    success = False
                    break
            if not success:
                continue

            # All colours satisfied – check the combined set against rules
            cell_edges = self._vertex_edges_to_cell_edges(used_edges, state)
            if self._is_valid(state, cell_edges):
                result.solution_count += 1
                if result.first_lines is None:
                    result.first_lines = cell_edges
                    result.first_solution = dict(state.player_values)
                if result.solution_count >= self.max_solutions:
                    return result

        return result

    # ------------------------------------------------------------------
    # Vertex graph (all edges touching an active cell)
    # ------------------------------------------------------------------
    def _build_vertex_graph(self, state: PuzzleState):
        cells = set(state.grid.cells)
        # All vertices that belong to at least one active cell
        vertices = set()
        for (r, c) in cells:
            for (vr, vc) in [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]:
                vertices.add((vr, vc))

        # Adjacency: two adjacent vertices connected by an edge that borders
        # at least one active cell.
        graph = defaultdict(set)
        active = set(cells)
        for (vr, vc) in vertices:
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = vr + dr, vc + dc
                if (nr, nc) not in vertices:
                    continue
                # determine the two cells on either side of this vertex edge
                if dr == 0:          # horizontal edge
                    r = vr
                    c = min(vc, nc)
                    cell1 = (r-1, c)
                    cell2 = (r, c)
                else:                # vertical edge
                    r = min(vr, nr)
                    c = vc
                    cell1 = (r, c-1)
                    cell2 = (r, c)
                if cell1 in active or cell2 in active:
                    graph[(vr, vc)].add((nr, nc))
                    graph[(nr, nc)].add((vr, vc))

        # List of all unique vertex edges (canonical order)
        edges = set()
        for v, nbs in graph.items():
            for nb in nbs:
                edges.add(tuple(sorted([v, nb])))
        return graph, list(edges)

    # ------------------------------------------------------------------
    # Terminal extraction & assignment generation
    # ------------------------------------------------------------------
    def _extract_terminals(self, state: PuzzleState):
        """Return dict: color -> {
            'cell_starts': [(r,c),...],
            'cell_ends':   [(r,c),...],
            'cell_boths':  [(r,c),...],
            'vertex_starts': [(vr,vc),...],
            'vertex_ends':   [(vr,vc),...],
            'vertex_boths':  [(vr,vc),...],
        }"""
        result = defaultdict(lambda: {
            'cell_starts': [], 'cell_ends': [], 'cell_boths': [],
            'vertex_starts': [], 'vertex_ends': [], 'vertex_boths': []
        })
        for (r, c), sym in state.symbols.items():
            if isinstance(sym, EndpointSymbol):
                color = sym.color_id
                if sym.role == 'start':
                    result[color]['cell_starts'].append((r, c))
                elif sym.role == 'end':
                    result[color]['cell_ends'].append((r, c))
                elif sym.role == 'both':
                    result[color]['cell_boths'].append((r, c))
        for (vr, vc), sym in state.vertex_symbols.items():
            if isinstance(sym, EndpointSymbol):
                color = sym.color_id
                if sym.role == 'start':
                    result[color]['vertex_starts'].append((vr, vc))
                elif sym.role == 'end':
                    result[color]['vertex_ends'].append((vr, vc))
                elif sym.role == 'both':
                    result[color]['vertex_boths'].append((vr, vc))
        return result

    def _generate_assignments(self, terminals: dict):
        """Yield all valid (starts, ends, self_loops) for a given colour,
        where cell endpoints are expanded to concrete corners."""
        cell_starts = terminals['cell_starts']
        cell_ends = terminals['cell_ends']
        cell_boths = terminals['cell_boths']
        vertex_starts = terminals['vertex_starts']
        vertex_ends = terminals['vertex_ends']
        vertex_boths = terminals['vertex_boths']

        # Helper: return the 4 corners of a cell
        def corners(r, c):
            return [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]

        # Generate all choices for start cells (pick one corner each)
        def choices_starts():
            if not cell_starts:
                yield []
            else:
                # recursive product
                def gen(idx, cur):
                    if idx == len(cell_starts):
                        yield list(cur)
                        return
                    r, c = cell_starts[idx]
                    for v in corners(r, c):
                        cur.append(v)
                        yield from gen(idx+1, cur)
                        cur.pop()
                yield from gen(0, [])

        def choices_ends():
            if not cell_ends:
                yield []
            else:
                def gen(idx, cur):
                    if idx == len(cell_ends):
                        yield list(cur)
                        return
                    r, c = cell_ends[idx]
                    for v in corners(r, c):
                        cur.append(v)
                        yield from gen(idx+1, cur)
                        cur.pop()
                yield from gen(0, [])

        def choices_boths():
            # For each 'both' cell, pick two distinct corners (order irrelevant)
            if not cell_boths:
                yield []
            else:
                def gen(idx, cur):
                    if idx == len(cell_boths):
                        yield list(cur)
                        return
                    r, c = cell_boths[idx]
                    corners_list = corners(r, c)
                    for i in range(len(corners_list)):
                        for j in range(i+1, len(corners_list)):
                            cur.append((corners_list[i], corners_list[j]))
                            yield from gen(idx+1, cur)
                            cur.pop()
                yield from gen(0, [])

        # Vertex boths: each becomes a self‑loop (start = end = vertex)
        for s_assignment in choices_starts():
            for e_assignment in choices_ends():
                for b_assignment in choices_boths():
                    # starts = vertex_starts + cell starts
                    starts = list(vertex_starts) + s_assignment
                    # ends = vertex_ends + cell ends
                    ends = list(vertex_ends) + e_assignment
                    # self_loops = vertex_boths + both cell pairs converted to self-loops?
                    # For cell both, we need a path connecting the two corners.
                    # That can be treated as a start-end pair, not a self-loop.
                    # So we'll add the two corners as a start-end pair.
                    for (v1, v2) in b_assignment:
                        starts.append(v1)
                        ends.append(v2)
                    # vertex_boths become self-loops (start=end=vertex)
                    self_loops = list(vertex_boths)
                    yield starts, ends, self_loops

    # ------------------------------------------------------------------
    # Colour‑specific solver
    # ------------------------------------------------------------------
    def _solve_color(self, vgraph, starts, ends, self_loops,
                     used_edges, vertex_degrees, vertex_colour, color):
        """
        Try to satisfy all terminals for `color` by finding paths.
        Modifies used_edges, vertex_degrees, vertex_colour in place on success;
        reverts on failure.
        """
        # We must pair up starts and ends arbitrarily.
        # For now we assume equal numbers (should hold for valid puzzles).
        if len(starts) != len(ends):
            return False

        # Build a list of (start, end) pairs that need to be connected.
        pairs = list(zip(starts, ends))
        for v in self_loops:
            pairs.append((v, v))   # self-loop

        # Sort pairs by Manhattan distance to try promising ones first
        pairs.sort(key=lambda p: abs(p[0][0]-p[1][0]) + abs(p[0][1]-p[1][1]))

        # Use backtracking to find disjoint paths
        return self._route_pairs(vgraph, pairs, 0, used_edges, vertex_degrees,
                                 vertex_colour, color)

    def _route_pairs(self, vgraph, pairs, idx, used_edges, vertex_degrees,
                     vertex_colour, color):
        if idx == len(pairs):
            return True
        s, e = pairs[idx]
        # Find all simple paths from s to e that respect current usage.
        paths = self._find_all_paths(vgraph, s, e, used_edges, vertex_degrees,
                                     vertex_colour, color)
        # Try each path
        for path in paths:
            # Apply edges and degrees
            self._apply_path(path, used_edges, vertex_degrees, vertex_colour, color)
            if self._route_pairs(vgraph, pairs, idx+1, used_edges, vertex_degrees,
                                 vertex_colour, color):
                return True
            # Revert
            self._unapply_path(path, used_edges, vertex_degrees, vertex_colour, color)
        return False

    def _find_all_paths(self, vgraph, start, end, used_edges, vertex_degrees,
                        vertex_colour, color, max_length=50):
        """
        Return all simple paths from start to end that can be added without
        violating degree/colour constraints.
        max_length limits search; increase if needed for large puzzles.
        """
        results = []
        # DFS for all simple paths
        def dfs(current, path, visited):
            if len(path) > max_length:
                return
            if current == end and len(path) > 1:
                results.append(list(path))
                return
            for nb in vgraph.get(current, []):
                edge = tuple(sorted([current, nb]))
                if edge in used_edges:
                    continue
                # Degree check: each endpoint (start/end) can have degree up to 1 (or 2 for self-loop)
                # but we'll allow adding edges as long as final degree won't exceed 2.
                # We check that the degree of current and nb after adding would be ≤2.
                if vertex_degrees.get(current, 0) >= 2:
                    continue
                if vertex_degrees.get(nb, 0) >= 2:
                    continue
                # Colour check: interior vertices must belong to exactly one colour
                if nb != end and nb in vertex_colour and vertex_colour[nb] != color:
                    continue
                if nb not in visited:
                    visited.add(nb)
                    dfs(nb, path + [nb], visited)
                    visited.discard(nb)
        dfs(start, [start], {start})
        return results

    def _apply_path(self, path, used_edges, vertex_degrees, vertex_colour, color):
        for i in range(len(path)-1):
            v1, v2 = path[i], path[i+1]
            edge = tuple(sorted([v1, v2]))
            used_edges.add(edge)
            vertex_degrees[v1] = vertex_degrees.get(v1, 0) + 1
            vertex_degrees[v2] = vertex_degrees.get(v2, 0) + 1
        # Mark interior vertices with this colour
        for v in path[1:-1]:
            vertex_colour[v] = color

    def _unapply_path(self, path, used_edges, vertex_degrees, vertex_colour, color):
        for i in range(len(path)-1):
            v1, v2 = path[i], path[i+1]
            edge = tuple(sorted([v1, v2]))
            used_edges.discard(edge)
            vertex_degrees[v1] = vertex_degrees.get(v1, 0) - 1
            vertex_degrees[v2] = vertex_degrees.get(v2, 0) - 1
        for v in path[1:-1]:
            if vertex_colour.get(v) == color:
                del vertex_colour[v]

    # ------------------------------------------------------------------
    # Conversion from vertex edges to cell‑pair edges
    # ------------------------------------------------------------------
    @staticmethod
    def _vertex_edges_to_cell_edges(vertex_edges: Set[VertexEdge],
                                    state: PuzzleState) -> Set[Edge]:
        """Map each vertex‑edge to the unique cell‑pair edge it divides."""
        cell_edges = set()
        for (v1, v2) in vertex_edges:
            r1, c1 = v1
            r2, c2 = v2
            if r1 == r2:          # horizontal edge
                r = r1
                c = max(c1, c2)
                cell1 = (r-1, c)
                cell2 = (r, c)
            else:                 # vertical edge
                c = c1
                r = max(r1, r2)
                cell1 = (r, c-1)
                cell2 = (r, c)
            cell_edges.add(tuple(sorted([cell1, cell2])))
        return cell_edges

    # ------------------------------------------------------------------
    # Final rule check
    # ------------------------------------------------------------------
    def _is_valid(self, state: PuzzleState, cell_edges: Set[Edge]) -> bool:
        old_lines = state.lines
        state.lines = cell_edges
        valid = state.is_solved()
        state.lines = old_lines
        return valid