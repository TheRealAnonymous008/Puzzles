from rules._common import * 


# @RuleRegistry.register
class AllCellsFilled(Rule):
    """Every active cell must have a player-assigned value."""
    rule_type = "all_cells_filled"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        empty = [c for c in state.grid.cells if state.player_values.get(c) is None]
        if empty:
            return [Violation(
                rule_id=self.rule_type,
                message=f"{len(empty)} cell(s) are still empty",
                cells=empty,
            )]
        return []

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "AllCellsFilled":
        return cls()

    def describe(self) -> str:
        return "All cells must be filled"