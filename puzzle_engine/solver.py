"""
Solver module: constraint-based backtracking solver for PuzzleState.

Design
------
The solver works by iterating over *unassigned* cells and trying each
value from a configurable domain.  After each assignment it runs all
rules; if any rule fires a *definitive* violation (i.e. one that cannot
be fixed by filling more cells) the branch is pruned immediately.

Configurable knobs:
  - `domain`          – iterable of candidate values to try per cell
  - `max_solutions`   – cap on how many solutions to enumerate (default 2,
                        just enough to know "unique or not")
  - `ordered_cells`   – optionally supply a custom cell ordering heuristic

SolveResult
-----------
Holds:
  - solution_count   number of solutions found (up to max_solutions)
  - first_solution   dict[CellCoord, value] for one solution
  - solve_path       ordered list of (cell, value) assignments that led
                     to the first solution (the *solve trace*)
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from puzzle_engine.grid import CellCoord
from puzzle_engine.puzzle import PuzzleState


@dataclass
class SolveResult:
    solution_count: int = 0
    first_solution: Optional[Dict[CellCoord, Any]] = None
    solve_path: List[Tuple[CellCoord, Any]] = field(default_factory=list)
    searched_nodes: int = 0

    @property
    def is_unique(self) -> bool:
        return self.solution_count == 1

    @property
    def has_solution(self) -> bool:
        return self.solution_count > 0

    def to_dict(self) -> dict:
        return {
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


class Solver:
    """
    Backtracking solver for a PuzzleState.

    Parameters
    ----------
    domain        Candidate values to assign to each empty cell.
                  Defaults to 1..9 (suitable for many number puzzles).
    max_solutions Maximum solutions to enumerate before stopping.
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
        """
        Solve *state* non-destructively.  Returns a SolveResult.
        The original state is not modified.
        """
        # Work on a fresh player-value dict so we don't clobber the caller
        working_values: Dict[CellCoord, Any] = deepcopy(state.player_values)

        # Determine cells we are allowed to fill (those without a fixed symbol
        # value — symbols are editor-placed and treated as givens)
        fixed_cells = self._fixed_cells(state)
        free_cells = [c for c in sorted(state.grid.cells) if c not in fixed_cells]

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
        )

        if result.has_solution and not result.solve_path:
            result.solve_path = first_path

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fixed_cells(self, state: PuzzleState) -> set:
        """
        Cells that already have a value and should not be overwritten.
        Currently: cells with symbols that expose a numeric value.
        """
        fixed = set()
        for cell, sym in state.symbols.items():
            label = sym.display_label()
            if label:  # treat any labelled symbol as pre-filled
                fixed.add(cell)
        return fixed

    def _apply_fixed(
        self, state: PuzzleState, working_values: Dict[CellCoord, Any]
    ) -> None:
        """Copy symbol display values into working_values as givens."""
        for cell, sym in state.symbols.items():
            label = sym.display_label()
            if label:
                try:
                    working_values[cell] = int(label)
                except ValueError:
                    working_values[cell] = label

    def _check_with_values(
        self, state: PuzzleState, working_values: Dict[CellCoord, Any]
    ) -> bool:
        """
        Run all rules against a temporary state built from working_values.
        Returns True if no violations are found.
        """
        # Temporarily swap player values
        old_values = state.player_values
        state.player_values = working_values
        violations = state.check_rules()
        state.player_values = old_values
        return len(violations) == 0

    # Rule types that require a complete board — skip during intermediate pruning
    _DEFERRED_RULE_TYPES: frozenset = frozenset(["all_cells_filled"])

    def _backtrack(
        self,
        state: PuzzleState,
        working_values: Dict[CellCoord, Any],
        free_cells: List[CellCoord],
        index: int,
        result: SolveResult,
        current_path: List[Tuple[CellCoord, Any]],
        first_path_ref: List[Tuple[CellCoord, Any]],
    ) -> None:
        result.searched_nodes += 1

        if result.solution_count >= self.max_solutions:
            return

        # Build merged state (fixed givens + current working assignments)
        merged = dict(working_values)
        self._apply_fixed(state, merged)

        if index == len(free_cells):
            # Terminal: run ALL rules
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

        # Intermediate: only run rules safe for partial states
        old = state.player_values
        state.player_values = merged
        early_violations = [
            v
            for rule in state.rules
            if rule.rule_type not in self._DEFERRED_RULE_TYPES
            for v in rule.check(state)
        ]
        state.player_values = old

        if early_violations:
            return  # Prune branch

        cell = free_cells[index]

        for value in self.domain:
            working_values[cell] = value
            current_path.append((cell, value))

            self._backtrack(
                state, working_values, free_cells,
                index + 1, result, current_path, first_path_ref,
            )

            current_path.pop()

            if result.solution_count >= self.max_solutions:
                break

        del working_values[cell]