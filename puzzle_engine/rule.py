"""
Rule module: defines the Rule base class, Violation, and the RuleRegistry.

Concrete rule implementations live in puzzle_engine/rules/.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Type

from puzzle_engine.grid import CellCoord

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from puzzle_engine.puzzle import PuzzleState


@dataclass
class Violation:
    rule_id: str
    message: str
    cells: List[CellCoord] = field(default_factory=list)


class Rule(ABC):
    """
    Abstract base for all puzzle rules.

    Subclasses must:
      - define `rule_type: ClassVar[str]`
      - define `param_schema: ClassVar[dict]`  (optional, for editor UI)
      - implement `check(state) -> list[Violation]`
      - implement `to_params() -> dict`
      - implement `from_params(params) -> Rule`
      - implement `describe() -> str`
    """
    rule_type: ClassVar[str]
    param_schema: ClassVar[dict] = {}

    @abstractmethod
    def check(self, state: "PuzzleState") -> List[Violation]:
        """Validate state; return [] if satisfied."""

    @abstractmethod
    def to_params(self) -> dict:
        """Serialize rule-specific parameters."""

    @classmethod
    @abstractmethod
    def from_params(cls, params: dict) -> "Rule":
        """Reconstruct from serialized params."""

    @abstractmethod
    def describe(self) -> str:
        """
        Concise human-readable description of this rule instance,
        including current parameter values. Shown in the editor Rules panel.
        """

    def serialize(self) -> dict:
        return {
            "rule_type": self.rule_type,
            "params": self.to_params(),
            "description": self.describe(),
        }


class RuleRegistry:
    _registry: Dict[str, Type[Rule]] = {}

    @classmethod
    def register(cls, rule_cls: Type[Rule]) -> Type[Rule]:
        key = rule_cls.rule_type
        if not key:
            raise ValueError(f"{rule_cls} must define a non-empty rule_type")
        cls._registry[key] = rule_cls
        return rule_cls

    @classmethod
    def get(cls, rule_type: str) -> Optional[Type[Rule]]:
        return cls._registry.get(rule_type)

    @classmethod
    def all_types(cls) -> List[str]:
        return list(cls._registry.keys())

    @classmethod
    def deserialize(cls, data: dict) -> Rule:
        rtype = data.get("rule_type")
        rule_cls = cls.get(rtype)
        if rule_cls is None:
            raise ValueError(f"Unknown rule type: {rtype!r}")
        return rule_cls.from_params(data.get("params", {}))

    @classmethod
    def schema(cls) -> List[dict]:
        result = []
        for rtype, rcls in cls._registry.items():
            doc = (rcls.__doc__ or "").strip()
            first_line = doc.split("\n")[0] if doc else ""
            result.append({
                "rule_type": rtype,
                "description": first_line,
                "param_schema": getattr(rcls, "param_schema", {}),
            })
        return result