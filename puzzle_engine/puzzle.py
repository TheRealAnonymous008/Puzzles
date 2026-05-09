"""
Puzzle module: PuzzleState is the central model combining grid, symbols,
rules, player-assigned values, and player-drawn lines.

Design notes:
  - The *editor state* is grid shape, placed symbols, and rules.
  - The *player state* adds player_values and lines on top of editor state.
  - Lines are stored as a set of canonical Edge tuples – sorted (a,b) pairs –
    so membership is O(1) and (a,b) == (b,a).
  - Symbols can be placed on cells, vertices, and edges.
    Serialization uses prefixed keys to distinguish them.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle_engine.grid import Grid, CellCoord
from puzzle_engine.symbol import Symbol, SymbolRegistry
from puzzle_engine.rule import Rule, RuleRegistry, Violation
from rules.line_structure import BuiltinLineStructureRule

# Canonical undirected edge: (smaller_cell, larger_cell)
Edge = Tuple[CellCoord, CellCoord]
# Vertex coordinate – top‑left corner of a cell
VertexCoord = Tuple[int, int]
# Canonical edge between two adjacent vertices
VertexEdge = Tuple[VertexCoord, VertexCoord]


def _make_edge(a: CellCoord, b: CellCoord) -> Edge:
    return (min(a, b), max(a, b))

def _make_vertex_edge(a: VertexCoord, b: VertexCoord) -> VertexEdge:
    return (min(a, b), max(a, b))

class PuzzleState:
    BUILT_IN_RULES = [BuiltinLineStructureRule()]

    def __init__(self) -> None:

        self.grid: Grid = Grid()
        self.symbols: Dict[CellCoord, Symbol] = {}           # cell symbols (backward compat)
        self.rules: List[Rule] = []
        self.player_values: Dict[CellCoord, Any] = {}
        self.lines: Set[VertexEdge] = set()
        self.metadata: Dict[str, Any] = {}

        # new – symbols on vertices and edges
        self.vertex_symbols: Dict[VertexCoord, Symbol] = {}
        self.edge_symbols: Dict[VertexEdge, Symbol] = {}

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
    # Symbol management (editor) – cell symbols
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
    # Vertex symbols
    # ------------------------------------------------------------------
    def place_vertex_symbol(self, row: int, col: int, symbol: Symbol) -> None:
        """Place a symbol at the vertex (row, col)."""
        if "vertex" not in symbol.allowed_locations:
            raise ValueError(f"{symbol.symbol_type} cannot be placed on a vertex")
        self.vertex_symbols[(row, col)] = symbol

    def remove_vertex_symbol(self, row: int, col: int) -> None:
        self.vertex_symbols.pop((row, col), None)

    def get_vertex_symbol(self, row: int, col: int) -> Optional[Symbol]:
        return self.vertex_symbols.get((row, col))

    # ------------------------------------------------------------------
    # Edge symbols
    # ------------------------------------------------------------------
    def place_edge_symbol(self, r1: int, c1: int, r2: int, c2: int, symbol: Symbol) -> None:
        """Place a symbol on the edge between vertices (r1,c1) and (r2,c2)."""
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            raise ValueError("Vertex edge must be between orthogonally adjacent vertices")
        if "edge" not in symbol.allowed_locations:
            raise ValueError(f"{symbol.symbol_type} cannot be placed on an edge")
        edge = _make_vertex_edge((r1, c1), (r2, c2))
        self.edge_symbols[edge] = symbol

    def remove_edge_symbol(self, r1: int, c1: int, r2: int, c2: int) -> None:
        edge = _make_vertex_edge((r1, c1), (r2, c2))
        self.edge_symbols.pop(edge, None)

    def get_edge_symbol(self, r1: int, c1: int, r2: int, c2: int) -> Optional[Symbol]:
        edge = _make_vertex_edge((r1, c1), (r2, c2))
        return self.edge_symbols.get(edge)

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
        """Add line as cell pair – stored as vertex edge separating them."""
        a, b = (r1, c1), (r2, c2)
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            raise ValueError("Cells must be orthogonally adjacent")
        # Convert to shared vertex edge
        if r1 == r2:                 # horizontal adjacency → vertical vertex edge
            row = r1
            col_right = max(c1, c2)
            v1, v2 = (row, col_right), (row + 1, col_right)
        else:                        # vertical adjacency → horizontal vertex edge
            col = c1
            row_bottom = max(r1, r2)
            v1, v2 = (row_bottom, col), (row_bottom, col + 1)
        self.lines.add(_make_vertex_edge(v1, v2))

    def remove_line_segment(self, r1: int, c1: int, r2: int, c2: int) -> None:
        if r1 == r2:
            row = r1
            col_right = max(c1, c2)
            v1, v2 = (row, col_right), (row + 1, col_right)
        else:
            col = c1
            row_bottom = max(r1, r2)
            v1, v2 = (row_bottom, col), (row_bottom, col + 1)
        self.lines.discard(_make_vertex_edge(v1, v2))

    def has_line_segment(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        if r1 == r2:
            row = r1; col_right = max(c1, c2)
            v1, v2 = (row, col_right), (row + 1, col_right)
        else:
            col = c1; row_bottom = max(r1, r2)
            v1, v2 = (row_bottom, col), (row_bottom, col + 1)
        return _make_vertex_edge(v1, v2) in self.lines

    def lines_at(self, row: int, col: int) -> List[CellCoord]:
        """Return neighbouring cells connected by a line from (row,col) – still cell‑based."""
        result = []
        for (vr, vc) in [(row, col), (row, col+1), (row+1, col), (row+1, col+1)]:
            for dr, dc in [(0,1),(1,0)]:
                nr, nc = vr+dr, vc+dc
                edge = _make_vertex_edge((vr, vc), (nr, nc))
                if edge in self.lines:
                    # Convert back to cell neighbour
                    if dr == 0:   # horizontal vertex edge -> cells: (vr-1, vc) and (vr, vc)
                        cell1 = (vr-1, vc)
                        cell2 = (vr, vc)
                    else:         # vertical vertex edge -> cells: (vr, vc-1) and (vr, vc)
                        cell1 = (vr, vc-1)
                        cell2 = (vr, vc)
                    if cell1 == (row, col):
                        result.append(cell2)
                    elif cell2 == (row, col):
                        result.append(cell1)
        return result

    def clear_all_lines(self) -> None:
        self.lines.clear()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def check_rules(self) -> List[Violation]:
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(self))
        for rule in self.BUILT_IN_RULES:
            violations.extend(rule.check(self))
        return violations

    def is_solved(self) -> bool:
        return len(self.check_rules()) == 0

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------
    def snapshot_player_state(self) -> dict:
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
            "symbols": self._serialize_symbols(),
            "rules": [rule.serialize() for rule in self.rules],
            "metadata": deepcopy(self.metadata),
        }

    def restore_editor_snapshot(self, data: dict) -> None:
        self.grid = Grid.from_dict(data["grid"])
        self._deserialize_symbols(data.get("symbols", {}))
        self.rules = [RuleRegistry.deserialize(rd) for rd in data.get("rules", [])]
        self.metadata = deepcopy(data.get("metadata", {}))
        self.player_values = {}
        self.lines = set()

    # ------------------------------------------------------------------
    # Full serialization
    # ------------------------------------------------------------------
    def _serialize_lines(self) -> list:
        return [[[v1[0], v1[1]], [v2[0], v2[1]]] for v1, v2 in sorted(self.lines)]

    @staticmethod
    def _deserialize_lines(raw: list) -> Set[VertexEdge]:
        result = set()
        for pair in raw:
            v1 = tuple(pair[0])
            v2 = tuple(pair[1])
            result.add(_make_vertex_edge(v1, v2))
        return result

    def _serialize_symbols(self) -> dict:
        """Unified symbol serialization with prefixed keys."""
        result = {}
        # cell symbols: key "c:{r},{c}"
        for (r, c), sym in self.symbols.items():
            result[f"c:{r},{c}"] = SymbolRegistry.serialize(sym)
        # vertex symbols: key "v:{r},{c}"
        for (r, c), sym in self.vertex_symbols.items():
            result[f"v:{r},{c}"] = SymbolRegistry.serialize(sym)
        # edge symbols: key "e:{r1},{c1}-{r2},{c2}" with sorted vertices
        for (v1, v2), sym in self.edge_symbols.items():
            r1, c1 = v1
            r2, c2 = v2
            result[f"e:{r1},{c1}-{r2},{c2}"] = SymbolRegistry.serialize(sym)
        return result

    def _deserialize_symbols(self, data: dict) -> None:
        """Populate cell/vertex/edge symbols from a prefixed-key dict."""
        self.symbols.clear()
        self.vertex_symbols.clear()
        self.edge_symbols.clear()
        for key, sym_data in data.items():
            sym = SymbolRegistry.deserialize(sym_data)
            if key.startswith("c:"):
                r, c = map(int, key[2:].split(","))
                self.symbols[(r, c)] = sym
            elif key.startswith("v:"):
                r, c = map(int, key[2:].split(","))
                self.vertex_symbols[(r, c)] = sym
            elif key.startswith("e:"):
                parts = key[2:].split("-")
                v1 = tuple(map(int, parts[0].split(",")))
                v2 = tuple(map(int, parts[1].split(",")))
                edge = _make_vertex_edge(v1, v2)
                self.edge_symbols[edge] = sym
            else:
                # backward compat – old "r,c" style treated as cell symbol
                r, c = map(int, key.split(","))
                self.symbols[(r, c)] = sym

    def _vertex_edge_to_cell_edge(self, v1: VertexCoord, v2: VertexCoord) -> Edge:
        r1, c1 = v1; r2, c2 = v2
        if r1 == r2:          # horizontal edge
            row = r1
            col = min(c1, c2)
            cell1, cell2 = (row-1, col), (row, col)
        else:                 # vertical edge
            col = c1
            row = min(r1, r2)
            cell1, cell2 = (row, col-1), (row, col)
        return tuple(sorted((cell1, cell2)))

    def to_dict(self) -> dict:
        d = self.editor_snapshot()          # now uses _serialize_symbols
        d["player_values"] = {
            f"{r},{c}": v for (r, c), v in self.player_values.items()
        }
        d["lines"] = [[[a[0], a[1]], [b[0], b[1]]] for v1, v2 in sorted(self.lines)
              for a, b in [self._vertex_edge_to_cell_edge(v1, v2)]]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PuzzleState":
        state = cls()
        state.restore_editor_snapshot(data)  # handles symbols with prefixes
        for key, v in data.get("player_values", {}).items():
            r, c = map(int, key.split(","))
            state.player_values[(r, c)] = v
        state.lines = cls._deserialize_lines(data.get("lines", []))
        return state