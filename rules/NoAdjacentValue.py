from rules._common import * 

@RuleRegistry.register
class NoAdjacentValue(Rule):
    """
    No two adjacent (4-directional) cells may share the same player value.
    Optionally restrict to a specific value X (None = all values).
    """
    rule_type = "no_adjacent_value"
    param_schema = {
        "forbidden_value": {
            "type": "int_or_null",
            "description": "If set, only this value is forbidden from being adjacent. "
                           "If null, no two adjacent cells may share any value.",
            "default": None,
        }
    }

    def __init__(self, forbidden_value: Optional[int] = None) -> None:
        self.forbidden_value = forbidden_value

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations = []
        values = state.player_values   # dict[CellCoord, Any]
        for cell in state.grid.cells:
            v = values.get(cell)
            if v is None:
                continue
            if self.forbidden_value is not None and v != self.forbidden_value:
                continue
            for neighbor in state.grid.neighbors(*cell):
                nv = values.get(neighbor)
                if nv is not None and nv == v:
                    # Deduplicate by canonical ordering
                    pair = tuple(sorted([cell, neighbor]))
                    msg = (
                        f"Adjacent cells {cell} and {neighbor} "
                        f"both have value {v}"
                    )
                    dup = any(
                        viol.cells == list(pair) for viol in violations
                    )
                    if not dup:
                        violations.append(Violation(
                            rule_id=self.rule_type,
                            message=msg,
                            cells=list(pair),
                        ))
        return violations

    def to_params(self) -> dict:
        return {"forbidden_value": self.forbidden_value}

    @classmethod
    def from_params(cls, params: dict) -> "NoAdjacentValue":
        return cls(forbidden_value=params.get("forbidden_value"))

    def describe(self) -> str:
        if self.forbidden_value is not None:
            return f"No adjacent cells may both contain {self.forbidden_value}"
        return "No two adjacent cells may share the same value"
