"""
Solver module: backtracking line solver for PuzzleState.
Only places line segments – no cell value assignment is attempted.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.puzzle import PuzzleState

Edge = Tuple[CellCoord, CellCoord]


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
            "solve_path": (
                [{"cell": list(cell), "value": v} for cell, v in self.solve_path]
            ),
        }
        if self.first_lines is not None:
            d["lines"] = [
                [[a[0], a[1]], [b[0], b[1]]] for a, b in sorted(self.first_lines)
            ]
        else:
            d["lines"] = []
        return d


class Solver:
    """Backtracking solver that only places lines. Cell values are left as they are."""

    def __init__(self, max_solutions: int = 2) -> None:
        self.max_solutions = max_solutions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def solve(self, state: PuzzleState) -> SolveResult:
        result = SolveResult()

        # Only handle line placement if endpoint symbols exist
        if not self._has_endpoints(state):
            # No line puzzle – just check current state
            result.searched_nodes = 1
            if state.is_solved():
                result.solution_count = 1
                result.first_solution = dict(state.player_values)
                result.first_lines = set(state.lines)
            return result

        variable_edges = self._collect_edges(state)
        result = SolveResult()
        self._backtrack_lines(
            state,
            set(),
            variable_edges,
            0,
            result,
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _has_endpoints(state: PuzzleState) -> bool:
        for sym in state.symbols.values():
            if getattr(sym, "symbol_type", None) == "endpoint":
                return True
        for sym in state.vertex_symbols.values():
            if getattr(sym, "symbol_type", None) == "endpoint":
                return True
        return False

    @staticmethod
    def _collect_edges(state: PuzzleState) -> List[Edge]:
        edges = []
        for (r, c) in state.grid.cells:
            for (dr, dc) in ((0, 1), (1, 0)):
                nr, nc = r + dr, c + dc
                if state.grid.has_cell(nr, nc):
                    edges.append(((r, c), (nr, nc)))
        return edges

    # ------------------------------------------------------------------
    # Backtracking – line edges only
    # ------------------------------------------------------------------
    def _backtrack_lines(
        self,
        state: PuzzleState,
        working_lines: Set[Edge],
        variable_edges: List[Edge],
        edge_index: int,
        result: SolveResult,
    ) -> None:
        result.searched_nodes += 1
        if result.solution_count >= self.max_solutions:
            return

        if edge_index == len(variable_edges):
            # All edges decided – check full state
            old_lines = state.lines
            state.lines = working_lines
            valid = state.is_solved()
            state.lines = old_lines
            if valid:
                result.solution_count += 1
                if result.first_lines is None:
                    result.first_lines = deepcopy(working_lines)
                    result.first_solution = dict(state.player_values)
            return

        edge = variable_edges[edge_index]

        # Option: don't draw this edge
        self._backtrack_lines(state, working_lines, variable_edges, edge_index + 1, result)
        if result.solution_count >= self.max_solutions:
            return

        # Option: draw this edge
        working_lines.add(edge)
        self._backtrack_lines(state, working_lines, variable_edges, edge_index + 1, result)
        working_lines.discard(edge)