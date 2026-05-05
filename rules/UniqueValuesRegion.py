from rules._common import * 

@RuleRegistry.register
class UniqueValuesInRegion(Rule):
    """
    All cells in the region must have distinct values.
    """
    rule_type = "unique_region"
    param_schema = {
        "cells": {
            "type": "list_of_cells",
            "description": "List of [row, col] pairs",
        },
        "label": {
            "type": "str",
            "description": "Optional display label for this region",
            "default": "",
        }
    }

    def __init__(self, cells: List[CellCoord], label: str = "") -> None:
        self.region_cells = [tuple(c) for c in cells]  # type: ignore
        self.label = label

    def check(self, state: "PuzzleState") -> List[Violation]:
        values = state.player_values
        seen: Dict[Any, CellCoord] = {}
        violations = []
        for cell in self.region_cells:
            v = values.get(tuple(cell))  # type: ignore
            if v is None:
                continue
            if v in seen:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Duplicate value {v} in region '{self.label}'",
                    cells=[seen[v], cell],
                ))
            else:
                seen[v] = cell  # type: ignore
        return violations

    def to_params(self) -> dict:
        return {"cells": list(self.region_cells), "label": self.label}

    @classmethod
    def from_params(cls, params: dict) -> "UniqueValuesInRegion":
        return cls(cells=params["cells"], label=params.get("label", ""))

    def describe(self) -> str:
        suffix = f" ({self.label})" if self.label else ""
        return f"All values in region{suffix} must be unique"