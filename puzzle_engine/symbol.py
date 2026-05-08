"""
Symbol module: defines the Symbol base class, a global SymbolRegistry,
and built-in NumberSymbol and EndpointSymbol.

Each symbol can restrict which places it can be placed on:
  allowed_locations = ["cell", "vertex", "edge"] (default all)
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Type


class Symbol(ABC):
    symbol_type: ClassVar[str]
    # Subclasses can override to restrict placement
    allowed_locations: ClassVar[list[str]] = ["cell", "vertex", "edge"]

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize symbol data (excluding symbol_type)."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Symbol":
        """Deserialize from dict produced by to_dict."""

    def get_implicit_rules(self) -> list:
        return []

    def display_label(self) -> str:
        return ""


class NumberSymbol(Symbol):
    """A simple integer label. By default only allowed on cells."""
    symbol_type = "number"
    allowed_locations = ["cell"]

    def __init__(self, value: int) -> None:
        self.value = value

    def to_dict(self) -> dict:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "NumberSymbol":
        return cls(data["value"])

    def display_label(self) -> str:
        return str(self.value)


class EndpointSymbol(Symbol):
    """Start/End terminal for line drawing. Only allowed on cells."""
    symbol_type = "endpoint"
    allowed_locations = ["cell"]

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


class SymbolRegistry:
    _registry: Dict[str, Type[Symbol]] = {}

    @classmethod
    def register(cls, symbol_cls: Type[Symbol]) -> Type[Symbol]:
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


SymbolRegistry.register(NumberSymbol)
SymbolRegistry.register(EndpointSymbol)