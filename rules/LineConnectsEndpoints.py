from rules._common import *

@RuleRegistry.register
class LineConnectsEndpointsRule(Rule):
    """
    For each color_id, all start and end points must be connected via lines.
    A 'both' endpoint counts as start and end; it must lie on a cycle that
    returns to itself.
    """
    rule_type = "line_connects_endpoints"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations = []
        endpoints = get_all_endpoints(state)
        vertex_graph = build_vertex_line_graph(state)

        for color_id, roles in endpoints.items():
            starts = roles["start"] + roles["both"]
            ends   = roles["end"]   + roles["both"]
            if not starts and not ends:
                continue

            # Collect all vertices that are "seeded" by this color's endpoints.
            # For a cell endpoint, its four corner vertices are added.
            seed_vertices = set()
            for loc in starts + ends:
                if isinstance(loc, tuple) and len(loc) == 2:
                    if loc in state.symbols:            # cell endpoint
                        r, c = loc
                        seed_vertices.update([(r, c), (r, c+1), (r+1, c), (r+1, c+1)])
                    elif loc in state.vertex_symbols:   # vertex endpoint
                        seed_vertices.add(loc)

            # BFS over the vertex graph starting from all seed vertices
            visited = set()
            stack = list(seed_vertices)
            while stack:
                v = stack.pop()
                if v in visited:
                    continue
                visited.add(v)
                for nb in vertex_graph.get(v, []):
                    if nb not in visited:
                        stack.append(nb)

            # Every endpoint must be reachable via at least one of its associated vertices
            for loc in starts + ends:
                if isinstance(loc, tuple) and len(loc) == 2:
                    if loc in state.symbols:            # cell endpoint
                        r, c = loc
                        corners = [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]
                        if not any(v in visited for v in corners):
                            violations.append(Violation(
                                rule_id=self.rule_type,
                                message=f"Color {color_id} endpoint {loc} is not connected.",
                                cells=[loc]
                            ))
                    elif loc in state.vertex_symbols:   # vertex endpoint
                        if loc not in visited:
                            violations.append(Violation(
                                rule_id=self.rule_type,
                                message=f"Color {color_id} vertex endpoint {loc} is not connected.",
                                cells=[]
                            ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "LineConnectsEndpointsRule":
        return cls()

    def describe(self) -> str:
        return "All endpoints of the same color must be connected by lines."