from rules._common import * 

@RuleRegistry.register
class LineConnectsEndpoints(Rule):
    """
    Every Start cell must be connected by a continuous line to exactly one
    End cell of the same color, with no branching or loops.
    This is the core rule for line-drawing (Numberlink-style) puzzles.
    """
    rule_type = "line_connects_endpoints"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []
        endpoints_by_color = collect_endpoints(state)

        if not endpoints_by_color:
            return []  # No endpoints placed yet

        adj = build_adjacency(state)
        all_endpoints: Set[CellCoord] = set()
        for color_data in endpoints_by_color.values():
            all_endpoints.update(color_data["start"])
            all_endpoints.update(color_data["end"])

        for color_id, color_data in sorted(endpoints_by_color.items()):
            starts = color_data["start"]
            ends   = color_data["end"]

            if len(starts) != 1 or len(ends) != 1:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Color {color_id}: expected exactly 1 Start and 1 End "
                            f"(found {len(starts)} starts, {len(ends)} ends)",
                    cells=starts + ends,
                ))
                continue

            start_cell = starts[0]
            end_cell   = ends[0]

            # Check start has exactly one line connection
            start_degree = len(adj.get(start_cell, []))
            if start_degree == 0:
                # Not yet drawn — silent (puzzle incomplete, not violated)
                continue
            if start_degree > 1:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Color {color_id}: Start cell {start_cell} has "
                            f"{start_degree} line connections (must have 1)",
                    cells=[start_cell],
                ))
                continue

            # Trace from start
            path = _trace_path(start_cell, adj, all_endpoints)
            if path is None:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Color {color_id}: line from Start {start_cell} "
                            f"branches or loops",
                    cells=[start_cell],
                ))
                continue

            # Path must terminate at the correct end cell
            terminal = path[-1]
            if terminal != end_cell:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Color {color_id}: line from Start {start_cell} "
                            f"reaches {terminal} instead of End {end_cell}",
                    cells=[start_cell, terminal, end_cell],
                ))
                continue

            # End cell must also have exactly one connection
            end_degree = len(adj.get(end_cell, []))
            if end_degree > 1:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Color {color_id}: End cell {end_cell} has "
                            f"{end_degree} connections (must have 1)",
                    cells=[end_cell],
                ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "LineConnectsEndpoints":
        return cls()

    def describe(self) -> str:
        return "Each Start cell must connect to its matching End cell via a continuous line"

