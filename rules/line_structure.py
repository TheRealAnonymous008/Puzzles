"""
Built-in rule: every connected line component must connect a start-type
endpoint to an end-type endpoint. "Both" counts as either.
"""

from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING, List, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.lines import build_vertex_line_graph, get_all_endpoints
from puzzle_engine.rule import Rule, Violation
from puzzle_engine.symbol import EndpointSymbol

if TYPE_CHECKING:
    from puzzle_engine.puzzle import PuzzleState


class BuiltinLineStructureRule(Rule):
    """Always‑on rule – ensures lines are not stray and connect starts to ends."""

    rule_type = "builtin_line_structure"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []

        # Build vertex‑level connectivity from drawn lines
        vertex_graph = build_vertex_line_graph(state)   # dict: vertex -> list of adjacent vertices
        endpoints = get_all_endpoints(state)            # per color, per role

        # Find connected components of vertices (ignoring isolated vertices)
        visited_vertices: Set[Tuple[int,int]] = set()
        for vertex, neighbors in vertex_graph.items():
            if vertex in visited_vertices or not neighbors:
                continue

            # BFS to collect all vertices in this component
            component = []
            stack = [vertex]
            while stack:
                v = stack.pop()
                if v in visited_vertices:
                    continue
                visited_vertices.add(v)
                component.append(v)
                for nb in vertex_graph.get(v, []):
                    if nb not in visited_vertices:
                        stack.append(nb)

            # Determine which endpoints are attached to this component
            starts = set()
            ends = set()

            for color_id, roles in endpoints.items():
                # Cell endpoints: attached if any of its 4 corner vertices are in the component
                for role, locs in roles.items():
                    for loc in locs:
                        if isinstance(loc, tuple) and len(loc) == 2:
                            if loc in state.symbols:            # cell endpoint
                                r, c = loc
                                corners = [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]
                                if any(corner in component for corner in corners):
                                    if role in ("start", "both"):
                                        starts.add(loc)
                                    if role in ("end", "both"):
                                        ends.add(loc)
                            elif loc in state.vertex_symbols:    # vertex endpoint
                                if loc in component:
                                    if role in ("start", "both"):
                                        starts.add(loc)
                                    if role in ("end", "both"):
                                        ends.add(loc)

            # The component must contain at least one start and one end
            if not starts:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message="A line component has no start or both endpoint.",
                    cells=[]   # no specific cell to highlight; the whole component is wrong
                ))
            if not ends:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message="A line component has no end or both endpoint.",
                    cells=[]
                ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "BuiltinLineStructureRule":
        return cls()

    def describe(self) -> str:
        return "Lines must connect a start to an end (both counts as either)"