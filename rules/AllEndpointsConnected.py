from rules._common import *

@RuleRegistry.register
class AllEndpointsConnected(Rule):
    """
    For each color_id, every start must be connected via lines to at least one end,
    and every end must be connected to at least one start.
    A 'both' endpoint counts as both a start and an end.
    """
    rule_type = "all_endpoints_connected"
    param_schema = {}

    def check(self, state: "PuzzleState") -> List[Violation]:
        violations: List[Violation] = []
        endpoints_per_color = get_all_endpoints(state)
        if not endpoints_per_color:
            return []

        vertex_graph = build_vertex_line_graph(state)

        for color_id, roles in endpoints_per_color.items():
            starts = roles["start"]
            ends   = roles["end"]
            boths  = roles["both"]
            all_starts = starts + boths
            all_ends   = ends   + boths
            if not all_starts and not all_ends:
                continue

            # Collect seed vertices for all endpoints of this color
            seed_vertices = set()
            for loc in all_starts + all_ends:
                if loc in state.symbols:                # cell endpoint → its four corners
                    r, c = loc
                    seed_vertices.update([(r, c), (r, c+1), (r+1, c), (r+1, c+1)])
                elif loc in state.vertex_symbols:       # vertex endpoint → itself
                    seed_vertices.add(loc)

            # BFS from seed vertices to label connected components
            component_of_vertex: Dict[VertexCoord, int] = {}
            visited = set()
            comp_id = 0

            for vertex in seed_vertices:
                if vertex not in visited:
                    comp_id += 1
                    stack = [vertex]
                    while stack:
                        v = stack.pop()
                        if v in visited:
                            continue
                        visited.add(v)
                        component_of_vertex[v] = comp_id
                        for nb in vertex_graph.get(v, []):
                            if nb not in visited:
                                stack.append(nb)

            # For each component, count how many starts and ends are present
            start_count = defaultdict(int)
            end_count   = defaultdict(int)

            # Helper: get component ids touched by an endpoint
            def comp_ids_of(loc) -> set:
                ids = set()
                if loc in state.symbols:                # cell
                    r, c = loc
                    corners = [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]
                    for v in corners:
                        cid = component_of_vertex.get(v)
                        if cid is not None:
                            ids.add(cid)
                elif loc in state.vertex_symbols:       # vertex
                    cid = component_of_vertex.get(loc)
                    if cid is not None:
                        ids.add(cid)
                return ids

            for loc in all_starts:
                for cid in comp_ids_of(loc):
                    start_count[cid] += 1
            for loc in all_ends:
                for cid in comp_ids_of(loc):
                    end_count[cid] += 1

            # A component is valid if it contains at least one start and one end
            valid_comp = set()
            for cid in range(1, comp_id + 1):
                if start_count.get(cid, 0) > 0 and end_count.get(cid, 0) > 0:
                    valid_comp.add(cid)

            # Check each endpoint
            for loc in all_starts:
                ids = comp_ids_of(loc)
                if not any(cid in valid_comp for cid in ids):
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Color {color_id} start {loc} is not connected to any end.",
                        cells=[loc] if loc in state.symbols else []
                    ))
            for loc in all_ends:
                ids = comp_ids_of(loc)
                if not any(cid in valid_comp for cid in ids):
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Color {color_id} end {loc} is not connected to any start.",
                        cells=[loc] if loc in state.symbols else []
                    ))

        return violations

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "AllEndpointsConnected":
        return cls()

    def describe(self) -> str:
        return "Every start must be connected to at least one end (per color)"