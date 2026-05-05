from rules._common import * 

@RuleRegistry.register
class NoLineOverlap(Rule):
    """
    No cell may be covered by two different line paths.
    Each non-endpoint cell on a line must have exactly 2 line connections
    (enter and exit). Endpoint cells must have exactly 1.
    Lines of different colors may not share any cell.
    """
    rule_type = "no_line_overlap"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []

        if not state.lines:
            return []

        adj = build_adjacency(state)
        endpoints_by_color = collect_endpoints(state)

        # Build a map from cell -> color_id for endpoint cells
        cell_color: Dict[CellCoord, int] = {}
        all_endpoints: Set[CellCoord] = set()
        for color_id, data in endpoints_by_color.items():
            for cell in data["start"] + data["end"]:
                cell_color[cell] = color_id
                all_endpoints.add(cell)

        # For each connected component of lines, determine which color it belongs to
        visited: Set[CellCoord] = set()
        # Map cell -> color determined from which endpoint it's connected to
        cell_line_color: Dict[CellCoord, int] = {}

        # BFS flood fill from endpoint cells to color-label every line cell
        queue: deque = deque()
        for color_id, data in endpoints_by_color.items():
            for cell in data["start"] + data["end"]:
                if cell in adj:
                    queue.append((cell, color_id))
                    cell_line_color[cell] = color_id

        while queue:
            cell, color = queue.popleft()
            if cell in visited:
                continue
            visited.add(cell)
            for nb in adj.get(cell, []):
                if nb in cell_line_color and cell_line_color[nb] != color:
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Lines of different colors meet at or near {nb}",
                        cells=[cell, nb],
                    ))
                elif nb not in cell_line_color:
                    cell_line_color[nb] = color
                    queue.append((nb, color))

        # Check degree constraints
        for cell, neighbors in adj.items():
            degree = len(neighbors)
            is_endpoint = cell in all_endpoints
            if is_endpoint and degree > 1:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Endpoint cell {cell} has {degree} line connections (must be 1)",
                    cells=[cell],
                ))
            elif not is_endpoint and degree > 2:
                violations.append(Violation(
                    rule_id=self.rule_type,
                    message=f"Cell {cell} has {degree} line connections (max 2 for interior cells)",
                    cells=[cell],
                ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "NoLineOverlap":
        return cls()

    def describe(self) -> str:
        return "Lines may not overlap — each cell can belong to at most one line"

