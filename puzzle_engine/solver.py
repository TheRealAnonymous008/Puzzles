"""
Solver module: constraint-based backtracking solver for PuzzleState.
Now also places line segments when endpoint symbols are present.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.puzzle import PuzzleState

# Type alias for edges used in line solving
Edge = Tuple[CellCoord, CellCoord]


@dataclass
class SolveResult:
    solution_count: int = 0
    first_solution: Optional[Dict[CellCoord, Any]] = None
    solve_path: List[Tuple[CellCoord, Any]] = field(default_factory=list)
    searched_nodes: int = 0
    # NEW: store the line edges for the first solution
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
        # serialise lines if present
        if self.first_lines is not None:
            d["lines"] = [
                [[a[0], a[1]], [b[0], b[1]]] for a, b in sorted(self.first_lines)
            ]
        else:
            d["lines"] = []
        return d


# Rule types that cannot be checked until all cell values are filled
_DEFERRED_CELL_RULE_TYPES = frozenset(["all_cells_filled"])

# Rule types that cannot be checked until all line edges are assigned
_DEFERRED_LINE_RULE_TYPES = frozenset(
    ["line_connects_endpoints", "all_endpoints_connected"]
)


class Solver:
    """
    Backtracking solver for a PuzzleState.
    Automatically includes line placement when endpoint symbols are present.
    """

    def __init__(
        self,
        domain: Iterable[Any] = range(1, 10),
        max_solutions: int = 2,
    ) -> None:
        self.domain = list(domain)
        self.max_solutions = max_solutions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def solve(self, state: PuzzleState) -> SolveResult:
        """Solve *state* non‑destructively. Returns a SolveResult."""
        # Working copy of player values (do not touch original)
        working_values: Dict[CellCoord, Any] = deepcopy(state.player_values)
        # Determine cells we are free to assign
        fixed_cells = self._fixed_cells(state)
        free_cells = [c for c in sorted(state.grid.cells) if c not in fixed_cells]

        # Determine variable edges if there are endpoint symbols
        variable_edges: List[Edge] = []
        if self._has_endpoints(state):
            variable_edges = self._collect_edges(state)

        result = SolveResult()
        first_path: List[Tuple[CellCoord, Any]] = []

        self._backtrack(
            state=state,
            working_values=working_values,
            free_cells=free_cells,
            index=0,
            result=result,
            current_path=[],
            first_path_ref=first_path,
            variable_edges=variable_edges,
        )

        # Ensure solve_path is recorded
        if result.has_solution and not result.solve_path:
            result.solve_path = first_path

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _has_endpoints(state: PuzzleState) -> bool:
        """True if at least one endpoint symbol is placed."""
        for sym in state.symbols.values():
            if hasattr(sym, 'symbol_type') and sym.symbol_type == 'endpoint':
                return True
        return False

    @staticmethod
    def _collect_edges(state: PuzzleState) -> List[Edge]:
        """Return all orthogonally adjacent active cell pairs that could contain a line."""
        edges = []
        for (r, c) in state.grid.cells:
            for (dr, dc) in ((0, 1), (1, 0)):  # right & down to avoid duplicates
                nr, nc = r + dr, c + dc
                if state.grid.has_cell(nr, nc):
                    edges.append(((r, c), (nr, nc)))
        return edges

    @staticmethod
    def _fixed_cells(state: PuzzleState) -> Set[CellCoord]:
        """Cells that already have a value and should not be overwritten."""
        fixed = set()
        for cell, sym in state.symbols.items():
            label = sym.display_label()
            if label:  # treat any labelled symbol as pre‑filled
                fixed.add(cell)
        return fixed

    def _apply_fixed(
        self, state: PuzzleState, working_values: Dict[CellCoord, Any]
    ) -> None:
        for cell, sym in state.symbols.items():
            label = sym.display_label()
            if label:
                try:
                    working_values[cell] = int(label)
                except ValueError:
                    working_values[cell] = label

    def _check_rules_with_state(
        self,
        state: PuzzleState,
        working_values: Dict[CellCoord, Any],
        working_lines: Optional[Set[Edge]] = None,
        deferred_types: frozenset = frozenset(),
    ) -> bool:
        """
        Temporarily swap player_values (and optionally lines),
        run rules except those in deferred_types, and return True if no violations.
        """
        old_values = state.player_values
        state.player_values = working_values
        if working_lines is not None:
            old_lines = state.lines
            state.lines = working_lines

        violations = []
        for rule in state.rules:
            if rule.rule_type in deferred_types:
                continue
            violations.extend(rule.check(state))

        # restore
        state.player_values = old_values
        if working_lines is not None:
            state.lines = old_lines

        return len(violations) == 0

    # ------------------------------------------------------------------
    # Backtracking – cell values
    # ------------------------------------------------------------------
    def _backtrack(
        self,
        state: PuzzleState,
        working_values: Dict[CellCoord, Any],
        free_cells: List[CellCoord],
        index: int,
        result: SolveResult,
        current_path: List[Tuple[CellCoord, Any]],
        first_path_ref: List[Tuple[CellCoord, Any]],
        variable_edges: List[Edge],
    ) -> None:
        result.searched_nodes += 1
        if result.solution_count >= self.max_solutions:
            return

        # Early pruning on cell values (skip deferred cell rules)
        # Build merged state (fixed givens + current assignments)
        merged = dict(working_values)
        self._apply_fixed(state, merged)
        if not self._check_rules_with_state(state, merged, deferred_types=_DEFERRED_CELL_RULE_TYPES):
            return

        # If all cell values have been assigned, proceed to line placement
        if index == len(free_cells):
            if variable_edges:
                # Start line backtracking with an empty line set
                self._backtrack_lines(
                    state=state,
                    working_values=merged,  # merged already includes fixed values
                    working_lines=set(),
                    variable_edges=variable_edges,
                    edge_index=0,
                    result=result,
                    current_path=current_path,
                    first_path_ref=first_path_ref,
                )
            else:
                # No line variables, check full rules (including deferred)
                old = state.player_values
                state.player_values = merged
                valid = state.is_solved()
                state.player_values = old
                if valid:
                    result.solution_count += 1
                    if result.first_solution is None:
                        result.first_solution = deepcopy(merged)
                        first_path_ref.extend(current_path)
            return

        # Assign next free cell
        cell = free_cells[index]
        for value in self.domain:
            working_values[cell] = value
            current_path.append((cell, value))
            self._backtrack(
                state, working_values, free_cells, index + 1,
                result, current_path, first_path_ref, variable_edges,
            )
            current_path.pop()
            if result.solution_count >= self.max_solutions:
                break
        del working_values[cell]

    # ------------------------------------------------------------------
    # Backtracking – line edges
    # ------------------------------------------------------------------
    def _backtrack_lines(
        self,
        state: PuzzleState,
        working_values: Dict[CellCoord, Any],
        working_lines: Set[Edge],
        variable_edges: List[Edge],
        edge_index: int,
        result: SolveResult,
        current_path: List[Tuple[CellCoord, Any]],
        first_path_ref: List[Tuple[CellCoord, Any]],
    ) -> None:
        """Recursively assign each edge (true/false) with pruning."""
        result.searched_nodes += 1
        if result.solution_count >= self.max_solutions:
            return

        # Early pruning with non‑deferred line rules
        if not self._check_rules_with_state(
            state, working_values, working_lines,
            deferred_types=_DEFERRED_LINE_RULE_TYPES,
        ):
            return

        if edge_index == len(variable_edges):
            # All edges assigned – full rule check
            old_values = state.player_values
            old_lines = state.lines
            state.player_values = working_values
            state.lines = working_lines
            valid = state.is_solved()
            state.player_values = old_values
            state.lines = old_lines
            if valid:
                result.solution_count += 1
                if result.first_solution is None:
                    result.first_solution = deepcopy(working_values)
                    result.first_lines = deepcopy(working_lines)
                    # current_path contains cell assignments; we do not record line decisions in the trace
                    first_path_ref.extend(current_path)
            return

        edge = variable_edges[edge_index]

        # Option 0: no line
        self._backtrack_lines(
            state, working_values, working_lines, variable_edges,
            edge_index + 1, result, current_path, first_path_ref,
        )
        if result.solution_count >= self.max_solutions:
            return

        # Option 1: add line
        working_lines.add(edge)
        self._check_rules_with_state(
            state, working_values, working_lines,
            deferred_types=_DEFERRED_LINE_RULE_TYPES,
        )  # run pruning again (redundant check, but safe)
        self._backtrack_lines(
            state, working_values, working_lines, variable_edges,
            edge_index + 1, result, current_path, first_path_ref,
        )
        working_lines.discard(edge)