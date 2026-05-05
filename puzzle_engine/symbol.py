"""
Symbol module: defines the Symbol base class and a global SymbolRegistry.

Symbols occupy cells and may carry data.  They can optionally attach
rules to the puzzle (e.g. a "given digit" symbol for Sudoku auto-adds
a constraint).  For now the default symbol is just a labelled number.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Type


class Symbol(ABC):
    """
    Abstract base for all symbols that can be placed on grid cells.

    Subclasses must:
      - define `symbol_type: str` (unique identifier)
      - implement `to_dict` / `from_dict` for serialization
      - optionally override `get_implicit_rules` to inject rules
        when the symbol is placed
    """
    symbol_type: ClassVar[str]

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize symbol data (excluding symbol_type)."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Symbol":
        """Deserialize from dict produced by to_dict."""

    def get_implicit_rules(self) -> list:
        """
        Return a list of Rule instances that this symbol implicitly adds
        when placed on the grid.  Most symbols return [].
        """
        return []

    def display_label(self) -> str:
        """Human-readable label shown on the cell in the editor/player."""
        return ""


# ---------------------------------------------------------------------------
# Concrete built-in symbol: NumberSymbol
# ---------------------------------------------------------------------------

class NumberSymbol(Symbol):
    """A simple integer label on a cell.  No implicit rules by default."""
    symbol_type = "number"

    def __init__(self, value: int) -> None:
        self.value = value

    def to_dict(self) -> dict:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "NumberSymbol":
        return cls(data["value"])

    def display_label(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class SymbolRegistry:
    """
    Global registry mapping symbol_type strings to Symbol subclasses.
    Use `register` to add new symbol types at runtime.
    """
    _registry: Dict[str, Type[Symbol]] = {}

    @classmethod
    def register(cls, symbol_cls: Type[Symbol]) -> Type[Symbol]:
        """
        Register a Symbol subclass.  Can be used as a decorator:

            @SymbolRegistry.register
            class MySymbol(Symbol): ...
        """
        key = symbol_cls.symbol_type
        if not key:
            raise ValueError(f"{symbol_cls} must define a non-empty symbol_type")
        cls._registry[key] = symbol_cls
        return symbol_cls

    @classmethod
    def get(cls, symbol_type: str) -> Optional[Type[Symbol]]:
        return cls._registry.get(symbol_type)

    @classmethod
    def all_types(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def deserialize(cls, data: dict) -> Symbol:
        stype = data.get("symbol_type")
        sym_cls = cls.get(stype)
        if sym_cls is None:
            raise ValueError(f"Unknown symbol type: {stype!r}")
        return sym_cls.from_dict(data)

    @classmethod
    def serialize(cls, symbol: Symbol) -> dict:
        d = symbol.to_dict()
        d["symbol_type"] = symbol.symbol_type
        return d


# Register built-ins
SymbolRegistry.register(NumberSymbol)

# ---------------------------------------------------------------------------
# EndpointSymbol – marks a cell as a Start or End for line-drawing puzzles
# ---------------------------------------------------------------------------

class EndpointSymbol(Symbol):
    """
    Marks a cell as a Start or End terminal for a line-drawing puzzle.

    Attributes
    ----------
    role        "start" or "end"
    color_id    Integer ≥ 0. Start and End with the same color_id must be
                connected by a line. Rendered as a distinct color in the UI.
    """
    symbol_type = "endpoint"

    ROLES = ("start", "end")

    def __init__(self, role: str, color_id: int) -> None:
        if role not in self.ROLES:
            raise ValueError(f"role must be one of {self.ROLES}, got {role!r}")
        self.role = role
        self.color_id = int(color_id)

    def to_dict(self) -> dict:
        return {"role": self.role, "color_id": self.color_id}

    @classmethod
    def from_dict(cls, data: dict) -> "EndpointSymbol":
        return cls(role=data["role"], color_id=int(data["color_id"]))

    def display_label(self) -> str:
        return "S" if self.role == "start" else "E"

    def __repr__(self) -> str:
        return f"EndpointSymbol(role={self.role!r}, color_id={self.color_id})"


SymbolRegistry.register(EndpointSymbol)