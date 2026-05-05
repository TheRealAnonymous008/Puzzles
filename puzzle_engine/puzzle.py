"""
Puzzle module: PuzzleState is the central model combining grid, symbols,
rules, player-assigned values, and player-drawn lines.

Design notes:
  - The *editor state* is grid shape, placed symbols, and rules.
  - The *player state* adds player_values and lines on top of editor state.
  - Lines are stored as a set of canonical Edge tuples – sorted (a,b) pairs –
    so membership is O(1) and (a,b) == (b,a).
  - Serialization uses plain lists for JSON compatibility.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import Grid, CellCoord
from puzzle_engine.symbol import Symbol, SymbolRegistry
from puzzle_engine.rule import Rule, RuleRegistry, Violation

# Canonical undirected edge: (smaller_cell, larger_cell)
Edge = Tuple[CellCoord, CellCoord]


def _make_edge(a: CellCoord, b: CellCoord) -> Edge:
    """Return a canonical (sorted) edge tuple so (a,b) == (b,a)."""
    return (min(a, b), max(a, b))


class PuzzleState:
    """
    Full puzzle state: grid + symbols + rules + player_values + lines.

    Attributes
    ----------
    grid            Active cells.
    symbols         Map of cell -> Symbol (editor-placed, immutable in play).
    rules           Ordered list of active rules.
    player_values   Map of cell -> value (set by player during play mode).
    lines           Set of canonical Edge tuples drawn by the player.
    metadata        Free-form dict (title, author, etc.).
    """

    def __init__(self) -> None:
        self.grid: Grid = Grid()
        self.symbols: Dict[CellCoord, Symbol] = {}
        self.rules: List[Rule] = []
        self.player_values: Dict[CellCoord, Any] = {}
        self.lines: Set[Edge] = set()
        self.metadata: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Grid editing
    # ------------------------------------------------------------------

    def add_cell(self, row: int, col: int) -> None:
        self.grid.add_cell(row, col)

    def remove_cell(self, row: int, col: int) -> None:
        cell = (row, col)
        self.grid.remove_cell(row, col)
        self.symbols.pop(cell, None)
        self.player_values.pop(cell, None)
        # Remove any lines that touch the removed cell
        self.lines = {e for e in self.lines if cell not in e}

    # ------------------------------------------------------------------
    # Symbol management (editor)
    # ------------------------------------------------------------------

    def place_symbol(self, row: int, col: int, symbol: Symbol) -> None:
        if not self.grid.has_cell(row, col):
            raise ValueError(f"Cell ({row}, {col}) is not active")
        self.symbols[(row, col)] = symbol

    def remove_symbol(self, row: int, col: int) -> None:
        self.symbols.pop((row, col), None)

    def get_symbol(self, row: int, col: int) -> Optional[Symbol]:
        return self.symbols.get((row, col))

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def remove_rule(self, index: int) -> None:
        if 0 <= index < len(self.rules):
            del self.rules[index]

    # ------------------------------------------------------------------
    # Player values
    # ------------------------------------------------------------------

    def set_player_value(self, row: int, col: int, value: Any) -> None:
        if not self.grid.has_cell(row, col):
            raise ValueError(f"Cell ({row}, {col}) is not active")
        self.player_values[(row, col)] = value

    def clear_player_value(self, row: int, col: int) -> None:
        self.player_values.pop((row, col), None)

    def clear_all_player_values(self) -> None:
        self.player_values.clear()

    # ------------------------------------------------------------------
    # Lines (player-drawn)
    # ------------------------------------------------------------------

    def add_line_segment(self, r1: int, c1: int, r2: int, c2: int) -> None:
        """
        Add an undirected line segment between two orthogonally adjacent cells.
        Raises ValueError if either cell is inactive or the cells are not adjacent.
        """
        a, b = (r1, c1), (r2, c2)
        if not self.grid.has_cell(r1, c1):
            raise ValueError(f"Cell ({r1},{c1}) is not active")
        if not self.grid.has_cell(r2, c2):
            raise ValueError(f"Cell ({r2},{c2}) is not active")
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            raise ValueError(f"Cells ({r1},{c1}) and ({r2},{c2}) are not orthogonally adjacent")
        self.lines.add(_make_edge(a, b))

    def remove_line_segment(self, r1: int, c1: int, r2: int, c2: int) -> None:
        """Remove the line segment between two cells (no-op if absent)."""
        self.lines.discard(_make_edge((r1, c1), (r2, c2)))

    def clear_all_lines(self) -> None:
        self.lines.clear()

    def has_line_segment(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        return _make_edge((r1, c1), (r2, c2)) in self.lines

    def lines_at(self, row: int, col: int) -> List[CellCoord]:
        """Return all cells connected to (row, col) by a line segment."""
        cell = (row, col)
        result = []
        for a, b in self.lines:
            if a == cell:
                result.append(b)
            elif b == cell:
                result.append(a)
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def check_rules(self) -> List[Violation]:
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(self))
        return violations

    def is_solved(self) -> bool:
        return len(self.check_rules()) == 0

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def snapshot_player_state(self) -> dict:
        """Snapshot player_values + lines for play/edit toggling."""
        return {
            "player_values": deepcopy(self.player_values),
            "lines": deepcopy(self.lines),
        }

    def restore_player_state(self, snapshot: dict) -> None:
        self.player_values = deepcopy(snapshot["player_values"])
        self.lines = deepcopy(snapshot["lines"])

    def editor_snapshot(self) -> dict:
        return {
            "grid": self.grid.to_dict(),
            "symbols": {
                f"{r},{c}": SymbolRegistry.serialize(sym)
                for (r, c), sym in self.symbols.items()
            },
            "rules": [rule.serialize() for rule in self.rules],
            "metadata": deepcopy(self.metadata),
        }

    def restore_editor_snapshot(self, data: dict) -> None:
        self.grid = Grid.from_dict(data["grid"])
        self.symbols = {}
        for key, sym_data in data.get("symbols", {}).items():
            r, c = map(int, key.split(","))
            self.symbols[(r, c)] = SymbolRegistry.deserialize(sym_data)
        self.rules = [RuleRegistry.deserialize(rd) for rd in data.get("rules", [])]
        self.metadata = deepcopy(data.get("metadata", {}))
        self.player_values = {}
        self.lines = set()

    # ------------------------------------------------------------------
    # Full serialization
    # ------------------------------------------------------------------

    def _serialize_lines(self) -> list:
        """Convert lines set to JSON-serializable list of [[r1,c1],[r2,c2]]."""
        return [[[a[0], a[1]], [b[0], b[1]]] for a, b in sorted(self.lines)]

    @staticmethod
    def _deserialize_lines(raw: list) -> Set[Edge]:
        result: Set[Edge] = set()
        for pair in raw:
            a, b = tuple(pair[0]), tuple(pair[1])
            result.add(_make_edge(a, b))  # type: ignore
        return result

    def to_dict(self) -> dict:
        d = self.editor_snapshot()
        d["player_values"] = {
            f"{r},{c}": v for (r, c), v in self.player_values.items()
        }
        d["lines"] = self._serialize_lines()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PuzzleState":
        state = cls()
        state.restore_editor_snapshot(data)
        for key, v in data.get("player_values", {}).items():
            r, c = map(int, key.split(","))
            state.player_values[(r, c)] = v
        state.lines = cls._deserialize_lines(data.get("lines", []))
        return state