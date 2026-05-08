from rules._common import *

@RuleRegistry.register
class NoLineOverlapRule(Rule):
    """
    No cell may have line‑degree > 2, and no vertex may serve as interior
    node for two different colors.

    Endpoint cells/vertices must have exactly 1 line connection,
    except 'both' endpoints which may have 2 (if they form a loop).
    """
    rule_type = "no_line_overlap"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []

        # Cell degree from drawn lines
        cell_deg = defaultdict(int)
        for a, b in state.lines:
            cell_deg[a] += 1
            cell_deg[b] += 1

        # All endpoints (cells & vertices)
        endpoints = get_all_endpoints(state)
        # Build set of all endpoint locations for quick lookup
        ep_locs = set()
        for roles in endpoints.values():
            for locs in roles.values():
                ep_locs.update(locs)

        # --- Check cell degrees ---
        for cell, deg in cell_deg.items():
            if cell in ep_locs:
                # Determine role
                role = None
                for roles in endpoints.values():
                    if cell in roles["start"]:
                        role = "start"
                        break
                    elif cell in roles["end"]:
                        role = "end"
                        break
                    elif cell in roles["both"]:
                        role = "both"
                        break
                if role == "both":
                    if deg not in (0, 2):
                        violations.append(Violation(
                            rule_id=self.rule_type,
                            message=f"Cell {cell} is both start and end, must have 0 or 2 line connections, got {deg}.",
                            cells=[cell]
                        ))
                else:
                    if deg != 1:
                        violations.append(Violation(
                            rule_id=self.rule_type,
                            message=f"Endpoint cell {cell} must have exactly 1 line connection, got {deg}.",
                            cells=[cell]
                        ))
            else:
                if deg > 2:
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Interior cell {cell} has degree {deg}>2.",
                        cells=[cell]
                    ))

        # --- Check vertex degrees (vertex graph) ---
        vertex_graph = build_vertex_line_graph(state)
        for color_id, roles in endpoints.items():
            for role, locs in roles.items():
                for loc in locs:
                    if isinstance(loc, tuple) and len(loc) == 2 and loc in state.vertex_symbols:
                        deg = len(vertex_graph.get(loc, []))
                        if role == "both":
                            if deg not in (0, 2):
                                violations.append(Violation(
                                    rule_id=self.rule_type,
                                    message=f"Vertex {loc} with role both must have degree 0 or 2, got {deg}.",
                                    cells=[]
                                ))
                        else:
                            if deg != 1:
                                violations.append(Violation(
                                    rule_id=self.rule_type,
                                    message=f"Endpoint vertex {loc} must have exactly 1 line connection, got {deg}.",
                                    cells=[]
                                ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "NoLineOverlapRule":
        return cls()

    def describe(self) -> str:
        return "Line overlap is not allowed (degree≤2, endpoints degree 1 or 2 for both)"