"""
Grid module: represents a variable-shape 2D grid as a set of active cells.
Cells are identified by (row, col) integer tuples.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator, Set, Tuple

CellCoord = Tuple[int, int]


@dataclass
class Grid:
    """
    A 2D grid whose shape is defined by an explicit set of active cells.
    Not necessarily rectangular — cells can be added/removed freely.
    """
    _cells: Set[CellCoord] = field(default_factory=set)

    # ------------------------------------------------------------------
    # Cell management
    # ------------------------------------------------------------------

    def add_cell(self, row: int, col: int) -> None:
        self._cells.add((row, col))

    def remove_cell(self, row: int, col: int) -> None:
        self._cells.discard((row, col))

    def has_cell(self, row: int, col: int) -> bool:
        return (row, col) in self._cells

    @property
    def cells(self) -> frozenset[CellCoord]:
        return frozenset(self._cells)

    def __len__(self) -> int:
        return len(self._cells)

    def __iter__(self) -> Iterator[CellCoord]:
        return iter(self._cells)

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def neighbors(self, row: int, col: int) -> list[CellCoord]:
        """Return the 4-directional active neighbors of a cell."""
        candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
        return [c for c in candidates if c in self._cells]

    def diagonal_neighbors(self, row: int, col: int) -> list[CellCoord]:
        """Return all 8-directional active neighbors of a cell."""
        candidates = [
            (row + dr, col + dc)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)
        ]
        return [c for c in candidates if c in self._cells]

    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Return (min_row, min_col, max_row, max_col)."""
        if not self._cells:
            return (0, 0, 0, 0)
        rows = [r for r, _ in self._cells]
        cols = [c for _, c in self._cells]
        return min(rows), min(cols), max(rows), max(cols)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"cells": list(self._cells)}

    @classmethod
    def from_dict(cls, data: dict) -> "Grid":
        g = cls()
        for r, c in data.get("cells", []):
            g.add_cell(r, c)
        return g

    @classmethod
    def make_rectangle(cls, rows: int, cols: int) -> "Grid":
        """Convenience factory for a standard rectangular grid."""
        g = cls()
        for r in range(rows):
            for c in range(cols):
                g.add_cell(r, c)
        return g