from rules._common import * 

@RuleRegistry.register
class AllEndpointsConnected(Rule):
    """
    All endpoint pairs must be fully connected and no dangling line segments
    may exist. Combines connectivity and completeness checks.
    Add this rule when you want to require the puzzle to be fully solved.
    """
    rule_type = "all_endpoints_connected"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []
        endpoints_by_color = collect_endpoints(state)

        if not endpoints_by_color:
            return []

        adj = build_adjacency(state)
        all_endpoints: Set[CellCoord] = set()
        for data in endpoints_by_color.values():
            all_endpoints.update(data["start"])
            all_endpoints.update(data["end"])

        # Every endpoint must have exactly one connection
        for color_id, data in sorted(endpoints_by_color.items()):
            for role, cells in data.items():
                for cell in cells:
                    deg = len(adj.get(cell, []))
                    if deg == 0:
                        violations.append(Violation(
                            rule_id=self.rule_type,
                            message=f"Color {color_id} {role.capitalize()} at {cell} is not connected",
                            cells=[cell],
                        ))
                    elif deg > 1:
                        violations.append(Violation(
                            rule_id=self.rule_type,
                            message=f"Color {color_id} {role.capitalize()} at {cell} has {deg} connections",
                            cells=[cell],
                        ))

        # No dangling segments (non-endpoint cells with degree 1)
        for cell, neighbors in adj.items():
            if cell not in all_endpoints and len(neighbors) == 1:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Dangling line segment at {cell} (dead end, not an endpoint)",
                    cells=[cell],
                ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "AllEndpointsConnectedRule":
        return cls()

    def describe(self) -> str:
        return "All Start/End pairs must be fully connected with no dangling segments"