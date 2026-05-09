"""
Solver: pure vertex‑graph backtracking.
No cells are used – only vertices and edges between them.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import permutations
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.puzzle import PuzzleState, VertexCoord, VertexEdge
from puzzle_engine.symbol import EndpointSymbol


@dataclass
class SolveResult:
    solution_count: int = 0
    first_solution: Optional[Dict[CellCoord, Any]] = None   # not used for lines
    solve_path: List[Tuple[CellCoord, Any]] = field(default_factory=list)
    searched_nodes: int = 0
    first_lines: Optional[Set[VertexEdge]] = None               # vertex edges

    @property
    def is_unique(self) -> bool:
        return self.solution_count == 1

    @property
    def has_solution(self) -> bool:
        return self.solution_count > 0

    def to_dict(self) -> dict:
        """Return a representation suitable for the front‑end.
        The front‑end expects cell‑pair edges, so we convert vertex edges here."""
        d = {
            "solution_count": self.solution_count,
            "has_solution": self.has_solution,
            "is_unique": self.is_unique,
            "searched_nodes": self.searched_nodes,
            "first_solution": None,
            "solve_path": [],
        }
        if self.first_lines is not None:
            cell_lines = []
            for v1, v2 in self.first_lines:
                cell1, cell2 = self._vertex_edge_to_cell_pair(v1, v2)
                cell_lines.append(((cell1[0], cell1[1]), (cell2[0], cell2[1])))
            d["lines"] = [
                [[a[0], a[1]], [b[0], b[1]]] for a, b in sorted(cell_lines)
            ]
        else:
            d["lines"] = []
        return d

    @staticmethod
    def _vertex_edge_to_cell_pair(v1: VertexCoord, v2: VertexCoord):
        r1, c1 = v1
        r2, c2 = v2
        if r1 == r2:          # horizontal vertex edge → cells above/below
            row = r1
            col = min(c1, c2)
            return (row - 1, col), (row, col)
        else:                 # vertical vertex edge → cells left/right
            col = c1
            row = min(r1, r2)
            return (row, col - 1), (row, col)


class Solver:
    """Backtracking solver that places lines on the vertex graph,
    connects endpoints, and runs built‑in rule validation."""

    def __init__(self, max_solutions: int = 2) -> None:
        self.max_solutions = max_solutions

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def solve(self, state: PuzzleState) -> SolveResult:
        result = SolveResult()

        # 1. Build the vertex graph (corners of all active cells + endpoint vertices)
        vgraph = self._build_vertex_graph(state)

        # 2. Extract all endpoint symbols as vertex locations
        color_endpoints = self._extract_endpoints(state)
        if not color_endpoints:
            result.searched_nodes = 1
            if state.is_solved():
                result.solution_count = 1
                result.first_lines = set(state.lines)
            return result

        # 3. For each colour, generate all possible concrete vertex sets
        assignments_per_color = []
        for color, eps in color_endpoints.items():
            assignments = list(self._generate_assignments(eps))
            if not assignments:
                return result
            assignments_per_color.append((color, assignments))

        # 4. Try every combination of assignments across colours
        for combo in self._product_assignments(assignments_per_color):
            used_edges: Set[VertexEdge] = set()
            degrees: Dict[VertexCoord, int] = defaultdict(int)
            colours: Dict[VertexCoord, int] = {}

            ok = True
            for (color, _), (starts, ends, self_loops) in zip(assignments_per_color, combo):
                if not self._solve_color(vgraph, starts, ends, self_loops,
                                         used_edges, degrees, colours, color):
                    ok = False
                    break
            if not ok:
                continue

            result.searched_nodes += 1
            # Directly assign the found vertex edges to the state
            old_lines = state.lines
            state.lines = used_edges
            valid = state.is_solved()
            state.lines = old_lines

            if valid:
                result.solution_count += 1
                if result.first_lines is None:
                    result.first_lines = set(used_edges)
                if result.solution_count >= self.max_solutions:
                    break

        return result

    # ------------------------------------------------------------------
    # Vertex graph – all corners of active cells + endpoint vertices
    # ------------------------------------------------------------------
    def _build_vertex_graph(self, state: PuzzleState):
        active_cells = set(state.grid.cells)
        vertices: Set[VertexCoord] = set()
        for r, c in active_cells:
            vertices.update([(r, c), (r, c+1), (r+1, c), (r+1, c+1)])

        # Also include every vertex that has an endpoint symbol
        for v in state.vertex_symbols:
            vertices.add(v)

        graph = defaultdict(set)
        for vr, vc in vertices:
            for dr, dc in ((0, 1), (1, 0)):
                nr, nc = vr + dr, vc + dc
                if (nr, nc) not in vertices:
                    continue
                # Edge exists if at least one of the two adjacent cells is active
                if dr == 0:          # horizontal edge
                    r = vr
                    c = min(vc, nc)
                    cell1 = (r-1, c)
                    cell2 = (r, c)
                else:                # vertical edge
                    c = vc
                    r = min(vr, nr)
                    cell1 = (r, c-1)
                    cell2 = (r, c)
                if cell1 in active_cells or cell2 in active_cells:
                    graph[(vr, vc)].add((nr, nc))
                    graph[(nr, nc)].add((vr, vc))

        return graph

    # ------------------------------------------------------------------
    # Endpoint collection – map colour -> {starts, ends, boths}
    # ------------------------------------------------------------------
    def _extract_endpoints(self, state: PuzzleState):
        result = defaultdict(lambda: {"starts": [], "ends": [], "boths": []})
        # cell endpoints → expand later to corners
        for (r, c), sym in state.symbols.items():
            if isinstance(sym, EndpointSymbol):
                color = sym.color_id
                role = sym.role
                if role == "start":
                    result[color]["starts"].append(("cell", (r, c)))
                elif role == "end":
                    result[color]["ends"].append(("cell", (r, c)))
                else:
                    result[color]["boths"].append(("cell", (r, c)))
        # vertex endpoints → already concrete
        for v, sym in state.vertex_symbols.items():
            if isinstance(sym, EndpointSymbol):
                color = sym.color_id
                role = sym.role
                if role == "start":
                    result[color]["starts"].append(("vertex", v))
                elif role == "end":
                    result[color]["ends"].append(("vertex", v))
                else:
                    result[color]["boths"].append(("vertex", v))
        return result

    # ------------------------------------------------------------------
    # Assignment generation – cell endpoints become concrete corners
    # ------------------------------------------------------------------
    def _generate_assignments(self, endpoints: dict):
        cell_starts = [loc for typ, loc in endpoints["starts"] if typ == "cell"]
        cell_ends   = [loc for typ, loc in endpoints["ends"]   if typ == "cell"]
        cell_boths  = [loc for typ, loc in endpoints["boths"]  if typ == "cell"]
        vertex_starts = [loc for typ, loc in endpoints["starts"] if typ == "vertex"]
        vertex_ends   = [loc for typ, loc in endpoints["ends"]   if typ == "vertex"]
        vertex_boths  = [loc for typ, loc in endpoints["boths"]  if typ == "vertex"]

        def corners(r, c):
            return [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]

        # All choices for cell starts
        def cell_start_choices():
            if not cell_starts:
                yield []
                return
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

        def cell_end_choices():
            if not cell_ends:
                yield []
                return
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

        def cell_both_choices():
            if not cell_boths:
                yield []
                return
            def gen(idx, cur):
                if idx == len(cell_boths):
                    yield list(cur)
                    return
                r, c = cell_boths[idx]
                clist = corners(r, c)
                for i in range(len(clist)):
                    for j in range(i+1, len(clist)):
                        cur.append((clist[i], clist[j]))
                        yield from gen(idx+1, cur)
                        cur.pop()
            yield from gen(0, [])

        for s_assign in cell_start_choices():
            for e_assign in cell_end_choices():
                for b_assign in cell_both_choices():
                    starts = list(vertex_starts) + s_assign
                    ends   = list(vertex_ends)   + e_assign
                    self_loops = list(vertex_boths)
                    for v1, v2 in b_assign:
                        starts.append(v1)
                        ends.append(v2)
                    yield starts, ends, self_loops

    @staticmethod
    def _product_assignments(assignments_per_color):
        if not assignments_per_color:
            yield []
            return
        first_list = assignments_per_color[0][1]
        rest = assignments_per_color[1:]
        for a in first_list:
            for tail in Solver._product_assignments(rest):
                yield [a] + tail

    # ------------------------------------------------------------------
    # Solve a single colour – try all pairings
    # ------------------------------------------------------------------
    def _solve_color(self, vgraph, starts, ends, self_loops,
                     used_edges, degrees, colours, color):
        if len(starts) != len(ends):
            return False

        pairs = [(v, v) for v in self_loops]
        n = len(starts)
        for perm in permutations(range(n)):
            cur_pairs = list(pairs)
            for i in range(n):
                cur_pairs.append((starts[i], ends[perm[i]]))
            # Save state
            old_edges = set(used_edges)
            old_deg   = dict(degrees)
            old_col   = dict(colours)
            if self._route_pairs(vgraph, cur_pairs, 0, used_edges, degrees, colours, color):
                return True
            # Revert
            used_edges.clear(); used_edges.update(old_edges)
            degrees.clear(); degrees.update(old_deg)
            colours.clear(); colours.update(old_col)
        return False

    def _route_pairs(self, vgraph, pairs, idx, used_edges, degrees, colours, color):
        if idx == len(pairs):
            return True
        s, e = pairs[idx]
        paths = self._find_all_paths(vgraph, s, e, used_edges, degrees, colours, color)
        for path in paths:
            self._apply_path(path, used_edges, degrees, colours, color)
            if self._route_pairs(vgraph, pairs, idx+1, used_edges, degrees, colours, color):
                return True
            self._unapply_path(path, used_edges, degrees, colours, color)
        return False

    def _find_all_paths(self, vgraph, start, end, used_edges, degrees, colours, color, max_len=100):
        results = []
        def dfs(current, path, visited):
            if len(path) > max_len:
                return
            if current == end and len(path) > 1:
                results.append(list(path))
                return
            for nb in vgraph.get(current, []):
                edge = tuple(sorted((current, nb)))
                if edge in used_edges:
                    continue
                if degrees.get(current, 0) >= 2:
                    continue
                if degrees.get(nb, 0) >= 2:
                    continue
                if nb != end and nb in colours and colours[nb] != color:
                    continue
                if nb not in visited:
                    visited.add(nb)
                    dfs(nb, path + [nb], visited)
                    visited.discard(nb)
        dfs(start, [start], {start})
        return results

    def _apply_path(self, path, used_edges, degrees, colours, color):
        for i in range(len(path)-1):
            v1, v2 = path[i], path[i+1]
            edge = tuple(sorted((v1, v2)))
            used_edges.add(edge)
            degrees[v1] = degrees.get(v1, 0) + 1
            degrees[v2] = degrees.get(v2, 0) + 1
        for v in path[1:-1]:
            colours[v] = color

    def _unapply_path(self, path, used_edges, degrees, colours, color):
        for i in range(len(path)-1):
            v1, v2 = path[i], path[i+1]
            edge = tuple(sorted((v1, v2)))
            used_edges.discard(edge)
            degrees[v1] = degrees.get(v1, 0) - 1
            degrees[v2] = degrees.get(v2, 0) - 1
        for v in path[1:-1]:
            if colours.get(v) == color:
                del colours[v]