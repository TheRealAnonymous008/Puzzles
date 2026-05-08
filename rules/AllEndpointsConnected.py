from rules._common import *

@RuleRegistry.register
class AllEndpointsConnected(Rule):
    """
    For every color, each start must be connected via lines to at least one end,
    and each end must be connected to at least one start.
    A 'both' endpoint serves as both a start and an end.
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
            # Treat both as both start and end
            all_starts = starts + boths
            all_ends   = ends   + boths
            if not all_starts and not all_ends:
                continue

            # Collect seed vertices for every endpoint of this color
            # We'll need to know which components contain which endpoints.
            # We'll assign a component ID to each vertex via BFS.
            component_of_vertex: Dict[VertexCoord, int] = {}
            component_counter = 0

            # 1) BFS from all seed vertices to label connected components
            seed_vertices = set()
            for loc in all_starts + all_ends:
                if loc in state.symbols:                # cell endpoint
                    r, c = loc
                    seed_vertices.update([(r, c), (r, c+1), (r+1, c), (r+1, c+1)])
                elif loc in state.vertex_symbols:       # vertex endpoint
                    seed_vertices.add(loc)

            # Expand components
            visited_vertices = set()
            for vertex in seed_vertices:
                if vertex not in visited_vertices:
                    component_counter += 1
                    stack = [vertex]
                    while stack:
                        v = stack.pop()
                        if v in visited_vertices:
                            continue
                        visited_vertices.add(v)
                        component_of_vertex[v] = component_counter
                        for nb in vertex_graph.get(v, []):
                            if nb not in visited_vertices:
                                stack.append(nb)

            # For each component, count starts and ends
            start_count_per_comp = defaultdict(int)
            end_count_per_comp   = defaultdict(int)

            for loc in all_starts:
                comp_ids = self._get_component_ids(loc, state, component_of_vertex)
                for cid in comp_ids:
                    start_count_per_comp[cid] += 1

            for loc in all_ends:
                comp_ids = self._get_component_ids(loc, state, component_of_vertex)
                for cid in comp_ids:
                    end_count_per_comp[cid] += 1

            # A component is valid if it has at least one start and one end
            valid_comp = set()
            for cid in range(1, component_counter + 1):
                if start_count_per_comp.get(cid, 0) > 0 and end_count_per_comp.get(cid, 0) > 0:
                    valid_comp.add(cid)

            # Check each endpoint: it must belong to at least one valid component
            for loc in all_starts:
                comp_ids = self._get_component_ids(loc, state, component_of_vertex)
                if not any(cid in valid_comp for cid in comp_ids):
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Color {color_id} start {loc} is not connected to any end.",
                        cells=[loc] if loc in state.symbols else []
                    ))

            for loc in all_ends:
                comp_ids = self._get_component_ids(loc, state, component_of_vertex)
                if not any(cid in valid_comp for cid in comp_ids):
                    violations.append(Violation(
                        rule_id=self.rule_type,
                        message=f"Color {color_id} end {loc} is not connected to any start.",
                        cells=[loc] if loc in state.symbols else []
                    ))

        return violations

    def _get_component_ids(self, loc, state, component_of_vertex: Dict[VertexCoord, int]) -> Set[int]:
        """
        Return the set of component ids that are reachable from the given endpoint
        through its adjacent vertices.
        """
        comp_ids = set()
        if loc in state.symbols:            # cell endpoint
            r, c = loc
            corners = [(r, c), (r, c+1), (r+1, c), (r+1, c+1)]
            for v in corners:
                cid = component_of_vertex.get(v)
                if cid is not None:
                    comp_ids.add(cid)
        elif loc in state.vertex_symbols:   # vertex endpoint
            cid = component_of_vertex.get(loc)
            if cid is not None:
                comp_ids.add(cid)
        return comp_ids

    def to_params(self) -> dict:
        return {}

    @classmethod
    def from_params(cls, params: dict) -> "AllEndpointsConnected":
        return cls()

    def describe(self) -> str:
        return "Every start must be connected to at least one end (per color)"